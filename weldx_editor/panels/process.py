"""
WeldX Editor - Schweißprozess Panel

Displays and allows editing of:
1. Schweißverfahren (process tag, base_process, manufacturer, power_source)
2. Schutzgas (shielding gas composition and flowrate)
3. Zusatzwerkstoff (filler material / wire)

Reads from state.process and state.shielding_gas as populated by weldx_io.py.
"""
import streamlit as st
from weldx_editor.utils.style import COLORS


def render_process(state):
    tab1, tab2, tab3 = st.tabs([
        "⚡ Schweißverfahren",
        "💨 Schutzgas (ISO 14175)",
        "🔩 Zusatzwerkstoff",
    ])

    with tab1:
        _render_welding_process(state)
    with tab2:
        _render_shielding_gas(state)
    with tab3:
        _render_filler_material(state)


# ─── Tab 1: Schweißverfahren ─────────────────────────────────

def _render_welding_process(state):
    st.header("Schweißverfahren")

    proc = state.process if isinstance(state.process, dict) else {}

    # Show existing data from file
    tag = proc.get("tag", "")
    base = proc.get("base_process", "")
    manufacturer = proc.get("manufacturer", "")
    power_source = proc.get("power_source", "")

    if tag or manufacturer:
        st.success(f"✅ Prozessdaten aus Datei erkannt")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Verfahren", tag if tag else "—")
            st.metric("Hersteller", manufacturer if manufacturer else "—")
        with col2:
            st.metric("Prozesstyp", base if base else "—")
            st.metric("Stromquelle", power_source if power_source else "—")

        st.divider()

    # Editable fields
    st.subheader("Verfahren bearbeiten")

    # Process tag
    tag_options = ["GMAW", "GTAW", "SAW", "SMAW"]
    tag_index = tag_options.index(tag) if tag in tag_options else 0
    new_tag = st.selectbox(
        "Schweißverfahren (Tag)",
        options=tag_options,
        index=tag_index,
        key="proc_tag",
    )
    state.process["tag"] = new_tag

    # Base process
    if new_tag == "GMAW":
        base_options = ["pulse", "spray", "short_circuit", "CMT", "other"]
    elif new_tag == "GTAW":
        base_options = ["DC", "AC", "pulse", "other"]
    else:
        base_options = ["standard", "other"]

    base_index = base_options.index(base) if base in base_options else 0
    new_base = st.selectbox(
        "Prozesstyp (base_process)",
        options=base_options,
        index=base_index,
        key="proc_base",
    )
    state.process["base_process"] = new_base

    col1, col2 = st.columns(2)
    with col1:
        new_mfr = st.text_input("Hersteller", value=manufacturer, key="proc_mfr")
        state.process["manufacturer"] = new_mfr
    with col2:
        new_ps = st.text_input("Stromquelle", value=power_source, key="proc_ps")
        state.process["power_source"] = new_ps

    # Check for existing measurement time series
    existing_ts = []
    if isinstance(state.measurements, dict):
        for key in ["welding_current", "welding_voltage", "wire_speed", "gas_flow"]:
            if key in state.measurements:
                info = state.measurements[key]
                samples = info.get("samples", "?")
                unit = info.get("unit", "")
                existing_ts.append(f"{key} ({samples} Samples, {unit})")

    if existing_ts:
        st.info("📊 **Vorhandene Prozess-Zeitreihen:** " + " · ".join(existing_ts))


# ─── Tab 2: Schutzgas ────────────────────────────────────────

def _render_shielding_gas(state):
    st.header("Schutzgas (ISO 14175)")

    gas = state.shielding_gas if isinstance(state.shielding_gas, dict) else {}

    # Show existing data from file
    common_name = gas.get("common_name", "")
    components = gas.get("components", [])
    flowrate_value = gas.get("flowrate_value", "")
    flowrate_unit = gas.get("flowrate_unit", "")

    if common_name or components:
        st.success("✅ Schutzgas-Daten aus Datei erkannt")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Schutzgas", common_name if common_name else "—")
        with col2:
            fr_display = f"{flowrate_value} {flowrate_unit}" if flowrate_value else "—"
            st.metric("Durchflussrate", fr_display)

        if components:
            st.markdown("**Zusammensetzung:**")
            for comp in components:
                name = comp.get("name", "?")
                pct = comp.get("percentage", "?")
                st.markdown(f"- **{name.capitalize()}**: {pct}%")

        st.divider()

    # Editable section
    st.subheader("Schutzgas bearbeiten")

    gas_presets = {
        "I1 — 100% Argon": {"Ar": 100},
        "M21 — 82% Ar / 18% CO₂": {"Ar": 82, "CO2": 18},
        "M12 — 98% Ar / 2% CO₂": {"Ar": 98, "CO2": 2},
        "C1 — 100% CO₂": {"CO2": 100},
        "Benutzerdefiniert": {},
    }

    # Try to match existing gas to preset
    preset_index = 0
    if common_name:
        for i, (label, _) in enumerate(gas_presets.items()):
            if common_name.lower().replace(" ", "") in label.lower().replace(" ", ""):
                preset_index = i
                break
        # Match "Ar 100%" -> I1
        if "ar" in common_name.lower() and "100" in common_name:
            preset_index = 0

    selected_preset = st.selectbox(
        "Schutzgas-Mischung",
        options=list(gas_presets.keys()),
        index=preset_index,
        key="gas_preset",
    )

    if "Benutzerdefiniert" in selected_preset:
        col1, col2 = st.columns(2)
        with col1:
            ar_pct = st.slider("Argon (%)", 0, 100, 80, key="gas_ar")
            co2_pct = st.slider("CO₂ (%)", 0, 100, 20, key="gas_co2")
        with col2:
            o2_pct = st.slider("O₂ (%)", 0, 100, 0, key="gas_o2")
            he_pct = st.slider("He (%)", 0, 100, 0, key="gas_he")

        total = ar_pct + co2_pct + o2_pct + he_pct
        if total != 100:
            st.warning(f"⚠️ Summe: {total}% (sollte 100% sein)")
        else:
            st.success(f"✅ Gasmischung korrekt: {total}%")

    # Flowrate
    default_fr = float(flowrate_value) if flowrate_value and isinstance(flowrate_value, (int, float)) else 15.0
    new_flowrate = st.number_input(
        "Durchflussrate (l/min)",
        min_value=0.0,
        max_value=100.0,
        value=default_fr,
        step=0.5,
        key="gas_flowrate",
    )
    state.shielding_gas["flowrate_value"] = new_flowrate
    state.shielding_gas["flowrate_unit"] = "liter / minute"


# ─── Tab 3: Zusatzwerkstoff ──────────────────────────────────

def _render_filler_material(state):
    st.header("Zusatzwerkstoff")

    filler = state.filler_material if isinstance(state.filler_material, dict) else {}

    wire_options = [
        "G3Si1 (SG2) — EN ISO 14341-A",
        "G4Si1 (SG3) — EN ISO 14341-A",
        "G 46 3 M G3Si1 — EN ISO 14341-A",
        "Benutzerdefiniert",
    ]

    current_wire = filler.get("wire_type", wire_options[0])
    try:
        wire_index = wire_options.index(current_wire)
    except ValueError:
        wire_index = 0

    wire_type = st.selectbox("Drahtsorte", options=wire_options, index=wire_index, key="wire_type")

    if "Benutzerdefiniert" in wire_type:
        custom = st.text_input("Benutzerdefinierte Drahtsorte", value=filler.get("custom_wire", ""), key="custom_wire")
        state.filler_material["wire_type"] = custom if custom else "Benutzerdefiniert"
    else:
        state.filler_material["wire_type"] = wire_type

    # Diameter
    st.subheader("Drahtdurchmesser")
    diameter_opts = [0.8, 1.0, 1.2, 1.6, "Benutzerdefiniert"]
    current_d = filler.get("diameter_mm", 1.2)
    if current_d in diameter_opts:
        d_index = diameter_opts.index(current_d)
    else:
        d_index = len(diameter_opts) - 1  # custom

    selection = st.radio(
        "Durchmesser (mm)",
        options=diameter_opts,
        index=d_index,
        key="wire_diameter",
        format_func=lambda x: f"{x} mm" if isinstance(x, (int, float)) else x,
        horizontal=True,
    )

    if selection == "Benutzerdefiniert":
        custom_default = float(current_d) if isinstance(current_d, (int, float)) else 1.2
        diameter = st.number_input(
            "Eigener Durchmesser (mm)",
            min_value=0.1,
            max_value=10.0,
            step=0.1,
            value=custom_default,
            key="wire_diameter_custom",
        )
    else:
        diameter = float(selection)

    state.filler_material["diameter_mm"] = diameter

    st.divider()

    # Summary
    st.info(
        f"**Drahtsorte:** {state.filler_material.get('wire_type', '—')} · "
        f"**Durchmesser:** {state.filler_material.get('diameter_mm', '—')} mm"
    )
