"""Explores all three user-story paths side by side (Part 4 of the brief)."""
from __future__ import annotations

from . import audit, context, drafting, ideation, planner
from .knowledge import IDEA_BANK, PERSONA_IDEAS, PERSONAS, PILLARS
from .persona_content import HUB, HUB_FEATURES, KPI_FIELDS, PAGES, PHASE_EFFECTS, PRIMARY_DELIVERABLES, nav_keys


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


def hook_options(profile: dict, persona: str, limit: int = 8) -> list[dict]:
    """A selectable set of first-hook options for a path: one per pillar plus the path's own extras."""
    p = {**profile, "persona": persona}
    c = context.build(p)
    extras = {pillar: (h, a) for pillar, h, a in PERSONA_IDEAS.get(persona, [])}
    out, seen = [], set()

    def add(pillar, hook, angle):
        text = context.fill(hook, c)
        if text not in seen:
            seen.add(text)
            out.append({"pillar": pillar, "hook": text, "angle": angle})
    for pillar in PILLARS:
        if pillar in extras:
            add(pillar, *extras[pillar])
        else:
            hook, angle = next(((h, a) for h, a in IDEA_BANK[pillar] if not h[0].isdigit()), IDEA_BANK[pillar][0])
            add(pillar, hook, angle)
    for pillar, h, a in PERSONA_IDEAS.get(persona, []):
        add(pillar, h, a)
    return out[:limit]


def impact(profile: dict, target: str) -> list[dict]:
    """What changes in each area if the user moves from their current path to `target`."""
    now = profile.get("persona", "professional")
    a, b = PERSONAS[now], PERSONAS[target]
    pa, pb = {**profile, "persona": now, "pillars": [], "custom_weights": {}}, {**profile, "persona": target, "pillars": [], "custom_weights": {}}
    mix = lambda pp: ", ".join(f"{PILLARS[k]['label']} {round(v * 100)}%" for k, v in sorted(context.effective_weights(pp).items(), key=lambda kv: -kv[1]))
    tabs = lambda k: ", ".join(PAGES[x].split(" ", 1)[1] for x in nav_keys(k) if x in HUB.values())
    rows = [
        {"Area": "Extra tab in the sidebar", "Now": tabs(now), "If you switch": tabs(target)},
        {"Area": "Pillar mix", "Now": mix(pa), "If you switch": mix(pb)},
        {"Area": "Posting days", "Now": ", ".join(d[:3] for d in a["default_days"]), "If you switch": ", ".join(d[:3] for d in b["default_days"])},
        {"Area": "Format rotation", "Now": " > ".join(a["format_cycle"]), "If you switch": " > ".join(b["format_cycle"])},
        {"Area": "Hub features", "Now": "; ".join(HUB_FEATURES[now]), "If you switch": "; ".join(HUB_FEATURES[target])},
    ]
    for ph, label in (("phase1", "Phase 1 · Audit & pillars"), ("phase2", "Phase 2 · Ideas & drafts"), ("phase3", "Phase 3 · Calendar"),
                      ("phase4", "Phase 4 · Weekly log"), ("phase5", "Phase 5 · Analytics")):
        rows.append({"Area": label, "Now": PHASE_EFFECTS[ph][now], "If you switch": PHASE_EFFECTS[ph][target]})
    rows += [{"Area": "Weekly path KPIs", "Now": ", ".join(f["label"] for f in KPI_FIELDS[now]), "If you switch": ", ".join(f["label"] for f in KPI_FIELDS[target])},
             {"Area": "Deliverables in focus", "Now": ", ".join(PRIMARY_DELIVERABLES[now]), "If you switch": ", ".join(PRIMARY_DELIVERABLES[target])}]
    return rows
