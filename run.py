#!/usr/bin/env python3
"""
WelDX Editor - Quick Start Script

Usage:
    python run.py

This will start the Streamlit server and open the WelDX Editor in your browser.
"""
import subprocess
import sys
import os


def check_dependencies():
    """Check if required packages are installed."""
    missing = []

    try:
        import streamlit
    except ImportError:
        missing.append("streamlit")

    try:
        import plotly
    except ImportError:
        missing.append("plotly")

    try:
        import pandas
    except ImportError:
        missing.append("pandas")

    try:
        import numpy
    except ImportError:
        missing.append("numpy")

    # weldx is optional (demo mode works without it)
    try:
        import weldx
        print(f"  ✅ weldx {weldx.__version__}")
    except ImportError:
        print("  ⚠️  weldx nicht installiert (Demo-Modus verfügbar)")

    if missing:
        print(f"\n❌ Fehlende Pakete: {', '.join(missing)}")
        print(f"\nInstallieren mit:")
        print(f"  pip install {' '.join(missing)}")
        sys.exit(1)


def main():
    print("=" * 50)
    print("  🔧 WelDX Editor v0.1.0")
    print("=" * 50)
    print("\nPrüfe Abhängigkeiten...")

    check_dependencies()

    print("\nStarte Streamlit-Server...\n")

    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, "weldx_editor", "app.py")

    # Launch streamlit
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        app_path,
        "--server.headless=false",
        "--theme.base=dark",
        "--theme.primaryColor=#4f8ef7",
        "--theme.backgroundColor=#0f1117",
        "--theme.secondaryBackgroundColor=#1a1d27",
        "--theme.textColor=#e2e8f0",
        "--browser.gatherUsageStats=false",
    ])


if __name__ == "__main__":
    main()
