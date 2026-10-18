"""Model (sample) data for trying and testing FocusDesk.

Dates are relative to "today", so the sample always looks fresh: some tasks are
overdue, some due today or soon, some done this week, and focus sessions are
spread over the last 3 weeks. Every sample record carries ``"sample": True`` so
it can be removed again without touching the user's own data.

Expected numbers (for any ``today``):
    open tasks 8 | overdue 2 | done in last 7 days 2 | done overall 3
    open by priority: High 2, Medium 3, Low 3
    focus last 7 days 365 min | focus overall 425 min
"""
from __future__ import annotations

from datetime import date, timedelta

# key, title, priority, due offset, created offset, done, completed offset
_TASKS = [
    ("t01", "Prepare Q4 project proposal", "High", -2, -9, False, None),
    ("t02", "Reply to client emails", "High", 0, -2, False, None),
    ("t03", "Review pull requests", "Medium", 1, -6, False, None),
    ("t04", "Plan next week's sprint", "Medium", 3, -8, False, None),
    ("t05", "Read Streamlit docs on caching", "Low", 7, -5, False, None),
    ("t06", "Organise project folders", "Low", None, -8, False, None),
    ("t07", "Update resume with AI projects", "Medium", -1, -12, False, None),
    ("t08", "Submit expense report", "High", -1, -7, True, -1),
    ("t09", "Set up GitHub repository", "Medium", None, -6, True, -3),
    ("t10", "Renew domain name", "Low", -9, -15, True, -10),
    ("t11", "Check <b>budget</b> & costs ($5 + $10)", "Low", 2, -1, False, None),
]

# day offset, minutes, task key (or None), note
_SESSIONS = [
    (0, 25, "t02", "Inbox zero sprint"),
    (0, 50, "t01", "Outline and first draft"),
    (-1, 45, "t07", "Resume bullet points"),
    (-2, 90, "t01", "Deep work block"),
    (-3, 30, None, "Reading and learning"),
    (-3, 25, "t09", "Repo setup"),
    (-4, 60, "t03", "Code review session"),
    (-6, 40, "t04", "Sprint planning notes"),
    (-8, 35, None, "Weekend study"),
    (-20, 25, None, "Older session"),
]


def _iso(today: date, offset: int | None) -> str | None:
    return None if offset is None else (today + timedelta(days=offset)).isoformat()


def build_sample(today: date | None = None) -> dict:
    """Return {"tasks": [...], "sessions": [...]} of fresh sample records."""
    today = today or date.today()
    tasks, titles = [], {}
    for key, title, prio, due, created, done, completed in _TASKS:
        tid = f"demo-{key}"
        titles[key] = (tid, title)
        tasks.append({
            "id": tid, "title": title, "priority": prio, "due": _iso(today, due),
            "done": done, "created": _iso(today, created),
            "completed": _iso(today, completed), "sample": True,
        })
    sessions = []
    for i, (offset, minutes, key, note) in enumerate(_SESSIONS, start=1):
        tid, title = titles[key] if key else (None, None)
        sessions.append({
            "id": f"demo-s{i:02d}", "date": _iso(today, offset), "minutes": minutes,
            "task_id": tid, "task_title": title, "note": note, "sample": True,
        })
    return {"tasks": tasks, "sessions": sessions}


def has_sample(data: dict) -> bool:
    return any(r.get("sample") for r in data["tasks"] + data["sessions"])


def remove_sample(data: dict) -> int:
    """Remove all sample records; returns how many were removed."""
    before = len(data["tasks"]) + len(data["sessions"])
    data["tasks"] = [t for t in data["tasks"] if not t.get("sample")]
    data["sessions"] = [s for s in data["sessions"] if not s.get("sample")]
    return before - len(data["tasks"]) - len(data["sessions"])


def load_sample(data: dict, today: date | None = None) -> int:
    """Add the sample records (replacing any earlier copy); returns records added."""
    remove_sample(data)
    sample = build_sample(today)
    data["tasks"].extend(sample["tasks"])
    data["sessions"].extend(sample["sessions"])
    return len(sample["tasks"]) + len(sample["sessions"])
