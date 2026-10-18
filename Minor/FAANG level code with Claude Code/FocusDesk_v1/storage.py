"""JSON file persistence for FocusDesk. Data stays on your machine."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from logic import new_data


def data_path() -> Path:
    env = os.environ.get("FOCUSDESK_DATA")
    return Path(env) if env else Path(__file__).parent / "data" / "focusdesk.json"


def load() -> dict:
    p = data_path()
    if not p.exists():
        return new_data()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Keep the unreadable file as a backup instead of silently overwriting it.
        try:
            p.replace(p.with_suffix(".corrupt.json"))
        except OSError:
            pass
        return new_data()
    data = new_data()
    if isinstance(raw, dict):
        data["tasks"] = raw.get("tasks", []) if isinstance(raw.get("tasks"), list) else []
        data["sessions"] = raw.get("sessions", []) if isinstance(raw.get("sessions"), list) else []
    return data


def save(data: dict) -> None:
    p = data_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, p)  # atomic write
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
