"""User inputs (profile) and plugin configuration."""
from __future__ import annotations

from datetime import date, timedelta

from . import paths, store

CHECK_KEYS = ["photo", "banner", "custom_url", "featured", "skills_15", "recs_3",
              "experience_metrics", "visibility"]


def next_monday(today: date | None = None) -> date:
    today = today or date.today()
    return today + timedelta(days=(7 - today.weekday()) % 7 or 7)


def default_profile() -> dict:
    return {
        "name": "", "email": "", "google_email": "", "linkedin_url": "", "taplio_account": "",
        "persona": "professional",
        "current_role": "", "company": "", "industry": "", "years_experience": "",
        "skills": "", "target_audience": "", "goal": "", "target_roles": "", "offer": "",
        "tone": "Professional but relatable",
        "pillars": [],
        "story_win": "", "story_mistake": "", "story_lesson": "", "achievements": "",
        "role_models": "",
        "current_headline": "", "current_about": "", "followers": 0, "connections": 0,
        "posts_per_month_now": 0,
        "checks": {k: False for k in CHECK_KEYS},
        "days": ["Tuesday", "Wednesday", "Thursday"], "time": "08:30",
        "timezone": "Asia/Kolkata", "start_date": next_monday().isoformat(),
    }


def profile_path():
    return paths.inputs_dir() / "profile.json"


def load_profile() -> dict:
    prof = default_profile()
    saved = store.read_json(profile_path(), {}) or {}
    checks = {**prof["checks"], **(saved.get("checks") or {})}
    prof.update({k: v for k, v in saved.items() if k != "checks"})
    prof["checks"] = checks
    return prof


def save_profile(profile: dict) -> None:
    store.write_json(profile_path(), profile)


REQUIRED = {"name": "Your name", "current_role": "Current role", "industry": "Industry",
            "target_audience": "Target audience", "goal": "Main goal", "skills": "Key skills"}


def missing_fields(profile: dict) -> list[str]:
    return [label for key, label in REQUIRED.items() if not str(profile.get(key, "")).strip()]


def skill_list(profile: dict) -> list[str]:
    return [s.strip() for s in str(profile.get("skills", "")).replace("\n", ",").split(",") if s.strip()]


# --- plugin configuration (kept separate: it may hold API keys) -------------
def plugin_cfg_path():
    return paths.inputs_dir() / "plugins.json"


def load_plugin_cfg() -> dict:
    cfg = store.read_json(plugin_cfg_path(), {}) or {}
    cfg.setdefault("active_ai", "ai_offline")
    cfg.setdefault("plugins", {})
    return cfg


def save_plugin_cfg(cfg: dict) -> None:
    store.write_json(plugin_cfg_path(), cfg)
