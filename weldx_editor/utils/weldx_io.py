"""
WeldX File I/O Utilities
Handles reading and writing WeldX/ASDF files and extracting/injecting data.

Adapted to the real RoboScope WeldX export structure:
  tree:
    data:              # time series (welding_current, welding_voltage, wire_speed, gas_flow)
      <name>:
        values: ndarray
        time: {values: ...}
        units: str
        shape: [N]
        interpolation: str
    equipment:         # measurement chains (current_measurement, voltage_measurement)
      <name>:
        name: str
        data_source: {name, output_signal, error}
        graph: {root_node: ...}
        source_equipment: {name, sources, transformations}
    metadata:
      roboscope: {operator, material, job_part, source_format, ...}
    process:
      shielding_gas: {torch_shielding_gas: {common_name, gas_component}, torch_shielding_gas_flowrate}
      welding_process: {tag, base_process, manufacturer, power_source, parameters}
"""
import io
import tempfile
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime

import numpy as np
import pandas as pd

try:
    import weldx
    from weldx import WeldxFile
    WELDX_AVAILABLE = True
except ImportError:
    WELDX_AVAILABLE = False


def _safe_float(val) -> float:
    """Convert a scalar, 0-d or 1-element array/Quantity to Python float."""
    if hasattr(val, "magnitude"):
        val = val.magnitude
    if isinstance(val, np.ndarray):
        return float(val.flat[0]) if val.size > 0 else 0.0
    return float(val)


@dataclass
class WeldxFileState:
    """Holds the complete state of a WeldX file being edited."""

    file_path: Optional[str] = None
    wx_file: Any = None
    tree: dict = field(default_factory=dict)

    # Extracted data categories
    measurements: dict = field(default_factory=dict)       # time series from data.*
    equipment: dict = field(default_factory=dict)           # measurement chains from equipment.*
    coordinate_systems: dict = field(default_factory=dict)
    _csm: Any = None                                          # weldx CoordinateSystemManager (if available)
    workpiece_meshes: list = field(default_factory=list)       # list of {vertices, triangles} dicts
    groove: Any = None
    base_metal: dict = field(default_factory=dict)
    shielding_gas: dict = field(default_factory=dict)       # extracted from process.shielding_gas
    process: dict = field(default_factory=dict)             # extracted from process.welding_process
    filler_material: dict = field(default_factory=dict)
    quality: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)            # from metadata.roboscope + top-level

    # Completion tracking
    completion: dict = field(default_factory=lambda: {
        "workpiece": {"status": "missing", "detail": ""},
        "process": {"status": "missing", "detail": ""},
        "measurements": {"status": "missing", "detail": ""},
        "coordinates": {"status": "missing", "detail": ""},
        "quality": {"status": "missing", "detail": ""},
    })

    def overall_completion_pct(self) -> int:
        status_values = {"complete": 1.0, "partial": 0.5, "missing": 0.0}
        total = sum(status_values.get(v["status"], 0) for v in self.completion.values())
        return int(total / len(self.completion) * 100)


# ─── Loading ─────────────────────────────────────────────────

def load_weldx_file(file_path: str) -> WeldxFileState:
    """Load a WeldX file and extract all data into a WeldxFileState."""
    if not WELDX_AVAILABLE:
        raise ImportError("weldx package is not installed")

    state = WeldxFileState(file_path=file_path)
    wx = WeldxFile(file_path, mode="r")
    state.wx_file = wx
    state.tree = dict(wx)

    _extract_measurements(state)
    _extract_equipment(state)
    _extract_coordinate_systems(state)
    _extract_groove(state)
    _extract_process(state)
    _extract_metadata(state)
    _extract_quality(state)
    _update_completion(state)

    return state


def load_weldx_from_bytes(file_bytes: bytes, filename: str) -> WeldxFileState:
    """Load a WeldX file from uploaded bytes.

    The uploaded file is persisted in a stable cache directory so that it
    survives browser reloads (the session restore logic re-opens the file
    by its path).
    """
    if not WELDX_AVAILABLE:
        raise ImportError("weldx package is not installed")

    cache_dir = Path(__file__).resolve().parent.parent.parent / ".weldx_cache"
    cache_dir.mkdir(exist_ok=True)
    cached_path = cache_dir / Path(filename).name
    cached_path.write_bytes(file_bytes)

    try:
        state = load_weldx_file(str(cached_path))
        return state
    except Exception:
        cached_path.unlink(missing_ok=True)
        raise


# ─── Extraction: Time Series (data.*) ───────────────────────

def _extract_measurements(state: WeldxFileState):
    """Extract time series from tree['data'] and/or tree['measurements']."""
    tree = state.tree

    # RoboScope: time series under "data"
    if "data" in tree and isinstance(tree["data"], dict):
        for name, ts in tree["data"].items():
            if name not in state.measurements:
                state.measurements[name] = _describe_time_series(name, ts)

    # Native weldx: "measurements" as list of Measurement objects
    if "measurements" in tree and isinstance(tree["measurements"], list):
        for meas in tree["measurements"]:
            meas_name = getattr(meas, "name", None) or str(meas)
            # Measurement.data is a list of TimeSeries
            ts_list = getattr(meas, "data", None)
            if isinstance(ts_list, list) and ts_list:
                ts = ts_list[0]
            else:
                ts = ts_list
            key = meas_name.replace(" ", "_")
            if key in state.measurements:
                continue
            info = _describe_time_series(meas_name, ts)
            mc = getattr(meas, "measurement_chain", None)
            if mc is not None:
                info["_measurement_chain"] = mc
                info["chain"] = _describe_measurement_chain(mc)
            state.measurements[key] = info

    if state.measurements:
        return

    # Fallback: "measurements" as dict (keyed by name)
    for key in ["measurements", "measurement_data"]:
        if key in tree and isinstance(tree[key], dict):
            for name, ts in tree[key].items():
                state.measurements[name] = _describe_time_series(name, ts)
            return

    # Fallback: individual known keys at top level
    for key in ["welding_current", "welding_voltage", "wire_feed_speed",
                "wire_speed", "gas_flow", "weld_speed", "heat_input"]:
        if key in tree:
            state.measurements[key] = _describe_time_series(key, tree[key])


def _describe_time_series(name: str, value: Any) -> dict:
    """Extract info + data array from a time series (dict or weldx object)."""
    info = {"name": name, "status": "present", "type": type(value).__name__}

    try:
        arr = None
        unit = ""

        # RoboScope dict format: {values: ndarray, units: str, time: {...}, ...}
        if isinstance(value, dict):
            if "values" in value:
                arr = np.asarray(value["values"]).flatten()
            if "units" in value:
                unit = str(value["units"])
            if "shape" in value and isinstance(value["shape"], list):
                info["samples"] = int(value["shape"][0])
            if "interpolation" in value:
                info["interpolation"] = str(value["interpolation"])
            # Extract time info
            if "time" in value and isinstance(value["time"], dict):
                time_d = value["time"]
                if "values" in time_d and isinstance(time_d["values"], dict):
                    tv = time_d["values"]
                    info["time_start"] = str(tv.get("start", ""))
                    info["time_end"] = str(tv.get("end", ""))

        # weldx TimeSeries object
        elif hasattr(value, "data"):
            data = value.data
            if hasattr(data, "magnitude"):
                arr = np.asarray(data.magnitude).flatten()
            elif hasattr(data, "values"):
                arr = np.asarray(data.values).flatten()
            elif isinstance(data, np.ndarray):
                arr = data.flatten()
            if hasattr(data, "units"):
                unit = str(data.units)

            # Extract time axis from weldx TimeSeries
            ts_time = getattr(value, "time", None)
            if ts_time is not None:
                try:
                    import weldx as _wx
                    tq = _wx.Time(ts_time).as_quantity()
                    t_seconds = np.asarray(tq.magnitude).flatten()
                    info["time_seconds"] = t_seconds
                    info["time_start"] = f"{t_seconds[0]:.3f}s"
                    info["time_end"] = f"{t_seconds[-1]:.3f}s"
                except Exception:
                    pass

        # weldx TimeSeries with data_array
        if arr is None and hasattr(value, "data_array"):
            da = value.data_array
            arr = np.asarray(da.values).flatten()
            if hasattr(da, "pint") and hasattr(da.pint, "units"):
                unit = str(da.pint.units)

        # Plain numpy array
        if arr is None and isinstance(value, (np.ndarray, list)):
            arr = np.asarray(value).flatten()

        if arr is not None and len(arr) > 0:
            info["samples"] = int(len(arr))
            info["unit"] = unit
            info["values_raw"] = arr

            # Outlier detection using IQR method
            q1 = float(np.nanpercentile(arr, 1))
            q99 = float(np.nanpercentile(arr, 99))
            iqr = q99 - q1
            lower_bound = q1 - 5 * iqr
            upper_bound = q99 + 5 * iqr

            outlier_mask = (arr < lower_bound) | (arr > upper_bound)
            n_outliers = int(np.sum(outlier_mask))

            if n_outliers > 0 and n_outliers < len(arr) * 0.5:
                # Replace outliers with NaN for clean visualization
                arr_clean = arr.astype(float).copy()
                arr_clean[outlier_mask] = np.nan
                info["values"] = arr_clean
                info["outliers_removed"] = n_outliers
                info["min"] = float(np.nanmin(arr_clean))
                info["max"] = float(np.nanmax(arr_clean))
            else:
                info["values"] = arr
                info["outliers_removed"] = 0
                info["min"] = float(np.nanmin(arr))
                info["max"] = float(np.nanmax(arr))

            info["range"] = f"{info['min']:.2f} – {info['max']:.2f}"
        elif unit:
            info["unit"] = unit

    except Exception as e:
        info["extraction_error"] = str(e)

    return info


def _describe_measurement_chain(mc) -> dict:
    """Extract full measurement chain details from a weldx MeasurementChain."""
    result = {
        "name": getattr(mc, "_name", ""),
        "steps": [],
    }

    # Source sensor
    src = getattr(mc, "_source", None)
    if src is not None:
        src_info = {
            "name": getattr(src, "name", ""),
            "signal_type": getattr(getattr(src, "output_signal", None), "signal_type", ""),
            "signal_unit": str(getattr(getattr(src, "output_signal", None), "units", "")),
        }
        err = getattr(src, "error", None)
        if err is not None:
            dev = getattr(err, "deviation", None)
            if dev is not None:
                src_info["error"] = str(dev)
        result["source"] = src_info

    # Source equipment
    src_eq = getattr(mc, "_source_equipment", None)
    if src_eq is not None:
        result["source_equipment"] = getattr(src_eq, "name", "")

    # Walk the chain graph: nodes (signal stages) and edges (transformations)
    g = getattr(mc, "_graph", None)
    if g is None:
        return result

    # Build ordered step list by following edges from source
    visited = set()
    node_order = []

    def walk(node):
        if node in visited:
            return
        visited.add(node)
        node_order.append(node)
        for _, successor in g.out_edges(node):
            walk(successor)

    # Start from the source node
    src_name = getattr(src, "name", "") if src is not None else ""
    if src_name in g.nodes:
        walk(src_name)
    else:
        # Fallback: use topological order
        try:
            import networkx as nx
            node_order = list(nx.topological_sort(g))
        except Exception:
            node_order = list(g.nodes)

    # Extract each step
    for i, node_name in enumerate(node_order):
        node_data = g.nodes.get(node_name, {})
        sig = node_data.get("signal")

        step = {
            "name": node_name,
            "signal_type": getattr(sig, "signal_type", "") if sig else "",
            "signal_unit": str(getattr(sig, "units", "")) if sig else "",
        }

        # Find the outgoing transformation edge
        for _, target, edge_data in g.out_edges(node_name, data=True):
            trafo = edge_data.get("transformation")
            eq = edge_data.get("equipment")

            if trafo is not None:
                t_info = {"name": getattr(trafo, "name", "")}

                # Transformation type (AD, calibration, etc.)
                t_type = getattr(trafo, "type_transformation", None)
                if t_type:
                    t_info["type"] = str(t_type)

                # Error
                t_err = getattr(trafo, "error", None)
                if t_err is not None:
                    dev = getattr(t_err, "deviation", None)
                    if dev is not None:
                        t_info["error"] = str(dev)

                # Mathematical function
                func = getattr(trafo, "func", None)
                if func is not None:
                    t_info["expression"] = str(getattr(func, "expression", ""))
                    params = getattr(func, "parameters", {})
                    if isinstance(params, dict):
                        t_info["parameters"] = {k: str(v) for k, v in params.items()}

                # Equipment
                if eq is not None:
                    t_info["equipment"] = getattr(eq, "name", "")

                # Software meta
                meta = getattr(trafo, "meta", None)
                if isinstance(meta, dict) and "name" in meta:
                    t_info["software"] = f"{meta['name']} {meta.get('version', '')}"

                step["transformation"] = t_info

        result["steps"].append(step)

    return result


# ─── Extraction: Equipment / Measurement Chains ─────────────

def _extract_equipment(state: WeldxFileState):
    """Extract measurement equipment and chains from tree['equipment']."""
    tree = state.tree

    if "equipment" not in tree:
        # Native weldx: equipment may be embedded in measurement chains
        # Try to extract from measurements that carry _measurement_chain
        for mkey, minfo in state.measurements.items():
            mc = minfo.pop("_measurement_chain", None)
            if mc is None:
                continue
            src_eq = getattr(mc, "_source_equipment", None) or getattr(mc, "source_equipment", None)
            if src_eq is not None:
                eq_name = getattr(src_eq, "name", mkey)
                eq_info = {"name": eq_name, "key": eq_name.replace(" ", "_")}
                sources = getattr(src_eq, "sources", [])
                eq_info["sources"] = []
                for src in sources:
                    src_entry = {"name": getattr(src, "name", "")}
                    sig = getattr(src, "output_signal", None)
                    if sig is not None:
                        src_entry["signal_type"] = getattr(sig, "signal_type", "")
                        src_entry["signal_unit"] = str(getattr(sig, "units", ""))
                    err = getattr(src, "error", None)
                    if err is not None:
                        dev = getattr(err, "deviation", None)
                        if dev is not None and hasattr(dev, "magnitude"):
                            src_entry["error_value"] = _safe_float(dev)
                            src_entry["error_unit"] = str(dev.units)
                    eq_info["sources"].append(src_entry)
                eq_info["has_chain"] = True
                state.equipment[eq_info["key"]] = eq_info
        return

    raw_eq = tree["equipment"]

    # Native weldx: equipment as list of MeasurementEquipment objects
    if isinstance(raw_eq, list):
        for eq in raw_eq:
            eq_name = getattr(eq, "name", None)
            if eq_name is None:
                eq_name = str(eq)
            key = eq_name.replace(" ", "_")
            eq_info = {"name": eq_name, "key": key}

            sources = getattr(eq, "sources", [])
            eq_info["sources"] = []
            for src in sources:
                src_entry = {"name": getattr(src, "name", "")}
                sig = getattr(src, "output_signal", None)
                if sig is not None:
                    src_entry["signal_type"] = getattr(sig, "signal_type", "")
                    src_entry["signal_unit"] = str(getattr(sig, "units", ""))
                err = getattr(src, "error", None)
                if err is not None:
                    dev = getattr(err, "deviation", None)
                    if dev is not None and hasattr(dev, "magnitude"):
                        src_entry["error_value"] = _safe_float(dev)
                        src_entry["error_unit"] = str(dev.units)
                eq_info["sources"].append(src_entry)

            transformations = getattr(eq, "transformations", [])
            eq_info["has_chain"] = bool(sources or transformations)
            state.equipment[key] = eq_info
        # Also clean up _measurement_chain refs from measurements
        for minfo in state.measurements.values():
            minfo.pop("_measurement_chain", None)
        return

    # RoboScope: equipment as dict
    if not isinstance(raw_eq, dict):
        return

    for name, eq in raw_eq.items():
        if not isinstance(eq, dict):
            continue

        eq_info = {
            "name": eq.get("name", name),
            "key": name,
        }

        # Data source (sensor info)
        ds = eq.get("data_source", {})
        if isinstance(ds, dict):
            eq_info["sensor_name"] = ds.get("name", "")
            out_sig = ds.get("output_signal", {})
            if isinstance(out_sig, dict):
                eq_info["signal_type"] = out_sig.get("signal_type", "")
                eq_info["signal_unit"] = str(out_sig.get("units", ""))
            err = ds.get("error", {})
            if isinstance(err, dict):
                dev = err.get("deviation", {})
                if isinstance(dev, dict):
                    eq_info["error_value"] = dev.get("value", "")
                    eq_info["error_unit"] = str(dev.get("units", ""))

        # Source equipment
        se = eq.get("source_equipment", {})
        if isinstance(se, dict):
            eq_info["equipment_name"] = se.get("name", "")
            sources = se.get("sources", [])
            eq_info["sources"] = []
            for src in sources:
                if isinstance(src, dict):
                    eq_info["sources"].append({
                        "name": src.get("name", ""),
                        "signal": src.get("output_signal", {}),
                        "error": src.get("error", {}),
                    })

        # Measurement chain graph
        graph = eq.get("graph", {})
        if isinstance(graph, dict):
            eq_info["has_chain"] = True
            chain_steps = _parse_chain_graph(graph)
            eq_info["chain_steps"] = chain_steps

        state.equipment[name] = eq_info


def _parse_chain_graph(graph: dict) -> list:
    """Parse a measurement chain graph into a list of steps."""
    steps = []
    root = graph.get("root_node", {})
    if not isinstance(root, dict):
        return steps

    def walk(node, depth=0):
        if not isinstance(node, dict) or depth > 10:
            return
        step = {
            "name": node.get("name", "?"),
            "depth": depth,
        }
        attrs = node.get("attributes", {})
        if isinstance(attrs, dict) and "signal" in attrs:
            sig = attrs["signal"]
            if isinstance(sig, dict):
                step["signal_type"] = sig.get("signal_type", "")
                step["signal_unit"] = str(sig.get("units", ""))
        steps.append(step)

        for edge in node.get("edges", []):
            if isinstance(edge, dict):
                target = edge.get("target_node", {})
                walk(target, depth + 1)

    walk(root)
    return steps


# ─── Extraction: Coordinate Systems ─────────────────────────

def _extract_coordinate_systems(state: WeldxFileState):
    tree = state.tree
    for key in ["coordinate_systems", "csm", "coordinate_system_manager"]:
        if key in tree:
            csm = tree[key]
            if hasattr(csm, "coordinate_system_names"):
                # Native weldx CoordinateSystemManager
                state._csm = csm
                _extract_cs_from_csm(csm, state)
            elif isinstance(csm, dict):
                # Native weldx dict with graph structure — walk nodes to find CS names
                graph = csm.get("graph")
                if graph is not None:
                    _walk_cs_graph(graph, state.coordinate_systems)
                if not state.coordinate_systems:
                    # Flat dict fallback (keys = CS names)
                    for name in csm:
                        if name not in ("name", "reference_time", "graph", "subsystems"):
                            state.coordinate_systems[name] = {"name": name, "status": "complete"}
            break


def _extract_cs_from_csm(csm, state: WeldxFileState):
    """Extract coordinate system data from a weldx CoordinateSystemManager."""
    import warnings

    names = list(csm.coordinate_system_names)

    # Determine root node
    root = getattr(csm, "root_system_name", None)
    if root is None and names:
        root = names[0]

    # Build parent map from defined graph edges
    parent_map = {}
    if hasattr(csm, "graph"):
        g = csm.graph
        for u, v, data in g.edges(data=True):
            if data.get("defined", False) and v not in parent_map:
                parent_map[v] = u

    for name in names:
        cs_info = {"name": name, "status": "complete", "parent": parent_map.get(name)}

        if name == root:
            cs_info["translation"] = {"x": 0.0, "y": 0.0, "z": 0.0}
            cs_info["orientation"] = np.eye(3).tolist()
            cs_info["is_root"] = True
            state.coordinate_systems[name] = cs_info
            continue

        # Get CS relative to root for absolute positioning
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                lcs = csm.get_cs(name, root)

            coords = lcs.coordinates.values
            if hasattr(coords, "magnitude"):
                coords = coords.magnitude

            orient = lcs.orientation.values

            if lcs.is_time_dependent:
                cs_info["is_time_dependent"] = True
                # Store first-timepoint position for static display
                c0 = coords[0] if coords.ndim > 1 else coords
                o0 = orient[0] if orient.ndim > 2 else orient
                cs_info["translation"] = {"x": float(c0[0]), "y": float(c0[1]), "z": float(c0[2])}
                cs_info["orientation"] = o0.tolist()
                # Store full trajectory for TCP path visualization
                if coords.ndim > 1 and coords.shape[0] > 1:
                    cs_info["trajectory"] = coords
            else:
                cs_info["translation"] = {"x": float(coords[0]), "y": float(coords[1]), "z": float(coords[2])}
                cs_info["orientation"] = orient.tolist()
        except Exception:
            cs_info["translation"] = {"x": 0.0, "y": 0.0, "z": 0.0}
            cs_info["orientation"] = np.eye(3).tolist()

        state.coordinate_systems[name] = cs_info

    # Extract workpiece mesh data (3D scan surfaces)
    _extract_workpiece_meshes(csm, root, state)


def _extract_workpiece_meshes(csm, root: str, state: WeldxFileState):
    """Extract 3D mesh data from workpiece scan nodes in the CSM graph."""
    import warnings

    if not hasattr(csm, "graph"):
        return
    g = csm.graph

    # Look for nodes with spatial data (scan_0, scan_1, ...)
    for node_name in csm.coordinate_system_names:
        node_data = g.nodes.get(node_name, {}).get("data", {})
        if not isinstance(node_data, dict):
            continue

        for scan_name, scan_obj in node_data.items():
            if not hasattr(scan_obj, "coordinates") or not hasattr(scan_obj, "triangles"):
                continue

            try:
                # Get vertices (raw, in node CS)
                verts = scan_obj.coordinates
                if hasattr(verts, "magnitude"):
                    verts = verts.magnitude
                elif hasattr(verts, "values"):
                    verts = verts.values
                raw_verts = np.asarray(verts)

                # Get triangles
                tris = scan_obj.triangles
                if hasattr(tris, "values"):
                    tris = tris.values
                tris = np.asarray(tris)

                # Transform vertices from node CS to root CS for visualization
                viz_verts = raw_verts
                if node_name != root:
                    try:
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            lcs = csm.get_cs(node_name, root)
                        coords = lcs.coordinates.values
                        if hasattr(coords, "magnitude"):
                            coords = coords.magnitude
                        orient = lcs.orientation.values
                        R = orient[0] if orient.ndim > 2 else orient
                        t = coords[0] if coords.ndim > 1 else coords
                        viz_verts = raw_verts @ R.T + t
                    except Exception:
                        pass

                state.workpiece_meshes.append({
                    "name": f"{node_name}/{scan_name}",
                    "scan_name": scan_name,
                    "target_cs": node_name,
                    "vertices": viz_verts,
                    "raw_vertices": raw_verts,
                    "triangles": tris,
                    "visible": True,
                })
            except Exception:
                continue


def _walk_cs_graph(graph, cs_dict: dict):
    """Walk a coordinate system graph (di_graph) and collect node names."""
    root = graph if not isinstance(graph, dict) else graph.get("root_node")
    if root is None:
        return

    def walk(node, visited=None):
        if visited is None:
            visited = set()
        if not isinstance(node, dict) or id(node) in visited:
            return
        visited.add(id(node))

        name = node.get("name")
        if name and name not in cs_dict:
            cs_dict[name] = {"name": name, "status": "present"}

        for edge in node.get("edges", []):
            if isinstance(edge, dict):
                target = edge.get("target_node")
                if target is not None:
                    walk(target, visited)

    walk(root)


# ─── Extraction: Groove ──────────────────────────────────────

def _extract_groove(state: WeldxFileState):
    tree = state.tree

    # Direct groove key
    if "groove" in tree:
        state.groove = tree["groove"]
        return

    # Workpiece with nested groove
    wp = tree.get("workpiece")
    if wp is not None:
        if isinstance(wp, dict):
            if "groove" in wp:
                state.groove = wp["groove"]
                return
            # Native weldx: workpiece.geometry.groove_shape
            geom = wp.get("geometry")
            if isinstance(geom, dict):
                groove_obj = geom.get("groove_shape")
                if groove_obj is not None:
                    state.groove = _groove_obj_to_dict(groove_obj)
                    return
            elif geom is not None and hasattr(geom, "groove_shape"):
                state.groove = _groove_obj_to_dict(geom.groove_shape)
                return
        elif hasattr(wp, "geometry"):
            geom = wp.geometry
            if hasattr(geom, "groove_shape"):
                state.groove = _groove_obj_to_dict(geom.groove_shape)
                return

    # Joint / weld_joint fallback
    for key in ["joint", "weld_joint"]:
        if key in tree:
            val = tree[key]
            if isinstance(val, dict) and "groove" in val:
                state.groove = val["groove"]
            else:
                state.groove = val
            return


_GROOVE_CLASS_TO_EDITOR = {
    "VGroove":   "V-Naht",
    "IGroove":   "I-Naht",
    "HVGroove":  "HV-Naht",
    "UGroove":   "U-Naht",
    "HUGroove":  "HU-Naht",
    "VVGroove":  "VV-Naht (V + HV)",
    "UVGroove":  "UV-Naht (U + HV)",
    "DVGroove":  "X-Naht (Doppel-V)",
    "DHVGroove": "Doppel-HV-Naht",
    "DUGroove":  "Doppel-U-Naht",
    "DHUGroove": "Doppel-HU-Naht",
    "FFGroove":  "Bördelnaht",  # or Kehlnaht — resolved by code_number in _groove_obj_to_dict
}


def _groove_obj_to_dict(groove_obj) -> dict:
    """Convert a weldx groove object (VGroove, etc.) to a dict for the editor."""
    class_name = type(groove_obj).__name__  # e.g. "VGroove", "IGroove"
    groove_type = _GROOVE_CLASS_TO_EDITOR.get(class_name, class_name)

    # FFGroove: distinguish Bördelnaht vs Kehlnaht by code_number
    if class_name == "FFGroove":
        code = getattr(groove_obj, "code_number", ["1.12"])
        if isinstance(code, list):
            code = code[0] if code else "1.12"
        if code.startswith(("3.", "4.")):
            groove_type = "Kehlnaht"
        else:
            groove_type = "Bördelnaht"

    result = {"type": groove_type}
    params = {}

    # Try .parameters() method first (returns dict of Quantity values)
    if hasattr(groove_obj, "parameters") and callable(groove_obj.parameters):
        try:
            for pname, pval in groove_obj.parameters().items():
                if hasattr(pval, "magnitude"):
                    params[pname] = _safe_float(pval)
                else:
                    params[pname] = pval
            result["params"] = params
            # Preserve code_number for FFGroove
            if class_name == "FFGroove":
                code = getattr(groove_obj, "code_number", None)
                if isinstance(code, list):
                    code = code[0] if code else None
                if code:
                    params["code_number"] = code
            return result
        except Exception:
            pass

    # Fallback: read known attributes directly
    for attr in ("t", "t_1", "t_2", "alpha", "b", "c", "e",
                 "beta", "R", "R2", "h", "h1", "h2",
                 "alpha_1", "alpha_2", "beta_1", "beta_2"):
        val = getattr(groove_obj, attr, None)
        if val is not None:
            if hasattr(val, "magnitude"):
                params[attr] = _safe_float(val)
            else:
                params[attr] = val
    if params:
        result["params"] = params
    return result


# ─── Extraction: Process (welding_process + shielding_gas) ──

def _extract_process(state: WeldxFileState):
    """Extract from tree['process'] — supports RoboScope dicts and native weldx objects."""
    tree = state.tree

    process_root = None
    for key in ["process", "welding_process", "weld_process"]:
        if key in tree:
            process_root = tree[key]
            break

    if process_root is None:
        return

    if not isinstance(process_root, dict):
        state.process = {"raw": process_root}
        return

    # --- Shielding gas ---
    sg = process_root.get("shielding_gas")
    if sg is not None:
        gas_info = {}

        if isinstance(sg, dict):
            # RoboScope dict format
            tsg = sg.get("torch_shielding_gas", {})
            if isinstance(tsg, dict):
                gas_info["common_name"] = tsg.get("common_name", "")
                components = tsg.get("gas_component", [])
                gas_info["components"] = []
                for comp in (components if isinstance(components, list) else []):
                    if isinstance(comp, dict):
                        pct = comp.get("gas_percentage", {})
                        pct_val = pct.get("value", "") if isinstance(pct, dict) else pct
                        gas_info["components"].append({
                            "name": comp.get("gas_chemical_name", ""),
                            "percentage": pct_val,
                        })

            flowrate = sg.get("torch_shielding_gas_flowrate", {})
            if isinstance(flowrate, dict):
                gas_info["flowrate_value"] = flowrate.get("value", "")
                gas_info["flowrate_unit"] = str(flowrate.get("units", ""))

            gas_info["use_torch"] = sg.get("use_torch_shielding_gas", None)
        else:
            # Native weldx ShieldingGasForProcedure object
            gas_info["use_torch"] = getattr(sg, "use_torch_shielding_gas", None)
            tsg = getattr(sg, "torch_shielding_gas", None)
            if tsg is not None:
                gas_info["common_name"] = getattr(tsg, "common_name", "")
                gas_comps = getattr(tsg, "gas_component", [])
                gas_info["components"] = []
                for comp in (gas_comps if isinstance(gas_comps, list) else []):
                    pct = getattr(comp, "gas_percentage", None)
                    if pct is not None and hasattr(pct, "magnitude"):
                        pct_val = _safe_float(pct)
                    elif pct is not None:
                        pct_val = pct
                    else:
                        pct_val = ""
                    gas_info["components"].append({
                        "name": getattr(comp, "gas_chemical_name", ""),
                        "percentage": pct_val,
                    })

            flowrate = getattr(sg, "torch_shielding_gas_flowrate", None)
            if flowrate is not None:
                if hasattr(flowrate, "magnitude"):
                    gas_info["flowrate_value"] = _safe_float(flowrate)
                    gas_info["flowrate_unit"] = str(flowrate.units)
                elif isinstance(flowrate, dict):
                    gas_info["flowrate_value"] = flowrate.get("value", "")
                    gas_info["flowrate_unit"] = str(flowrate.get("units", ""))

        state.shielding_gas = gas_info

    # --- Welding process ---
    wp = process_root.get("welding_process")
    if wp is not None:
        if isinstance(wp, dict):
            # RoboScope dict format
            state.process = {
                "tag": wp.get("tag", ""),
                "base_process": wp.get("base_process", ""),
                "manufacturer": wp.get("manufacturer", ""),
                "power_source": wp.get("power_source", ""),
            }
        elif hasattr(wp, "tag"):
            # Native weldx GmawProcess / similar object
            state.process = {
                "tag": getattr(wp, "tag", ""),
                "base_process": getattr(wp, "base_process", ""),
                "manufacturer": getattr(wp, "manufacturer", ""),
                "power_source": getattr(wp, "power_source", ""),
            }
            # Extract process parameters (TimeSeries values)
            params = getattr(wp, "parameters", None)
            if isinstance(params, dict):
                proc_params = {}
                for pname, pval in params.items():
                    if hasattr(pval, "data") and hasattr(pval.data, "magnitude"):
                        proc_params[pname] = {
                            "value": _safe_float(pval.data),
                            "unit": str(pval.data.units),
                        }
                    elif hasattr(pval, "value"):
                        proc_params[pname] = {"value": pval.value, "unit": str(getattr(pval, "units", ""))}
                if proc_params:
                    state.process["parameters"] = proc_params

    if not state.process:
        # Maybe tag is at top level (e.g. tree["GMAW"])
        for tag in ["GMAW", "GTAW", "SAW"]:
            if tag in tree:
                state.process = {"tag": tag, "raw": tree[tag]}
                break

    # --- Welding wire (filler material) ---
    ww = process_root.get("welding_wire")
    if ww is not None and not state.filler_material:
        if isinstance(ww, dict):
            fm = {}
            if "diameter" in ww:
                d = ww["diameter"]
                if hasattr(d, "magnitude"):
                    fm["diameter"] = _safe_float(d)
                    fm["diameter_unit"] = str(d.units)
                elif isinstance(d, dict):
                    fm["diameter"] = d.get("value", "")
                    fm["diameter_unit"] = str(d.get("units", ""))
            if "class" in ww:
                fm["classification"] = ww["class"]
            wx_u = ww.get("wx_user", {})
            if isinstance(wx_u, dict):
                fm["manufacturer"] = wx_u.get("manufacturer", "")
                fm["charge_id"] = wx_u.get("charge id", "")
            state.filler_material = fm


# ─── Extraction: Metadata ────────────────────────────────────

def _extract_metadata(state: WeldxFileState):
    """Extract metadata from tree — supports RoboScope and native weldx layouts."""
    tree = state.tree
    meta = {}

    if "metadata" in tree and isinstance(tree["metadata"], dict):
        raw_meta = tree["metadata"]
        # RoboScope nests under "roboscope"
        if "roboscope" in raw_meta and isinstance(raw_meta["roboscope"], dict):
            rs = raw_meta["roboscope"]
            meta["operator"] = rs.get("operator", "")
            meta["material"] = rs.get("material", "")
            meta["job_part"] = rs.get("job_part", "")
            meta["source_format"] = rs.get("source_format", "")

            # Convert timestamps
            ts_export = rs.get("exported_at_unix_ms")
            if ts_export and isinstance(ts_export, (int, float)):
                meta["exported_at"] = datetime.fromtimestamp(ts_export / 1000).isoformat()
            ts_start = rs.get("start_time_unix_ms")
            if ts_start and isinstance(ts_start, (int, float)):
                meta["start_time"] = datetime.fromtimestamp(ts_start / 1000).isoformat()
        else:
            # Flat metadata
            meta = dict(raw_meta)

    # Native weldx: user info under "wx_user"
    if not meta and "wx_user" in tree:
        wx_u = tree["wx_user"]
        if isinstance(wx_u, dict):
            meta["operator"] = wx_u.get("operator", "")
            meta["project"] = wx_u.get("project", "")
            wid = wx_u.get("WID")
            if wid is not None:
                meta["WID"] = str(wid)
            meta["source_format"] = "WeldX"

    # reference_timestamp (native weldx)
    ref_ts = tree.get("reference_timestamp")
    if ref_ts is not None and "start_time" not in meta:
        meta["start_time"] = str(ref_ts)

    # Extract material info into base_metal if present (RoboScope path)
    if meta.get("material") and not state.base_metal:
        state.base_metal = {"designation": meta["material"]}

    # Native weldx: workpiece.base_metal
    if not state.base_metal:
        wp = tree.get("workpiece")
        if isinstance(wp, dict):
            bm = wp.get("base_metal")
            if isinstance(bm, dict):
                designation = bm.get("common_name", "")
                standard = bm.get("standard", "")
                state.base_metal = {"designation": designation}
                if standard:
                    state.base_metal["standard"] = standard
            elif bm is not None:
                # weldx object
                designation = getattr(bm, "common_name", "") or str(bm)
                state.base_metal = {"designation": designation}
                std = getattr(bm, "standard", None)
                if std:
                    state.base_metal["standard"] = str(std)

    # Match designation to material database entry
    if state.base_metal and state.base_metal.get("designation") and not state.base_metal.get("material"):
        _match_material_db(state.base_metal)

    state.metadata = meta


def _match_material_db(base_metal: dict):
    """Match a designation (e.g. 'S355J2+N') to the editor's material DB."""
    try:
        from weldx_editor.panels.workpiece import MATERIALS_DB
    except ImportError:
        return

    designation = base_metal.get("designation", "")
    if not designation:
        return

    # Extract the base name (e.g. "S355J2" from "S355J2+N")
    base = designation.split("+")[0].strip()

    for group_name, materials in MATERIALS_DB.items():
        for mat_key in materials:
            # mat_key is like "S355J2 (1.0577) — EN 10025-2"
            if base in mat_key:
                base_metal["material"] = mat_key
                base_metal["material_group"] = group_name
                return


# ─── Extraction: Quality ─────────────────────────────────────

def _extract_quality(state: WeldxFileState):
    """Extract quality data from tree['quality']."""
    tree = state.tree
    if "quality" in tree and isinstance(tree["quality"], dict):
        state.quality = dict(tree["quality"])


# ─── Completion Update ───────────────────────────────────────

def _update_completion(state: WeldxFileState):
    # Workpiece
    has_groove = state.groove is not None
    has_material = bool(state.base_metal)
    if has_groove and has_material:
        state.completion["workpiece"] = {"status": "complete", "detail": "Material und Naht definiert"}
    elif has_groove or has_material:
        mat = state.base_metal.get("designation", "")
        state.completion["workpiece"] = {"status": "partial", "detail": f"Material: {mat}" if mat else "Teilweise definiert"}
    else:
        state.completion["workpiece"] = {"status": "missing", "detail": "Material, Naht, Geometrie fehlen"}

    # Process
    has_process = bool(state.process) and state.process.get("tag", "")
    has_gas = bool(state.shielding_gas) and any(
        state.shielding_gas.get(k) for k in ("common_name", "flowrate_value", "components")
    )
    if has_process and has_gas:
        tag = state.process.get("tag", "")
        gas = state.shielding_gas.get("common_name", "") or "Schutzgas definiert"
        state.completion["process"] = {"status": "complete", "detail": f"{tag} – {gas}"}
    elif has_process or has_gas:
        state.completion["process"] = {"status": "partial", "detail": "Teilweise definiert"}
    else:
        state.completion["process"] = {"status": "missing", "detail": "Schweißverfahren nicht definiert"}

    # Measurements
    n_meas = len(state.measurements)
    if n_meas >= 3:
        state.completion["measurements"] = {"status": "complete", "detail": f"{n_meas} Zeitreihen vorhanden"}
    elif n_meas > 0:
        state.completion["measurements"] = {"status": "partial", "detail": f"{n_meas} Zeitreihe(n) vorhanden"}
    else:
        state.completion["measurements"] = {"status": "missing", "detail": "Keine Messdaten"}

    # Equipment / Measurement chains
    n_eq = len(state.equipment)
    if n_eq > 0:
        detail = state.completion["measurements"]["detail"]
        state.completion["measurements"]["detail"] = f"{detail}, {n_eq} Messkette(n)"

    # Coordinates
    n_cs = len(state.coordinate_systems)
    if n_cs >= 3:
        state.completion["coordinates"] = {"status": "complete", "detail": f"{n_cs} Koordinatensysteme"}
    elif n_cs > 0:
        state.completion["coordinates"] = {"status": "partial", "detail": f"{n_cs} Koordinatensystem(e)"}
    else:
        state.completion["coordinates"] = {"status": "missing", "detail": "Keine Koordinatensysteme"}

    # Quality
    if bool(state.quality) and state.quality.get("level"):
        level = state.quality.get("level", "")
        state.completion["quality"] = {"status": "complete", "detail": f"ISO 5817 Level {level}"}
    elif bool(state.quality):
        state.completion["quality"] = {"status": "partial", "detail": "Teilweise definiert"}
    else:
        state.completion["quality"] = {"status": "missing", "detail": "Keine Bewertungsgruppe"}


# ─── Mesh I/O (STL, NPZ) + Add/Remove ────────────────────────

def parse_mesh_bytes(file_bytes: bytes, filename: str) -> tuple:
    """Parse uploaded mesh file into (vertices [N,3] float64, triangles [M,3] int64).

    Supports binary and ASCII STL, plus NPZ files containing 'vertices' and
    'triangles' arrays. Vertex coordinates are interpreted as millimetres.
    """
    suffix = Path(filename).suffix.lower()
    if suffix == ".npz":
        with io.BytesIO(file_bytes) as buf:
            npz = np.load(buf, allow_pickle=False)
            if "vertices" not in npz or "triangles" not in npz:
                raise ValueError("NPZ muss 'vertices' und 'triangles' enthalten.")
            verts = np.asarray(npz["vertices"], dtype=np.float64).reshape(-1, 3)
            tris = np.asarray(npz["triangles"], dtype=np.int64).reshape(-1, 3)
        return verts, tris
    if suffix == ".stl":
        return _parse_stl_bytes(file_bytes)
    raise ValueError(f"Format nicht unterstützt: {suffix}. Erlaubt: .stl, .npz")


def _parse_stl_bytes(data: bytes) -> tuple:
    """Parse STL bytes (auto-detect binary vs ASCII)."""
    is_binary = False
    if len(data) >= 84:
        n_tris = int.from_bytes(data[80:84], "little")
        if len(data) == 84 + 50 * n_tris:
            is_binary = True
    if not is_binary:
        head = data[:512].lstrip().lower()
        if not head.startswith(b"solid") or b"facet" not in head:
            is_binary = True

    if is_binary:
        n_tris = int.from_bytes(data[80:84], "little")
        rec = np.frombuffer(
            data, offset=84, count=n_tris,
            dtype=np.dtype([
                ("normal", "<f4", 3),
                ("v", "<f4", (3, 3)),
                ("attr", "<u2"),
            ]),
        )
        flat = rec["v"].reshape(-1, 3).astype(np.float64)
    else:
        text = data.decode("utf-8", errors="ignore")
        coords = []
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("vertex"):
                parts = s.split()
                if len(parts) >= 4:
                    coords.append([float(parts[1]), float(parts[2]), float(parts[3])])
        if len(coords) % 3 != 0:
            raise ValueError("ASCII-STL: Vertex-Anzahl ist kein Vielfaches von 3.")
        flat = np.asarray(coords, dtype=np.float64)

    # Deduplicate vertices
    verts, inverse = np.unique(flat, axis=0, return_inverse=True)
    tris = inverse.reshape(-1, 3).astype(np.int64)
    return verts, tris


def add_workpiece_mesh(
    state: WeldxFileState,
    scan_name: str,
    target_cs: str,
    vertices: np.ndarray,
    triangles: np.ndarray,
) -> dict:
    """Add a 3D mesh to state.workpiece_meshes attached to ``target_cs``.

    Vertices are interpreted in the frame of ``target_cs``. A transformed copy
    in the CSM root frame is computed for visualization, when a CSM is loaded.
    """
    raw = np.asarray(vertices, dtype=np.float64).reshape(-1, 3)
    tris = np.asarray(triangles, dtype=np.int64).reshape(-1, 3)

    # Ensure scan_name is unique within current state
    existing = {m.get("scan_name") for m in state.workpiece_meshes}
    base = scan_name or "scan"
    name = base
    i = 0
    while name in existing:
        i += 1
        name = f"{base}_{i}"

    viz = _transform_verts_to_root(state._csm, target_cs, raw)

    mesh = {
        "name": f"{target_cs}/{name}",
        "scan_name": name,
        "target_cs": target_cs,
        "vertices": viz,
        "raw_vertices": raw,
        "triangles": tris,
        "visible": True,
    }
    state.workpiece_meshes.append(mesh)
    return mesh


def remove_workpiece_mesh(state: WeldxFileState, index: int) -> bool:
    """Remove a mesh by index from state.workpiece_meshes. Returns True on success."""
    if 0 <= index < len(state.workpiece_meshes):
        state.workpiece_meshes.pop(index)
        return True
    return False


def _transform_verts_to_root(csm, target_cs: Optional[str], verts: np.ndarray) -> np.ndarray:
    """Transform vertices from ``target_cs`` into the CSM root frame."""
    if csm is None or not target_cs:
        return verts
    root = getattr(csm, "root_system_name", None)
    if not root or target_cs == root:
        return verts
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            lcs = csm.get_cs(target_cs, root)
        coords = lcs.coordinates.values
        if hasattr(coords, "magnitude"):
            coords = coords.magnitude
        orient = lcs.orientation.values
        R = orient[0] if orient.ndim > 2 else orient
        t = coords[0] if coords.ndim > 1 else coords
        return verts @ R.T + t
    except Exception:
        return verts


# ─── Path I/O (CSV trajectories) ─────────────────────────────

def add_imported_path(
    state: WeldxFileState,
    name: str,
    parent_cs: str,
    points_xyz_mm: np.ndarray,
    time_s: Optional[np.ndarray] = None,
) -> dict:
    """Add an imported 3D path as a time-dependent CS in state and (live) CSM.

    Vertices are interpreted as millimetres in ``parent_cs``. If ``time_s`` is
    ``None`` the sample index (in seconds) is used.
    """
    pts = np.asarray(points_xyz_mm, dtype=np.float64).reshape(-1, 3)
    if pts.size == 0:
        raise ValueError("Pfad enthält keine Punkte.")
    if time_s is None or len(time_s) != len(pts):
        t = np.arange(len(pts), dtype=np.float64)
    else:
        t = np.asarray(time_s, dtype=np.float64)

    # Live update of the CSM if available
    if WELDX_AVAILABLE:
        try:
            from weldx import LocalCoordinateSystem, CoordinateSystemManager, Q_
            csm = state._csm
            if csm is None:
                csm = CoordinateSystemManager(parent_cs or "user_frame")
                state._csm = csm
            if parent_cs not in csm.coordinate_system_names:
                csm.add_cs(parent_cs, csm.root_system_name, LocalCoordinateSystem())
            # Ensure name is unique in the CSM
            base = name or "path"
            unique = base
            i = 0
            while unique in csm.coordinate_system_names:
                i += 1
                unique = f"{base}_{i}"
            name = unique
            lcs = LocalCoordinateSystem(
                coordinates=Q_(pts, "mm"),
                time=Q_(t, "s"),
            )
            csm.add_cs(name, parent_cs, lcs)
        except Exception:
            # Fall back: still keep the path in state.coordinate_systems
            pass

    info = {
        "name": name,
        "status": "complete",
        "parent": parent_cs,
        "is_time_dependent": True,
        "translation": {
            "x": float(pts[0, 0]),
            "y": float(pts[0, 1]),
            "z": float(pts[0, 2]),
        },
        "orientation": np.eye(3).tolist(),
        "trajectory": pts,
        "time_seconds": t,
        "_imported_path": True,
    }
    state.coordinate_systems[name] = info
    return info


def remove_imported_path(state: WeldxFileState, name: str) -> bool:
    """Remove an imported path from state and the live CSM."""
    info = state.coordinate_systems.get(name)
    if info is None or not info.get("_imported_path"):
        return False
    state.coordinate_systems.pop(name, None)
    if WELDX_AVAILABLE and state._csm is not None:
        try:
            if name in state._csm.coordinate_system_names:
                state._csm.delete_cs(name)
        except Exception:
            pass
    return True


# ─── Saving ──────────────────────────────────────────────────

def save_weldx_file(state: WeldxFileState, output_path: str):
    if not WELDX_AVAILABLE:
        raise ImportError("weldx package is not installed")

    # Build output tree from original tree (preserves all data)
    out_tree = dict(state.tree) if state.tree else {}

    # Apply user edits — only write extracted/edited fields,
    # don't overwrite original nested weldx objects with flat dicts
    if state.groove is not None:
        out_tree["groove"] = state.groove
    if state.base_metal:
        out_tree["base_metal"] = state.base_metal
    if state.quality:
        out_tree["quality"] = state.quality
    if state.metadata:
        out_tree["metadata"] = state.metadata

    # Process: merge into existing process dict rather than replacing
    if state.process or state.shielding_gas or state.filler_material:
        proc = out_tree.get("process")
        if not isinstance(proc, dict):
            proc = {}
            out_tree["process"] = proc
        if state.process:
            # Only write flat editor fields if no native welding_process exists
            if "welding_process" not in proc:
                proc["welding_process"] = state.process
        if state.shielding_gas:
            if "shielding_gas" not in proc:
                proc["shielding_gas"] = state.shielding_gas
        if state.filler_material:
            if "welding_wire" not in proc:
                proc["welding_wire"] = state.filler_material

    # Sync 3D meshes (workpiece scans) into the CSM
    _sync_meshes_into_csm(state, out_tree)

    # Persist user-imported time series into tree['data']
    _sync_imported_measurements(state, out_tree)

    wx = WeldxFile(tree=out_tree, mode="rw")
    wx.write_to(output_path, all_array_compression="zlib")
    return output_path


def _sync_imported_measurements(state: WeldxFileState, out_tree: dict):
    """Write user-imported time series into out_tree['data'] as weldx TimeSeries."""
    try:
        from weldx import TimeSeries, Q_
    except ImportError:
        return

    imported = {
        k: v for k, v in getattr(state, "measurements", {}).items()
        if isinstance(v, dict) and v.get("_imported")
    }
    if not imported:
        return

    data = out_tree.get("data")
    if not isinstance(data, dict):
        data = {}
        out_tree["data"] = data

    for key, info in imported.items():
        values = info.get("values")
        if values is None or len(values) == 0:
            continue
        unit = info.get("unit") or "dimensionless"
        time_s = info.get("time_seconds")

        try:
            data_q = Q_(np.asarray(values, dtype=np.float64), unit)
            if time_s is not None and len(time_s) == len(values):
                t = np.asarray(time_s, dtype=np.float64)
            else:
                t = np.arange(len(values), dtype=np.float64)
            ts = TimeSeries(data=data_q, time=Q_(t, "s"))
            data[key] = ts
        except Exception:
            continue


def _sync_meshes_into_csm(state: WeldxFileState, out_tree: dict):
    """Replace SpatialData entries in the CSM to match state.workpiece_meshes."""
    try:
        from weldx import CoordinateSystemManager, LocalCoordinateSystem, SpatialData, Q_
    except ImportError:
        return

    # Find or build a CSM
    csm = None
    csm_key = None
    for key in ("coordinate_systems", "csm", "coordinate_system_manager"):
        val = out_tree.get(key)
        if isinstance(val, CoordinateSystemManager):
            csm = val
            csm_key = key
            break
    if csm is None:
        csm = state._csm if isinstance(state._csm, CoordinateSystemManager) else None
        csm_key = "coordinate_systems"

    # No CSM and no meshes: nothing to do
    if csm is None and not state.workpiece_meshes:
        return

    # No CSM but we have meshes: build a minimal one
    if csm is None:
        csm = CoordinateSystemManager("user_frame")
        if "workpiece" not in csm.coordinate_system_names:
            csm.add_cs("workpiece", "user_frame", LocalCoordinateSystem())

    # Strip all existing SpatialData from the CSM so we can re-attach in sync
    g = csm.graph
    to_delete = []
    for node_name in list(csm.coordinate_system_names):
        node_data = g.nodes.get(node_name, {}).get("data", {})
        if isinstance(node_data, dict):
            for dname, dval in node_data.items():
                if isinstance(dval, SpatialData):
                    to_delete.append(dname)
    for dname in to_delete:
        try:
            csm.delete_data(dname)
        except Exception:
            pass

    # Re-attach meshes from state
    used_names = set()
    for m in state.workpiece_meshes:
        target = m.get("target_cs")
        if not target or target not in csm.coordinate_system_names:
            target = csm.root_system_name

        verts = np.asarray(m.get("raw_vertices", m.get("vertices")), dtype=np.float64)
        tris = np.asarray(m["triangles"], dtype=np.uint32)
        if verts.size == 0 or tris.size == 0:
            continue

        # Ensure unique data name across the CSM
        base = m.get("scan_name") or "scan"
        name = base
        i = 0
        while name in used_names or name in getattr(csm, "data_names", []):
            i += 1
            name = f"{base}_{i}"
        used_names.add(name)

        try:
            sd = SpatialData(coordinates=Q_(verts, "mm"), triangles=tris)
            csm.assign_data(sd, name, target)
        except Exception:
            continue

    out_tree[csm_key] = csm


def get_tree_summary(state: WeldxFileState) -> dict:
    def summarize(obj, depth=0, max_depth=3):
        if depth > max_depth:
            return "..."
        if isinstance(obj, dict):
            return {k: summarize(v, depth + 1) for k, v in obj.items()}
        elif isinstance(obj, (list, np.ndarray)):
            length = len(obj) if hasattr(obj, '__len__') else '?'
            return f"[Array: {length} items]"
        elif isinstance(obj, np.ndarray):
            return f"<ndarray {obj.shape} {obj.dtype}>"
        elif hasattr(obj, '__class__'):
            return f"<{type(obj).__name__}>"
        else:
            return str(obj)[:100]

    return summarize(state.tree)
