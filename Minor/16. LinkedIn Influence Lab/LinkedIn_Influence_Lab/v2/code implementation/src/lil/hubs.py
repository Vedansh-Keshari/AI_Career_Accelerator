"""Path-specific features: the Consistency Hub (professional), Recruiter Hub (job seeker),
Authority Studio (thought leader), plus the weekly path KPI log used in Phase 4 and 5."""
from __future__ import annotations

import re
from datetime import date, timedelta

import pandas as pd

from . import context, paths
from .persona_content import KPI_FIELDS

OPP_COLS = ["company", "role", "source", "stage", "date_added", "next_step", "linked_post", "notes"]
OPP_STAGES = ["Saved", "Applied", "Recruiter chat", "Interview", "Offer", "Closed"]
LEAD_COLS = ["date", "who", "org", "lead_type", "source_post", "status", "notes"]
LEAD_TYPES = ["Inbound DM", "Comment-to-DM", "Referral", "Speaking invite", "Collaboration", "Other"]
LEAD_STATUS = ["New", "Replied", "Call booked", "Proposal", "Won", "Lost"]
PEER_COLS = ["date", "comments_made", "replies_within_2h", "notes"]
KPI_COLS = ["week", "a", "b", "c", "notes"]


# ------------------------------------------------------------------ storage ---------------
def hub_dir():
    d = paths.home() / "data" / "hub"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_table(name: str, cols: list[str], folder=None) -> pd.DataFrame:
    p = (folder or hub_dir()) / name
    if not p.exists():
        return pd.DataFrame(columns=cols)
    df = pd.read_csv(p, dtype=str).fillna("")
    for c in cols:
        if c not in df:
            df[c] = ""
    return df[cols]


def save_table(name: str, df: pd.DataFrame, folder=None) -> None:
    p = (folder or hub_dir()) / name
    df.to_csv(p, index=False)


# ------------------------------------------------------------------ path KPI log -----------
def kpi_folder():
    return paths.phase_dir("phase4")


def load_kpis() -> pd.DataFrame:
    df = load_table("persona_kpis.csv", KPI_COLS, kpi_folder())
    for c in ("week", "a", "b", "c"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    return df


def save_kpi(week: int, a: int, b: int, c: int, notes: str = "") -> pd.DataFrame:
    df = load_kpis()
    df = df[df["week"] != int(week)]
    df = pd.concat([df, pd.DataFrame([{"week": int(week), "a": int(a), "b": int(b), "c": int(c), "notes": notes}])], ignore_index=True)
    df = df.sort_values("week")
    save_table("persona_kpis.csv", df, kpi_folder())
    return df


def kpi_targets(profile: dict) -> dict:
    """Per-key 6-week targets: defaults from the path, overridden by profile['kpi_targets']."""
    out = {f["key"]: f["target"] for f in KPI_FIELDS[profile.get("persona", "professional")]}
    for k, v in (profile.get("kpi_targets") or {}).items():
        if k in out:
            try:
                out[k] = max(1, int(v))
            except (TypeError, ValueError):
                pass
    return out


def kpi_progress(profile: dict) -> list[dict]:
    df, targets = load_kpis(), kpi_targets(profile)
    rows = []
    for f in KPI_FIELDS[profile.get("persona", "professional")]:
        total = int(df[f["key"]].sum()) if not df.empty else 0
        t = targets[f["key"]]
        rows.append({"key": f["key"], "label": f["label"], "total": total, "target": t, "pct": min(100, round(total / t * 100))})
    return rows


def kpi_insights(profile: dict, metrics: dict) -> list[dict]:
    """Path-specific recommendations from the weekly KPI log and engagement totals."""
    persona = profile.get("persona", "professional")
    df, prog = load_kpis(), kpi_progress(profile)
    out = []
    if df.empty:
        return [{"icon": "🧮", "finding": "No weekly path KPIs logged yet.", "action": "Log this week's numbers in Phase 4 > Weekly path KPIs."}]
    weeks_logged = max(1, df["week"].nunique())
    for p in prog:
        pace = p["target"] * weeks_logged / 6
        if p["total"] < pace * 0.7:
            out.append({"icon": "⏱️", "finding": f"{p['label']}: {p['total']} logged vs about {pace:.0f} expected by now (target {p['target']}).",
                        "action": "Pick one small daily action that moves this number and log it weekly."})
    visits = metrics.get("profile_visits", 0) if not metrics.get("empty") else 0
    imp = metrics.get("impressions", 0) if not metrics.get("empty") else 0
    if persona == "job_seeker":
        msgs = int(df["a"].sum())
        if visits >= 40 and msgs == 0:
            out.append({"icon": "🎯", "finding": f"{visits} profile visits but no recruiter messages.", "action": "Tighten the headline, switch on Open to Work (recruiters only) and pin a proof-of-work post in Featured."})
        elif visits:
            out.append({"icon": "🎯", "finding": f"{msgs} recruiter messages from {visits} profile visits ({msgs / visits * 100:.1f}%).", "action": "Aim for the same ratio next cycle; each new Featured proof item should lift it."})
    elif persona == "thought_leader":
        gained, leads = int(df["a"].sum()), int(df["b"].sum())
        if imp:
            out.append({"icon": "🏛️", "finding": f"{gained / imp * 1000:.1f} followers gained per 1,000 impressions; {leads} inbound leads.", "action": "Double down on the format that earned the most shares and end it with a clear next step."})
    else:
        comments = int(df["b"].sum())
        out.append({"icon": "🔁", "finding": f"{comments} peer comments made across {weeks_logged} logged week(s).", "action": "Keep the 5-comments-a-day habit; consistent peer visibility is what lifts reach over time."})
    return out or [{"icon": "✅", "finding": "Path KPIs are on pace.", "action": "Keep the weekly logging habit going."}]


# ------------------------------------------------------------------ professional ------------
def consistency(calendar: list[dict], engagement: pd.DataFrame, today: date | None = None) -> dict:
    today = today or date.today()
    logged_ids = set(engagement["post_id"]) if not engagement.empty else set()
    rows = []
    for w in sorted({c["week"] for c in calendar}):
        wk = [c for c in calendar if c["week"] == w]
        due = [c for c in wk if c["date"] <= today.isoformat()]
        rows.append({"week": w, "planned": len(wk), "due": len(due), "logged": sum(1 for c in wk if c["draft_id"] in logged_ids)})
    due_all = sorted((c for c in calendar if c["date"] <= today.isoformat()), key=lambda c: c["date"], reverse=True)
    streak = 0
    for c in due_all:
        if c["draft_id"] in logged_ids:
            streak += 1
        else:
            break
    dates = sorted(c["date"] for c in calendar if c["draft_id"] in logged_ids)
    gaps = [(date.fromisoformat(b) - date.fromisoformat(a)).days for a, b in zip(dates, dates[1:])]
    return {"weeks": pd.DataFrame(rows), "streak": streak, "longest_gap": max(gaps) if gaps else 0, "due": len(due_all),
            "logged_due": sum(1 for c in due_all if c["draft_id"] in logged_ids),
            "rate": round(100 * sum(1 for c in due_all if c["draft_id"] in logged_ids) / len(due_all)) if due_all else None}


STARTERS = ["Add one specific takeaway you learned from the post.", "Ask a question that continues their idea.",
            "Share a short example from your own work (nothing confidential).", "Respectfully add a different angle.",
            "Thank them and name the part that helped you most."]


def peers(profile: dict) -> list[str]:
    names = [line.split("|")[0].strip() for line in str(profile.get("role_models", "")).splitlines() if line.strip()]
    c = context.build(profile)
    fillers = [f"A colleague in {c['industry']}", f"A leader in {c['industry']} you admire", f"Someone in your {c['audience']} audience",
               "A person who recently commented on your post", "Someone you have never commented on"]
    return names + [f for f in fillers if f not in names]


def daily_peer_plan(profile: dict, day: date, n: int = 5) -> list[dict]:
    pool = peers(profile)
    start = day.toordinal() * n
    return [{"peer": pool[(start + i) % len(pool)], "starter": STARTERS[(day.toordinal() + i) % len(STARTERS)]} for i in range(n)]


# ------------------------------------------------------------------ job seeker --------------
STOP = set("""a an and are as at be been but by can could do does for from had has have he her his how i if in into is it its may more must
no not of on or our out over per she should so such than that the their them then there these they this those to up us was we were what when which who
will with would you your about also any all each other some very well able across within including include required requirements preferred plus etc
experience ability work working team teams role roles years year strong skills skill knowledge looking join company candidate responsibilities
responsible position job opportunity ideal using use used new good great high based related relevant least minimum degree hiring build present ensure help support plus""".split())
SHORT_OK = {"sql", "bi", "aws", "etl", "kpi", "gcp", "api", "css", "ml", "ai", "ux", "ui", "vba", "dax"}


def extract_keywords(text: str, top: int = 20, known: list[str] | None = None) -> list[str]:
    tokens = [t.lower() for t in re.findall(r"[A-Za-z][A-Za-z+#.]*", text)]
    counts: dict[str, int] = {}
    for t in tokens:
        t = t.strip(".")
        if t in STOP or (len(t) < 3 and t not in SHORT_OK):
            continue
        counts[t] = counts.get(t, 0) + 1
    known_single = {k.lower() for k in (known or []) if " " not in k}
    ranked = sorted(counts, key=lambda k: (-(k in known_single or k in SHORT_OK), -counts[k], k))
    out = []
    low = text.lower()
    for phrase in known or []:  # multi-word skills the user already lists, if present in the posting
        if " " in phrase and phrase.lower() in low:
            out.append(phrase.lower())
    for k in ranked:
        if not any(k in o.split() for o in out if " " in o):
            out.append(k)
    return out[:top]


def keyword_match(profile: dict, jd_text: str, drafts: list[dict] | None = None, top: int = 20) -> dict:
    from . import settings
    skills = settings.skill_list(profile)
    kws = extract_keywords(jd_text, top, skills)
    corpus = " ".join([profile.get("skills", ""), profile.get("current_headline", ""), profile.get("current_about", ""),
                       profile.get("achievements", ""), profile.get("target_roles", "")] + [d.get("text", "") for d in (drafts or [])]).lower()
    where = {"skills": profile.get("skills", "").lower(), "headline": profile.get("current_headline", "").lower(),
             "about": profile.get("current_about", "").lower(), "posts": " ".join(d.get("text", "") for d in (drafts or [])).lower()}
    rows = []
    for k in kws:
        found_in = [w for w, t in where.items() if re.search(rf"(?<![a-z]){re.escape(k)}(?![a-z])", t)]
        rows.append({"keyword": k, "found_in": ", ".join(found_in) if found_in else "missing", "present": bool(found_in)})
    hit = sum(r["present"] for r in rows)
    return {"rows": rows, "score": round(hit / len(rows) * 100) if rows else 0, "missing": [r["keyword"] for r in rows if not r["present"]]}


def recruiter_templates(profile: dict) -> list[tuple[str, str]]:
    c = context.build(profile)
    win = (profile.get("story_win") or "").strip() or "[one real result from your work]"
    return [
        ("Reply to a recruiter's message",
         f"Hi [Recruiter name],\n\nThank you for reaching out. I am exploring {c['target_roles']} roles and your message caught my eye. "
         f"My strongest areas are {c['skill']} and {c['skill2']}. For example: {win}\n\nCould you share the role description, location or remote policy, and the hiring process? "
         f"I am happy to speak this week.\n\nBest,\n{c['first_name'] or '[Your name]'}"),
        ("Ask for a referral",
         f"Hi [Name],\n\nI noticed [Company] is hiring a {c['target_roles']}. I work with {c['skill']} and {c['skill2']} and recently {win[:140]}\n\n"
         "Would you be open to a 10-minute chat about the team, or a referral if you think I am a fit? No pressure at all, and thank you either way.\n\n"
         f"{c['first_name'] or '[Your name]'}"),
        ("Follow up after applying",
         f"Hi [Name],\n\nI applied for the {c['target_roles']} role at [Company] on [date]. I wanted to reaffirm my interest: the role matches my work in {c['skill']}. "
         "If it helps, I can share a short example of a related project.\n\nThank you for your time,\n" + (c['first_name'] or '[Your name]')),
        ("Thank you after an interview",
         "Hi [Name],\n\nThank you for speaking with me today about the [role]. I enjoyed learning about [specific topic you discussed]. "
         f"Our conversation reinforced my interest, especially where {c['skill']} can help the team with [problem discussed]. "
         "Please let me know if I can share anything else.\n\nBest,\n" + (c['first_name'] or '[Your name]')),
        ("Turn a post like into a conversation",
         f"Hi [Name],\n\nThanks for engaging with my post on {c['industry']}. I noticed you work on [their area]. I would value your view on how {c['skill']} is used in your team. "
         "If you are open to it, I would appreciate a short chat.\n\n" + (c['first_name'] or '[Your name]')),
    ]


# ------------------------------------------------------------------ thought leader ----------
SERIES_STEPS = [("{name} #1: The problem nobody names in {industry}", "text"),
                ("{name} #2: A myth about {theme} I used to believe", "carousel"),
                ("{name} #3: A 5-step framework for {theme}", "carousel"),
                ("{name} #4: What it looks like in practice (a real example)", "micro_story"),
                ("{name} #5: Where {audience} get stuck with {theme}", "poll"),
                ("{name} #6: What I would do differently, and what to try next", "text")]


def plan_series(profile: dict, name: str, theme: str, episodes: int = 5) -> list[dict]:
    c = context.build(profile)
    ctx = {**c, "name": name.strip() or "My series", "theme": theme.strip() or c["skill"]}
    return [{"episode": i + 1, "hook": context.fill(h, ctx), "format": f} for i, (h, f) in enumerate(SERIES_STEPS[:max(1, min(episodes, 6))])]


def carousel_markdown(drafts: list[dict]) -> str:
    out = ["# Carousel outlines", ""]
    for d in drafts:
        if d.get("slides"):
            out += [f"## {d['id']} - {d['hook']}", ""]
            out += [f"{n}. **{s['title']}**  \n   {s['body']}" for n, s in enumerate(d["slides"], 1)] + [""]
    return "\n".join(out)


def carousel_rows(drafts: list[dict]) -> list[dict]:
    return [{"draft_id": d["id"], "slide": n, "title": s["title"], "body": s["body"]}
            for d in drafts if d.get("slides") for n, s in enumerate(d["slides"], 1)]
