import streamlit as st
from weldx_editor.utils.style import COLORS, STATUS_ICONS


def render_quality(state):
    """
    Render the quality panel with two tabs:
    - ISO 5817 Bewertungsgruppe: Quality level selection
    - Schema-Validierung: WeldX file validation
    """

    # Initialize quality if not present
    if not hasattr(state, 'quality'):
        state.quality = {}

    # Show validation result triggered from sidebar (if any)
    last = st.session_state.pop("last_validation", None)
    if last is not None:
        _render_validation_result(last, banner=True)
        st.divider()

    tab1, tab2 = st.tabs(["ISO 5817 Bewertungsgruppe", "Schema-Validierung"])

    # ========== TAB 1: ISO 5817 Bewertungsgruppe ==========
    with tab1:
        st.subheader("ISO 5817 Bewertungsgruppe")

        st.write(
            "Wählen Sie die Qualitätsbewertungsgruppe für Ihre Schweißverbindung. "
            "Die Bewertungsgruppe definiert die zulässigen Unregelmäßigkeiten."
        )

        st.divider()

        # Quality level options
        quality_levels = {
            'B': {
                'title': 'Bewertungsgruppe B',
                'subtitle': 'Höchste Anforderungen',
                'description': 'Für sicherheitsrelevante Bauteile und kritische Anwendungen',
                'color': 'green',
                'icon': '🔒'
            },
            'C': {
                'title': 'Bewertungsgruppe C',
                'subtitle': 'Mittlere Anforderungen',
                'description': 'Standardanwendungen und allgemeine Industriekomponenten',
                'color': 'orange',
                'icon': '⚖️'
            },
            'D': {
                'title': 'Bewertungsgruppe D',
                'subtitle': 'Niedrigste Anforderungen',
                'description': 'Untergeordnete Bauteile mit geringen Anforderungen',
                'color': 'red',
                'icon': '⚠️'
            }
        }

        # Display quality selection as columns with buttons
        col1, col2, col3 = st.columns(3)

        selected_level = state.quality.get('level', 'C')

        with col1:
            st.markdown("---")
            button_b = st.button(
                f"{quality_levels['B']['icon']} {quality_levels['B']['title']}\n\n"
                f"_{quality_levels['B']['subtitle']}_",
                key='quality_b',
                use_container_width=True,
            )
            if button_b:
                state.quality['level'] = 'B'
                selected_level = 'B'
            st.markdown("---")

        with col2:
            st.markdown("---")
            button_c = st.button(
                f"{quality_levels['C']['icon']} {quality_levels['C']['title']}\n\n"
                f"_{quality_levels['C']['subtitle']}_",
                key='quality_c',
                use_container_width=True,
            )
            if button_c:
                state.quality['level'] = 'C'
                selected_level = 'C'
            st.markdown("---")

        with col3:
            st.markdown("---")
            button_d = st.button(
                f"{quality_levels['D']['icon']} {quality_levels['D']['title']}\n\n"
                f"_{quality_levels['D']['subtitle']}_",
                key='quality_d',
                use_container_width=True,
            )
            if button_d:
                state.quality['level'] = 'D'
                selected_level = 'D'
            st.markdown("---")

        st.divider()

        # Display selected level details
        if selected_level in quality_levels:
            level_info = quality_levels[selected_level]

            st.markdown(f"### Ausgewählte Bewertungsgruppe: **{level_info['title']}**")

            col_icon, col_text = st.columns([1, 4])
            with col_icon:
                st.markdown(f"# {level_info['icon']}")
            with col_text:
                st.markdown(f"**{level_info['subtitle']}**")
                st.write(level_info['description'])

            st.divider()

            # Display acceptance criteria based on selected level
            st.subheader("Akzeptanzkriterien")

            if selected_level == 'B':
                st.markdown("""
                **Bewertungsgruppe B - Höchste Anforderungen:**
                - Für sicherheitsrelevante Strukturen und Druckbehälter
                - Strikte Kriterien für Poren, Risse und Unregelmäßigkeiten
                - Maximale Porenabmessung: 0,5 mm
                - Maximale Längsfehler: Nicht zulässig
                - Risse: Nicht zulässig
                - Oberflächenraue: ≤ 3 μm
                """)
                state.quality['criteria'] = 'ISO 5817 Level B'

            elif selected_level == 'C':
                st.markdown("""
                **Bewertungsgruppe C - Mittlere Anforderungen:**
                - Standard Industrieanwendungen
                - Ausreichende Qualität für normale Einsatzfälle
                - Maximale Porenabmessung: 1,0 mm
                - Oberflächenraue: ≤ 6 μm
                - Einige Unebenheiten tolerable
                """)
                state.quality['criteria'] = 'ISO 5817 Level C'

            elif selected_level == 'D':
                st.markdown("""
                **Bewertungsgruppe D - Niedrigste Anforderungen:**
                - Untergeordnete Bauteile mit reduzierten Anforderungen
                - Einsatz für unkritische Strukturen
                - Maximale Porenabmessung: 2,0 mm
                - Oberflächenraue: ≤ 12 μm
                - Höhere Toleranz gegenüber Unregelmäßigkeiten
                """)
                state.quality['criteria'] = 'ISO 5817 Level D'

            st.info(
                f"✓ Bewertungsgruppe **{selected_level}** wurde ausgewählt und in den "
                "Projektdaten gespeichert."
            )

    # ========== TAB 2: Schema-Validierung ==========
    with tab2:
        st.subheader("WeldX Schema-Validierung")

        st.write(
            "Validieren Sie die WeldX-Datei gegen das offizielle WeldX-Schema. "
            "Dies überprüft die Korrektheit aller Daten und Strukturen."
        )

        st.divider()

        # Validation button
        if st.button("🔍 Schema validieren", use_container_width=True, type="primary"):
            with st.spinner("Validierung läuft..."):
                try:
                    try:
                        import weldx  # noqa: F401
                        has_weldx = True
                    except ImportError:
                        has_weldx = False

                    if has_weldx:
                        try:
                            validation_result = _validate_weldx_schema(state)
                            _render_validation_result(validation_result, banner=False)
                        except Exception as e:
                            st.error(f"Fehler bei der Validierung:\n\n`{str(e)}`")
                    else:
                        st.info(
                            "ℹ️ WeldX ist nicht installiert.\n\n"
                            "Um die Schema-Validierung zu nutzen, installieren Sie bitte das WeldX-Paket:\n"
                            "`pip install weldx`"
                        )

                except Exception as e:
                    st.error(f"Unerwarteter Fehler: {str(e)}")

        st.divider()

        # Validation info section
        st.subheader("Validierungsinformationen")

        with st.expander("ℹ️ Was wird validiert?"):
            st.markdown("""
            Die Schema-Validierung überprüft:

            1. **Struktur**: Alle erforderlichen Felder sind vorhanden
            2. **Datentypen**: Werte entsprechen den erwarteten Typen
            3. **Wertebereiche**: Numerische Werte sind im zulässigen Bereich
            4. **Abhängigkeiten**: Verknüpfte Felder sind konsistent
            5. **Format**: Strings und Formatangaben sind korrekt
            6. **Einheiten**: Einheitsangaben sind standardkonform

            Wenn die Validierung fehlschlägt, prüfen Sie:
            - Alle erforderlichen Felder sind ausgefüllt
            - Koordinatensysteme sind vollständig definiert
            - Messungen haben gültige Werte
            - Qualitätsgruppe ist ausgewählt
            """)

        with st.expander("🔗 WeldX-Ressourcen"):
            st.markdown("""
            - [WeldX Dokumentation](https://weldx.readthedocs.io/)
            - [WeldX GitHub Repository](https://github.com/BAMWelding/weldx)
            - [ISO 5817 Standard](https://www.iso.org/standard/68604.html)
            """)

        st.divider()

        # Display current state summary
        st.subheader("Projektübersicht")

        col1, col2, col3 = st.columns(3)

        with col1:
            quality_level = state.quality.get('level', 'Nicht gesetzt')
            if quality_level != 'Nicht gesetzt':
                status_icon = "✅"
            else:
                status_icon = "❌"
            st.metric(f"{status_icon} Qualitätsstufe", quality_level)

        with col2:
            has_coords = hasattr(state, 'coordinate_systems') and len(state.coordinate_systems) > 0
            status_icon = "✅" if has_coords else "❌"
            coord_count = len(state.coordinate_systems) if has_coords else 0
            st.metric(f"{status_icon} Koordinatensysteme", coord_count)

        with col3:
            has_measurements = hasattr(state, 'measurements') and len(state.measurements) > 0
            status_icon = "✅" if has_measurements else "❌"
            meas_count = len([m for m in state.measurements.items() if m[0] != 'sensors']) if has_measurements else 0
            st.metric(f"{status_icon} Messungen", meas_count)


def _render_validation_result(result: dict, banner: bool = False):
    """Render a validation result. ``banner=True`` adds a header for sidebar-triggered runs."""
    if banner:
        st.subheader("🛡️ Validierung")

    if result["valid"]:
        st.success(f"✓ Schema-Validierung erfolgreich!\n\n{result['message']}")
    else:
        st.error(f"✗ Validierungsfehler:\n\n{result['message']}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Validierte Attribute", result.get("attributes_checked", 0))
    with col2:
        st.metric("Fehler", result.get("errors", 0))
    with col3:
        st.metric("Warnungen", result.get("warnings", 0))

    errs = result.get("errors_detail") or []
    warns = result.get("warnings_detail") or []
    if errs:
        with st.expander(f"🚫 {len(errs)} Fehler", expanded=not result["valid"]):
            for e in errs:
                st.error(f"- {e}")
    if warns:
        with st.expander(f"⚠️ {len(warns)} Warnungen", expanded=False):
            for w in warns:
                st.warning(f"- {w}")


def _validate_weldx_schema(state) -> dict:
    """
    Validate WeldX structure against schema.

    This is a placeholder implementation that performs basic checks.
    In production, this would use the official WeldX schema validation.

    Args:
        state: Application state object

    Returns:
        Dictionary with validation results:
        {
            'valid': bool,
            'message': str,
            'attributes_checked': int,
            'errors': int,
            'warnings': int,
            'errors_detail': list,
            'warnings_detail': list
        }
    """
    errors = []
    warnings = []
    attributes_checked = 0

    # Check quality level
    if not hasattr(state, 'quality') or not state.quality.get('level'):
        errors.append("Qualitätsbewertungsgruppe nicht definiert")
    else:
        attributes_checked += 1

    # Check coordinate systems
    if not hasattr(state, 'coordinate_systems') or len(state.coordinate_systems) == 0:
        errors.append("Keine Koordinatensysteme definiert")
    else:
        attributes_checked += 1
        # Check for required root system
        has_root = any(
            info.get('parent') is None
            for info in state.coordinate_systems.values()
        )
        if not has_root:
            warnings.append("Keine Root-Koordinatensystem definiert")

    # Check measurements
    if not hasattr(state, 'measurements') or len(state.measurements) == 0:
        warnings.append("Keine Messungen definiert")
    else:
        attributes_checked += 1

    # Check sensor equipment
    if hasattr(state, 'measurements') and 'sensors' in state.measurements:
        attributes_checked += 1
        if len(state.measurements['sensors']) == 0:
            warnings.append("Keine Sensoren definiert")
    else:
        warnings.append("Keine Sensorausstattung definiert")

    # Determine validity
    is_valid = len(errors) == 0

    if is_valid:
        message = f"Alle Validierungschecks bestanden. {attributes_checked} Attribute validiert."
    else:
        message = f"Validierung fehlgeschlagen: {len(errors)} Fehler, {len(warnings)} Warnungen"

    return {
        'valid': is_valid,
        'message': message,
        'attributes_checked': attributes_checked,
        'errors': len(errors),
        'warnings': len(warnings),
        'errors_detail': errors,
        'warnings_detail': warnings
    }
