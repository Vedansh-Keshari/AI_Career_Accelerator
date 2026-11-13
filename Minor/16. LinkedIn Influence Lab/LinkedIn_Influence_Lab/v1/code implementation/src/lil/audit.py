"""Phase 1: branding audit (Appendix: Profile Optimization Checklist), headline/about rewrites, pillars."""
from __future__ import annotations

import re

from . import context, llm
from .context import PLACEHOLDER
from .knowledge import IDEA_BANK, PERSONAS, PILLARS

CHECKLIST = [
    # key, label, points, fix
    ("photo", "Professional profile photo", 8, "Use a clear, well-lit headshot where your face fills about 60% of the frame."),
    ("banner", "Banner that states your value", 6, "Replace the default banner with one line on who you help and how."),
    ("headline", "Keyword-rich headline (60-220 chars)", 14, "Use: role | who you help / what you do | 2-3 skills. Avoid a bare job title."),
    ("about", "About section with proof and a call to action", 14, "Write 600-1,500 characters: hook, proof, what you post about, how to reach you."),
    ("custom_url", "Custom profile URL", 4, "Edit public profile & URL in LinkedIn settings, use your name."),
    ("featured", "Featured section populated", 8, "Pin your best post, a project, and a link that proves your skills."),
    ("skills_15", "15+ skills, top 3 pinned", 6, "Add relevant skills and pin the three you want to be known for."),
    ("recs_3", "3+ recommendations", 8, "Ask three colleagues or managers for specific recommendations."),
    ("experience_metrics", "Experience bullets include numbers", 12, "Rewrite each role with one measurable result."),
    ("visibility", "Visibility setting", 6, ""),
    ("cadence", "Posting at least 8 times a month", 8, "Start with the 6-week calendar from this project."),
    ("network", "500+ connections", 6, "Send 5 personalised connection requests a day to peers and recruiters."),
]
VISIBILITY = {"job_seeker": ("Open to Work set (recruiters only)", "Turn on Open to Work for recruiters only."),
              "thought_leader": ("Creator mode / Follow button on", "Switch on Creator mode and add 5 topics."),
              "professional": ("Contact info and a clear call to action", "Add email or a booking link in contact info.")}


def score_profile(profile: dict) -> dict:
    checks, persona = profile.get("checks", {}), profile.get("persona", "professional")
    head, about = profile.get("current_headline", "").strip(), profile.get("current_about", "").strip()
    items = []
    for key, label, pts, fix in CHECKLIST:
        if key == "headline":
            got = 0 if not head else 14 if len(head) >= 60 and re.search(r"\||·|\bhelping\b|\bI help\b", head, re.I) \
                else 9 if len(head) >= 40 else 4
        elif key == "about":
            got = 0 if not about else (10 if len(about) >= 1200 else 7 if len(about) >= 600 else 3)
            got += 4 if re.search(r"reach out|\bDM\b|connect|message me|email|contact", about, re.I) else 0
        elif key == "cadence":
            got = pts if int(profile.get("posts_per_month_now") or 0) >= 8 else 0
        elif key == "network":
            got = pts if int(profile.get("connections") or 0) >= 500 else 0
        elif key == "visibility":
            label, fix = VISIBILITY[persona]
            got = pts if checks.get("visibility") else 0
        else:
            got = pts if checks.get(key) else 0
        items.append({"key": key, "label": label, "points": pts, "score": got, "fix": fix, "ok": got >= pts})
    total = sum(i["score"] for i in items)
    band = "Strong" if total >= 80 else "Solid base" if total >= 60 else "Needs work" if total >= 40 else "Starting out"
    return {"total": total, "band": band, "items": items,
            "gaps": [i for i in items if not i["ok"]]}


def headline_options(profile: dict) -> list[str]:
    c, persona = context.build(profile), profile.get("persona", "professional")
    at = f" at {c['company']}" if c["company"] else ""
    if persona == "job_seeker":
        opts = [f"{c['role']} | {c['skill']} · {c['skill2']} · {c['skill3']} | Open to {c['target_roles']}",
                f"Aspiring {c['target_roles']} | Turning {c['skill']} into results for {c['audience']}",
                f"{c['role']} who ships: {c['skill']}, {c['skill2']} | Looking for {c['target_roles']} roles"]
    elif persona == "thought_leader":
        opts = [f"{c['offer']} | Helping {c['audience']} win with {c['skill']} | Writing on {c['industry']}",
                f"Founder{at} | {c['offer']} for {c['audience']} | Weekly ideas on {c['industry']}",
                f"{c['role']}{at} | Making {c['skill']} simple for {c['audience']}"]
    else:
        opts = [f"{c['role']}{at} | Helping {c['audience']} with {c['skill']} | {c['skill2']} · {c['skill3']}",
                f"{c['role']} | {c['skill']} · {c['skill2']} · {c['skill3']} | Sharing lessons from {c['industry']}",
                f"{c['role']}{at} | I turn {c['skill']} into clear decisions for {c['audience']}"]
    return [o[:220] for o in opts]


def about_draft(profile: dict) -> str:
    c, persona = context.build(profile), profile.get("persona", "professional")
    pool = context.experience_pool(profile)
    proof = "\n".join(f"• {p}" for p in pool[:3]) or f"• {PLACEHOLDER}\n• {PLACEHOLDER}"
    labels = ", ".join(PILLARS[p]["label"].lower() for p in context.effective_weights(profile))
    opener = {"job_seeker": f"I help teams get dependable {c['skill']} work done, and I am looking for my next role as a {c['target_roles']}.",
              "thought_leader": f"I help {c['audience']} get more from {c['skill']} through {c['offer']}.",
              "professional": f"I am a {c['role']} in {c['industry']} who helps {c['audience']} make better use of {c['skill']}."}[persona]
    cta = {"job_seeker": f"If you are hiring for {c['target_roles']}, message me. I reply to every note.",
           "thought_leader": f"If you want to talk about {c['industry']}, send me a message or follow along.",
           "professional": "Always happy to swap notes. Connect or send me a message."}[persona]
    return (f"{opener}\n\nWhat I bring:\n{proof}\n\nWhat I write about: {labels}.\n"
            f"Skills I use most: {profile.get('skills', c['skill'])}.\n\n{cta}")


def parse_role_models(text: str) -> list[dict]:
    out = []
    for line in str(text).splitlines():
        parts = [p.strip() for p in line.split("|")]
        if parts and parts[0]:
            out.append({"name": parts[0], "url": parts[1] if len(parts) > 1 else "",
                        "learn": parts[2] if len(parts) > 2 else "Study their hooks, formats and posting rhythm."})
    return out


def run_audit(profile: dict, use_ai: bool = True) -> dict:
    result = score_profile(profile)
    heads, about, note = headline_options(profile), about_draft(profile), "Template engine"
    if use_ai and llm.ai_enabled():
        txt = llm.complete(
            "Rewrite this LinkedIn About section so it is specific, human and ends with a call to action. "
            "Keep every [bracketed placeholder] and invent no facts.\n\n" + about)
        if txt:
            about, note = txt, f"AI plugin ({llm.active_plugin()})"
    return {**result, "persona": profile.get("persona"), "headline_options": heads, "about_draft": about,
            "about_source": note, "role_models": parse_role_models(profile.get("role_models", "")),
            "current_headline": profile.get("current_headline", ""), "current_about": profile.get("current_about", "")}


def build_pillars(profile: dict) -> dict:
    c = context.build(profile)
    weights = context.effective_weights(profile)
    ppw = len(profile.get("days", [])) or 3
    total_posts = ppw * 6
    out = []
    for key, w in sorted(weights.items(), key=lambda kv: -kv[1]):
        examples = [context.fill(h, c) for h, _ in IDEA_BANK[key][:3]]
        out.append({"key": key, "label": PILLARS[key]["label"], "weight": w, "posts": round(w * total_posts),
                    "desc": PILLARS[key]["desc"], "examples": examples})
    return {"persona": profile.get("persona"), "pillars": out, "posts_per_week": ppw,
            "persona_goal": PERSONAS[profile.get("persona", "professional")]["goal"]}
