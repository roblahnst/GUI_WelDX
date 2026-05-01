import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from weldx_editor.utils.style import COLORS


def render_measurements(state):
    """
    Render the measurements panel with three tabs:
    - Zeitreihen-Daten: Time series data visualization and import
    - Messketten: Measurement chain visualization
    - Sensorik & Equipment: Sensor equipment management
    """

    # Initialize measurements if not present
    if not hasattr(state, 'measurements'):
        state.measurements = {}

    tab1, tab2, tab3 = st.tabs(["Zeitreihen-Daten", "Messketten", "Sensorik & Equipment"])

    # ========== TAB 1: Zeitreihen-Daten ==========
    with tab1:
        st.subheader("Zeitreihen-Daten")
        _render_csv_import(state)

        # Display existing measurements
        if state.measurements:
            # ── Combined overview plot (weldx-widgets style) ──
            real_meas = {k: v for k, v in state.measurements.items()
                         if "values" in v and v["values"] is not None}
            if real_meas:
                st.markdown("**Messübersicht:**")
                try:
                    _plot_measurements_overview(real_meas)
                except Exception as e:
                    st.warning(f"Übersichtsplot nicht möglich: {e}")

            st.divider()

            # ── Individual measurement details ──
            st.write("**Einzelmessungen:**")
            for meas_name, meas_info in state.measurements.items():
                with st.container(border=True):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.markdown(f"**{meas_info.get('name', meas_name)}**")
                    with col2:
                        st.caption(f"Samples: {meas_info.get('samples', 0):,}")
                    with col3:
                        st.caption(f"Einheit: {meas_info.get('unit', '—')}")
                    with col4:
                        mn = meas_info.get('min')
                        mx = meas_info.get('max')
                        if mn is not None and not isinstance(mn, str):
                            st.caption(f"Bereich: {mn:.2f} – {mx:.2f}")

                    n_outliers = meas_info.get("outliers_removed", 0)
                    if n_outliers > 0:
                        st.warning(
                            f"⚠️ {n_outliers} Ausreißer erkannt und entfernt."
                        )

                    with st.expander(f"Einzeldarstellung: {meas_info.get('name', meas_name)}"):
                        _plot_single_interactive(meas_name, meas_info)
        else:
            st.info("Noch keine Messungen vorhanden. Importieren Sie eine CSV-Datei um zu beginnen.")

    # ========== TAB 2: Messketten ==========
    with tab2:
        st.subheader("Messketten")

        # Collect chains from measurements (native weldx) and equipment (RoboScope)
        chains_found = []
        for mkey, minfo in getattr(state, 'measurements', {}).items():
            chain = minfo.get("chain")
            if chain and chain.get("steps"):
                chains_found.append((mkey, minfo.get("name", mkey), chain))

        if chains_found:
            st.success(f"✅ {len(chains_found)} Messkette(n) aus Datei erkannt")

            for mkey, meas_name, chain in chains_found:
                with st.container(border=True):
                    st.markdown(f"#### {chain.get('name', meas_name)}")

                    # Source info
                    src = chain.get("source", {})
                    src_eq = chain.get("source_equipment", "")
                    if src:
                        st.markdown(
                            f"**Quelle:** {src.get('name', '')} "
                            f"({src.get('signal_type', '')} / {src.get('signal_unit', '')})"
                            f" &mdash; Fehler: ±{src.get('error', '—')}"
                            f" &mdash; Equipment: **{src_eq}**"
                        )

                    # Chain flow arrow
                    steps = chain.get("steps", [])
                    step_names = [s["name"] for s in steps]
                    flow = " → ".join([f"`{s}`" for s in step_names])
                    st.markdown(f"**Signalfluss:** {flow}")

                    st.markdown("")

                    # Detailed step table
                    for i, step in enumerate(steps):
                        trafo = step.get("transformation")
                        sig_type = step.get("signal_type", "")
                        sig_unit = step.get("signal_unit", "")

                        col_step, col_detail = st.columns([1, 3])

                        with col_step:
                            badge = "🟢" if sig_type == "digital" else "🔵"
                            st.markdown(f"{badge} **{step['name']}**")
                            if sig_type or sig_unit:
                                st.caption(f"{sig_type} / {sig_unit}" if sig_unit else sig_type)

                        with col_detail:
                            if trafo:
                                # Transformation details
                                t_name = trafo.get("name", "")
                                t_type = trafo.get("type", "")
                                expr = trafo.get("expression", "")
                                params = trafo.get("parameters", {})
                                error = trafo.get("error", "")
                                eq_name = trafo.get("equipment", "")
                                sw = trafo.get("software", "")

                                type_badge = f" `{t_type}`" if t_type else ""
                                st.markdown(f"↓ **{t_name}**{type_badge}")

                                detail_parts = []
                                if expr:
                                    params_str = ", ".join(f"{k}={v}" for k, v in params.items())
                                    detail_parts.append(f"`{expr}` ({params_str})")
                                if error and error != "0.0":
                                    detail_parts.append(f"Fehler: ±{error}")
                                if eq_name:
                                    detail_parts.append(f"Equipment: {eq_name}")
                                if sw:
                                    detail_parts.append(f"Software: {sw}")

                                if detail_parts:
                                    st.caption(" · ".join(detail_parts))
                            elif i < len(steps) - 1:
                                st.markdown("↓")

                    st.markdown("")
        else:
            # Fallback: show equipment-based chains (RoboScope format)
            equipment = getattr(state, 'equipment', {})
            if equipment:
                st.success(f"✅ {len(equipment)} Messkette(n) aus Datei erkannt")
                for eq_key, eq_info in equipment.items():
                    with st.container(border=True):
                        st.markdown(f"**{eq_info.get('name', eq_key)}**")
                        sensor_name = eq_info.get("sensor_name", "Sensor")
                        signal_unit = eq_info.get("signal_unit", "")
                        error_val = eq_info.get("error_value", "")
                        error_unit = eq_info.get("error_unit", "")
                        equip_name = eq_info.get("equipment_name", "")
                        chain_steps = eq_info.get("chain_steps", [])
                        if chain_steps:
                            step_names = [s["name"] for s in chain_steps]
                            st.markdown(" → ".join([f"**{s}**" for s in step_names]))
                        else:
                            st.markdown(f"**{sensor_name}** → **{equip_name}**")
                        cols = st.columns(3)
                        with cols[0]:
                            st.caption(f"Sensor: {sensor_name}")
                        with cols[1]:
                            st.caption(f"Einheit: {signal_unit}")
                        with cols[2]:
                            err_display = f"±{error_val} {error_unit}" if error_val else "—"
                            st.caption(f"Fehler: {err_display}")
            else:
                st.info("Keine Messketten in der Datei gefunden.")

        # Add new measurement chain
        st.subheader("Neue Messkette hinzufügen")
        with st.expander("➕ Messkette hinzufügen"):
            with st.form("add_measurement_chain_form", border=False):
                col1, col2 = st.columns(2)
                with col1:
                    sensor_name = st.text_input("Sensorname", key="chain_sensor_name")
                    model = st.text_input("Modell", key="chain_model")
                with col2:
                    manufacturer = st.text_input("Hersteller", key="chain_manufacturer")
                    serial = st.text_input("Seriennummer", key="chain_serial")

                col3, col4 = st.columns(2)
                with col3:
                    cal_formula = st.text_input("Kalibrierformel (z.B. y=a*x+b)", key="chain_cal_formula")
                with col4:
                    unit_in = st.text_input("Eingang (Einheit)", key="chain_unit_in")

                col5, col6 = st.columns(2)
                with col5:
                    unit_out = st.text_input("Ausgang (Einheit)", key="chain_unit_out")
                with col6:
                    range_val = st.number_input("Messbereich (max)", key="chain_range", value=100.0)

                if st.form_submit_button("Messkette speichern"):
                    if sensor_name:
                        if sensor_name not in state.measurements:
                            state.measurements[sensor_name] = {}

                        state.measurements[sensor_name].update({
                            'name': sensor_name,
                            'status': 'konfiguriert',
                            'type': 'MeasurementChain',
                            'model': model,
                            'manufacturer': manufacturer,
                            'serial': serial,
                            'calibration_formula': cal_formula,
                            'unit_input': unit_in,
                            'unit_output': unit_out,
                            'range': range_val,
                            'samples': 0
                        })
                        st.success(f"Messkette '{sensor_name}' hinzugefügt!")
                    else:
                        st.error("Bitte geben Sie einen Sensornamen ein.")

    # ========== TAB 3: Sensorik & Equipment ==========
    with tab3:
        st.subheader("Sensorik & Equipment")

        # ── Equipment from file (extracted during import) ──
        equipment = getattr(state, 'equipment', {})

        # Also collect equipment from measurement chains
        chain_equipment = {}
        for mkey, minfo in getattr(state, 'measurements', {}).items():
            chain = minfo.get("chain")
            if not chain:
                continue
            # Source equipment
            src_eq = chain.get("source_equipment", "")
            src = chain.get("source", {})
            if src_eq and src_eq not in chain_equipment:
                chain_equipment[src_eq] = {
                    "name": src_eq,
                    "sources": [src] if src else [],
                    "used_by": [minfo.get("name", mkey)],
                }
            elif src_eq and src_eq in chain_equipment:
                chain_equipment[src_eq]["used_by"].append(minfo.get("name", mkey))

            # Equipment from transformation steps
            for step in chain.get("steps", []):
                trafo = step.get("transformation", {})
                eq_name = trafo.get("equipment", "")
                if eq_name and eq_name not in chain_equipment:
                    chain_equipment[eq_name] = {
                        "name": eq_name,
                        "sources": [],
                        "role": trafo.get("name", ""),
                        "used_by": [minfo.get("name", mkey)],
                    }
                elif eq_name and eq_name in chain_equipment:
                    if minfo.get("name", mkey) not in chain_equipment[eq_name].get("used_by", []):
                        chain_equipment[eq_name].setdefault("used_by", []).append(minfo.get("name", mkey))

        # Merge: prefer chain_equipment (richer info), then state.equipment
        all_equipment = dict(chain_equipment)
        for eq_key, eq_info in equipment.items():
            name = eq_info.get("name", eq_key)
            if name not in all_equipment:
                all_equipment[name] = eq_info

        if all_equipment:
            st.success(f"✅ {len(all_equipment)} Gerät(e) aus Datei erkannt")

            for eq_name, eq_info in all_equipment.items():
                with st.container(border=True):
                    st.markdown(f"#### {eq_info.get('name', eq_name)}")

                    col1, col2 = st.columns(2)

                    with col1:
                        # Sources
                        sources = eq_info.get("sources", [])
                        if sources:
                            st.markdown("**Signalquellen:**")
                            for src in sources:
                                if isinstance(src, dict):
                                    src_name = src.get("name", "")
                                    sig_type = src.get("signal_type", "")
                                    sig_unit = src.get("signal_unit", "")
                                    err = src.get("error", "")
                                    parts = []
                                    if sig_type:
                                        parts.append(sig_type)
                                    if sig_unit:
                                        parts.append(sig_unit)
                                    sig_str = " / ".join(parts) if parts else ""
                                    err_str = f", Fehler: ±{err}" if err else ""
                                    st.caption(f"• {src_name} ({sig_str}{err_str})")

                        # Role in chain
                        role = eq_info.get("role", "")
                        if role:
                            st.caption(f"Funktion: {role}")

                    with col2:
                        # Used by which measurements
                        used_by = eq_info.get("used_by", [])
                        if used_by:
                            st.markdown("**Verwendet in:**")
                            for m_name in used_by:
                                st.caption(f"• {m_name}")

                        # Has chain info
                        has_chain = eq_info.get("has_chain", False)
                        if has_chain:
                            st.caption("Messkette vorhanden")

            st.divider()
        else:
            st.info("Keine Sensorik/Equipment in der Datei gefunden.")
            st.divider()

        # ── Manual sensor entry ──
        st.subheader("Neuen Sensor hinzufügen")
        with st.expander("➕ Sensor manuell hinzufügen"):
            with st.form("add_sensor_form", border=False):
                col1, col2 = st.columns(2)
                with col1:
                    sensor_name = st.text_input("Name", key="sensor_name")
                    manufacturer = st.text_input("Hersteller", key="sensor_manufacturer")
                with col2:
                    model = st.text_input("Modell", key="sensor_model")
                    serial = st.text_input("Seriennummer", key="sensor_serial")

                col3, col4 = st.columns(2)
                with col3:
                    min_range = st.number_input("Messbereich (min)", key="sensor_min_range", value=0.0)
                with col4:
                    max_range = st.number_input("Messbereich (max)", key="sensor_max_range", value=100.0)

                accuracy = st.number_input("Genauigkeit (%)", key="sensor_accuracy", value=1.0, min_value=0.0)

                if st.form_submit_button("Sensor speichern"):
                    if sensor_name:
                        if 'sensors' not in state.measurements:
                            state.measurements['sensors'] = []

                        sensor_data = {
                            'name': sensor_name,
                            'manufacturer': manufacturer,
                            'model': model,
                            'serial': serial,
                            'min_range': min_range,
                            'max_range': max_range,
                            'accuracy': accuracy
                        }

                        if not any(s.get('name') == sensor_name for s in state.measurements.get('sensors', [])):
                            state.measurements.setdefault('sensors', []).append(sensor_data)
                            st.success(f"Sensor '{sensor_name}' hinzugefügt!")
                        else:
                            st.warning(f"Sensor '{sensor_name}' existiert bereits.")
                    else:
                        st.error("Bitte geben Sie einen Sensornamen ein.")


# ─── Matplotlib Visualization (weldx-widgets style) ───────────

# Signal colors matching welding convention
_SIGNAL_COLORS = {
    "welding_current": "#00bcd4",   # cyan
    "welding_voltage": "#ffc107",   # amber
    "current": "#00bcd4",
    "voltage": "#ffc107",
    "gas_flow": "#4caf50",          # green
    "wire_speed": "#e040fb",        # purple
    "temperature": "#ff5722",       # deep orange
}


def _get_signal_color(name: str) -> str:
    """Get a color for a signal by matching known keywords."""
    name_lower = name.lower()
    for key, color in _SIGNAL_COLORS.items():
        if key in name_lower:
            return color
    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
    return palette[hash(name) % len(palette)]


_TIME_KEYWORDS = ("time", "zeit", "sec", "t_s", "tsec")
_UNIT_PRESETS = ["A", "V", "m/min", "l/min", "mm/s", "°C", "kJ/cm", "Hz", "%", "—"]


def _render_csv_help():
    """Info expander explaining the expected CSV structure."""
    with st.expander("ℹ️ CSV-Format & Beispiele"):
        st.markdown(
            """
**Erwartet:** Komma-getrennte CSV mit einer Header-Zeile (UTF-8).

**Spalten**
- **Wertespalte** (Pflicht) – numerische Messwerte. Wird automatisch
  erkannt; vor dem Import lässt sich eine andere Spalte wählen.
- **Zeitspalte** (optional) – Zeit in **Sekunden**. Spalten mit Namen wie
  `time`, `zeit`, `t_s`, `seconds` werden als Zeitachse erkannt. Ohne
  Zeitspalte wird der Sample-Index (0, 1, 2, …) als Sekunden verwendet.
- **Einheit** – wird vor dem Import ausgewählt (z. B. `A`, `V`, `m/min`,
  `l/min`, `°C`).

**Beispiel ohne Zeit:**

```
welding_current
142.3
145.1
148.7
146.2
```

**Beispiel mit Zeit (s, Werte in A):**

```
time_s,welding_current
0.000,142.3
0.001,145.1
0.002,148.7
0.003,146.2
```

Beim Speichern werden importierte Zeitreihen als `weldx.TimeSeries` in
`tree['data']` der WelDX-Datei abgelegt — sie sind danach von jedem
weldx-kompatiblen Tool lesbar.
            """
        )


def _render_csv_import(state):
    """File uploader + column/unit picker form for CSV time series."""
    col_upload, col_info = st.columns([2, 1])
    with col_upload:
        uploaded_file = st.file_uploader(
            "CSV Zeitreihen importieren",
            type=["csv"],
            key="timeseries_uploader",
        )
    with col_info:
        _render_csv_help()

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"CSV nicht lesbar: {e}")
            df = None

        if df is not None and not df.empty:
            cols = list(df.columns)

            # Auto-detect time column
            time_default = None
            for c in cols:
                if any(k in str(c).lower() for k in _TIME_KEYWORDS):
                    time_default = c
                    break

            # First numeric, non-time column → value default
            value_default = None
            for c in cols:
                if c == time_default:
                    continue
                if pd.api.types.is_numeric_dtype(df[c]):
                    value_default = c
                    break
            if value_default is None:
                value_default = cols[0]

            with st.form("csv_import_form", border=True):
                st.markdown("**Vorschau (erste 5 Zeilen):**")
                st.dataframe(df.head(), use_container_width=True)

                col_v, col_t, col_u = st.columns([2, 2, 1])
                with col_v:
                    value_col = st.selectbox(
                        "Wertespalte",
                        cols,
                        index=cols.index(value_default),
                        help="Spalte mit den eigentlichen Messwerten.",
                    )
                with col_t:
                    time_options = ["(keine — Sample-Index)"] + cols
                    t_idx = time_options.index(time_default) if time_default in cols else 0
                    time_col = st.selectbox(
                        "Zeitspalte (s)",
                        time_options,
                        index=t_idx,
                        help="Optional. Werte in Sekunden.",
                    )
                with col_u:
                    unit = st.selectbox(
                        "Einheit",
                        _UNIT_PRESETS,
                        index=0,
                        help="Einheit der Wertespalte.",
                    )

                meas_default = uploaded_file.name.rsplit(".", 1)[0]
                meas_name = st.text_input(
                    "Messungsname",
                    value=meas_default,
                    help="Schlüssel in tree['data'] der WelDX-Datei.",
                )

                submitted = st.form_submit_button("Importieren", type="primary")

            if submitted:
                try:
                    values = pd.to_numeric(df[value_col], errors="coerce").to_numpy(dtype=float)
                    time_arr = None
                    if time_col != "(keine — Sample-Index)":
                        time_arr = pd.to_numeric(df[time_col], errors="coerce").to_numpy(dtype=float)

                    if time_arr is not None:
                        mask = ~(np.isnan(values) | np.isnan(time_arr))
                        values = values[mask]
                        time_arr = time_arr[mask]
                    else:
                        nan_mask = ~np.isnan(values)
                        values = values[nan_mask]
                        time_arr = np.arange(len(values), dtype=float)

                    if values.size == 0:
                        st.error("Keine numerischen Werte gefunden.")
                    else:
                        info = {
                            "name": meas_name,
                            "type": "TimeSeries",
                            "status": "importiert",
                            "unit": unit if unit != "—" else "",
                            "values": values,
                            "values_raw": values,
                            "time_seconds": time_arr,
                            "time_start": f"{time_arr[0]:.3f}s",
                            "time_end": f"{time_arr[-1]:.3f}s",
                            "samples": int(len(values)),
                            "min": float(np.min(values)),
                            "max": float(np.max(values)),
                            "range": f"{float(np.min(values)):.2f} – {float(np.max(values)):.2f}",
                            "outliers_removed": 0,
                            "_imported": True,
                        }
                        state.measurements[meas_name] = info
                        st.success(
                            f"'{meas_name}' importiert: {len(values):,} Samples, "
                            f"Bereich {info['range']} {info['unit']}"
                        )
                        st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Importieren: {e}")


def _plot_measurements_overview(measurements: dict):
    """Combined matplotlib figure with all measurements sharing the time axis."""
    n = len(measurements)
    if n == 0:
        return

    fig, axes = plt.subplots(
        nrows=n, sharex=True,
        figsize=(10, 2.2 * n + 0.5),
        squeeze=False,
    )
    axes = axes.flatten()
    fig.patch.set_facecolor("white")

    x_label = "Sample"

    for i, (meas_name, meas_info) in enumerate(measurements.items()):
        ax = axes[i]
        ax.set_facecolor("white")

        y_vals = meas_info["values"]
        samples = len(y_vals)
        unit = meas_info.get("unit", "")
        display_name = meas_info.get("name", meas_name)
        color = _get_signal_color(meas_name)

        # Downsample for plotting (max 5000 points)
        step = max(1, samples // 5000)
        y_plot = y_vals[::step]

        # Use real time axis if available
        time_s = meas_info.get("time_seconds")
        if time_s is not None and len(time_s) == samples:
            x_plot = time_s[::step]
            x_label = "Zeit / s"
        else:
            x_plot = np.arange(len(y_plot))

        ax.plot(x_plot, y_plot, color=color, linewidth=0.7, alpha=0.9)
        ax.set_ylabel(f"{display_name}\n/ {unit}" if unit else display_name,
                       fontsize=9, color="#333333")
        ax.grid(True, alpha=0.3, color="#cccccc")
        ax.tick_params(labelsize=8, colors="#333333")
        for spine in ax.spines.values():
            spine.set_color("#cccccc")

        # Min/Max lines
        mn = meas_info.get("min")
        mx = meas_info.get("max")
        if mn is not None and mx is not None and not isinstance(mn, str):
            ax.axhline(mn, color=color, alpha=0.3, linewidth=0.5, linestyle="--")
            ax.axhline(mx, color=color, alpha=0.3, linewidth=0.5, linestyle="--")

    axes[-1].set_xlabel(x_label, fontsize=9, color="#333333")
    fig.suptitle("Messdaten", fontsize=11, color="#111111", y=1.0)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def _plot_single_measurement(meas_name: str, meas_info: dict):
    """Render a single measurement as matplotlib figure."""
    has_real_data = "values" in meas_info and meas_info["values"] is not None

    if has_real_data:
        y_vals = meas_info["values"]
        step = max(1, len(y_vals) // 5000)
        y_plot = y_vals[::step]
    else:
        n_samples = meas_info.get('samples', 100)
        if isinstance(n_samples, str):
            n_samples = 100
        demo_min = meas_info.get('min', 0)
        demo_max = meas_info.get('max', 100)
        if isinstance(demo_min, str):
            demo_min = 0
        if isinstance(demo_max, str):
            demo_max = 100
        y_plot = np.sin(np.linspace(0, 4 * np.pi, n_samples)) * (demo_max - demo_min) / 2 + (demo_min + demo_max) / 2

    unit = meas_info.get('unit', '')
    display_name = meas_info.get('name', meas_name)
    color = _get_signal_color(meas_name)

    fig, ax = plt.subplots(figsize=(10, 3.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.plot(np.arange(len(y_plot)), y_plot, color=color, linewidth=0.7)
    ax.set_ylabel(f"{unit}" if unit else "Wert", fontsize=9, color="#333333")
    ax.set_xlabel("Sample", fontsize=9, color="#333333")
    ax.set_title(
        f"{display_name}" + ("" if has_real_data else " (Demo-Daten)"),
        fontsize=10, color="#111111",
    )
    ax.grid(True, alpha=0.3, color="#cccccc")
    ax.tick_params(labelsize=8, colors="#333333")
    for spine in ax.spines.values():
        spine.set_color("#cccccc")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    if not has_real_data:
        st.caption("Keine echten Messwerte — Darstellung zeigt Platzhalter-Daten.")


def _plot_single_interactive(meas_name: str, meas_info: dict):
    """Render a single measurement as interactive Plotly chart (zoomable)."""
    has_real_data = "values" in meas_info and meas_info["values"] is not None

    if has_real_data:
        y_vals = meas_info["values"]
        step = max(1, len(y_vals) // 10000)
        y_plot = y_vals[::step]
    else:
        n_samples = meas_info.get('samples', 100)
        if isinstance(n_samples, str):
            n_samples = 100
        demo_min = meas_info.get('min', 0)
        demo_max = meas_info.get('max', 100)
        if isinstance(demo_min, str):
            demo_min = 0
        if isinstance(demo_max, str):
            demo_max = 100
        y_plot = np.sin(np.linspace(0, 4 * np.pi, n_samples)) * (demo_max - demo_min) / 2 + (demo_min + demo_max) / 2

    unit = meas_info.get('unit', '')
    display_name = meas_info.get('name', meas_name)
    color = _get_signal_color(meas_name)

    x_title = "Sample"
    x_plot = np.arange(len(y_plot))

    # Use real time axis if available
    if has_real_data:
        time_s = meas_info.get("time_seconds")
        if time_s is not None:
            step = max(1, len(time_s) // 10000)
            x_plot = time_s[::step]
            x_title = "Zeit / s"

    fig = go.Figure()
    fig.add_trace(go.Scattergl(
        x=x_plot, y=y_plot,
        mode='lines',
        line=dict(color=color, width=1),
        name=display_name,
    ))
    fig.update_layout(
        title=display_name + ("" if has_real_data else " (Demo-Daten)"),
        xaxis_title=x_title,
        yaxis_title=f"{unit}" if unit else "Wert",
        hovermode='x unified',
        height=400,
        template="plotly_dark",
    )
    st.plotly_chart(fig, use_container_width=True)

    if not has_real_data:
        st.caption("Keine echten Messwerte — Darstellung zeigt Platzhalter-Daten.")
