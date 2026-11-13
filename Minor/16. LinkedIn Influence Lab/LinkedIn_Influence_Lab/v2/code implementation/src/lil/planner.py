"""Turns cadence + persona weights into the 6-week slot plan (date, pillar, format)."""
from __future__ import annotations

from datetime import date, timedelta

from . import context
from .knowledge import PERSONAS, WEEKDAYS

PILOT_FORMATS = ["text", "poll", "micro_story"]  # first 3 posts double as the pilot test


def weighted_sequence(weights: dict, n: int) -> list[str]:
    """Smooth weighted round-robin: honours the mix and avoids the same pillar twice in a row."""
    keys = [k for k, w in weights.items() if w > 0]
    total = sum(weights[k] for k in keys) or 1
    credit = {k: 0.0 for k in keys}
    out, prev = [], None
    for _ in range(n):
        for k in keys:
            credit[k] += weights[k] / total
        ranked = sorted(keys, key=lambda k: -credit[k])
        pick = next((k for k in ranked if k != prev), ranked[0])
        credit[pick] -= 1
        out.append(pick)
        prev = pick
    return out


def plan_slots(profile: dict, weeks: int = 6, minimum: int = 10) -> list[dict]:
    idx = sorted({WEEKDAYS.index(d) for d in profile.get("days", []) if d in WEEKDAYS}) or [1, 2, 3]
    start = date.fromisoformat(profile["start_date"])
    monday = start - timedelta(days=start.weekday())
    dates, w = [], 0
    while w < weeks or len(dates) < minimum:
        for d in idx:
            day = monday + timedelta(days=7 * w + d)
            if day >= start:
                dates.append((w + 1, day))
        w += 1
    pillars = weighted_sequence(context.effective_weights(profile), len(dates))
    cycle = PERSONAS[profile.get("persona", "professional")]["format_cycle"]
    slots = []
    for i, ((week, day), pillar) in enumerate(zip(dates, pillars)):
        fmt = PILOT_FORMATS[i] if i < 3 else cycle[i % len(cycle)]
        slots.append({"slot_id": f"S{i + 1:02d}", "week": week, "date": day.isoformat(),
                      "weekday": WEEKDAYS[day.weekday()], "time": profile.get("time", "08:30"),
                      "pillar": pillar, "format": fmt, "is_pilot": i < 3})
    return slots
