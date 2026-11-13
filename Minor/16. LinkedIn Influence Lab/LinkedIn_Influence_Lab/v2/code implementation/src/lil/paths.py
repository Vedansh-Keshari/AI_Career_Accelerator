"""Single source of truth for every folder the project reads or writes.

Set the environment variable LIL_HOME to point the whole project at a different
workspace (the test-suite does this so it never touches real data).
"""
from __future__ import annotations

import os
from pathlib import Path

PHASES = [
    {"key": "phase1", "n": 1, "folder": "phase_1_foundation", "week": "Week 1",
     "title": "Foundation: Audit & Pillars", "icon": "🧭", "color": "#7C3AED",
     "goal": "Audit the LinkedIn profile, benchmark role models, define 3-5 content pillars."},
    {"key": "phase2", "n": 2, "folder": "phase_2_ideation_drafting", "week": "Week 2",
     "title": "AI Ideation & Drafting", "icon": "💡", "color": "#F97316",
     "goal": "Generate 15+ ideas, draft 10+ optimized posts, pick 2-3 pilot posts."},
    {"key": "phase3", "n": 3, "folder": "phase_3_calendar_taplio", "week": "Week 3",
     "title": "Calendar & Taplio Setup", "icon": "📅", "color": "#EC4899",
     "goal": "Build the 6-week content calendar and the Taplio-ready scheduling queue."},
    {"key": "phase4", "n": 4, "folder": "phase_4_publish_track", "week": "Weeks 4-5",
     "title": "Publish & Track", "icon": "🚀", "color": "#0EA5E9",
     "goal": "Publish consistently, log likes / comments / shares / impressions per post."},
    {"key": "phase5", "n": 5, "folder": "phase_5_analytics_review", "week": "Week 6",
     "title": "Analytics & Review", "icon": "📈", "color": "#10B981",
     "goal": "Analyse engagement, refine the strategy, produce the performance review."},
]

DELIVERABLES = {
    "capstone": "00_capstone_report",
    "calendar": "01_content_calendar",
    "drafts": "02_post_drafts",
    "dashboard": "03_engagement_dashboard",
    "audit": "04_branding_audit_report",
    "review": "05_performance_review_report",
    "taplio": "06_taplio_queue",
}


_resolver = None  # set by the Streamlit app so each browser session can pick its own workspace


def set_resolver(fn) -> None:
    """fn() must return "sample" or "mine". Pass None to restore the default ("mine")."""
    global _resolver
    _resolver = fn


def app_root() -> Path:
    """Where the program itself lives (docs, templates, sample_data). Never a workspace."""
    return Path(__file__).resolve().parents[2]


def base() -> Path:
    """Parent of the workspaces. LIL_HOME relocates it (the test-suite does this)."""
    env = os.environ.get("LIL_HOME")
    root = Path(env).resolve() if env else app_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


_last = "mine"  # last workspace a browser session reported; used by code running outside a script run (tests, tools)


def workspace() -> str:
    global _last
    if _resolver is None:
        return "mine"
    try:
        name = _resolver()
    except Exception:
        name = None
    if name in ("mine", "sample"):
        _last = name
        return name
    return _last


def is_sample() -> bool:
    return workspace() == "sample"


def home() -> Path:
    """The active workspace: <base>/ for your own work, <base>/sample_workspace/ for the sample data."""
    root = base() / "sample_workspace" if is_sample() else base()
    root.mkdir(parents=True, exist_ok=True)
    return root


def sample_dir() -> Path:
    return app_root() / "sample_data"


def _mk(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def inputs_dir() -> Path:
    return _mk(home() / "data" / "inputs")


def state_dir() -> Path:
    return _mk(home() / "data" / "state")


def logs_dir() -> Path:
    return _mk(home() / "logs")


def backups_dir() -> Path:
    return _mk(home() / "backups")


def phase_dir(key: str) -> Path:
    folder = next(p["folder"] for p in PHASES if p["key"] == key)
    return _mk(home() / "phases" / folder)


def deliverable_dir(key: str) -> Path:
    return _mk(home() / "deliverables" / DELIVERABLES[key])


def phase_info(key: str) -> dict:
    return next(p for p in PHASES if p["key"] == key)
