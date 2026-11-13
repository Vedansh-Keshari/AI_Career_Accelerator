"""Phase 2a: content-idea generation (Template A). AI plugin first, template engine as fallback."""
from __future__ import annotations

import random
import re
import zlib

from . import context, llm, planner
from .knowledge import FORMATS, IDEA_BANK, PERSONA_IDEAS, PILLARS, TEMPLATE_A


def brief(profile: dict) -> str:
    c = context.build(profile)
    return (f"Author: {c['name'] or 'the author'}, {c['role']}"
            f"{' at ' + c['company'] if c['company'] else ''}, industry: {c['industry']}. "
            f"Key skills: {profile.get('skills', '')}. Audience: {c['audience']}. Goal: {c['goal']}. "
            f"Persona: {profile.get('persona')}. Tone: {profile.get('tone')}.")


def rng_for(profile: dict, salt: int = 0) -> random.Random:
    seed = zlib.crc32((profile.get("name", "") + profile.get("persona", "")).encode()) + salt
    return random.Random(seed)


STORY_ANGLES = {"mistake", "win", "origin story", "turning point", "lesson", "vulnerability", "story with lesson",
                "reflective advice", "letter to past self", "job search lesson", "why I post", "trust",
                "proof of work", "observation", "habit", "productivity", "process", "recap", "early signal", "bet",
                "team view", "recruiter view"}


def _is_list_hook(hook: str) -> bool:
    return bool(re.match(r"^(\d|three|five)\b", hook, re.I)) or "Three ideas" in hook


def _fits(hook: str, angle: str, fmt: str) -> bool:
    """Keep hooks and formats coherent: 'Top 3...' hooks never become polls or one-story posts."""
    if fmt == "micro_story":
        return angle in STORY_ANGLES and not _is_list_hook(hook)
    if fmt == "poll":
        return not _is_list_hook(hook)
    return True


def _offline(profile: dict, wanted: list[tuple]) -> list[dict]:
    c = context.build(profile)
    rng = rng_for(profile)
    persona = profile.get("persona", "professional")
    pools, used = {}, {}
    ideas = []
    pins = {}
    for h in profile.get("pinned_hooks", []):  # hooks the user pinned in the Persona Lab are used first
        if h.get("persona") == persona and h.get("hook"):
            pins.setdefault(h["pillar"], []).append(h["hook"])
    for i, (pillar, fmt, slot_id) in enumerate(wanted, 1):
        pin = next((h for h in pins.get(pillar, []) if not (fmt in ("poll", "micro_story") and _is_list_hook(h))), None)
        if pin:
            pins[pillar].remove(pin)
            ideas.append({"id": f"I{i:02d}", "pillar": pillar, "format": fmt, "slot_id": slot_id,
                          "hook": pin, "angle": "pinned by you", "source": "pinned"})
            continue
        if pillar not in pools:
            bank = list(IDEA_BANK[pillar]) + [(h, a) for p, h, a in PERSONA_IDEAS.get(persona, []) if p == pillar]
            rng.shuffle(bank)
            pools[pillar], used[pillar] = bank, set()
        bank = pools[pillar]
        fresh = [n for n in range(len(bank)) if n not in used[pillar]]
        revisit = not fresh
        if revisit:
            used[pillar], fresh = set(), list(range(len(bank)))
        n = next((k for k in fresh if _fits(*bank[k], fmt)), None)
        if n is None:  # nothing unused fits this format: reuse a fitting hook with a fresh angle before compromising
            n = next((k for k in range(len(bank)) if _fits(*bank[k], fmt)), fresh[0])
            revisit = revisit or n in used[pillar]
        used[pillar].add(n)
        hook, angle = bank[n]
        if revisit:
            angle += " (fresh angle, new example)"
        ideas.append({"id": f"I{i:02d}", "pillar": pillar, "format": fmt, "slot_id": slot_id,
                      "hook": context.fill(hook, c), "angle": angle, "source": "template"})
    return ideas


def generate_ideas(profile: dict, slots: list[dict], reserve: int = 3, use_ai: bool = True) -> dict:
    weights = context.effective_weights(profile)
    extra = planner.weighted_sequence(weights, len(slots) + reserve)[-reserve:]
    wanted = [(s["pillar"], s["format"], s["slot_id"]) for s in slots] + [(p, "text", None) for p in extra]
    ideas, source, warning = _offline(profile, wanted), "Template engine", ""

    if use_ai and llm.ai_enabled():
        order = "\n".join(f"{i}. pillar={PILLARS[p]['label']}, format={FORMATS[f]['label']}"
                          for i, (p, f, _) in enumerate(wanted, 1))
        prompt = (f"{TEMPLATE_A}\n\nAuthor brief: {brief(profile)}\n"
                  f"Return ONLY a JSON array of exactly {len(wanted)} objects "
                  f'{{"hook": "...", "angle": "..."}} in this order, one per line below:\n{order}')
        data = llm.extract_json(llm.complete(prompt))
        if isinstance(data, list) and len(data) == len(wanted) and all(isinstance(d, dict) and d.get("hook") for d in data):
            for idea, d in zip(ideas, data):
                idea.update(hook=str(d["hook"]).strip(), angle=str(d.get("angle", "")).strip(), source="ai")
            source = f"AI plugin ({llm.active_plugin()})"
        else:
            warning = "AI plugin did not return usable ideas, template engine used. " + llm.LAST_ERROR["message"]
    return {"ideas": ideas, "source": source, "warning": warning}
