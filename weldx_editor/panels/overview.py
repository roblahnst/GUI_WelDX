"""
WeldX Editor - Dateiübersicht Panel (File Overview Panel)

Displays an overview of the loaded WeldX file including:
- File metadata and general information
- Key metrics (measurements, coordinate systems, completion status)
- Completion status for all categories
- File structure information
"""

import streamlit as st
from weldx_editor.utils.style import (
    COLORS, STATUS_COLORS, STATUS_LABELS, STATUS_ICONS,
    status_badge_html, progress_bar_html, metric_card_html,
)


def render_overview(state):
    """
    Render the file overview panel.

    Args:
        state: WeldxFileState object containing file information
    """

    # =========================================================================
    # TITLE AND SUBTITLE
    # =========================================================================
    st.markdown("## 📄 Datei-Übersicht")

    if state.file_path:
        filename = state.file_path.split("/")[-1] if "/" in state.file_path else state.file_path
        st.markdown(f"**Datei:** `{filename}`")
    else:
        st.markdown("*Keine Datei geladen*")

    st.divider()

    # =========================================================================
    # KEY METRICS (3 COLUMNS)
    # =========================================================================
    st.markdown("### Kennzahlen")

    metric_col1, metric_col2, metric_col3 = st.columns(3)

    # Number of measurements (time series)
    num_measurements = len(state.measurements) if state.measurements else 0
    with metric_col1:
        st.metric(
            label="Zeitserienmessungen",
            value=num_measurements,
            help="Anzahl der in der Datei enthaltenen Messungen"
        )

    # Coordinate systems
    num_cs = len(state.coordinate_systems) if state.coordinate_systems else 0
    with metric_col2:
        st.metric(
            label="Koordinatensysteme",
            value=num_cs,
            help="Anzahl der definierten Koordinatensysteme"
        )

    # Overall completion percentage
    completion_pct = state.overall_completion_pct()
    with metric_col3:
        st.metric(
            label="Gesamtvollständigkeit",
            value=f"{completion_pct}%",
            help="Gesamtvollständigkeit der Datei"
        )

    st.divider()

    # =========================================================================
    # COMPLETION STATUS BY CATEGORY
    # =========================================================================
    st.markdown("### Vollständigkeitsstatus")

    # Define category order and labels in German
    categories = [
        ("workpiece", "Werkstück"),
        ("process", "Prozess"),
        ("measurements", "Messungen"),
        ("coordinates", "Koordinaten"),
        ("quality", "Qualität"),
    ]

    # Create status rows
    for category_key, category_label in categories:
        col1, col2 = st.columns([1, 4])

        if category_key in state.completion:
            completion_info = state.completion[category_key]
            status = completion_info.get("status", "missing")
            detail = completion_info.get("detail", "")

            # Status badge (left column)
            with col1:
                status_html = _get_status_badge(status)
                st.markdown(status_html, unsafe_allow_html=True)

            # Category label and detail (right column)
            with col2:
                detail_text = f" — {detail}" if detail else ""
                st.markdown(f"**{category_label}**{detail_text}")
        else:
            with col1:
                st.markdown(":gray[—]")
            with col2:
                st.markdown(f"**{category_label}** — Keine Information")

    st.divider()

    # =========================================================================
    # FILE METADATA
    # =========================================================================
    st.markdown("### Dateimetadaten")

    if state.metadata and isinstance(state.metadata, dict):
        if state.metadata:
            # Display metadata in a clean format
            metadata_col1, metadata_col2 = st.columns(2)

            items = list(state.metadata.items())
            for idx, (key, value) in enumerate(items):
                if idx % 2 == 0:
                    with metadata_col1:
                        st.markdown(f"**{key}:** `{value}`")
                else:
                    with metadata_col2:
                        st.markdown(f"**{key}:** `{value}`")
        else:
            st.info("Keine Metadaten in der Datei vorhanden")
    else:
        st.info("Keine Metadaten in der Datei vorhanden")

    st.divider()

    # =========================================================================
    # ASDF TREE STRUCTURE
    # =========================================================================
    st.markdown("### ASDF-Baumstruktur")

    with st.expander("🌳 Dateiverzweigung anzeigen", expanded=False):
        if state.tree:
            # Show summarized tree (avoids serialization issues with large arrays)
            from weldx_editor.utils.weldx_io import get_tree_summary
            try:
                summary = get_tree_summary(state)
                st.json(summary, expanded=False)
            except Exception as e:
                st.warning(f"Baumstruktur konnte nicht vollständig dargestellt werden: {e}")
                st.code(str(list(state.tree.keys())), language=None)
        else:
            st.info("Keine Baumstruktur verfügbar")

    st.divider()

    # =========================================================================
    # MEASUREMENTS SECTION (if any exist)
    # =========================================================================
    if state.measurements:
        st.markdown("### Zeitserienmessungen")

        with st.expander("📊 Messungen anzeigen", expanded=False):
            for meas_name, meas_info in state.measurements.items():
                st.markdown(f"**{meas_name}**")

                # Display measurement info
                if isinstance(meas_info, dict):
                    for key, value in meas_info.items():
                        st.markdown(f"- {key}: `{value}`")
                else:
                    st.markdown(f"- {meas_info}")

                st.markdown("")

    # =========================================================================
    # COORDINATE SYSTEMS SECTION (if any exist)
    # =========================================================================
    if state.coordinate_systems:
        st.markdown("### Koordinatensysteme")

        with st.expander("🗂️ Koordinatensysteme anzeigen", expanded=False):
            for cs_name, cs_info in state.coordinate_systems.items():
                st.markdown(f"**{cs_name}**")

                # Display CS info
                if isinstance(cs_info, dict):
                    for key, value in cs_info.items():
                        st.markdown(f"- {key}: `{value}`")
                else:
                    st.markdown(f"- {cs_info}")

                st.markdown("")


def _get_status_badge(status: str) -> str:
    """
    Generate HTML badge for a status indicator.

    Args:
        status: Status string ("complete", "partial", "missing")

    Returns:
        HTML string for the badge
    """
    status_map = {
        "complete": ("✅", COLORS["success"], "Vollständig"),
        "partial": ("⚠️", COLORS["warning"], "Teilweise"),
        "missing": ("❌", COLORS["error"], "Fehlt"),
    }

    icon, color, label = status_map.get(status, ("?", COLORS["text_dim"], "Unbekannt"))

    return f'<span style="font-size: 1.2em;">{icon}</span>'
