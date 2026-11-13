"""Tiny persistence helpers: JSON / CSV files plus the phase-status ledger."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from . import paths


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path, obj) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    tmp.replace(p)
    return p


def log(message: str) -> None:
    """Append one line to logs/lil.log (first place to look when debugging)."""
    line = f"{datetime.now().isoformat(timespec='seconds')}  {message}\n"
    with open(paths.logs_dir() / "lil.log", "a", encoding="utf-8") as fh:
        fh.write(line)


# --- phase status ledger -------------------------------------------------
STATES = {
    "not_started": "Not started",
    "waiting": "Waiting on you",
    "preview": "Preview (demo data)",
    "done": "Complete",
}


def _status_path() -> Path:
    return paths.state_dir() / "status.json"


def get_status() -> dict:
    return read_json(_status_path(), {}) or {}


def set_status(key: str, state: str, note: str = "", **extra) -> None:
    data = get_status()
    data[key] = {"state": state, "note": note, "updated": datetime.now().isoformat(timespec="seconds"), **extra}
    write_json(_status_path(), data)


def phase_state(key: str) -> str:
    return get_status().get(key, {}).get("state", "not_started")
