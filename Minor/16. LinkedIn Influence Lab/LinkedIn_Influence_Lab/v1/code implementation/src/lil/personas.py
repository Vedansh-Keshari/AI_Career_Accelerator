"""Explores all three user-story paths side by side (Part 4 of the brief)."""
from __future__ import annotations

from . import audit, context, drafting, ideation, planner
from .knowledge import PERSONAS, PILLARS


def compare(profile: dict) -> list[dict]:
    rows = []
    for key, meta in PERSONAS.items():
        p = {**profile, "persona": key, "pillars": [], "days": meta["default_days"]}
        slots = planner.plan_slots(p)
        ideas = ideation.generate_ideas(p, slots, use_ai=False)["ideas"]
        sample = drafting.build_drafts(p, ideas[:1], use_ai=False)[0] if ideas else {"text": ""}
        w = context.effective_weights(p)
        rows.append({
            "key": key, "label": meta["label"], "emoji": meta["emoji"], "color": meta["color"],
            "story": meta["story"], "goal": meta["goal"], "kpis": meta["kpis"],
            "days": ", ".join(d[:3] for d in meta["default_days"]),
            "mix": {PILLARS[k]["label"]: f"{round(v * 100)}%" for k, v in w.items()},
            "formats": " > ".join(meta["format_cycle"]), "headline": audit.headline_options(p)[0],
            "sample_hook": sample.get("hook", ""), "slots": len(slots),
        })
    return rows
