import numpy as np
import streamlit as st
from weldx_editor.utils.style import COLORS
from weldx_editor.utils.weldx_io import (
    parse_mesh_bytes, add_workpiece_mesh, remove_workpiece_mesh,
)


def render_coordinates(state):
    """
    Render the coordinates panel with two tabs:
    - KOS-Hierarchie: Coordinate system tree hierarchy
    - Transformationen: Transformation matrix editor
    """

    # Initialize coordinate systems if not present
    if not hasattr(state, 'coordinate_systems'):
        state.coordinate_systems = {}

    # Initialize default systems if empty
    if not state.coordinate_systems:
        state.coordinate_systems = {
            'robot_base': {'name': 'robot_base', 'status': 'complete', 'parent': None},
            'tcp': {'name': 'tcp', 'status': 'complete', 'parent': 'robot_base'},
        }

    tab1, tab2 = st.tabs(["KOS-Hierarchie", "Transformationen"])

    # ========== TAB 1: KOS-Hierarchie ==========
    with tab1:
        st.subheader("Koordinatensystem-Hierarchie")

        # Build and display tree
        st.write("**Verfügbare Koordinatensysteme:**")

        tree_text = _build_kos_tree(state.coordinate_systems)
        st.code(tree_text, language="text")

        st.divider()

        # Add new coordinate system
        st.subheader("Neues Koordinatensystem hinzufügen")
        with st.expander("➕ Koordinatensystem hinzufügen"):
            with st.form("add_kos_form", border=False):
                kos_name = st.text_input(
                    "Name des Koordinatensystems",
                    key="new_kos_name"
                )

                # Get list of existing systems for parent selection
                existing_systems = list(state.coordinate_systems.keys())
                parent_system = st.selectbox(
                    "Übergeordnetes System",
                    options=existing_systems,
                    key="kos_parent"
                )

                col1, col2, col3 = st.columns(3)
                with col1:
                    trans_x = st.number_input(
                        "Translation X (mm)",
                        value=0.0,
                        key="kos_trans_x"
                    )
                with col2:
                    trans_y = st.number_input(
                        "Translation Y (mm)",
                        value=0.0,
                        key="kos_trans_y"
                    )
                with col3:
                    trans_z = st.number_input(
                        "Translation Z (mm)",
                        value=0.0,
                        key="kos_trans_z"
                    )

                st.write("**Rotation (optional):**")
                rot_type = st.radio(
                    "Rotationsformat",
                    options=["Euler Winkel (deg)", "Quaternion", "Keine"],
                    horizontal=True,
                    key="kos_rot_type"
                )

                if rot_type == "Euler Winkel (deg)":
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        rot_x = st.number_input("Roll (°)", value=0.0, key="kos_roll")
                    with col2:
                        rot_y = st.number_input("Pitch (°)", value=0.0, key="kos_pitch")
                    with col3:
                        rot_z = st.number_input("Yaw (°)", value=0.0, key="kos_yaw")
                    rotation = {'type': 'euler', 'x': rot_x, 'y': rot_y, 'z': rot_z}
                elif rot_type == "Quaternion":
                    col1, col2 = st.columns(2)
                    with col1:
                        col_q1, col_q2 = st.columns(2)
                        with col_q1:
                            qw = st.number_input("w", value=1.0, key="kos_qw")
                        with col_q2:
                            qx = st.number_input("x", value=0.0, key="kos_qx")
                    with col2:
                        col_q3, col_q4 = st.columns(2)
                        with col_q3:
                            qy = st.number_input("y", value=0.0, key="kos_qy")
                        with col_q4:
                            qz = st.number_input("z", value=0.0, key="kos_qz")
                    rotation = {'type': 'quaternion', 'w': qw, 'x': qx, 'y': qy, 'z': qz}
                else:
                    rotation = None

                if st.form_submit_button("Koordinatensystem speichern"):
                    if kos_name and kos_name not in state.coordinate_systems:
                        state.coordinate_systems[kos_name] = {
                            'name': kos_name,
                            'status': 'incomplete',
                            'parent': parent_system,
                            'translation': {'x': trans_x, 'y': trans_y, 'z': trans_z},
                            'rotation': rotation
                        }
                        st.success(f"Koordinatensystem '{kos_name}' hinzugefügt!")
                    elif kos_name in state.coordinate_systems:
                        st.error(f"Koordinatensystem '{kos_name}' existiert bereits.")
                    else:
                        st.error("Bitte geben Sie einen Namen ein.")

    # ========== TAB 2: Transformationen ==========
    with tab2:
        st.subheader("Transformationen zwischen Koordinatensystemen")

        st.write("**Transformationsmatrizen:**")

        if not state.coordinate_systems:
            st.info("Noch keine Koordinatensysteme vorhanden.")
        else:
            # Display transformation matrix for each system with parent
            for kos_name, kos_info in state.coordinate_systems.items():
                if kos_info.get('parent'):
                    parent = kos_info['parent']
                    st.write(f"**{parent} → {kos_name}**")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.write("**Translation (mm):**")
                        trans = kos_info.get('translation', {'x': 0, 'y': 0, 'z': 0})
                        trans_x = st.number_input(
                            "X",
                            value=trans.get('x', 0.0),
                            key=f"trans_x_{kos_name}"
                        )
                        trans_y = st.number_input(
                            "Y",
                            value=trans.get('y', 0.0),
                            key=f"trans_y_{kos_name}"
                        )
                        trans_z = st.number_input(
                            "Z",
                            value=trans.get('z', 0.0),
                            key=f"trans_z_{kos_name}"
                        )

                        # Update state
                        kos_info['translation'] = {'x': trans_x, 'y': trans_y, 'z': trans_z}

                    with col2:
                        st.write("**Rotation:**")
                        rotation = kos_info.get('rotation')
                        if rotation and rotation.get('type') == 'euler':
                            rot_x = st.number_input(
                                "Roll (°)",
                                value=rotation.get('x', 0.0),
                                key=f"rot_x_{kos_name}"
                            )
                            rot_y = st.number_input(
                                "Pitch (°)",
                                value=rotation.get('y', 0.0),
                                key=f"rot_y_{kos_name}"
                            )
                            rot_z = st.number_input(
                                "Yaw (°)",
                                value=rotation.get('z', 0.0),
                                key=f"rot_z_{kos_name}"
                            )
                            kos_info['rotation'] = {'type': 'euler', 'x': rot_x, 'y': rot_y, 'z': rot_z}
                        elif rotation and rotation.get('type') == 'quaternion':
                            qw = st.number_input(
                                "w",
                                value=rotation.get('w', 1.0),
                                key=f"qw_{kos_name}"
                            )
                            qx = st.number_input(
                                "x",
                                value=rotation.get('x', 0.0),
                                key=f"qx_{kos_name}"
                            )
                            qy = st.number_input(
                                "y",
                                value=rotation.get('y', 0.0),
                                key=f"qy_{kos_name}"
                            )
                            qz = st.number_input(
                                "z",
                                value=rotation.get('z', 0.0),
                                key=f"qz_{kos_name}"
                            )
                            kos_info['rotation'] = {
                                'type': 'quaternion',
                                'w': qw,
                                'x': qx,
                                'y': qy,
                                'z': qz
                            }
                        else:
                            st.caption("Keine Rotation definiert")

                    # Transformation matrix visualization
                    with st.expander(f"Transformationsmatrix (4x4)"):
                        trans_data = kos_info.get('translation', {'x': 0, 'y': 0, 'z': 0})
                        rot_data = kos_info.get('rotation')

                        # Build a simple transformation matrix representation
                        matrix_text = "┌                          ┐\n"
                        matrix_text += "│  1.00   0.00   0.00  {: >6.2f} │\n".format(trans_data.get('x', 0))
                        matrix_text += "│  0.00   1.00   0.00  {: >6.2f} │\n".format(trans_data.get('y', 0))
                        matrix_text += "│  0.00   0.00   1.00  {: >6.2f} │\n".format(trans_data.get('z', 0))
                        matrix_text += "│  0.00   0.00   0.00   1.00  │\n"
                        matrix_text += "└                          ┘\n"

                        st.code(matrix_text, language="text")

                        if rot_data:
                            if rot_data.get('type') == 'euler':
                                st.caption(
                                    f"Euler angles: "
                                    f"Roll={rot_data.get('x', 0):.1f}°, "
                                    f"Pitch={rot_data.get('y', 0):.1f}°, "
                                    f"Yaw={rot_data.get('z', 0):.1f}°"
                                )
                            elif rot_data.get('type') == 'quaternion':
                                st.caption(
                                    f"Quaternion: "
                                    f"w={rot_data.get('w', 1):.3f}, "
                                    f"x={rot_data.get('x', 0):.3f}, "
                                    f"y={rot_data.get('y', 0):.3f}, "
                                    f"z={rot_data.get('z', 0):.3f}"
                                )

                    st.divider()

        st.divider()
        _render_3d_visualization(state)


# ─── 3D Mesh Management (Add / Delete) ───────────────────────

_MESH_COLORS = ["#808080", "#5b8def", "#e07b5b", "#7fb069", "#c69bd9", "#e0c059"]


def _render_mesh_manager(state):
    """UI for uploading and removing 3D meshes (workpiece scans)."""
    st.subheader("3D-Daten verwalten")

    meshes = getattr(state, "workpiece_meshes", [])

    # ── List existing meshes with visibility toggle + delete button ──
    if meshes:
        st.write("**Vorhandene Meshes:**")
        for idx, m in enumerate(list(meshes)):
            verts = m.get("vertices")
            tris = m.get("triangles")
            n_v = len(verts) if verts is not None else 0
            n_t = len(tris) if tris is not None else 0
            color = _MESH_COLORS[idx % len(_MESH_COLORS)]

            col_vis, col_info, col_del = st.columns([1, 5, 1])
            with col_vis:
                visible = st.checkbox(
                    " ",
                    value=m.get("visible", True),
                    key=f"vis_mesh_{idx}",
                    help="Mesh in der 3D-Ansicht ein-/ausblenden",
                    label_visibility="collapsed",
                )
                m["visible"] = visible
            with col_info:
                st.markdown(
                    f"<span style='display:inline-block;width:10px;height:10px;"
                    f"background:{color};border-radius:2px;margin-right:6px;"
                    f"vertical-align:middle;'></span>"
                    f"`{m.get('name', '?')}` — "
                    f"{n_v:,} Vertices, {n_t:,} Dreiecke "
                    f"(KOS: `{m.get('target_cs', '?')}`)",
                    unsafe_allow_html=True,
                )
            with col_del:
                if st.button("🗑️", key=f"del_mesh_{idx}", help="Mesh entfernen"):
                    remove_workpiece_mesh(state, idx)
                    st.rerun()
    else:
        st.caption("Keine Meshes vorhanden.")

    # ── Upload new mesh ──
    with st.expander("➕ Mesh hinzufügen (STL / NPZ)"):
        uploaded = st.file_uploader(
            "Mesh-Datei",
            type=["stl", "npz"],
            key="mesh_uploader",
            help=(
                "STL (binär oder ASCII) oder NPZ mit den Arrays "
                "'vertices' (N×3, mm) und 'triangles' (M×3)."
            ),
        )

        cs_options = list(state.coordinate_systems.keys()) if state.coordinate_systems else []
        if not cs_options:
            cs_options = ["workpiece"]

        # Default to "workpiece" if present, else first option
        default_idx = cs_options.index("workpiece") if "workpiece" in cs_options else 0

        col_a, col_b = st.columns([2, 3])
        with col_a:
            target_cs = st.selectbox(
                "Ziel-Koordinatensystem",
                options=cs_options,
                index=default_idx,
                key="mesh_target_cs",
                help="Vertices werden in diesem KOS interpretiert.",
            )
        with col_b:
            scan_name = st.text_input(
                "Scan-Name",
                value="scan_neu",
                key="mesh_scan_name",
                help="Eindeutiger Bezeichner innerhalb des CSM (z. B. scan_2).",
            )

        if st.button("Mesh hinzufügen", key="add_mesh_btn", type="primary",
                     disabled=uploaded is None):
            try:
                verts, tris = parse_mesh_bytes(uploaded.getvalue(), uploaded.name)
                add_workpiece_mesh(state, scan_name.strip() or "scan",
                                   target_cs, verts, tris)
                st.success(
                    f"Mesh '{uploaded.name}' hinzugefügt: "
                    f"{len(verts):,} Vertices, {len(tris):,} Dreiecke."
                )
                st.rerun()
            except Exception as e:
                st.error(f"Fehler beim Einlesen: {e}")

    st.divider()


# ─── 3D Visualization (PyVista / VTK) ─────────────────────────

def _render_3d_visualization(state):
    """Render interactive 3D visualization using Plotly Mesh3d (matches workpiece preview)."""
    cs = state.coordinate_systems
    meshes = getattr(state, "workpiece_meshes", [])

    if not cs and not meshes:
        st.info("Keine Koordinatensysteme vorhanden.")
        return

    # 3D mesh management (add/delete) — always available when CS exist
    _render_mesh_manager(state)

    has_data = meshes or any(
        isinstance(info.get("translation"), dict) for info in cs.values()
    )
    if not has_data:
        st.info("Keine Transformationsdaten vorhanden.")
        return

    st.subheader("3D-Visualisierung")

    import plotly.graph_objects as go
    fig = go.Figure()

    # Compute scene bounding box for dynamic light placement
    all_pts = []
    for mesh_data in meshes:
        if mesh_data.get("visible", True):
            v = mesh_data["vertices"]
            all_pts.append(v[~np.isnan(v).any(axis=1)])
    if all_pts:
        all_pts_arr = np.vstack(all_pts)
        bb_min = all_pts_arr.min(axis=0)
        bb_max = all_pts_arr.max(axis=0)
    else:
        bb_min = np.array([0.0, 0.0, 0.0])
        bb_max = np.array([100.0, 100.0, 100.0])
    bb_center = (bb_min + bb_max) / 2
    bb_size = float(np.linalg.norm(bb_max - bb_min)) or 100.0
    light_pos = dict(
        x=float(bb_center[0] - bb_size * 1.2),
        y=float(bb_center[1] - bb_size * 1.0),
        z=float(bb_max[2] + bb_size * 1.5),
    )

    # ── Workpiece meshes ──
    for idx, mesh_data in enumerate(meshes):
        if not mesh_data.get("visible", True):
            continue
        verts, tris = _clean_and_decimate(
            mesh_data["vertices"].astype(np.float64),
            mesh_data["triangles"].astype(np.int64),
            max_tris=80_000,
        )
        if verts.size == 0 or tris.size == 0:
            continue

        color = _MESH_COLORS[idx % len(_MESH_COLORS)]
        fig.add_trace(go.Mesh3d(
            x=verts[:, 0], y=verts[:, 1], z=verts[:, 2],
            i=tris[:, 0], j=tris[:, 1], k=tris[:, 2],
            color=color,
            opacity=1.0,
            flatshading=False,
            lighting=dict(
                ambient=0.22, diffuse=0.9, specular=0.15,
                roughness=0.6, fresnel=0.1,
            ),
            lightposition=light_pos,
            name=mesh_data.get("name", f"mesh_{idx}"),
            showlegend=True,
            hoverinfo="name",
        ))

    # ── Trajectories (any time-dependent CS with multi-point path) ──
    for name, info in cs.items():
        traj = info.get("trajectory")
        if traj is None or not hasattr(traj, "shape") or traj.shape[0] < 2:
            continue
        pts = traj[::max(1, traj.shape[0] // 500)].astype(np.float64)
        is_imported = info.get("_imported_path", False)
        line_color = "#1565c0" if is_imported else "#cc0000"
        fig.add_trace(go.Scatter3d(
            x=pts[:, 0], y=pts[:, 1], z=pts[:, 2],
            mode="lines",
            line=dict(color=line_color, width=4),
            name=f"{name} (Trajektorie)",
            hoverinfo="name",
        ))

    # ── KOS labels (markers + text) ──
    label_x, label_y, label_z, label_text, label_color = [], [], [], [], []
    for name, info in cs.items():
        t = info.get("translation")
        if not isinstance(t, dict):
            continue
        label_x.append(t["x"]); label_y.append(t["y"]); label_z.append(t["z"])
        label_text.append(name)
        if any(k in name.lower() for k in ("tcp", "design")):
            label_color.append("#cc0000")
        elif any(k in name.lower() for k in ("t1", "t2")):
            label_color.append("#00aa00")
        else:
            label_color.append("#333333")

    if label_x:
        fig.add_trace(go.Scatter3d(
            x=label_x, y=label_y, z=label_z,
            mode="markers+text",
            marker=dict(size=4, color=label_color),
            text=label_text,
            textposition="top center",
            textfont=dict(size=11, color=label_color),
            name="Koordinatensysteme",
            hoverinfo="text",
            showlegend=False,
        ))

    fig.update_layout(
        scene=dict(
            xaxis_title="X [mm]",
            yaxis_title="Y [mm]",
            zaxis_title="Z [mm]",
            aspectmode="data",
            bgcolor="white",
            xaxis=dict(gridcolor="#ddd", color="#333", backgroundcolor="#f5f5f5"),
            yaxis=dict(gridcolor="#ddd", color="#333", backgroundcolor="#f5f5f5"),
            zaxis=dict(gridcolor="#ddd", color="#333", backgroundcolor="#f5f5f5"),
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=0.8),
                up=dict(x=0, y=0, z=1),
            ),
        ),
        paper_bgcolor="white",
        font=dict(color="#333333"),
        height=650,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(bgcolor="rgba(255,255,255,0.8)", bordercolor="#ddd", borderwidth=1),
    )
    st.plotly_chart(fig, use_container_width=True)


def _clean_and_decimate(verts: np.ndarray, tris: np.ndarray, max_tris: int = 80_000):
    """Drop NaN vertices and decimate to at most ``max_tris`` triangles."""
    nan_mask = np.isnan(verts).any(axis=1)
    if nan_mask.any():
        valid_tri = ~(nan_mask[tris[:, 0]] | nan_mask[tris[:, 1]] | nan_mask[tris[:, 2]])
        tris = tris[valid_tri]
        used = np.unique(tris)
        remap = np.full(verts.shape[0], -1, dtype=np.int64)
        remap[used] = np.arange(len(used))
        verts = verts[used]
        tris = remap[tris]

    if tris.shape[0] > max_tris:
        try:
            import pyvista as pv
            import vtk
            vtk.vtkLogger.SetStderrVerbosity(vtk.vtkLogger.VERBOSITY_OFF)
            faces = np.column_stack([np.full(tris.shape[0], 3, dtype=np.int64), tris]).ravel()
            pv_mesh = pv.PolyData(verts, faces)
            alg = vtk.vtkQuadricClustering()
            alg.SetInputData(pv_mesh)
            alg.SetNumberOfXDivisions(300)
            alg.SetNumberOfYDivisions(300)
            alg.SetNumberOfZDivisions(300)
            alg.Update()
            dec = pv.wrap(alg.GetOutput())
            verts = np.asarray(dec.points)
            tris = dec.faces.reshape(-1, 4)[:, 1:4]
        except ImportError:
            step = max(1, tris.shape[0] // max_tris)
            tris = tris[::step]
            used = np.unique(tris)
            remap2 = np.full(verts.shape[0], -1, dtype=np.int64)
            remap2[used] = np.arange(len(used))
            verts = verts[used]
            tris = remap2[tris]
    return verts, tris


def _build_kos_tree(coordinate_systems: dict, parent=None, indent=0) -> str:
    """
    Build a tree representation of coordinate system hierarchy.

    Args:
        coordinate_systems: Dictionary of coordinate system info
        parent: Parent system name to filter by
        indent: Current indentation level

    Returns:
        String representation of the tree
    """
    tree_lines = []

    # Find root systems on first call
    if parent is None:
        root_systems = [
            name for name, info in coordinate_systems.items()
            if info.get('parent') is None
        ]
        for root in root_systems:
            tree_lines.append(_format_kos_line(coordinate_systems[root], 0))
            tree_lines.extend(_build_kos_subtree(coordinate_systems, root, 0))
        return '\n'.join(tree_lines) if tree_lines else "Keine Koordinatensysteme vorhanden"
    else:
        return _build_kos_subtree(coordinate_systems, parent, indent)


def _build_kos_subtree(coordinate_systems: dict, parent: str, indent: int) -> list:
    """
    Recursively build subtree for a parent coordinate system.

    Args:
        coordinate_systems: Dictionary of coordinate system info
        parent: Parent system name
        indent: Current indentation level

    Returns:
        List of tree lines
    """
    lines = []
    children = [
        name for name, info in coordinate_systems.items()
        if info.get('parent') == parent
    ]

    for i, child in enumerate(children):
        is_last = (i == len(children) - 1)
        prefix = "└── " if is_last else "├── "
        lines.append(prefix + _format_kos_line(coordinate_systems[child], indent + 1))

        # Recursively add children
        child_lines = _build_kos_subtree(coordinate_systems, child, indent + 2)
        for j, line in enumerate(child_lines):
            if is_last:
                lines.append("    " + line)
            else:
                lines.append("│   " + line)

    return lines


def _format_kos_line(kos_info: dict, indent: int) -> str:
    """
    Format a single coordinate system line with status indicator.

    Args:
        kos_info: Coordinate system information dictionary
        indent: Indentation level

    Returns:
        Formatted string for the coordinate system
    """
    name = kos_info.get('name', 'unknown')
    status = kos_info.get('status', 'unknown')

    if status == 'complete':
        icon = "✅"
    elif status == 'incomplete':
        icon = "❌ (fehlt)"
    else:
        icon = "⚠️"

    return f"{name} {icon}"
