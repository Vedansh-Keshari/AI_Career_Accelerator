"""Pure business logic for FocusDesk (no Streamlit imports, easy to test)."""
from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import date, timedelta

PRIORITIES = ["High", "Medium", "Low"]
_RANK = {p: i for i, p in enumerate(PRIORITIES)}
MAX_SESSION_MINUTES = 600


_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$"
)


def new_data() -> dict:
    return {"tasks": [], "sessions": []}


# ---------- email (required to enter the app) ----------
def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def validate_email(email: str) -> str:
    """Return the normalised email, or raise ValueError with a friendly message.

    This checks the *format* only. FocusDesk runs locally with no mail server,
    so it cannot confirm that the address really belongs to the user.
    """
    clean = normalize_email(email)
    if not clean:
        raise ValueError("Email is required to enter FocusDesk.")
    if len(clean) > 254 or ".." in clean or not _EMAIL_RE.match(clean):
        raise ValueError("Enter a valid email address, for example name@example.com.")
    return clean


# ---------- tasks ----------
def add_task(data: dict, title: str, priority: str = "Medium",
             due: date | None = None, today: date | None = None) -> dict:
    title = (title or "").strip()
    if not title:
        raise ValueError("Task title cannot be empty.")
    if priority not in _RANK:
        raise ValueError(f"Priority must be one of {PRIORITIES}.")
    today = today or date.today()
    task = {
        "id": uuid.uuid4().hex[:8],
        "title": title,
        "priority": priority,
        "due": due.isoformat() if due else None,
        "done": False,
        "created": today.isoformat(),
        "completed": None,
    }
    data["tasks"].append(task)
    return task


def _find(data: dict, task_id: str) -> dict:
    for t in data["tasks"]:
        if t["id"] == task_id:
            return t
    raise KeyError(f"Task {task_id} not found.")


def complete_task(data: dict, task_id: str, today: date | None = None) -> dict:
    t = _find(data, task_id)
    t["done"] = True
    t["completed"] = (today or date.today()).isoformat()
    return t


def reopen_task(data: dict, task_id: str) -> dict:
    t = _find(data, task_id)
    t["done"] = False
    t["completed"] = None
    return t


def delete_task(data: dict, task_id: str) -> None:
    _find(data, task_id)
    data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]


def is_overdue(task: dict, today: date | None = None) -> bool:
    today = today or date.today()
    return bool(task["due"]) and not task["done"] and task["due"] < today.isoformat()


def sort_tasks(tasks: list[dict]) -> list[dict]:
    """Open tasks first, then by priority, due date (soonest), creation date."""
    return sorted(
        tasks,
        key=lambda t: (t["done"], _RANK[t["priority"]], t["due"] or "9999-12-31", t["created"]),
    )


def filter_tasks(tasks: list[dict], status: str = "Open",
                 priorities: list[str] | None = None, query: str = "") -> list[dict]:
    out = []
    q = (query or "").strip().lower()
    for t in tasks:
        if status == "Open" and t["done"]:
            continue
        if status == "Done" and not t["done"]:
            continue
        if priorities is not None and t["priority"] not in priorities:
            continue
        if q and q not in t["title"].lower():
            continue
        out.append(t)
    return sort_tasks(out)


# ---------- focus sessions ----------
def add_session(data: dict, minutes: int, task_id: str | None = None,
                note: str = "", day: date | None = None) -> dict:
    if not isinstance(minutes, int) or not 1 <= minutes <= MAX_SESSION_MINUTES:
        raise ValueError(f"Minutes must be a whole number between 1 and {MAX_SESSION_MINUTES}.")
    title = None
    if task_id:
        title = _find(data, task_id)["title"]
    s = {
        "id": uuid.uuid4().hex[:8],
        "date": (day or date.today()).isoformat(),
        "minutes": minutes,
        "task_id": task_id,
        "task_title": title,
        "note": (note or "").strip(),
    }
    data["sessions"].append(s)
    return s


def delete_session(data: dict, session_id: str) -> None:
    data["sessions"] = [s for s in data["sessions"] if s["id"] != session_id]


def focus_by_day(data: dict, today: date | None = None, days: int = 7) -> list[tuple[str, int]]:
    today = today or date.today()
    totals = {(today - timedelta(days=i)).isoformat(): 0 for i in range(days - 1, -1, -1)}
    for s in data["sessions"]:
        if s["date"] in totals:
            totals[s["date"]] += s["minutes"]
    return list(totals.items())


def summary(data: dict, today: date | None = None) -> dict:
    today = today or date.today()
    week_start = (today - timedelta(days=6)).isoformat()
    tasks = data["tasks"]
    return {
        "open": sum(1 for t in tasks if not t["done"]),
        "overdue": sum(1 for t in tasks if is_overdue(t, today)),
        "done_week": sum(1 for t in tasks if t["done"] and t["completed"] and t["completed"] >= week_start),
        "focus_week": sum(s["minutes"] for s in data["sessions"] if s["date"] >= week_start),
        "focus_total": sum(s["minutes"] for s in data["sessions"]),
    }


def priority_counts(data: dict) -> dict[str, int]:
    """Number of open tasks per priority (used by the Insights tab)."""
    counts = {p: 0 for p in PRIORITIES}
    for t in data["tasks"]:
        if not t["done"]:
            counts[t["priority"]] += 1
    return counts


def format_minutes(total: int) -> str:
    h, m = divmod(int(total), 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"


def tasks_to_csv(tasks: list[dict]) -> str:
    buf = io.StringIO()
    fields = ["id", "title", "priority", "due", "done", "created", "completed"]
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(tasks)
    return buf.getvalue()
