"""
Session persistence for WeldX Editor.

Saves user-editable state (material, groove, quality, etc.) as JSON so it
survives browser reloads.  The original .wx measurement data is NOT duplicated
— only the file_path is stored so the file can be re-loaded on restore.
"""

import json
import os
from pathlib import Path
from typing import Optional

# Persist next to the running app (or /tmp as fallback)
_SESSION_DIR = Path(os.environ.get(
    "WELDX_SESSION_DIR",
    Path(__file__).resolve().parent.parent.parent,  # WeldX_GUI/
))
_SESSION_FILE = _SESSION_DIR / ".weldx_session.json"


def _serialisable(obj):
    """Convert state fields to JSON-safe types."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _serialisable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialisable(v) for v in obj]
    # Skip non-serialisable objects (numpy arrays, weldx objects, etc.)
    return None


def save_session(state, active_panel: str = "overview") -> bool:
    """Persist user-editable state fields to disk.  Returns True on success."""
    try:
        groove_raw = getattr(state, "groove", {}) or {}
        groove_data = {k: v for k, v in groove_raw.items() if k != "object"} if isinstance(groove_raw, dict) else {}
        data = {
            "file_path": state.file_path,
            "base_metal": _serialisable(getattr(state, "base_metal", {})),
            "groove": _serialisable(groove_data),
            "shielding_gas": _serialisable(getattr(state, "shielding_gas", {})),
            "process": _serialisable(getattr(state, "process", {})),
            "filler_material": _serialisable(getattr(state, "filler_material", {})),
            "quality": _serialisable(getattr(state, "quality", {})),
            "coordinate_systems": _serialisable(getattr(state, "coordinate_systems", {})),
            "metadata": _serialisable(getattr(state, "metadata", {})),
            "active_panel": active_panel,
        }
        _SESSION_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        return True
    except Exception:
        return False


def load_session() -> Optional[dict]:
    """Load saved session data from disk.  Returns dict or None."""
    try:
        if _SESSION_FILE.exists():
            return json.loads(_SESSION_FILE.read_text())
    except Exception:
        pass
    return None


def restore_into_state(state, saved: dict):
    """Apply saved user-editable fields back into a WeldxFileState."""
    for key in ("base_metal", "groove", "shielding_gas", "process",
                "filler_material", "quality", "coordinate_systems", "metadata"):
        val = saved.get(key)
        if val:
            setattr(state, key, val)


def clear_session():
    """Remove saved session file."""
    try:
        if _SESSION_FILE.exists():
            _SESSION_FILE.unlink()
    except Exception:
        pass
