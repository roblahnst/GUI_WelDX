import streamlit as st
import numpy as np
from weldx_editor.utils.style import COLORS


# Material database for different material groups
MATERIALS_DB = {
    "Stähle": {
        "S235JR (1.0038) — EN 10025-2": {
            "yield_strength": 235,  # MPa
            "tensile_strength": 360,  # MPa
            "density": 7850,  # kg/m³
        },
        "S355J2 (1.0577) — EN 10025-2": {
            "yield_strength": 355,
            "tensile_strength": 510,
            "density": 7850,
        },
        "P265GH (1.0425) — EN 10028-2": {
            "yield_strength": 265,
            "tensile_strength": 430,
            "density": 7850,
        },
        "X5CrNi18-10 (1.4301) — EN 10088-2": {
            "yield_strength": 210,
            "tensile_strength": 500,
            "density": 8000,
        },
        "Benutzerdefiniert": {
            "yield_strength": None,
            "tensile_strength": None,
            "density": None,
        },
    },
    "Aluminium": {
        "EN AW-5083 H32": {
            "yield_strength": 215,
            "tensile_strength": 305,
            "density": 2660,
        },
        "EN AW-6061 T6": {
            "yield_strength": 275,
            "tensile_strength": 310,
            "density": 2700,
        },
        "Benutzerdefiniert": {
            "yield_strength": None,
            "tensile_strength": None,
            "density": None,
        },
    },
    "Nickel-Legierungen": {
        "Inconel 625": {
            "yield_strength": 414,
            "tensile_strength": 965,
            "density": 8440,
        },
        "Benutzerdefiniert": {
            "yield_strength": None,
            "tensile_strength": None,
            "density": None,
        },
    },
    "Titan-Legierungen": {
        "Ti-6Al-4V": {
            "yield_strength": 880,
            "tensile_strength": 930,
            "density": 4430,
        },
        "Benutzerdefiniert": {
            "yield_strength": None,
            "tensile_strength": None,
            "density": None,
        },
    },
}

GROOVE_TYPES = {
    "V-Naht": ["alpha", "b", "c"],
    "I-Naht": ["b"],
    "HV-Naht": ["beta", "b", "c"],
    "U-Naht": ["beta", "R", "c", "b"],
    "X-Naht (Doppel-V)": ["alpha_1", "alpha_2", "c", "b"],
}



def _get_groove_object(groove_type: str, params: dict):
    """
    Create a WeldX groove object using the ISO 9692-1 API.

    Groove classes and their weldx parameters:
      VGroove:  t, alpha (groove_angle), c (root_face), b (root_gap)
      IGroove:  t, b (root_gap)
      HVGroove: t, beta (bevel_angle), c (root_face), b (root_gap)
      UGroove:  t, beta (bevel_angle), R (bevel_radius), c (root_face), b (root_gap)
      DVGroove: t, alpha_1 (groove_angle), alpha_2 (groove_angle2), c (root_face), b (root_gap)
    """
    try:
        from weldx import Q_
        from weldx.welding.groove.iso_9692_1 import get_groove

        t = Q_(params.get("t", 10), "mm")

        if groove_type == "V-Naht":
            return get_groove(
                groove_type="VGroove",
                workpiece_thickness=t,
                groove_angle=Q_(params.get("alpha", 60), "deg"),
                root_face=Q_(params.get("c", 1), "mm"),
                root_gap=Q_(params.get("b", 2), "mm"),
            )
        elif groove_type == "I-Naht":
            return get_groove(
                groove_type="IGroove",
                workpiece_thickness=t,
                root_gap=Q_(params.get("b", 2), "mm"),
            )
        elif groove_type == "HV-Naht":
            return get_groove(
                groove_type="HVGroove",
                workpiece_thickness=t,
                bevel_angle=Q_(params.get("beta", 50), "deg"),
                root_face=Q_(params.get("c", 1), "mm"),
                root_gap=Q_(params.get("b", 2), "mm"),
            )
        elif groove_type == "U-Naht":
            return get_groove(
                groove_type="UGroove",
                workpiece_thickness=t,
                bevel_angle=Q_(params.get("beta", 8), "deg"),
                bevel_radius=Q_(params.get("R", 6), "mm"),
                root_face=Q_(params.get("c", 1), "mm"),
                root_gap=Q_(params.get("b", 2), "mm"),
            )
        elif groove_type == "X-Naht (Doppel-V)":
            return get_groove(
                groove_type="DVGroove",
                workpiece_thickness=t,
                groove_angle=Q_(params.get("alpha_1", 50), "deg"),
                groove_angle2=Q_(params.get("alpha_2", 60), "deg"),
                root_face=Q_(params.get("c", 2), "mm"),
                root_gap=Q_(params.get("b", 2), "mm"),
            )
        return None
    except ImportError:
        return None
    except Exception as e:
        st.warning(f"Fehler beim Erstellen des Nutobjekts: {e}")
        return None


def _render_basismaterial_tab(state):
    """Render the base material tab."""
    st.subheader("Basismaterial")

    # Initialize base_metal if not present
    if not hasattr(state, "base_metal") or state.base_metal is None:
        state.base_metal = {
            "material_group": "Stähle",
            "material": None,
            "plate_thickness": 10.0,
        }

    # Show info if material was detected from metadata
    designation = state.base_metal.get("designation", "")
    if designation:
        st.success(f"✅ Material aus Datei erkannt: **{designation}**")

    col1, col2 = st.columns(2)

    with col1:
        material_group = st.radio(
            "Werkstoffgruppe:",
            list(MATERIALS_DB.keys()),
            index=list(MATERIALS_DB.keys()).index(state.base_metal.get("material_group", "Stähle")),
        )
        state.base_metal["material_group"] = material_group

    with col2:
        available_materials = list(MATERIALS_DB[material_group].keys())
        selected_material = st.selectbox(
            "Werkstoff:",
            available_materials,
            index=available_materials.index(state.base_metal.get("material", available_materials[0]))
            if state.base_metal.get("material") in available_materials
            else 0,
        )
        state.base_metal["material"] = selected_material

    plate_thickness = st.number_input(
        "Blechdicke (mm):",
        min_value=0.5,
        max_value=100.0,
        value=float(state.base_metal.get("plate_thickness", 10.0)),
        step=0.5,
    )
    state.base_metal["plate_thickness"] = plate_thickness

    # Display material properties if available
    if selected_material and selected_material != "Benutzerdefiniert":
        props = MATERIALS_DB[material_group][selected_material]
        if props["yield_strength"] is not None:
            info_text = f"""
            **Werkstoffeigenschaften:**
            - Streckgrenze: {props['yield_strength']} MPa
            - Zugfestigkeit: {props['tensile_strength']} MPa
            - Dichte: {props['density']} kg/m³
            """
            st.info(info_text)
    else:
        st.info("Benutzerdefinierter Werkstoff: Bitte geben Sie die Werkstoffeigenschaften ein")


def _render_groove_tab(state):
    """Render the groove geometry tab."""
    st.subheader("Nahtgeometrie (ISO 9692-1)")

    # Initialize groove if not present
    if not hasattr(state, "groove") or state.groove is None:
        state.groove = {
            "type": "V-Naht",
            "params": {},
        }

    groove_type = st.selectbox(
        "Nahttyp:",
        list(GROOVE_TYPES.keys()),
        index=list(GROOVE_TYPES.keys()).index(state.groove.get("type", "V-Naht"))
        if isinstance(state.groove, dict)
        else 0,
    )

    if isinstance(state.groove, dict):
        state.groove["type"] = groove_type
        if "params" not in state.groove:
            state.groove["params"] = {}
    else:
        state.groove = {"type": groove_type, "params": {}}

    # Render parameter inputs based on groove type
    st.markdown("**Parameter:**")
    params = state.groove.get("params", {})
    # Ensure all param values are float (JSON restore may yield int)
    params = {k: float(v) if isinstance(v, (int, float)) else v for k, v in params.items()}

    if groove_type == "V-Naht":
        alpha = st.number_input(
            "Öffnungswinkel α (°):",
            min_value=10.0,
            max_value=90.0,
            value=params.get("alpha", 60.0),
            step=1.0,
        )
        b = st.number_input(
            "Spalt b (mm):",
            min_value=0.5,
            max_value=20.0,
            value=params.get("b", 2.0),
            step=0.5,
        )
        c = st.number_input(
            "Steg c (mm):",
            min_value=0.0,
            max_value=10.0,
            value=params.get("c", 1.0),
            step=0.5,
        )
        params = {"alpha": alpha, "b": b, "c": c}

    elif groove_type == "I-Naht":
        b = st.number_input(
            "Spalt b (mm):",
            min_value=0.5,
            max_value=20.0,
            value=params.get("b", 2.0),
            step=0.5,
        )
        params = {"b": b}

    elif groove_type == "HV-Naht":
        beta = st.number_input(
            "Flankenwinkel β (°):",
            min_value=5.0,
            max_value=90.0,
            value=params.get("beta", 50.0),
            step=1.0,
            help="Winkel der angeschrägten Seite (die andere Seite bleibt senkrecht)",
        )
        b = st.number_input(
            "Spalt b (mm):",
            min_value=0.0,
            max_value=20.0,
            value=params.get("b", 2.0),
            step=0.5,
        )
        c = st.number_input(
            "Steg c (mm):",
            min_value=0.0,
            max_value=10.0,
            value=params.get("c", 1.0),
            step=0.5,
        )
        params = {"beta": beta, "b": b, "c": c}

    elif groove_type == "U-Naht":
        beta = st.number_input(
            "Flankenwinkel β (°):",
            min_value=0.0,
            max_value=45.0,
            value=params.get("beta", 8.0),
            step=1.0,
            help="Winkel der Flanken oberhalb des Radius",
        )
        R = st.number_input(
            "Radius R (mm):",
            min_value=1.0,
            max_value=30.0,
            value=params.get("R", 6.0),
            step=0.5,
            help="Rundungsradius am Nutgrund",
        )
        c = st.number_input(
            "Steg c (mm):",
            min_value=0.0,
            max_value=10.0,
            value=params.get("c", 1.0),
            step=0.5,
        )
        b = st.number_input(
            "Spalt b (mm):",
            min_value=0.0,
            max_value=20.0,
            value=params.get("b", 2.0),
            step=0.5,
        )
        params = {"beta": beta, "R": R, "c": c, "b": b}

    elif groove_type == "X-Naht (Doppel-V)":
        col1, col2 = st.columns(2)
        with col1:
            alpha_1 = st.number_input(
                "Winkel oben α₁ (°):",
                min_value=10.0,
                max_value=90.0,
                value=params.get("alpha_1", 50.0),
                step=1.0,
                help="Öffnungswinkel der oberen V-Naht",
            )
        with col2:
            alpha_2 = st.number_input(
                "Winkel unten α₂ (°):",
                min_value=10.0,
                max_value=90.0,
                value=params.get("alpha_2", 60.0),
                step=1.0,
                help="Öffnungswinkel der unteren V-Naht",
            )
        c = st.number_input(
            "Steg c (mm):",
            min_value=0.0,
            max_value=10.0,
            value=params.get("c", 2.0),
            step=0.5,
            help="Höhe des Stegs in der Mitte",
        )
        b = st.number_input(
            "Spalt b (mm):",
            min_value=0.0,
            max_value=20.0,
            value=params.get("b", 2.0),
            step=0.5,
        )
        params = {"alpha_1": alpha_1, "alpha_2": alpha_2, "c": c, "b": b}

    state.groove["params"] = params

    # Try to create groove object and render preview
    groove_obj = _get_groove_object(groove_type, params)
    if groove_obj:
        st.success("✅ Nutobjekt erfolgreich erstellt")
        state.groove["object"] = groove_obj

        st.markdown("---")

        # ─── Extract profile data for both views ─────────────
        profile_data = None
        try:
            from weldx import Q_

            profile = groove_obj.to_profile(width_default=Q_(2, "mm"))

            # Collect points from each shape, rasterizing arcs for smooth curves
            shape_point_lists = []
            for shape in profile.shapes:
                pts = []
                for seg in shape.segments:
                    seg_type = type(seg).__name__
                    if seg_type == "ArcSegment":
                        raster = seg.rasterize(raster_width=Q_(0.5, "mm"))
                        arc_pts = raster.m.T
                        for pt in arc_pts[:-1]:
                            pts.append((float(pt[0]), float(pt[1])))
                    else:
                        start = seg.point_start.m
                        pts.append((float(start[0]), float(start[1])))
                last_end = shape.segments[-1].point_end.m
                pts.append((float(last_end[0]), float(last_end[1])))
                shape_point_lists.append(pts)

            # Build closed outline: left half bottom→top, right half top→bottom
            left_pts = [p for spl in shape_point_lists for p in spl if p[0] <= 0.01]
            right_pts = [p for spl in shape_point_lists for p in spl if p[0] >= -0.01]
            left_pts.sort(key=lambda p: p[1])
            right_pts.sort(key=lambda p: p[1], reverse=True)
            outline = left_pts + right_pts
            if outline and outline[0] != outline[-1]:
                outline.append(outline[0])
            profile_data = outline
        except Exception:
            pass

        # ─── Side-by-side: 2D + 3D ───────────────────────────
        col_2d, col_3d = st.columns(2)

        with col_2d:
            st.markdown("**Querschnitt (2D):**")
            try:
                import matplotlib
                matplotlib.use("Agg")
                import matplotlib.pyplot as plt

                fig, ax = plt.subplots(figsize=(5, 4))
                groove_obj.plot(ax=ax)

                ax.set_aspect("equal")
                ax.set_xlabel("Breite [mm]")
                ax.set_ylabel("Höhe [mm]")
                ax.set_title(f"{groove_type} — ISO 9692-1")
                ax.grid(True, alpha=0.3, color="#cccccc")

                fig.patch.set_facecolor("white")
                ax.set_facecolor("white")
                ax.tick_params(colors="#333333")
                ax.xaxis.label.set_color("#333333")
                ax.yaxis.label.set_color("#333333")
                ax.title.set_color("#111111")
                for spine in ax.spines.values():
                    spine.set_color("#999999")

                st.pyplot(fig)
                plt.close(fig)
            except Exception as e:
                st.warning(f"2D-Vorschau nicht möglich: {e}")

        with col_3d:
            st.markdown("**3D-Vorschau:**")
            try:
                import plotly.graph_objects as go

                if not profile_data or len(profile_data) < 3:
                    raise ValueError("Profil-Geometrie nicht extrahierbar")

                # Cross-section in X (width) / Z (height), extruded along Y (seam)
                cx = [p[0] for p in profile_data]
                cz = [p[1] for p in profile_data]
                seam_len = max(
                    max(cx) - min(cx),
                    max(cz) - min(cz),
                ) * 3  # proportional seam length

                fig3d = go.Figure()

                # Front + back face outlines
                for y_val, name in [(0.0, "Vorderseite"), (seam_len, "Rückseite")]:
                    fig3d.add_trace(go.Scatter3d(
                        x=cx, y=[y_val] * len(cx), z=cz,
                        mode="lines",
                        line=dict(color="#4f8ef7", width=4),
                        name=name,
                        showlegend=False,
                    ))

                # Filled front + back faces
                for y_fill in [0.0, seam_len]:
                    fig3d.add_trace(go.Mesh3d(
                        x=cx, y=[y_fill] * len(cx), z=cz,
                        color="#4f8ef7", opacity=0.15,
                        delaunayaxis="y", showlegend=False,
                    ))

                # Side surface mesh (extrusion walls)
                n = len(cx) - 1
                wx, wy, wz = [], [], []
                wi, wj, wk = [], [], []
                for idx in range(n):
                    base = len(wx)
                    wx.extend([cx[idx], cx[idx + 1], cx[idx], cx[idx + 1]])
                    wy.extend([0, 0, seam_len, seam_len])
                    wz.extend([cz[idx], cz[idx + 1], cz[idx], cz[idx + 1]])
                    wi.extend([base, base])
                    wj.extend([base + 1, base + 2])
                    wk.extend([base + 2, base + 3])
                fig3d.add_trace(go.Mesh3d(
                    x=wx, y=wy, z=wz,
                    i=wi, j=wj, k=wk,
                    color="#4f8ef7", opacity=0.3,
                    showlegend=False,
                ))

                fig3d.update_layout(
                    scene=dict(
                        xaxis_title="Breite [mm]",
                        yaxis_title="Nahtlänge [mm]",
                        zaxis_title="Höhe [mm]",
                        aspectmode="data",
                        bgcolor="white",
                        xaxis=dict(gridcolor="#ddd", color="#333", backgroundcolor="white"),
                        yaxis=dict(gridcolor="#ddd", color="#333", backgroundcolor="white"),
                        zaxis=dict(gridcolor="#ddd", color="#333", backgroundcolor="white"),
                        camera=dict(
                            eye=dict(x=1.5, y=1.5, z=0.8),
                            up=dict(x=0, y=0, z=1),
                        ),
                    ),
                    paper_bgcolor="white",
                    font=dict(color="#333333"),
                    height=420,
                    margin=dict(l=0, r=0, t=10, b=0),
                )
                st.plotly_chart(fig3d, use_container_width=True)
            except Exception as e:
                st.info(f"3D-Vorschau nicht verfügbar: {e}")
    else:
        st.warning(
            "Nutobjekt konnte nicht erstellt werden. "
            "Stellen Sie sicher, dass **weldx** installiert ist."
        )


def _render_workpiece_geometry_tab(state):
    """Render the workpiece geometry tab."""
    st.subheader("Werkstück-Geometrie")

    # Initialize tree if not present
    if not hasattr(state, "tree") or state.tree is None:
        state.tree = {
            "seam_length": 100.0,
            "welding_speed": 500.0,
        }

    col1, col2 = st.columns(2)

    with col1:
        seam_length = st.number_input(
            "Nahtlänge (mm):",
            min_value=1.0,
            max_value=10000.0,
            value=float(state.tree.get("seam_length", 100.0)),
            step=10.0,
        )
        state.tree["seam_length"] = seam_length

    with col2:
        welding_speed = st.number_input(
            "Schweißgeschwindigkeit (mm/s):",
            min_value=0.1,
            max_value=1000.0,
            value=float(state.tree.get("welding_speed", 500.0)),
            step=10.0,
        )
        state.tree["welding_speed"] = welding_speed

    st.info(
        "**Komplexe 3D-Schweißbahnen:** Sie können komplexe 3D-Schweißpfade aus "
        "CSM-Dateien oder als CSV-Pfaddaten importieren. Dies ermöglicht realistische "
        "Schweißbahnen für mehrdimensionale Strukturen."
    )

    st.markdown("**CSV-Pfaddaten (optional):**")
    uploaded_file = st.file_uploader(
        "CSV-Datei mit Schweißbahnkoordinaten hochladen",
        type=["csv"],
        help="Erwartet Spalten: x, y, z (oder ähnlich)",
    )

    if uploaded_file is not None:
        try:
            import pandas as pd

            df = pd.read_csv(uploaded_file)
            st.success(f"CSV geladen: {len(df)} Zeilen")

            # Display a preview
            st.dataframe(df.head(10), use_container_width=True)

            # Store the path data
            state.tree["path_data"] = df.to_dict(orient="list")
        except Exception as e:
            st.error(f"Fehler beim Laden der CSV-Datei: {e}")


def render_workpiece(state):
    """
    Main render function for the workpiece panel.

    Parameters
    ----------
    state : WeldxFileState
        The application state object with attributes:
        - state.base_metal: dict with material information
        - state.groove: dict or object with groove geometry
        - state.tree: dict with workpiece geometry parameters
    """
    st.markdown("## Werkstück-Konfiguration")

    # Create three tabs
    tab1, tab2, tab3 = st.tabs([
        "Basismaterial",
        "Nahtgeometrie (ISO 9692-1)",
        "Werkstück-Geometrie",
    ])

    with tab1:
        _render_basismaterial_tab(state)

    with tab2:
        _render_groove_tab(state)

    with tab3:
        _render_workpiece_geometry_tab(state)
