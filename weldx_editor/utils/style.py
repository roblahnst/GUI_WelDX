"""
Shared styling constants and CSS for the WeldX Editor.
"""

# Color palette matching our prototype
COLORS = {
    "bg": "#0f1117",
    "surface": "#1a1d27",
    "card": "#1e2230",
    "border": "#2a2f40",
    "border_active": "#4f8ef7",
    "text": "#e2e8f0",
    "text_muted": "#8892a8",
    "text_dim": "#5a6378",
    "accent": "#4f8ef7",
    "success": "#34d399",
    "warning": "#fbbf24",
    "error": "#f87171",
    "purple": "#a78bfa",
}

STATUS_COLORS = {
    "complete": COLORS["success"],
    "partial": COLORS["warning"],
    "missing": COLORS["error"],
}

STATUS_LABELS = {
    "complete": "Vollständig",
    "partial": "Teilweise",
    "missing": "Fehlt",
}

STATUS_ICONS = {
    "complete": "✅",
    "partial": "🟡",
    "missing": "🔴",
}

# Navigation structure
NAV_ITEMS = [
    {"id": "overview", "icon": "📋", "label": "Übersicht", "description": "Datei-Status & Vollständigkeit"},
    {"id": "workpiece", "icon": "📦", "label": "Werkstück", "description": "Material, Geometrie, Nahtform"},
    {"id": "process", "icon": "⚡", "label": "Schweißprozess", "description": "Verfahren, Parameter, Schutzgas"},
    {"id": "measurements", "icon": "📊", "label": "Messdaten", "description": "Zeitreihen, Sensoren, Messketten"},
    {"id": "coordinates", "icon": "🌳", "label": "Koordinatensysteme", "description": "CSM, Transformationen, Roboter"},
    {"id": "quality", "icon": "🛡️", "label": "Qualität", "description": "Standards, Normen, Validierung"},
]


def get_custom_css() -> str:
    """Return custom CSS for the Streamlit app."""
    return """
    <style>
    /* Global dark theme adjustments */
    .stApp {
        background-color: #0f1117;
    }

    /* Navigation styling */
    .nav-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 14px;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.15s;
        border: 1px solid transparent;
        margin-bottom: 4px;
    }
    .nav-item:hover {
        background-color: #222633;
    }
    .nav-item.active {
        background-color: rgba(79, 142, 247, 0.12);
        border-color: rgba(79, 142, 247, 0.3);
    }

    /* Status badges */
    .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 2px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
    }
    .status-complete { color: #34d399; background: rgba(52, 211, 153, 0.1); }
    .status-partial { color: #fbbf24; background: rgba(251, 191, 36, 0.1); }
    .status-missing { color: #f87171; background: rgba(248, 113, 113, 0.1); }

    /* Card styling */
    .wx-card {
        background-color: #1e2230;
        border: 1px solid #2a2f40;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 10px;
    }
    .wx-card:hover {
        border-color: #3a4560;
    }

    /* Progress bar */
    .wx-progress-container {
        height: 6px;
        background-color: #2a2f40;
        border-radius: 3px;
        overflow: hidden;
    }
    .wx-progress-bar {
        height: 100%;
        border-radius: 3px;
        transition: width 0.5s ease;
    }

    /* Metric cards */
    .metric-card {
        background: #1e2230;
        border: 1px solid #2a2f40;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
    }

    /* Groove preview */
    .groove-preview {
        background: #0f1117;
        border: 1px solid #2a2f40;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        font-family: monospace;
    }

    /* Measurement chain */
    .chain-step {
        display: inline-flex;
        flex-direction: column;
        align-items: center;
        padding: 10px 14px;
        border-radius: 8px;
        border: 1px solid #2a2f40;
        background: #0f1117;
        min-width: 120px;
        text-align: center;
    }
    .chain-arrow {
        display: inline-flex;
        align-items: center;
        padding: 0 8px;
        color: #5a6378;
        font-size: 18px;
    }

    /* Hide default Streamlit elements for cleaner look */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Hide header branding/deploy buttons but keep sidebar toggle */
    [data-testid="stHeader"] {
        pointer-events: auto !important;
    }
    [data-testid="stAppDeployButton"],
    [data-testid="stHeaderActionElements"],
    [data-testid="stStatusWidget"] {
        display: none !important;
    }

    /* Sidebar refinements */
    [data-testid="stSidebar"] {
        background-color: #1a1d27;
    }
    [data-testid="stSidebar"] .stMarkdown h1 {
        font-size: 18px;
    }

    /* Selectbox styling */
    .stSelectbox > div > div {
        background-color: #0f1117;
        border-color: #2a2f40;
    }
    </style>
    """


def status_badge_html(status: str) -> str:
    """Generate HTML for a status badge."""
    label = STATUS_LABELS.get(status, status)
    css_class = f"status-{status}"
    return f'<span class="status-badge {css_class}">{label}</span>'


def progress_bar_html(value: int, color: str = "#4f8ef7") -> str:
    """Generate HTML for a custom progress bar."""
    return f"""
    <div class="wx-progress-container">
        <div class="wx-progress-bar" style="width: {value}%; background-color: {color};"></div>
    </div>
    """


def metric_card_html(value: str, label: str, sub: str, color: str = "#4f8ef7") -> str:
    """Generate HTML for a metric card."""
    return f"""
    <div class="metric-card">
        <div class="metric-value" style="color: {color};">{value}</div>
        <div style="font-size: 13px; color: #e2e8f0; font-weight: 500;">{label}</div>
        <div style="font-size: 11px; color: #8892a8;">{sub}</div>
    </div>
    """
