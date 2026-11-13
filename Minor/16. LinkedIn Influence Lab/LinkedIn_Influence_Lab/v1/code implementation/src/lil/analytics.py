"""Phase 4-5: engagement tracking, metrics, insights and the evaluation scorecard."""
from __future__ import annotations

import random
from datetime import date

import pandas as pd

from . import paths, store
from .knowledge import FORMATS, PILLARS
from .plugins import import_analytics

COLUMNS = ["post_id", "published_date", "impressions", "likes", "comments", "shares", "profile_visits", "source"]


def engagement_path(demo: bool = False):
    return paths.phase_dir("phase4") / ("engagement_demo.csv" if demo else "engagement.csv")


def load_engagement(demo: bool = False) -> pd.DataFrame:
    p = engagement_path(demo)
    if not p.exists():
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(p)
    for c in COLUMNS:
        if c not in df:
            df[c] = 0 if c not in ("post_id", "published_date", "source") else ""
    return df[COLUMNS]


def save_engagement(df: pd.DataFrame, demo: bool = False) -> None:
    df.to_csv(engagement_path(demo), index=False)


def add_entry(post_id, published_date, impressions, likes, comments, shares, profile_visits=0, source="manual") -> pd.DataFrame:
    df = load_engagement()
    df = df[df["post_id"] != post_id]
    row = {"post_id": post_id, "published_date": str(published_date), "impressions": int(impressions),
           "likes": int(likes), "comments": int(comments), "shares": int(shares),
           "profile_visits": int(profile_visits), "source": source}
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save_engagement(df)
    return df


def import_csv(file_like, post_ids: list[str] | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Merge an uploaded Taplio/LinkedIn export. Returns (merged, warnings)."""
    raw = pd.read_csv(file_like)
    mapped = import_analytics.map_columns(raw)
    warnings = []
    for need in ("impressions", "likes", "comments", "shares"):
        if need not in mapped:
            mapped[need] = 0
            warnings.append(f"No '{need}' column found; filled with 0.")
    if "post_id" not in mapped:
        if post_ids and len(post_ids) >= len(mapped):
            mapped["post_id"] = post_ids[:len(mapped)]
            warnings.append("No post id column: rows were matched to your posts in calendar order.")
        else:
            mapped["post_id"] = [f"IMP{i + 1:02d}" for i in range(len(mapped))]
            warnings.append("No post id column: rows were labelled IMP01, IMP02...")
    for c in ("published_date", "profile_visits"):
        if c not in mapped:
            mapped[c] = "" if c == "published_date" else 0
    mapped["source"] = "import"
    df = load_engagement()
    df = df[~df["post_id"].isin(mapped["post_id"])]
    merged = pd.concat([df, mapped[COLUMNS]], ignore_index=True)
    for c in ("impressions", "likes", "comments", "shares", "profile_visits"):
        merged[c] = pd.to_numeric(merged[c], errors="coerce").fillna(0).astype(int)
    save_engagement(merged)
    return merged, warnings


def make_demo(calendar: list[dict], n: int = 12, seed: int = 7) -> pd.DataFrame:
    """Clearly-labelled simulated metrics so the dashboard can be previewed before real posting."""
    rng = random.Random(seed)
    rows = []
    for i, s in enumerate(calendar[:n]):
        boost = {"poll": 1.4, "carousel": 1.25, "micro_story": 1.15}.get(s["format"], 1.0)
        imp = int(rng.randint(600, 1400) * boost * (1 + i * 0.06))
        likes = int(imp * rng.uniform(.025, .05)); com = int(imp * rng.uniform(.004, .012))
        rows.append({"post_id": s["draft_id"], "published_date": s["date"], "impressions": imp, "likes": likes,
                     "comments": com, "shares": int(imp * rng.uniform(.002, .007)),
                     "profile_visits": int(imp * rng.uniform(.01, .03)), "source": "demo"})
    df = pd.DataFrame(rows, columns=COLUMNS)
    save_engagement(df, demo=True)
    return df


def enrich(df: pd.DataFrame, calendar: list[dict]) -> pd.DataFrame:
    if df.empty:
        return df.assign(week=[], pillar=[], format=[], weekday=[], engagement=[], rate=[])
    meta = pd.DataFrame(calendar)[["draft_id", "week", "pillar", "format", "weekday", "theme", "date"]].rename(columns={"draft_id": "post_id"})
    out = df.merge(meta, on="post_id", how="left")
    out["published_date"] = pd.to_datetime(out["published_date"].replace("", pd.NA), errors="coerce").fillna(pd.to_datetime(out["date"], errors="coerce"))
    out["week"] = out["week"].fillna(0).astype(int)
    out["engagement"] = out["likes"] + out["comments"] + out["shares"]
    out["rate"] = (out["engagement"] / out["impressions"].where(out["impressions"] > 0)).fillna(0) * 100
    return out


def compute(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"empty": True}
    tot_imp = int(df["impressions"].sum())
    wk = df.groupby("week").agg(impressions=("impressions", "sum"), likes=("likes", "sum"), comments=("comments", "sum"),
                                shares=("shares", "sum"), profile_visits=("profile_visits", "sum"), posts=("post_id", "count")).reset_index()
    wk["rate"] = ((wk["likes"] + wk["comments"] + wk["shares"]) / wk["impressions"].where(wk["impressions"] > 0)).fillna(0) * 100

    def grp(col):
        g = df.groupby(col).agg(posts=("post_id", "count"), impressions=("impressions", "sum"), likes=("likes", "sum"),
                                comments=("comments", "sum"), shares=("shares", "sum")).reset_index()
        g["rate"] = ((g["likes"] + g["comments"] + g["shares"]) / g["impressions"].where(g["impressions"] > 0)).fillna(0) * 100
        return g.sort_values("rate", ascending=False)

    growth = None
    valid = wk[wk["week"] > 0]
    if len(valid) >= 2 and valid.iloc[0]["rate"] > 0:
        growth = (valid.iloc[-1]["rate"] - valid.iloc[0]["rate"]) / valid.iloc[0]["rate"] * 100
    return {"empty": False, "posts": int(len(df)), "impressions": tot_imp, "likes": int(df["likes"].sum()),
            "comments": int(df["comments"].sum()), "shares": int(df["shares"].sum()),
            "profile_visits": int(df["profile_visits"].sum()),
            "rate": float(df["engagement"].sum() / tot_imp * 100) if tot_imp else 0.0,
            "weekly": wk, "by_pillar": grp("pillar").dropna(subset=["pillar"]), "by_format": grp("format").dropna(subset=["format"]),
            "by_weekday": grp("weekday").dropna(subset=["weekday"]),
            "top": df.sort_values("engagement", ascending=False).head(5), "growth_pct": growth}


def insights(m: dict, calendar: list[dict], profile: dict) -> list[dict]:
    """Rule-based recommendations: (what we saw, what to do). Mirrors the Risks & Mitigations table."""
    if m.get("empty"):
        return [{"icon": "🕒", "finding": "No engagement logged yet.", "action": "Publish the 3 pilot posts and log their metrics in Phase 4."}]
    out = []
    bp, bf, bd = m["by_pillar"].iloc[0], m["by_format"].iloc[0], m["by_weekday"].iloc[0]
    out.append({"icon": "🏆", "finding": f"'{PILLARS[bp['pillar']]['label']}' is your strongest pillar ({bp['rate']:.1f}% engagement).",
                "action": "Raise its share of the next calendar by about 10 points; keep the others for range."})
    out.append({"icon": FORMATS[bf["format"]]["emoji"], "finding": f"{FORMATS[bf['format']]['label']} posts perform best ({bf['rate']:.1f}%).",
                "action": "Use this format at least twice a week; test a new hook style inside it."})
    out.append({"icon": "📆", "finding": f"{bd['weekday']} posts lead on engagement.", "action": f"Move one more post to {bd['weekday']} (same time of day) and compare."})
    if m["rate"] < 2:
        out.append({"icon": "⚠️", "finding": f"Overall engagement is {m['rate']:.1f}% (below the 2% rule of thumb).",
                    "action": "Mitigation - low engagement: shorten hooks, end with a direct question, test an earlier posting time."})
    if m["comments"] < m["likes"] * 0.1:
        out.append({"icon": "💬", "finding": "Comments are under 10% of likes.", "action": "Ask one specific question per post and reply to every comment within 2 hours."})
    if m["growth_pct"] is not None:
        d = "up" if m["growth_pct"] >= 0 else "down"
        out.append({"icon": "📈" if d == "up" else "📉", "finding": f"Engagement rate is {d} {abs(m['growth_pct']):.0f}% from first to latest week.",
                    "action": "Keep what changed." if d == "up" else "Review the latest week's hooks against the first week's winners."})
    if m["profile_visits"] and m["impressions"]:
        out.append({"icon": "👀", "finding": f"{m['profile_visits'] / m['impressions'] * 100:.1f}% of impressions became profile visits.",
                    "action": "Make sure the headline and Featured section convert those visits (see the audit)."})
    return out


def scorecard(profile: dict, drafts: list[dict], calendar: list[dict], df: pd.DataFrame, m: dict, doc_count: int, doc_expected: int) -> dict:
    """Self-assessment on the brief's evaluation criteria (Part 11). Formulas are documented in docs/02."""
    from . import context
    parts = {}
    if drafts:
        parts["Content Quality & Relevance"] = (30, sum(d["quality"] for d in drafts) / len(drafts))
    due = [c for c in calendar if c["date"] <= date.today().isoformat()]
    if due:
        done = df["post_id"].isin([c["draft_id"] for c in due]).sum() if not df.empty else 0
        parts["Consistency of Posting"] = (25, min(100, done / len(due) * 100))
    if m.get("growth_pct") is not None:
        parts["Engagement Growth"] = (20, max(0, min(100, 50 + m["growth_pct"] * 0.5)))
    if calendar:
        target = context.effective_weights(profile)
        actual = {k: sum(1 for c in calendar if c["pillar"] == k) / len(calendar) for k in target}
        tvd = sum(abs(actual[k] - target[k]) for k in target) / 2
        parts["Personal Branding Alignment"] = (15, (1 - tvd) * 100)
    parts["Documentation & Clarity"] = (10, min(100, doc_count / max(1, doc_expected) * 100))
    wsum = sum(w for w, _ in parts.values())
    total = sum(w * s for w, s in parts.values()) / wsum if wsum else 0
    return {"parts": {k: {"weight": w, "score": round(float(s), 1)} for k, (w, s) in parts.items()},
            "total": round(float(total), 1), "provisional": wsum < 100, "covered_weight": wsum}


def refine_weights(profile: dict, m: dict) -> dict:
    """Next-cycle pillar mix: +10 points to the best performer, take up to 5 from the weakest, re-normalise."""
    from . import context
    w = dict(context.effective_weights(profile))
    if m.get("empty") or len(m["by_pillar"]) < 2:
        return w
    rated = [p for p in m["by_pillar"]["pillar"] if p in w]
    if len(rated) < 2:
        return w
    best, worst = rated[0], rated[-1]
    w[best] += 0.10
    w[worst] = max(0.05, w[worst] - 0.05)
    tot = sum(w.values())
    return {k: round(v / tot, 3) for k, v in w.items()}
