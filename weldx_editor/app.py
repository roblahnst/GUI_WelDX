"""
WeldX Editor - Streamlit GUI for enriching WeldX files.
Main application entry point.

Usage:
    streamlit run weldx_editor/app.py
"""
import streamlit as st
import tempfile
import os
from pathlib import Path

from weldx_editor.utils.style import (
    COLORS, NAV_ITEMS, STATUS_ICONS, STATUS_LABELS,
    get_custom_css, progress_bar_html,
)
from weldx_editor.utils.weldx_io import (
    WeldxFileState, load_weldx_file, load_weldx_from_bytes,
    save_weldx_file, get_tree_summary, WELDX_AVAILABLE,
    _update_completion,
)
from weldx_editor.panels.overview import render_overview
from weldx_editor.panels.workpiece import render_workpiece
from weldx_editor.panels.process import render_process
from weldx_editor.panels.measurements import render_measurements
from weldx_editor.panels.coordinates import render_coordinates
from weldx_editor.panels.quality import render_quality
from weldx_editor.utils.session_persistence import (
    save_session, load_session, restore_into_state, clear_session,
)


def init_session_state():
    """Initialize session state variables.

    On first load, try to restore a previously saved session so that
    user-entered data (material, groove params, quality, …) survives a
    browser reload (F5).
    """
    if "state" not in st.session_state:
        st.session_state.state = None
    if "active_panel" not in st.session_state:
        st.session_state.active_panel = "overview"
    if "file_loaded" not in st.session_state:
        st.session_state.file_loaded = False

    # ── Auto-restore from disk on fresh session ────────────
    if st.session_state.state is None:
        saved = load_session()
        if saved:
            file_path = saved.get("file_path")
            restored = False
            # Try to re-open the original .wx file for measurement data
            if file_path and os.path.isfile(file_path):
                try:
                    state = load_weldx_file(file_path)
                    restore_into_state(state, saved)
                    st.session_state.state = state
                    st.session_state.file_loaded = True
                    restored = True
                except Exception:
                    pass
            # If original file not available, restore metadata-only
            if not restored:
                state = WeldxFileState(file_path=file_path)
                restore_into_state(state, saved)
                st.session_state.state = state
                st.session_state.file_loaded = True
            # Restore active panel
            panel = saved.get("active_panel")
            if panel:
                st.session_state.active_panel = panel


def render_sidebar():
    """Render the navigation sidebar."""
    with st.sidebar:
        # App header
        st.markdown("## 🔧 WelDX Editor")
        st.caption("Schweißversuchsdaten anreichern")

        st.divider()

        # File management section
        state = st.session_state.state

        if state and state.file_path:
            st.markdown(f"**Geladene Datei:**")
            st.code(Path(state.file_path).name, language=None)

            # Completion overview
            pct = state.overall_completion_pct()
            st.markdown(f"**Vollständigkeit: {pct}%**")
            st.progress(pct / 100)
            st.divider()
        else:
            st.info("Noch keine Datei geladen")
            st.divider()

        # Navigation
        st.markdown("**Navigation**")

        for item in NAV_ITEMS:
            # Get status for this category
            status_icon = ""
            if state and item["id"] != "overview":
                comp = state.completion.get(
                    item["id"],
                    state.completion.get(
                        {"workpiece": "workpiece", "process": "process",
                         "measurements": "measurements", "coordinates": "coordinates",
                         "quality": "quality"}.get(item["id"], ""),
                        {"status": "missing"}
                    )
                )
                status_icon = STATUS_ICONS.get(comp["status"], "")

            is_active = st.session_state.active_panel == item["id"]
            btn_type = "primary" if is_active else "secondary"
            disabled = not st.session_state.file_loaded and item["id"] != "overview"

            col_label, col_status = st.columns([5, 1])
            with col_label:
                if st.button(
                    f"{item['icon']} {item['label']}",
                    key=f"nav_{item['id']}",
                    use_container_width=True,
                    type=btn_type,
                    disabled=disabled,
                ):
                    st.session_state.active_panel = item["id"]
                    st.rerun()
            with col_status:
                if status_icon:
                    st.markdown(
                        f"<div style='display:flex;align-items:center;"
                        f"justify-content:center;height:42px;'>"
                        f"{status_icon}</div>",
                        unsafe_allow_html=True,
                    )

        st.divider()

        # Save / Validate / Close buttons
        if st.session_state.file_loaded and state:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Speichern", use_container_width=True, type="primary"):
                    _save_file(state)
            with col2:
                if st.button("🛡️ Validieren", use_container_width=True):
                    st.session_state.active_panel = "quality"
                    st.rerun()

            if st.button("🗙 Datei schließen", use_container_width=True):
                clear_session()
                st.session_state.state = None
                st.session_state.file_loaded = False
                st.session_state.active_panel = "overview"
                st.rerun()


def render_file_upload():
    """Render the file upload section when no file is loaded."""
    st.markdown("# 🔧 WelDX Editor")
    st.markdown("### Schweißversuchsdaten laden und anreichern")
    st.markdown("---")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("#### Datei laden")
        st.markdown(
            "Laden Sie eine WelDX-Datei (.weldx, .wx, .asdf) aus einem "
            "RoboScope-Export oder einer anderen Quelle."
        )

        uploaded_file = st.file_uploader(
            "WelDX-Datei auswählen",
            type=["weldx", "wx", "asdf", "hdf5"],
            help="Unterstützte Formate: .weldx, .wx, .asdf",
        )

        if uploaded_file is not None:
            with st.spinner("Datei wird geladen..."):
                try:
                    state = load_weldx_from_bytes(
                        uploaded_file.getvalue(),
                        uploaded_file.name,
                    )
                    st.session_state.state = state
                    st.session_state.file_loaded = True
                    st.success(f"✅ **{uploaded_file.name}** erfolgreich geladen!")
                    st.rerun()
                except ImportError:
                    st.error(
                        "❌ Das **weldx**-Paket ist nicht installiert. "
                        "Bitte installieren Sie es mit:\n\n"
                        "```\npip install weldx\n```"
                    )
                except Exception as e:
                    st.error(f"❌ Fehler beim Laden: {e}")

        st.markdown("---")

        # Option to start with empty file
        st.markdown("#### Oder: Neue Datei erstellen")
        if st.button("📝 Leere WelDX-Datei starten", use_container_width=True):
            state = WeldxFileState(file_path="neue_datei.weldx")
            st.session_state.state = state
            st.session_state.file_loaded = True
            st.rerun()

        # Demo mode
        st.markdown("#### Demo-Modus")
        if st.button("🎯 Mit Demo-Daten starten", use_container_width=True):
            state = _create_demo_state()
            st.session_state.state = state
            st.session_state.file_loaded = True
            st.rerun()

    with col2:
        st.markdown("#### Voraussetzungen")

        if WELDX_AVAILABLE:
            st.success("✅ weldx installiert")
            import weldx
            st.caption(f"Version: {weldx.__version__}")
        else:
            st.warning("⚠️ weldx nicht installiert")
            st.caption("Demo-Modus ist verfügbar")

        st.markdown("#### So funktioniert's")
        st.markdown(
            "1. **Laden** Sie eine .weldx-Datei\n"
            "2. **Ergänzen** Sie fehlende Metadaten\n"
            "3. **Speichern** Sie die angereicherte Datei"
        )

        st.markdown("#### Unterstützte Daten")
        st.markdown(
            "- Werkstück & Material\n"
            "- Nahtgeometrie (ISO 9692-1)\n"
            "- Schweißverfahren & Schutzgas\n"
            "- Messdaten & Messketten\n"
            "- Koordinatensysteme\n"
            "- Qualitätsstandards (ISO 5817)"
        )


def _create_demo_state() -> WeldxFileState:
    """Create a demo state with sample data for testing."""
    state = WeldxFileState(file_path="demo_experiment.weldx")

    # Simulate RoboScope measurement data
    state.measurements = {
        "welding_current": {
            "name": "welding_current",
            "status": "present",
            "type": "TimeSeries",
            "samples": 24000,
            "unit": "A",
            "min": 120.3,
            "max": 185.7,
            "range": "120.3-185.7",
        },
        "welding_voltage": {
            "name": "welding_voltage",
            "status": "present",
            "type": "TimeSeries",
            "samples": 24000,
            "unit": "V",
            "min": 18.2,
            "max": 24.1,
            "range": "18.2-24.1",
        },
        "wire_feed_speed": {
            "name": "wire_feed_speed",
            "status": "present",
            "type": "TimeSeries",
            "samples": 24000,
            "unit": "m/min",
            "min": 4.2,
            "max": 6.8,
            "range": "4.2-6.8",
        },
    }

    # Simulate some coordinate systems
    state.coordinate_systems = {
        "robot_base": {"name": "robot_base", "status": "present"},
        "tcp": {"name": "tcp", "status": "present"},
    }

    # Metadata from RoboScope export
    state.metadata = {
        "experiment_date": "2026-03-20T14:30:00",
        "operator": "R. Lahnsteiner",
        "roboscope_version": "2.4.1",
        "sampling_rate": "1000 Hz",
        "welding_duration": "24.0 s",
    }

    # Update completion
    state.completion = {
        "workpiece": {"status": "missing", "detail": "Material, Naht, Geometrie fehlen"},
        "process": {"status": "partial", "detail": "Messdaten vorhanden, Prozess-Typ fehlt"},
        "measurements": {"status": "complete", "detail": "3 Zeitreihen (Strom, Spannung, Drahtvorschub)"},
        "coordinates": {"status": "partial", "detail": "Robot-Base & TCP vorhanden, Werkstück fehlt"},
        "quality": {"status": "missing", "detail": "Keine Bewertungsgruppe definiert"},
    }

    return state


def _save_file(state: WeldxFileState):
    """Save the current state to a WelDX file."""
    if not WELDX_AVAILABLE:
        st.sidebar.warning("⚠️ Speichern erfordert das weldx-Paket")
        return

    try:
        # Create a download
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".weldx")
        save_weldx_file(state, tmp.name)

        with open(tmp.name, "rb") as f:
            data = f.read()

        filename = Path(state.file_path).stem + "_enriched.weldx"

        st.sidebar.download_button(
            label="⬇️ Datei herunterladen",
            data=data,
            file_name=filename,
            mime="application/octet-stream",
            use_container_width=True,
        )
        st.sidebar.success("✅ Datei bereit zum Download")

        os.unlink(tmp.name)
    except Exception as e:
        st.sidebar.error(f"❌ Fehler beim Speichern: {e}")


def render_main_content():
    """Render the main content area based on active panel."""
    state = st.session_state.state
    panel = st.session_state.active_panel

    if panel == "overview":
        render_overview(state)
    elif panel == "workpiece":
        render_workpiece(state)
    elif panel == "process":
        render_process(state)
    elif panel == "measurements":
        render_measurements(state)
    elif panel == "coordinates":
        render_coordinates(state)
    elif panel == "quality":
        render_quality(state)


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="WelDX Editor",
        page_icon="🔧",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Inject custom CSS
    st.markdown(get_custom_css(), unsafe_allow_html=True)

    # Initialize session state
    init_session_state()

    if st.session_state.file_loaded and st.session_state.state:
        # Refresh completion status from current state
        _update_completion(st.session_state.state)

        # File is loaded - show sidebar + content
        render_sidebar()
        render_main_content()

        # ── Auto-save after every render cycle ──────────────
        _auto_save()
    else:
        # No file - show upload screen
        render_sidebar()
        render_file_upload()


def _auto_save():
    """Persist current user-editable state to disk (silent, no UI)."""
    state = st.session_state.state
    if state is None:
        return
    save_session(state, active_panel=st.session_state.active_panel)


if __name__ == "__main__":
    main()
