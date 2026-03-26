# WelDX Editor

Streamlit-basierte GUI zum Anreichern von WelDX-Dateien, die aus dem RoboScope-Schweißroboter exportiert wurden.

RoboScope exportiert Messdaten (Strom, Spannung, Drahtgeschwindigkeit, Gasfluss) im [WelDX-Format](https://weldx.readthedocs.io/) (ASDF-basiert). Der WelDX Editor ergänzt diese Dateien um fehlende Metadaten: Werkstoff, Nahtgeometrie, Schweißverfahren, Schutzgas, Koordinatensysteme und Qualitätsbewertung.

## Schnellstart

```bash
# Abhängigkeiten installieren
pip install -r requirements.txt

# App starten
python run.py
```

Die App öffnet sich automatisch im Browser unter `http://localhost:8501`.

## Voraussetzungen

- Python 3.9+
- Die Pakete aus `requirements.txt` (streamlit, weldx, plotly, pandas, numpy, pint)
- Optional: Eine `.wx`-Datei aus einem RoboScope-Export

Falls `weldx` nicht installiert ist, steht ein Demo-Modus mit Beispieldaten zur Verfügung.

## Funktionsumfang

### Übersicht
Zeigt den Vollständigkeitsstatus aller Bereiche und eine Zusammenfassung des geladenen ASDF-Baums.

### Werkstück
- **Basismaterial** — Werkstoffgruppe und -bezeichnung (Stahl, Aluminium, Nickel, Titan) mit Kennwerten aus Normdatenbank
- **Nahtgeometrie (ISO 9692-1)** — V-Naht, I-Naht, HV-Naht, U-Naht, X-Naht (Doppel-V) mit parametrischer Eingabe, 2D-Querschnitt (matplotlib) und interaktiver 3D-Vorschau (plotly) nebeneinander
- **Werkstück-Geometrie** — Nahtlänge, Schweißgeschwindigkeit, CSV-Import für 3D-Schweißbahnen

### Schweißprozess
- Schweißverfahren (Tag, Basisprozess, Hersteller, Stromquelle)
- Schutzgas (Bezeichnung, Komponenten, Durchflussrate nach ISO 14175)
- Zusatzwerkstoff (Drahttyp, Durchmesser)

### Messdaten
Interaktive Plotly-Visualisierung der Zeitreihen aus dem RoboScope-Export (Schweißstrom, -spannung, Drahtvorschub, Gasfluss) mit Equipment-basierten Messketten.

### Koordinatensysteme
Hierarchische Darstellung der Koordinatensystem-Baumstruktur mit Transformations-Editor.

### Qualität
Bewertungsstufen B/C/D nach ISO 5817 mit Schema-Validierung.

## Projektstruktur

```
WeldX_GUI/
├── run.py                          # Start-Script mit Dependency-Check
├── requirements.txt
├── .streamlit/config.toml          # Dark-Theme-Konfiguration
└── weldx_editor/
    ├── app.py                      # Haupt-App (Sidebar, Routing, Upload)
    ├── panels/
    │   ├── overview.py             # Übersicht + Vollständigkeit
    │   ├── workpiece.py            # Material, Nahtgeometrie, Geometrie
    │   ├── process.py              # Verfahren, Gas, Zusatzwerkstoff
    │   ├── measurements.py         # Zeitreihen-Visualisierung
    │   ├── coordinates.py          # KOS-Hierarchie
    │   └── quality.py              # ISO 5817 Bewertung
    └── utils/
        ├── weldx_io.py             # WelDX/ASDF Lesen + Schreiben
        ├── style.py                # Farben, CSS, UI-Helfer
        └── session_persistence.py  # Auto-Save/Restore bei Browser-Reload
```

## Datei-Formate

Der Editor unterstützt `.weldx`, `.wx` und `.asdf` Dateien. Das Laden erfolgt per Drag & Drop oder Dateiauswahl in der Seitenleiste. Die angereicherte Datei kann als `.weldx` gespeichert werden.

## Session-Persistenz

Alle Nutzereingaben (Material, Nut-Parameter, Qualitätsstufe etc.) werden automatisch als `.weldx_session.json` gespeichert und bei einem Browser-Reload wiederhergestellt. Falls die Original-`.wx`-Datei noch vorhanden ist, werden auch die Messdaten neu geladen.

## Referenzen

- [WelDX-Dokumentation](https://weldx.readthedocs.io/)
- [WelDX GitHub](https://github.com/BAMWelDX/weldx)
- [ISO 9692-1](https://www.iso.org/standard/62520.html) — Schweißnahtvorbereitung
- [ISO 14175](https://www.iso.org/standard/54893.html) — Schutzgase
- [ISO 5817](https://www.iso.org/standard/54952.html) — Bewertungsgruppen für Unregelmäßigkeiten

## Lizenz

Internes Projekt — RoboScope / BAM.
