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


def home() -> Path:
    env = os.environ.get("LIL_HOME")
    root = Path(env).resolve() if env else Path(__file__).resolve().parents[2]
    root.mkdir(parents=True, exist_ok=True)
    return root


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
