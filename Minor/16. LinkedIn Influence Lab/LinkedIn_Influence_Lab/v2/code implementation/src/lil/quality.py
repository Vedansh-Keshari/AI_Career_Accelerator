"""Content-quality, inclusivity and authenticity checks (Part 19 + Content Quality criterion)."""
from __future__ import annotations

import re

from .knowledge import INCLUSIVE_REPLACEMENTS


def check(text: str, fmt: str = "text") -> dict:
    """Score 0-100 and list issues. Rules are plain heuristics, documented in docs/02_ARCHITECTURE.md."""
    issues, score = [], 100
    body = re.sub(r"(?m)^\s*(#\w+\s*)+$", "", text).strip()
    lines = [l for l in body.splitlines() if l.strip()]
    hook = lines[0] if lines else ""
    n = len(body)

    if not hook:
        return {"score": 0, "issues": ["Empty draft"], "length": 0}
    if len(hook) > 140:
        score -= 10; issues.append("Hook is longer than 140 characters; the first line gets cut in the feed.")
    lo, hi = {"poll": (250, 1900), "carousel": (250, 1900), "micro_story": (400, 1900)}.get(fmt, (500, 1900))
    if n < lo:
        score -= 12; issues.append(f"Short post ({n} chars). Aim for {lo}+ for richer value.")
    elif n > 2600:
        score -= 10; issues.append("Very long post (over 2,600 chars). Consider a carousel or trimming.")
    if re.search(r"\[[^\]]+\]", body):
        score -= 20; issues.append("Placeholder left in the text. Replace it with your real example before approving.")
    if not re.search(r"\?|comment|DM|follow|connect|share|tell me|let us|open to", body, re.I):
        score -= 10; issues.append("No call to action or question; add one to invite comments.")
    tags = re.findall(r"#\w+", text)
    if len(tags) > 5:
        score -= 6; issues.append("More than 5 hashtags looks spammy; keep 3-5.")
    if len(re.findall(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", body)) > 3:
        score -= 5; issues.append("Too many emojis; keep at most 1-3.")
    sentences = [s for s in re.split(r"[.!?]+\s", body) if s.strip()]
    if sentences and sum(len(s.split()) for s in sentences) / len(sentences) > 24:
        score -= 6; issues.append("Long sentences; shorten them for mobile reading.")
    for bad, good in INCLUSIVE_REPLACEMENTS.items():
        if re.search(rf"\b{re.escape(bad)}\b", body, re.I):
            score -= 4; issues.append(f"Inclusive language: replace '{bad}' with '{good}'.")
    if re.search(r"\b\d+\s?%|\bstudy\b|\bstudies\b|according to|\bsurvey\b", body, re.I) \
            and not re.search(r"source|via |according to [A-Z]|http", body, re.I):
        score -= 8; issues.append("Statistic or study mentioned without a named source; attribute it.")
    if not re.search(r"\b(I|my|me|I'm|we)\b", body, re.I):
        score -= 6; issues.append("Reads impersonal; add a first-person angle so it sounds like you.")
    return {"score": max(0, min(100, score)), "issues": issues, "length": n}


def grade(score: float) -> str:
    return "Excellent" if score >= 90 else "Good" if score >= 75 else "Needs work" if score >= 60 else "Rework"
