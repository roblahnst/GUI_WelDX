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

# Axis colors: X=red, Y=green, Z=blue
_AXIS_COLORS = ["#e74c3c", "#2ecc71", "#3498db"]
_AXIS_LABELS = ["X", "Y", "Z"]


def _render_3d_visualization(state):
    """Render an interactive 3D Plotly visualization of all coordinate systems."""
    cs = state.coordinate_systems
    if not cs:
        st.info("Keine Koordinatensysteme vorhanden.")
        return

    # Check if any CS has actual translation data
    has_transforms = any(
        isinstance(info.get("translation"), dict)
        for info in cs.values()
    )
    if not has_transforms:
        st.info("Keine Transformationsdaten vorhanden.")
        return

    st.subheader("3D-Visualisierung")

    fig = go.Figure()

    # Compute axis arrow length relative to scene extent
    positions = []
    for info in cs.values():
        t = info.get("translation")
        if isinstance(t, dict):
            positions.append([t["x"], t["y"], t["z"]])
    positions = np.array(positions)
    extent = np.ptp(positions, axis=0).max() if len(positions) > 1 else 100.0
    arrow_len = max(extent * 0.06, 5.0)

    # Draw each coordinate system
    for name, info in cs.items():
        t = info.get("translation")
        if not isinstance(t, dict):
            continue
        origin = np.array([t["x"], t["y"], t["z"]])
        orient = info.get("orientation")
        if orient is not None:
            R = np.array(orient)
        else:
            R = np.eye(3)

        # Draw 3 axis arrows
        for axis_idx in range(3):
            direction = R[:, axis_idx] if R.ndim == 2 else np.eye(3)[:, axis_idx]
            tip = origin + direction * arrow_len
            color = _AXIS_COLORS[axis_idx]

            # Axis line
            fig.add_trace(go.Scatter3d(
                x=[origin[0], tip[0]],
                y=[origin[1], tip[1]],
                z=[origin[2], tip[2]],
                mode="lines",
                line=dict(color=color, width=4),
                showlegend=False,
                hoverinfo="skip",
            ))

            # Arrowhead cone
            fig.add_trace(go.Cone(
                x=[tip[0]], y=[tip[1]], z=[tip[2]],
                u=[direction[0]], v=[direction[1]], w=[direction[2]],
                sizemode="absolute",
                sizeref=arrow_len * 0.3,
                colorscale=[[0, color], [1, color]],
                showscale=False,
                showlegend=False,
                hoverinfo="skip",
            ))

        # Origin marker + label
        fig.add_trace(go.Scatter3d(
            x=[origin[0]], y=[origin[1]], z=[origin[2]],
            mode="markers+text",
            marker=dict(size=4, color="#2c3e50"),
            text=[name],
            textposition="top center",
            textfont=dict(size=10, color="#2c3e50"),
            showlegend=False,
            hovertext=f"{name}<br>X={origin[0]:.1f}<br>Y={origin[1]:.1f}<br>Z={origin[2]:.1f}",
            hoverinfo="text",
        ))

        # Connection line to parent
        parent_name = info.get("parent")
        if parent_name and parent_name in cs:
            pt = cs[parent_name].get("translation")
            if isinstance(pt, dict):
                parent_pos = [pt["x"], pt["y"], pt["z"]]
                fig.add_trace(go.Scatter3d(
                    x=[parent_pos[0], origin[0]],
                    y=[parent_pos[1], origin[1]],
                    z=[parent_pos[2], origin[2]],
                    mode="lines",
                    line=dict(color="#bdc3c7", width=1, dash="dash"),
                    showlegend=False,
                    hoverinfo="skip",
                ))

    # Draw trajectories for TCP-related coordinate systems
    _TRAJ_COLORS = ["#f39c12", "#e67e22", "#d35400"]
    traj_idx = 0
    for name, info in cs.items():
        traj = info.get("trajectory")
        if traj is None or not hasattr(traj, "shape") or traj.shape[0] <= 2:
            continue
        # Only show trajectories for TCP-like systems (the actual tool path)
        name_lower = name.lower()
        if not any(k in name_lower for k in ("tcp", "tool", "trace")):
            continue
        # Downsample for performance (max 2000 points)
        n = traj.shape[0]
        step = max(1, n // 2000)
        sampled = traj[::step]
        color = _TRAJ_COLORS[traj_idx % len(_TRAJ_COLORS)]
        fig.add_trace(go.Scatter3d(
            x=sampled[:, 0], y=sampled[:, 1], z=sampled[:, 2],
            mode="lines",
            line=dict(color=color, width=3),
            name=f"{name} Trajektorie",
            showlegend=True,
            hoverinfo="skip",
        ))
        traj_idx += 1

    # Layout
    fig.update_layout(
        scene=dict(
            xaxis_title="X (mm)",
            yaxis_title="Y (mm)",
            zaxis_title="Z (mm)",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        height=600,
        legend=dict(
            yanchor="top", y=0.99,
            xanchor="left", x=0.01,
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Legend for axis colors
    st.caption(
        "Achsenfarben: "
        "<span style='color:#e74c3c'>X</span> / "
        "<span style='color:#2ecc71'>Y</span> / "
        "<span style='color:#3498db'>Z</span>"
        " &mdash; gestrichelte Linien: Parent-Verbindungen"
        " &mdash; <span style='color:#f39c12'>orange</span>: Trajektorie",
        unsafe_allow_html=True,
    )


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
