"""JSON file persistence for FocusDesk v2. One data file per user (by email).

Data never leaves this computer. Files live in ``data/`` (or in the folder set by
the FOCUSDESK_DATA_DIR environment variable) and are named from a hash of the
email, so file names do not reveal the address. The email itself is stored
inside the file as ``owner``.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import date
from pathlib import Path

import logic

LEGACY_FILE = "focusdesk.json"  # single-user file written by v1
LEGACY_BACKUP = "focusdesk.v1-backup.json"


def data_dir() -> Path:
    env = os.environ.get("FOCUSDESK_DATA_DIR")
    return Path(env) if env else Path(__file__).parent / "data"


def user_file(email: str) -> Path:
    key = hashlib.sha256(logic.normalize_email(email).encode("utf-8")).hexdigest()[:16]
    return data_dir() / f"user_{key}.json"


# ---------- reading ----------
def _clean_task(t) -> dict | None:
    if not isinstance(t, dict) or not t.get("id") or not str(t.get("title", "")).strip():
        return None
    out = dict(t)
    out["id"] = str(t["id"])
    out["title"] = str(t["title"]).strip()
    if out.get("priority") not in logic.PRIORITIES:
        out["priority"] = "Medium"
    out["due"] = out.get("due") or None
    out["done"] = bool(out.get("done", False))
    out["created"] = out.get("created") or date.today().isoformat()
    out["completed"] = out.get("completed") or None
    return out


def _clean_session(s) -> dict | None:
    if not isinstance(s, dict) or not s.get("id") or not s.get("date"):
        return None
    minutes = s.get("minutes")
    if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes < 1:
        return None
    out = dict(s)
    out["id"] = str(s["id"])
    out["task_id"] = out.get("task_id") or None
    out["task_title"] = out.get("task_title") or None
    out["note"] = str(out.get("note") or "")
    return out


def _read(path: Path) -> dict | None:
    """Read and sanitise a data file. Returns None if missing or unreadable."""
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        # Keep the unreadable file as a backup instead of silently overwriting it.
        try:
            path.replace(path.with_suffix(".corrupt.json"))
        except OSError:
            pass
        return None
    data = logic.new_data()
    if isinstance(raw, dict):
        tasks = raw.get("tasks") if isinstance(raw.get("tasks"), list) else []
        sessions = raw.get("sessions") if isinstance(raw.get("sessions"), list) else []
        data["tasks"] = [t for t in map(_clean_task, tasks) if t]
        data["sessions"] = [s for s in map(_clean_session, sessions) if s]
    return data


def load(email: str) -> dict:
    """Load this user's data. On a user's very first login, any v1 data file
    (data/focusdesk.json) is adopted once and kept as a backup copy."""
    path = user_file(email)
    data = _read(path)
    if data is not None:
        return data
    legacy = data_dir() / LEGACY_FILE
    data = _read(legacy)
    if data is not None:
        save(data, email)
        try:
            legacy.replace(data_dir() / LEGACY_BACKUP)
        except OSError:
            pass
        return data
    return logic.new_data()


# ---------- writing ----------
def save(data: dict, email: str) -> None:
    path = user_file(email)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"owner": logic.normalize_email(email), **data}
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, path)  # atomic write
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
