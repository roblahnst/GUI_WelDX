import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
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

        col_upload, col_info = st.columns([2, 1])
        with col_upload:
            uploaded_file = st.file_uploader(
                "CSV Zeitreihen importieren",
                type=['csv'],
                key='timeseries_uploader'
            )
            if uploaded_file is not None:
                try:
                    df = pd.read_csv(uploaded_file)
                    # Auto-detect measurement info
                    name = uploaded_file.name.replace('.csv', '')
                    state.measurements[name] = {
                        'name': name,
                        'status': 'importiert',
                        'samples': len(df),
                        'unit': 'A',  # Default unit
                        'min': float(df.iloc[:, 0].min()) if len(df) > 0 else 0,
                        'max': float(df.iloc[:, 0].max()) if len(df) > 0 else 0,
                        'range': float(df.iloc[:, 0].max() - df.iloc[:, 0].min()) if len(df) > 0 else 0,
                        'type': 'TimeSeries',
                        'data': df
                    }
                    st.success(f"Datei '{name}' erfolgreich importiert ({len(df)} Samples)")
                except Exception as e:
                    st.error(f"Fehler beim Importieren: {str(e)}")

        # Display existing measurements
        if state.measurements:
            st.write("**Vorhandene Messungen:**")
            for meas_name, meas_info in state.measurements.items():
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Name", meas_name)
                with col2:
                    st.metric("Samples", meas_info.get('samples', 0))
                with col3:
                    st.metric("Unit", meas_info.get('unit', 'N/A'))
                with col4:
                    st.metric("Status", meas_info.get('status', 'unbekannt'))

                # Range display
                min_val = meas_info.get('min', None)
                max_val = meas_info.get('max', None)
                range_val = meas_info.get('range', None)
                parts = []
                if min_val is not None and not isinstance(min_val, str):
                    parts.append(f"Min: {min_val:.2f}")
                if max_val is not None and not isinstance(max_val, str):
                    parts.append(f"Max: {max_val:.2f}")
                if range_val is not None:
                    parts.append(f"Bereich: {range_val}")
                range_text = ", ".join(parts) if parts else "Keine Bereichsdaten"
                st.caption(range_text)

                # Visualization expander
                # Show outlier warning if applicable
                n_outliers = meas_info.get("outliers_removed", 0)
                if n_outliers > 0:
                    st.warning(
                        f"⚠️ {n_outliers} Ausreißer erkannt und aus der Darstellung entfernt "
                        f"(Sensor-Artefakte / ungültige Messwerte)."
                    )

                with st.expander(f"📊 Visualisieren: {meas_name}"):
                    try:
                        has_real_data = "values" in meas_info and meas_info["values"] is not None

                        if has_real_data:
                            y_vals = meas_info["values"]
                            # Downsample for performance if > 10k points
                            if len(y_vals) > 10000:
                                step = len(y_vals) // 5000
                                y_plot = y_vals[::step]
                            else:
                                y_plot = y_vals
                            x_vals = np.arange(len(y_plot))
                            data_label = "Messdaten"
                        else:
                            # Fallback: generate demo sine for demo mode
                            n_samples = meas_info.get('samples', 100)
                            if isinstance(n_samples, str):
                                n_samples = 100
                            x_vals = np.arange(n_samples)
                            demo_min = meas_info.get('min', 0)
                            demo_max = meas_info.get('max', 100)
                            if isinstance(demo_min, str):
                                demo_min = 0
                            if isinstance(demo_max, str):
                                demo_max = 100
                            demo_mid = (demo_min + demo_max) / 2
                            demo_amp = (demo_max - demo_min) / 2
                            y_plot = np.sin(np.linspace(0, 4 * np.pi, n_samples)) * demo_amp + demo_mid
                            data_label = "Demo-Daten (keine echten Messwerte)"

                        unit = meas_info.get('unit', '')
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=x_vals,
                            y=y_plot,
                            mode='lines',
                            name=meas_name,
                            line=dict(color=COLORS.get('accent', '#4f8ef7'), width=1.5),
                        ))
                        fig.update_layout(
                            title=f"{meas_name} – {data_label}",
                            xaxis_title="Sample",
                            yaxis_title=f"{unit}" if unit else "Wert",
                            hovermode='x unified',
                            height=400,
                            template="plotly_dark",
                        )
                        st.plotly_chart(fig, use_container_width=True)

                        if not has_real_data:
                            st.caption("⚠️ Keine echten Messwerte in der Datei gefunden – Darstellung zeigt Platzhalter-Daten.")
                    except Exception as e:
                        st.error(f"Fehler beim Visualisieren: {str(e)}")

                st.divider()
        else:
            st.info("Noch keine Messungen vorhanden. Importieren Sie eine CSV-Datei um zu beginnen.")

    # ========== TAB 2: Messketten ==========
    with tab2:
        st.subheader("Messketten")

        # Display equipment-based measurement chains from state.equipment
        equipment = getattr(state, 'equipment', {})
        if equipment:
            st.success(f"✅ {len(equipment)} Messkette(n) aus Datei erkannt")
            for eq_key, eq_info in equipment.items():
                with st.container(border=True):
                    st.markdown(f"**{eq_info.get('name', eq_key)}**")

                    # Chain visualization
                    sensor_name = eq_info.get("sensor_name", "Sensor")
                    signal_unit = eq_info.get("signal_unit", "")
                    error_val = eq_info.get("error_value", "")
                    error_unit = eq_info.get("error_unit", "")
                    equip_name = eq_info.get("equipment_name", "")

                    # Show chain steps if available
                    chain_steps = eq_info.get("chain_steps", [])
                    if chain_steps:
                        step_names = [s["name"] for s in chain_steps]
                        chain_display = " → ".join([f"**{s}**" for s in step_names])
                        st.markdown(chain_display)
                    else:
                        st.markdown(f"**{sensor_name}** → **{equip_name}**")

                    # Details
                    cols = st.columns(3)
                    with cols[0]:
                        st.caption(f"Sensor: {sensor_name}")
                    with cols[1]:
                        st.caption(f"Einheit: {signal_unit}")
                    with cols[2]:
                        err_display = f"±{error_val} {error_unit}" if error_val else "—"
                        st.caption(f"Fehler: {err_display}")

                st.markdown("")
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

        # Add new sensor form
        st.write("**Neuen Sensor hinzufügen:**")
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

                    # Check if sensor already exists
                    if not any(s.get('name') == sensor_name for s in state.measurements.get('sensors', [])):
                        state.measurements.setdefault('sensors', []).append(sensor_data)
                        st.success(f"Sensor '{sensor_name}' hinzugefügt!")
                    else:
                        st.warning(f"Sensor '{sensor_name}' existiert bereits.")
                else:
                    st.error("Bitte geben Sie einen Sensornamen ein.")

        st.divider()

        # Display existing sensors
        st.write("**Vorhandene Sensoren:**")
        sensors = state.measurements.get('sensors', [])
        if sensors:
            for sensor in sensors:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.markdown(f"**{sensor.get('name', 'N/A')}**")
                        st.caption(f"{sensor.get('manufacturer', 'N/A')} - {sensor.get('model', 'N/A')}")
                    with col2:
                        st.text(f"SN: {sensor.get('serial', 'N/A')}")
                        st.text(f"Bereich: {sensor.get('min_range', 0):.1f} - {sensor.get('max_range', 100):.1f}")
                    with col3:
                        st.text(f"Genauigkeit: {sensor.get('accuracy', 0):.1f}%")
        else:
            st.info("Noch keine Sensoren hinzugefügt.")
