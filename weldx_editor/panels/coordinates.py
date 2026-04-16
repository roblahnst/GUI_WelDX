import numpy as np
import streamlit as st
import plotly.graph_objects as go
from weldx_editor.utils.style import COLORS


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


# ─── 3D Visualization ─────────────────────────────────────────

# Axis colors: X=red, Y=green, Z=blue (matching k3d convention)
_AXIS_COLORS = ["#e74c3c", "#2ecc71", "#3498db"]


def _render_3d_visualization(state):
    """Render interactive 3D visualization: workpiece mesh + TCP path + CS labels."""
    cs = state.coordinate_systems
    meshes = getattr(state, "workpiece_meshes", [])

    if not cs and not meshes:
        st.info("Keine Koordinatensysteme vorhanden.")
        return

    st.subheader("3D-Visualisierung")

    fig = go.Figure()

    # ── Workpiece mesh (3D scan surfaces) ──
    _MAX_TRIS = 20_000  # browser-friendly triangle budget per mesh
    for mesh in meshes:
        verts = mesh["vertices"]
        tris = mesh["triangles"]

        # Downsample triangles and reindex vertices for browser performance
        if tris.shape[0] > _MAX_TRIS:
            step = max(1, tris.shape[0] // _MAX_TRIS)
            tris = tris[::step]

        # Keep only referenced vertices (avoids sending 277k when only 50k used)
        used = np.unique(tris)
        remap = np.full(verts.shape[0], -1, dtype=np.int64)
        remap[used] = np.arange(len(used))
        verts = verts[used]
        tris = remap[tris]

        fig.add_trace(go.Mesh3d(
            x=verts[:, 0], y=verts[:, 1], z=verts[:, 2],
            i=tris[:, 0], j=tris[:, 1], k=tris[:, 2],
            color="#808080",
            opacity=0.85,
            flatshading=True,
            lighting=dict(
                ambient=0.4,
                diffuse=0.6,
                specular=0.2,
                roughness=0.8,
            ),
            lightposition=dict(x=200, y=200, z=300),
            showlegend=False,
            hoverinfo="skip",
            name=mesh.get("name", "Werkstück"),
        ))

    # ── TCP / design trajectories ──
    _traj_colors = {"tcp": "#cc0000", "design": "#cc0000", "trace": "#cc0000"}
    for name, info in cs.items():
        # Static 2-point paths (e.g. TCP design)
        traj = info.get("trajectory")
        name_lower = name.lower()

        if traj is not None and hasattr(traj, "shape") and traj.shape[0] >= 2:
            is_tcp = any(k in name_lower for k in ("tcp", "tool", "trace", "design"))
            if not is_tcp:
                continue
            n = traj.shape[0]
            step = max(1, n // 500)
            sampled = traj[::step]
            fig.add_trace(go.Scatter3d(
                x=sampled[:, 0], y=sampled[:, 1], z=sampled[:, 2],
                mode="lines",
                line=dict(color="#cc0000", width=5),
                name=name,
                showlegend=True,
                hoverinfo="skip",
            ))

    # ── CS labels (positioned at their origin) ──
    # Only label key coordinate systems to avoid clutter
    _label_colors = {
        "tcp": "#cc0000", "design": "#cc0000", "trace": "#cc0000",
        "t1": "#00aa00", "t2": "#00aa00",
        "workpiece": "#333333", "user_frame": "#333333",
        "flange": "#0066cc", "llt": "#0066cc", "xiris": "#0066cc",
    }
    for name, info in cs.items():
        t = info.get("translation")
        if not isinstance(t, dict):
            continue

        # Determine label color based on CS type
        name_lower = name.lower()
        color = "#333333"
        for key, c in _label_colors.items():
            if key in name_lower:
                color = c
                break

        fig.add_trace(go.Scatter3d(
            x=[t["x"]], y=[t["y"]], z=[t["z"]],
            mode="text",
            text=[f"<b>{name}</b>"],
            textposition="top center",
            textfont=dict(size=12, color=color),
            showlegend=False,
            hovertext=f"{name}<br>X={t['x']:.1f} mm<br>Y={t['y']:.1f} mm<br>Z={t['z']:.1f} mm",
            hoverinfo="text",
        ))

    # ── Layout (matching k3d style: light grid background) ──
    grid_style = dict(
        showgrid=True,
        gridcolor="#cccccc",
        showbackground=True,
        backgroundcolor="#f5f5f5",
        gridwidth=1,
    )
    fig.update_layout(
        scene=dict(
            xaxis=dict(title="X (mm)", **grid_style),
            yaxis=dict(title="Y (mm)", **grid_style),
            zaxis=dict(title="Z (mm)", **grid_style),
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        height=650,
        legend=dict(
            yanchor="top", y=0.99,
            xanchor="left", x=0.01,
            bgcolor="rgba(255,255,255,0.8)",
        ),
        paper_bgcolor="white",
    )

    st.plotly_chart(fig, use_container_width=True)


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
