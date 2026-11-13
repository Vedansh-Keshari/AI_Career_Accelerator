"""Phase 2b: turn ideas into publish-ready drafts, plus the Template B / C helpers."""
from __future__ import annotations

import re

from . import context, ideation, llm, quality
from .context import PLACEHOLDER, fill
from .knowledge import (FORMATS, PERSONAS, PILLAR_TAGS, PILLARS, POINTS, POLLS, SETUPS,
                        TEMPLATE_B, TEMPLATE_C)

TONE_PREFIX = {"Warm and encouraging": "I would love your thoughts. ", "Playful and witty": "Plot twist question: ",
               "Calm and authoritative": "Worth reflecting on: "}


def _cta(profile, c, i):
    persona = PERSONAS[profile.get("persona", "professional")]
    text = fill(persona["ctas"][i % len(persona["ctas"])], c)
    return TONE_PREFIX.get(profile.get("tone", ""), "") + text


def _points(pillar, c, i, k=3):
    pts = POINTS[pillar]
    return [fill(pts[(i * 2 + j) % len(pts)], c) for j in range(k)]


def _hashtags(pillar, c):
    tags = [PILLAR_TAGS[pillar][0], context.slug_tag(c["industry"]), context.slug_tag(c["skill"]), PILLAR_TAGS[pillar][1]]
    out = []
    for t in tags:
        if t and t not in out:
            out.append(t)
    return out[:4]


def offline_draft(profile: dict, idea: dict, i: int) -> dict:
    c = context.build(profile)
    pool = context.experience_pool(profile)
    exp = pool[i % len(pool)] if pool else None
    pillar, fmt, hook = idea["pillar"], idea["format"], idea["hook"]
    setup = fill(SETUPS[pillar][i % 3], c)
    pts = _points(pillar, c, i)
    cta = _cta(profile, c, i)
    extra = {}
    bullets = (lambda ps: "\n".join(f"{n}. {p}" for n, p in enumerate(ps, 1))) if pillar == "actionable_tips" \
        else (lambda ps: "\n".join(f"→ {p}" for p in ps))

    if fmt == "micro_story":
        body = (f"{hook}\n\nHere is the short version:\n{exp or PLACEHOLDER}\n\nWhat it taught me:\n{pts[0]}\n\n"
                f"If you are {c['audience']}, take this with you:\n{pts[1]}\n\n{cta}")
    elif fmt == "poll":
        q, opts = POLLS[pillar][i % len(POLLS[pillar])]
        extra["poll"] = {"question": fill(q, c), "options": [fill(o, c) for o in opts]}
        body = f"{hook}\n\n{setup}\n\n{pts[0]}\n\nVote in the poll below, then tell me why in the comments."
    elif fmt == "carousel":
        more = _points(pillar, c, i + 1, 5)
        slides = [{"title": hook, "body": f"A quick guide for {c['audience']}"}]
        for n, p in enumerate(more, 1):
            first, _, rest = p.partition(". ")
            slides.append({"title": first.rstrip("."), "body": rest or "Try it this week and note what changes."})
        slides.append({"title": "Your turn", "body": cta})
        extra["slides"] = slides
        body = f"{hook}\n\nI turned this into a short carousel so you can save it for later. Swipe through.\n\n{cta}"
    else:
        proof = f"\nFrom my own experience: {exp}\n" if exp and pillar in ("personal_journey", "career_insights", "actionable_tips") else ""
        if pillar == "personal_journey" and not exp:
            proof = f"\n{PLACEHOLDER}\n"
        body = f"{hook}\n\n{setup}\n\n{bullets(pts)}\n{proof}\n{cta}"
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return {"idea_id": idea["id"], "slot_id": idea["slot_id"], "pillar": pillar, "format": fmt, "hook": hook,
            "body": body, "hashtags": _hashtags(pillar, c), "source": "template", **extra}


def _ai_draft(profile: dict, idea: dict, i: int) -> dict | None:
    c = context.build(profile)
    pool = context.experience_pool(profile)
    shape = {"poll": '{"text": caption, "question": poll question, "options": [4 short options]}',
             "carousel": '{"text": caption, "slides": [{"title": ..., "body": ...}] (6-8 slides)}'}.get(
        idea["format"], '{"text": the full post}')
    prompt = (f"Write one LinkedIn {FORMATS[idea['format']]['label']} for this author.\n"
              f"Brief: {ideation.brief(profile)}\nPillar: {PILLARS[idea['pillar']]['label']}. "
              f"Hook idea: {idea['hook']}. Angle: {idea['angle']}.\n"
              f"Real experiences you may use (invent nothing else): {pool or 'none provided, use [placeholders]'}.\n"
              f"Length: 900-1300 characters for text posts. Return ONLY JSON shaped like {shape}.")
    data = llm.extract_json(llm.complete(prompt))
    if not isinstance(data, dict) or not str(data.get("text", "")).strip():
        return None
    d = {"idea_id": idea["id"], "slot_id": idea["slot_id"], "pillar": idea["pillar"], "format": idea["format"],
         "hook": idea["hook"], "body": str(data["text"]).strip(), "hashtags": _hashtags(idea["pillar"], c), "source": "ai"}
    if idea["format"] == "poll" and data.get("question") and isinstance(data.get("options"), list):
        d["poll"] = {"question": str(data["question"]), "options": [str(o) for o in data["options"]][:4]}
    if idea["format"] == "carousel" and isinstance(data.get("slides"), list):
        d["slides"] = [{"title": str(s.get("title", "")), "body": str(s.get("body", ""))} for s in data["slides"] if isinstance(s, dict)]
    if idea["format"] == "poll" and "poll" not in d or idea["format"] == "carousel" and "slides" not in d:
        return None
    return d


def finalize(d: dict) -> dict:
    d["text"] = d["body"] + ("\n\n" + " ".join("#" + t for t in d["hashtags"]) if d["hashtags"] else "")
    q = quality.check(d["text"], d["format"])
    d["quality"], d["issues"] = q["score"], q["issues"]
    d.setdefault("human_reviewed", False)
    d.setdefault("status", "draft")
    return d


def build_drafts(profile: dict, ideas: list[dict], use_ai: bool = True, progress=None) -> list[dict]:
    """One draft per idea that owns a calendar slot (reserve ideas stay in the idea bank)."""
    drafts, n = [], 0
    chosen = [i for i in ideas if i.get("slot_id")]
    for i, idea in enumerate(chosen):
        d = _ai_draft(profile, idea, i) if use_ai and llm.ai_enabled() else None
        d = d or offline_draft(profile, idea, i)
        n += 1
        d["id"] = f"D{n:02d}"
        drafts.append(finalize(d))
        if progress:
            progress((i + 1) / len(chosen))
    return drafts


def regenerate(profile: dict, draft: dict, ideas: list[dict], bump: int = 1, use_ai: bool = True) -> dict:
    idea = next((i for i in ideas if i["id"] == draft["idea_id"]), None) or {
        "id": draft["idea_id"], "slot_id": draft["slot_id"], "pillar": draft["pillar"], "format": draft["format"],
        "hook": draft["hook"], "angle": ""}
    n = int(draft["id"][1:])
    new = (_ai_draft(profile, idea, n + bump) if use_ai and llm.ai_enabled() else None) or offline_draft(profile, idea, n + bump)
    new["id"] = draft["id"]
    return finalize(new)


# ---- Template B: rewrite in a professional but relatable tone ----------------
JARGON = {"leverage": "use", "utilize": "use", "synergy": "teamwork", "circle back": "follow up",
          "touch base": "check in", "paradigm shift": "big change", "low-hanging fruit": "quick win",
          "go-getter": "self-starter", "world-class": "excellent", "best-in-class": "excellent",
          "in order to": "to", "at this point in time": "now", "moving forward": "from here"}
CONTRACTIONS = {"do not": "don't", "does not": "doesn't", "cannot": "can't", "I am": "I'm", "I have": "I've",
                "it is": "it's", "that is": "that's", "we are": "we're", "will not": "won't"}


def rewrite_tone(profile: dict, draft_text: str) -> tuple[str, str]:
    prompt = f"{TEMPLATE_B}\nKeep every fact unchanged, keep the hashtags.\n\nDRAFT:\n{draft_text}"
    out = llm.complete(prompt)
    if out:
        return out, f"Rewritten by {llm.active_plugin()}"
    text = draft_text
    for k, v in JARGON.items():
        text = re.sub(rf"\b{re.escape(k)}\b", v, text, flags=re.I)
    for k, v in CONTRACTIONS.items():
        text = re.sub(rf"\b{re.escape(k)}\b", v, text)
    return text, "Template engine: simplified jargon and added contractions (connect an AI plugin for a full rewrite)"


# ---- Template C: summarise an article into a post --------------------------
def article_to_post(profile: dict, article: str, source: str) -> tuple[str, str]:
    c = context.build(profile)
    prompt = (f"{TEMPLATE_C}\nWrite in my voice. Credit the source: {source or 'the author'}. "
              f"Audience: {c['audience']}.\n\nARTICLE:\n{article[:6000]}")
    out = llm.complete(prompt)
    if out:
        return out, f"Summarised by {llm.active_plugin()}"
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", article.strip()) if len(s.split()) >= 6]
    words = re.findall(r"[a-z]{4,}", article.lower())
    freq = {w: words.count(w) for w in set(words)}
    ranked = sorted(sentences, key=lambda s: -sum(freq.get(w, 0) for w in re.findall(r"[a-z]{4,}", s.lower())) / max(1, len(s.split())))[:3]
    ranked.sort(key=sentences.index)
    if not ranked:
        return "", "The article text was too short to summarise."
    take = "\n".join(f"{n}. {s}" for n, s in enumerate(ranked, 1))
    post = (f"3 takeaways from something I read this week:\n\n{take}\n\nWhy it matters for {c['audience']}: "
            f"{PLACEHOLDER}\n\nSource: {source or '[add the link or author]'}\n\nWhat would you add?")
    return post, "Template engine: picked the 3 most information-dense sentences (extractive). Add your own view before posting."


def apply_edit(d: dict, new_text: str) -> dict:
    """Store a hand-edited post: split a trailing hashtag line back out, then re-score."""
    lines = new_text.rstrip().splitlines()
    tags = []
    if lines and lines[-1].strip() and all(w.startswith("#") for w in lines[-1].split()):
        tags = [w.lstrip("#") for w in lines[-1].split()]
        lines = lines[:-1]
    d["body"] = "\n".join(lines).rstrip()
    d["hashtags"] = tags
    d["hook"] = next((l for l in lines if l.strip()), d["hook"])
    return finalize(d)
