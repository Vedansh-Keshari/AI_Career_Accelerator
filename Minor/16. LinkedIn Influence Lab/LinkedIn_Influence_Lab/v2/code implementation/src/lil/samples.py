"""Sample workspace: a complete, fictional, internally consistent example for each user path.

Everything lives in <base>/sample_workspace/ so sample data can never mix with your own work.
Only call these functions while the sample workspace is active (they refuse otherwise)."""
from __future__ import annotations

import shutil
from datetime import date, timedelta

import pandas as pd

from . import analytics, hubs, paths, pipeline, settings, store

PERSONAS = ("professional", "job_seeker", "thought_leader")
UPCOMING_APPROVED = 3  # published posts are reviewed, plus the next few; the rest wait for review so the gate is visible


def _need_sample():
    if not paths.is_sample():
        raise RuntimeError("Sample data can only be loaded into the sample workspace.")


def sample_profile(persona: str) -> dict:
    prof = settings.default_profile()
    prof.update(store.read_json(paths.sample_dir() / f"profile_{persona}.json", {}))
    prof["checks"] = {**settings.default_profile()["checks"], **prof.get("checks", {})}
    today = date.today()
    start = today - timedelta(days=28)
    prof["start_date"] = (start - timedelta(days=start.weekday())).isoformat()  # Monday four weeks ago: week 5 of 6 in progress
    return prof


def is_seeded() -> bool:
    return (paths.state_dir() / "seeded.json").exists()


def reset_workspace() -> None:
    _need_sample()
    root = paths.home()
    for sub in ("data", "phases", "deliverables", "backups", "logs"):
        shutil.rmtree(root / sub, ignore_errors=True)


def _days_ago(n) -> str:
    return (date.today() - timedelta(days=int(n))).isoformat()


def seed(persona: str = "professional") -> dict:
    """Wipe the sample workspace and rebuild it for one path, ready to explore from Phase 1 to the deliverables."""
    _need_sample()
    if persona not in PERSONAS:
        raise ValueError(persona)
    reset_workspace()
    prof = sample_profile(persona)
    settings.save_profile(prof)
    pipeline.run_phase1(prof, use_ai=False)
    pipeline.run_phase2(prof, use_ai=False)
    drafts = pipeline.load_drafts()
    slots = pipeline.load("phase2", "slots.json", [])
    n_due = sum(1 for sl in slots if sl["date"] <= date.today().isoformat())
    for d in drafts[:max(0, min(n_due + UPCOMING_APPROVED, len(drafts) - 2))]:
        d["human_reviewed"] = True
    pipeline.save_drafts(drafts)
    pipeline.run_phase3(prof)

    cal = pipeline.load_calendar()
    due = [c for c in cal if c["date"] <= date.today().isoformat()]
    numbers = pd.read_csv(paths.sample_dir() / f"sample_engagement_{persona}.csv")
    for slot, (_, row) in zip(due, numbers.iterrows()):
        analytics.add_entry(slot["draft_id"], slot["date"], row["Impressions"], row["Reactions"], row["Comments"], row["Reposts"],
                            row["Profile views"], source="sample")
    pipeline.mark_published()

    kp = pd.read_csv(paths.sample_dir() / f"sample_kpis_{persona}.csv", dtype=str).fillna("")
    hubs.save_table("persona_kpis.csv", kp, hubs.kpi_folder())
    d = paths.sample_dir()
    if persona == "professional":
        log = pd.read_csv(d / "sample_peer_log.csv", dtype=str).fillna("")
        log.insert(0, "date", [_days_ago(x) for x in log.pop("days_ago")])
        hubs.save_table("peer_log.csv", log[hubs.PEER_COLS])
    elif persona == "job_seeker":
        opp = pd.read_csv(d / "sample_opportunities.csv", dtype=str).fillna("")
        opp.insert(0, "date_added", [_days_ago(x) for x in opp.pop("days_ago")])
        hubs.save_table("opportunities.csv", opp[hubs.OPP_COLS])
    else:
        leads = pd.read_csv(d / "sample_leads.csv", dtype=str).fillna("")
        leads.insert(0, "date", [_days_ago(x) for x in leads.pop("days_ago")])
        hubs.save_table("leads.csv", leads[hubs.LEAD_COLS])
        store.write_json(hubs.hub_dir() / "series.json", store.read_json(d / "sample_series.json", {}))

    pipeline.run_phase4(prof)
    pipeline.build_deliverables(prof)
    from . import backup
    backup.backup_snapshot(tag="sample_ready")
    store.write_json(paths.state_dir() / "seeded.json", {"persona": persona, "at": date.today().isoformat()})
    return {"persona": persona, "name": prof["name"]}


def ensure_seeded(default: str = "professional") -> bool:
    """Called on first use of the sample workspace. Returns True if it had to build it."""
    _need_sample()
    if is_seeded():
        return False
    seed(default)
    return True
