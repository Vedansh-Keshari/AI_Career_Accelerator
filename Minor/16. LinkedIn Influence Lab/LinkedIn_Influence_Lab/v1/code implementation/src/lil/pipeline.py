"""The automated flow. Each run_phaseN does its work, saves to its own folder, updates the status
ledger and writes a backup zip. run_all chains them; build_deliverables writes the client files."""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from . import analytics, audit, backup, calendar_builder as cb, charts, drafting, folder_map, ideation
from . import paths, personas, planner, plugins, reports, settings, store
from .knowledge import PILLARS

MIN_POSTS_DONE = 10


# ------------------------------------------------------------ data access --
def _p(key, name):
    return paths.phase_dir(key) / name


def load(key, name, default=None):
    return store.read_json(_p(key, name), default)


def save(key, name, obj):
    store.write_json(_p(key, name), obj)


def load_drafts() -> list[dict]:
    return load("phase2", "drafts.json", []) or []


def save_drafts(drafts: list[dict]) -> None:
    save("phase2", "drafts.json", drafts)
    sync_calendar()


def load_calendar() -> list[dict]:
    return load("phase3", "calendar.json", []) or []


def sync_calendar() -> None:
    """Push draft edits (theme, quality, review flag) into the calendar rows, keep statuses."""
    cal = load_calendar()
    if not cal:
        return
    by_id = {d["id"]: d for d in load_drafts()}
    for row in cal:
        d = by_id.get(row["draft_id"])
        if d:
            row.update(theme=d["hook"], quality=d["quality"], human_reviewed=bool(d.get("human_reviewed")))
    save("phase3", "calendar.json", cal)


def mark_published() -> None:
    """Calendar status follows the engagement log: a logged post counts as Published."""
    cal, df = load_calendar(), analytics.load_engagement()
    done = set(df["post_id"])
    for row in cal:
        if row["draft_id"] in done:
            row["status"] = "Published"
    if cal:
        save("phase3", "calendar.json", cal)


def data_source(demo_ok: bool):
    real = analytics.load_engagement()
    if not real.empty:
        return real, False
    if demo_ok:
        d = analytics.load_engagement(demo=True)
        if d.empty:
            d = analytics.make_demo(load_calendar())
        return d, True
    return real, False


# ------------------------------------------------------------- the phases --
def run_phase1(profile: dict, use_ai: bool = True) -> dict:
    a = audit.run_audit(profile, use_ai)
    pl = audit.build_pillars(profile)
    save("phase1", "audit.json", a)
    save("phase1", "pillars.json", pl)
    save("phase1", "personas.json", personas.compare(profile))
    save("phase1", "profile_snapshot.json", profile)
    store.set_status("phase1", "done", f"Audit score {a['total']}/100; {len(pl['pillars'])} pillars")
    backup.backup_phase("phase1")
    return {"audit": a, "pillars": pl}


def run_phase2(profile: dict, use_ai: bool = True, progress=None) -> dict:
    if load_drafts():
        backup.backup_phase("phase2", tag="before_rerun")  # protect hand-edited drafts
    slots = planner.plan_slots(profile)
    res = ideation.generate_ideas(profile, slots, use_ai=use_ai)
    drafts = drafting.build_drafts(profile, res["ideas"], use_ai=use_ai, progress=progress)
    save("phase2", "slots.json", slots)
    save("phase2", "ideas.json", res)
    save("phase2", "drafts.json", drafts)
    save("phase2", "pilot.json", [d["id"] for d, s in zip(drafts, slots) if s["is_pilot"]])
    pending = sum(1 for d in drafts if any("Placeholder" in i for i in d["issues"]))
    store.set_status("phase2", "waiting" if pending else "done",
                     f"{len(res['ideas'])} ideas, {len(drafts)} drafts; {pending} need your real examples")
    backup.backup_phase("phase2")
    return {"ideas": res, "drafts": drafts, "needs_personalisation": pending}


def run_phase3(profile: dict) -> dict:
    drafts, slots = load_drafts(), load("phase2", "slots.json", [])
    if not drafts or not slots:
        raise RuntimeError("Run Phase 2 first: there are no drafts to schedule.")
    old = {r["draft_id"]: r["status"] for r in load_calendar()}
    if load_calendar():
        backup.backup_phase("phase3", tag="before_rerun")
    cal = cb.build_calendar(slots, drafts)
    for r in cal:
        r["status"] = old.get(r["draft_id"], r["status"])
    save("phase3", "calendar.json", cal)
    write_calendar_files(profile, cal, drafts)
    approved = sum(1 for d in drafts if d.get("human_reviewed"))
    store.set_status("phase3", "waiting" if approved < len(drafts) else "done",
                     f"{len(cal)} slots; {approved}/{len(drafts)} drafts human-approved for Taplio")
    backup.backup_phase("phase3")
    return {"calendar": cal, "approved": approved}


def write_calendar_files(profile, cal, drafts) -> list:
    out = paths.deliverable_dir("calendar")
    cb.write_excel(profile, cal, drafts, out / "Content_Calendar_6_Weeks.xlsx")
    cb.write_csv(cal, drafts, out / "Content_Calendar_6_Weeks.csv")
    files = [out / "Content_Calendar_6_Weeks.xlsx", out / "Content_Calendar_6_Weeks.csv"]
    reg = plugins.discover()
    for pid in plugins.enabled_exports():
        mod = reg[pid]["module"]
        target = paths.deliverable_dir("taplio") if pid == "export_taplio" else out
        if pid == "export_ical":
            files += mod.export(profile, cal, drafts, target, minutes=int(plugins.plugin_config(pid).get("minutes") or 30))
        else:
            files += mod.export(profile, cal, drafts, target)
    return files


def run_phase4(profile: dict, demo: bool = False) -> dict:
    cal = load_calendar()
    mark_published()
    real = analytics.load_engagement()
    if demo and real.empty:
        analytics.make_demo(cal)
    n = len(real)
    store.set_status("phase4", "done" if n >= MIN_POSTS_DONE else "waiting",
                     f"{n} of {MIN_POSTS_DONE}+ posts logged" + (" (demo preview available)" if demo else ""))
    backup.backup_phase("phase4")
    return {"logged": n}


def run_phase5(profile: dict, demo: bool = False) -> dict:
    cal = load_calendar()
    df, is_demo = data_source(demo)
    enriched = analytics.enrich(df, cal)
    m = analytics.compute(enriched)
    ins = analytics.insights(m, cal, profile)
    refined = analytics.refine_weights(profile, m)
    drafts = load_drafts()
    present = sum(1 for f in folder_map.REQUIRED_DOCS if (paths.home() / f).exists())
    sc = analytics.scorecard(profile, drafts, cal, enriched, m, present, len(folder_map.REQUIRED_DOCS))
    slim = {k: v for k, v in m.items() if not isinstance(v, pd.DataFrame)}
    save("phase5", "metrics_summary.json", {**slim, "demo": is_demo})
    save("phase5", "insights.json", ins)
    save("phase5", "scorecard.json", sc)
    save("phase5", "refined_weights.json", refined)
    real_n = len(analytics.load_engagement())
    state = "preview" if is_demo else ("done" if real_n >= MIN_POSTS_DONE else "waiting")
    store.set_status("phase5", state, "Built from demo data" if is_demo else f"Built from {real_n} real posts")
    backup.backup_phase("phase5")
    return {"metrics": m, "insights": ins, "score": sc, "refined": refined, "demo": is_demo, "enriched": enriched}


# ------------------------------------------------------------ deliverables --
def build_deliverables(profile: dict, demo: bool = False) -> dict:
    """Write every client file. Safe to re-run; each file goes into its own deliverables sub-folder."""
    made = {}
    a, pl = load("phase1", "audit.json"), load("phase1", "pillars.json")
    pers = load("phase1", "personas.json") or personas.compare(profile)
    drafts, cal = load_drafts(), load_calendar()
    ideas = (load("phase2", "ideas.json", {}) or {}).get("ideas", [])
    if a and pl:
        made["audit"] = reports.build_audit_report(profile, a, pl, pers, paths.deliverable_dir("audit"))
    if drafts:
        made["drafts"] = reports.build_drafts_files(profile, drafts, paths.deliverable_dir("drafts"))
    if cal:
        made["calendar"] = write_calendar_files(profile, cal, drafts)
    res = run_phase5(profile, demo=demo)
    m, is_demo = res["metrics"], res["demo"]
    made["dashboard"] = reports.build_dashboard(profile, res["enriched"], m, paths.deliverable_dir("dashboard"), is_demo)
    chart_dir = paths.deliverable_dir("dashboard") / "charts"
    chart_dir.mkdir(exist_ok=True)
    charts.workflow_diagram(chart_dir / "workflow.png")
    made["review"] = reports.build_performance_report(profile, m, res["insights"], res["score"], res["refined"],
                                                      paths.deliverable_dir("review"), is_demo, chart_dir)
    if a and pl:
        bundle = {"audit": a, "pillars": pl, "ideas": ideas, "drafts": drafts, "calendar": cal, "metrics": m,
                  "insights": res["insights"], "score": res["score"], "demo": is_demo, "personas": pers,
                  "phases": paths.PHASES}
        made["capstone"] = reports.build_capstone(profile, bundle, paths.deliverable_dir("capstone"), chart_dir)
    store.log(f"deliverables built: {', '.join(made)}")
    return made


# ------------------------------------------------------------------ run all --
def run_all(profile: dict, use_ai: bool = True, demo: bool = False, progress=None) -> dict:
    """Phase 1 -> 5 and all deliverables. `progress(fraction, message)` keeps the UI informed."""
    def tick(f, msg):
        if progress:
            progress(f, msg)
    miss = settings.missing_fields(profile)
    if miss:
        raise ValueError("Fill these inputs first: " + ", ".join(miss))
    tick(0.05, "Phase 1: auditing profile and defining pillars")
    run_phase1(profile, use_ai)
    tick(0.20, "Phase 2: generating ideas and drafting posts")
    run_phase2(profile, use_ai, progress=lambda f: tick(0.20 + 0.3 * f, "Phase 2: drafting posts"))
    tick(0.55, "Phase 3: building calendar and Taplio queue")
    run_phase3(profile)
    tick(0.65, "Phase 4: preparing tracking")
    run_phase4(profile, demo=demo)
    tick(0.75, "Phase 5 and deliverables")
    made = build_deliverables(profile, demo=demo)
    snap = backup.backup_snapshot()
    tick(1.0, "Done")
    return {"made": made, "snapshot": snap.name, "finished": datetime.now().isoformat(timespec="seconds")}
