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
    wx = WeldxFile(file_path, mode="rw")
    state.wx_file = wx
    state.tree = dict(wx)

    _extract_measurements(state)
    _extract_equipment(state)
    _extract_coordinate_systems(state)
    _extract_groove(state)
    _extract_process(state)
    _extract_metadata(state)
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
    """Extract time series from tree['data'] — RoboScope structure."""
    tree = state.tree

    # Primary: RoboScope puts time series under "data"
    if "data" in tree and isinstance(tree["data"], dict):
        for name, ts in tree["data"].items():
            info = _describe_time_series(name, ts)
            state.measurements[name] = info
        return

    # Fallback: look for keys at top level
    for key in ["measurements", "measurement_data"]:
        if key in tree and isinstance(tree[key], dict):
            for name, ts in tree[key].items():
                info = _describe_time_series(name, ts)
                state.measurements[name] = info
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


# ─── Extraction: Equipment / Measurement Chains ─────────────

def _extract_equipment(state: WeldxFileState):
    """Extract measurement equipment and chains from tree['equipment']."""
    tree = state.tree

    if "equipment" not in tree or not isinstance(tree["equipment"], dict):
        return

    for name, eq in tree["equipment"].items():
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
                for name in csm.coordinate_system_names:
                    state.coordinate_systems[name] = {"name": name, "status": "present"}
            elif isinstance(csm, dict):
                for name in csm:
                    state.coordinate_systems[name] = {"name": name, "status": "present"}
            break


# ─── Extraction: Groove ──────────────────────────────────────

def _extract_groove(state: WeldxFileState):
    tree = state.tree
    for key in ["groove", "workpiece", "joint", "weld_joint"]:
        if key in tree:
            val = tree[key]
            if isinstance(val, dict) and "groove" in val:
                state.groove = val["groove"]
            else:
                state.groove = val
            break


# ─── Extraction: Process (welding_process + shielding_gas) ──

def _extract_process(state: WeldxFileState):
    """Extract from tree['process'] — RoboScope structure."""
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
    sg = process_root.get("shielding_gas", {})
    if isinstance(sg, dict):
        gas_info = {}
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
        state.shielding_gas = gas_info

    # --- Welding process ---
    wp = process_root.get("welding_process", {})
    if isinstance(wp, dict):
        state.process = {
            "tag": wp.get("tag", ""),                    # e.g. "GMAW"
            "base_process": wp.get("base_process", ""),  # e.g. "pulse"
            "manufacturer": wp.get("manufacturer", ""),  # e.g. "Fronius"
            "power_source": wp.get("power_source", ""),  # e.g. "Transpuls 420"
        }
    elif not state.process:
        # Maybe tag is at top level (e.g. tree["GMAW"])
        for tag in ["GMAW", "GTAW", "SAW"]:
            if tag in tree:
                state.process = {"tag": tag, "raw": tree[tag]}
                break


# ─── Extraction: Metadata ────────────────────────────────────

def _extract_metadata(state: WeldxFileState):
    """Extract from tree['metadata'] — RoboScope nests under 'roboscope' key."""
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

    # Extract material info into base_metal if present
    if meta.get("material"):
        state.base_metal = {"designation": meta["material"]}

    state.metadata = meta


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
    if bool(state.quality):
        state.completion["quality"] = {"status": "complete", "detail": "Bewertungsgruppe definiert"}
    else:
        state.completion["quality"] = {"status": "missing", "detail": "Keine Bewertungsgruppe"}


# ─── Saving ──────────────────────────────────────────────────

def save_weldx_file(state: WeldxFileState, output_path: str):
    if not WELDX_AVAILABLE:
        raise ImportError("weldx package is not installed")

    wx = state.wx_file
    if wx is None:
        wx = WeldxFile(tree={}, mode="rw")

    if state.groove is not None:
        wx["groove"] = state.groove
    if state.base_metal:
        wx["base_metal"] = state.base_metal
    if state.process:
        wx["process"] = state.process
    if state.shielding_gas:
        wx["shielding_gas"] = state.shielding_gas
    if state.filler_material:
        wx["filler_material"] = state.filler_material
    if state.quality:
        wx["quality"] = state.quality
    if state.metadata:
        wx["metadata"] = state.metadata

    wx.write_to(output_path)
    return output_path


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
