"""Turns the raw profile into the placeholders used by hooks, posts and prompts."""
from __future__ import annotations

import re

from . import settings
from .knowledge import PERSONAS, PILLARS

PLACEHOLDER = "[add your real example here]"


class SafeDict(dict):
    def __missing__(self, key):
        return ""


def fill(template: str, ctx: dict) -> str:
    return template.format_map(SafeDict(ctx))


def experience_pool(profile: dict) -> list[str]:
    pool = [profile.get("story_win", ""), profile.get("story_mistake", ""), profile.get("story_lesson", "")]
    pool += str(profile.get("achievements", "")).splitlines()
    return [p.strip() for p in pool if p and p.strip()]


def build(profile: dict) -> dict:
    skills = settings.skill_list(profile)
    industry = profile.get("industry", "").strip() or "my field"
    role = profile.get("current_role", "").strip() or "professional"
    years = str(profile.get("years_experience", "")).strip()
    return {
        "name": profile.get("name", "").strip(),
        "first_name": (profile.get("name", "").strip().split() or [""])[0],
        "role": role, "company": profile.get("company", "").strip(), "industry": industry,
        "skill": skills[0] if skills else industry,
        "skill2": skills[1] if len(skills) > 1 else (skills[0] if skills else industry),
        "skill3": skills[2] if len(skills) > 2 else (skills[1] if len(skills) > 1 else industry),
        "audience": profile.get("target_audience", "").strip() or "professionals",
        "goal": profile.get("goal", "").strip(),
        "target_roles": profile.get("target_roles", "").strip() or role,
        "offer": profile.get("offer", "").strip() or (skills[0] if skills else industry),
        "years": (f"{years} years" if years.isdigit() else years) or "a few years",
    }


def effective_weights(profile: dict) -> dict:
    """Persona default weights limited to the pillars the user selected (3-5), re-normalised."""
    base = PERSONAS[profile.get("persona", "professional")]["weights"]
    chosen = [p for p in profile.get("pillars", []) if p in PILLARS] or [
        k for k, _ in sorted(base.items(), key=lambda kv: -kv[1])[:4]]
    custom = profile.get("custom_weights") or {}
    weights = {k: float(custom.get(k, base[k])) for k in chosen}  # custom = mix applied from the Phase 5 review
    total = sum(weights.values()) or 1
    return {k: round(v / total, 4) for k, v in weights.items()}


def slug_tag(text: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", text)
    return "".join(w.capitalize() for w in words)[:30]
