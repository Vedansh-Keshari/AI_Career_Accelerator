import io
import json
import zipfile
from datetime import date

import pandas as pd
import pytest
from docx import Document
from openpyxl import load_workbook

from lil import analytics, backup, folder_map, paths, pipeline, plugins, settings, store
from lil.trace import TRACE

ROOT = paths.Path(__file__).resolve().parents[1]


def test_full_pipeline_files_status_backups(profile):
    res = pipeline.run_all(profile, use_ai=False, demo=True)
    for key in paths.DELIVERABLES:
        assert any(paths.deliverable_dir(key).rglob("*.*")), key
    cap = next(paths.deliverable_dir("capstone").glob("*.docx"))
    doc = Document(cap)
    assert len(doc.paragraphs) > 40 and doc.sections[0].different_first_page_header_footer
    assert "Page" in "".join(p.text for p in doc.sections[0].footer.paragraphs) and "LIL-2025-P1" in doc.sections[0].header.paragraphs[0].text
    wb = load_workbook(paths.deliverable_dir("calendar") / "Content_Calendar_6_Weeks.xlsx")
    assert wb.sheetnames[:2] == ["6-Week Calendar", "Week View"] and wb.active.max_row >= 12
    st = store.get_status()
    assert st["phase1"]["state"] == "done" and st["phase5"]["state"] == "preview"
    assert len(list(paths.backups_dir().glob("phase_*"))) >= 5 and res["snapshot"].startswith("FULL")
    assert any(paths.deliverable_dir("dashboard").glob("*DEMO*.xlsx"))
    run = pipeline.last_run()
    assert [s["phase"] for s in run["stages"]] == ["phase1", "phase2", "phase3", "phase4", "phase5"] and all(s["summary"] for s in run["stages"])


def test_missing_inputs_rejected(home):
    with pytest.raises(ValueError):
        pipeline.run_all(settings.default_profile())


def test_phase_dependencies_enforced(profile):
    assert pipeline.phase_ready("phase1")[0] and pipeline.phase_ready("phase2")[0]
    for key, needs in (("phase3", "Phase 2"), ("phase4", "Phase 3"), ("phase5", "Phase 4")):
        ok, msg = pipeline.phase_ready(key)
        assert not ok and needs in msg
    with pytest.raises(RuntimeError):
        pipeline.run_phase3(profile)
    pipeline.run_phase2(profile, use_ai=False)
    assert pipeline.phase_ready("phase3")[0]
    pipeline.run_phase3(profile)
    assert pipeline.phase_ready("phase4")[0] and not pipeline.phase_ready("phase5")[0]


def test_taplio_approved_only_and_sync(profile):
    pipeline.run_all(profile, use_ai=False)
    queue = paths.deliverable_dir("taplio") / "taplio_queue_approved_only.csv"
    assert len(pd.read_csv(queue)) == 0
    ds = pipeline.load_drafts()
    ds[0]["human_reviewed"] = True
    pipeline.save_drafts(ds)
    assert pipeline.load_calendar()[0]["human_reviewed"] is True
    pipeline.run_phase3(profile)
    assert len(pd.read_csv(queue)) == 1


def test_backup_restore_and_secrets_excluded(profile):
    settings.save_plugin_cfg({"active_ai": "ai_offline", "plugins": {"ai_openai": {"enabled": True, "config": {"api_key": "SECRET123"}}}})
    pipeline.run_phase1(profile)
    zips = list(paths.backups_dir().glob("phase_1*"))
    with zipfile.ZipFile(zips[0]) as z:
        assert not any("plugins.json" in n for n in z.namelist())
        assert b"SECRET123" not in b"".join(z.read(n) for n in z.namelist())
        m = json.loads(z.read("MANIFEST.json"))
        assert m["type"] == "phase" and m["count"] == len(m["files"]) and all(len(e["sha256"]) == 64 for e in m["files"])
    audit_file = paths.phase_dir("phase1") / "audit.json"
    original = audit_file.read_text()
    audit_file.write_text("corrupted")
    res = backup.restore(zips[0].name)
    assert audit_file.read_text() == original and res["safety_backup"].startswith("FULL_SNAPSHOT") and "before_restore" in res["safety_backup"]
    with pytest.raises(FileNotFoundError):
        backup.restore("missing.zip")


def test_snapshot_restore_roundtrip_and_tamper_detection(profile):
    pipeline.run_all(profile, use_ai=False)
    snap = backup.backup_snapshot(tag="test")
    desc = backup.describe(snap.name)
    assert desc["type"] == "snapshot" and any(k.startswith("deliverables/") for k in desc["groups"])
    assert backup.verify(snap.name) == (True, [])
    cal = next(paths.deliverable_dir("calendar").glob("*.csv"))
    original = cal.read_bytes()
    cal.write_text("deleted")
    (paths.phase_dir("phase3") / "stray_new_file.json").write_text("{}")
    backup.restore(snap.name)
    assert cal.read_bytes() == original and not (paths.phase_dir("phase3") / "stray_new_file.json").exists()
    # flip one byte inside the zip's stored content: integrity check must refuse it
    bad = paths.backups_dir() / "FULL_SNAPSHOT__tampered.zip"
    with zipfile.ZipFile(snap) as zin, zipfile.ZipFile(bad, "w") as zout:
        for n in zin.namelist():
            data = zin.read(n)
            zout.writestr(n, data + b"x" if n.endswith("audit.json") else data)
    ok, problems = backup.verify(bad.name)
    assert not ok and any("audit.json" in p for p in problems)
    with pytest.raises(ValueError):
        backup.restore(bad.name)


def test_import_backup_validation_and_zip_slip(profile):
    pipeline.run_phase1(profile)
    z = next(paths.backups_dir().glob("phase_1*"))
    name = backup.import_backup(z.read_bytes(), "from my laptop.zip")
    assert name.startswith("IMPORTED__") and backup.verify(name)[0]
    with pytest.raises(ValueError):
        backup.import_backup(b"not a zip", "x.zip")
    evil = io.BytesIO()
    with zipfile.ZipFile(evil, "w") as zf:
        zf.writestr("phases/../../evil.txt", "x")
        zf.writestr("MANIFEST.json", json.dumps({"type": "snapshot", "files": [{"path": "phases/../../evil.txt", "bytes": 1, "sha256": "0" * 64}]}))
    with pytest.raises(ValueError):
        backup.import_backup(evil.getvalue(), "evil.zip")


def test_rerun_phase2_backs_up_edits(profile):
    pipeline.run_phase2(profile, use_ai=False)
    ds = pipeline.load_drafts()
    ds[0]["text"] = "MY EDIT"
    pipeline.save("phase2", "drafts.json", ds)
    pipeline.run_phase2(profile, use_ai=False)
    assert any("before_rerun" in b["file"] for b in backup.list_backups())


def test_analytics_import_and_live_analysis(profile):
    pipeline.run_phase2(profile, use_ai=False)
    pipeline.run_phase3(profile)
    cal = pipeline.load_calendar()
    csv = (ROOT / "sample_data" / "sample_engagement_job_seeker.csv").read_text()
    merged, warns = analytics.import_csv(io.StringIO(csv), [r["draft_id"] for r in cal])
    assert len(merged) == 18 and warns and merged["likes"].iloc[0] == int(csv.splitlines()[1].split(",")[1])
    pipeline.mark_published()
    assert all(r["status"] == "Published" for r in pipeline.load_calendar()[:18])
    before = len(backup.list_backups())
    live = pipeline.analyse(profile)  # read-only: no files, no backups
    assert live["metrics"]["posts"] == 18 and len(backup.list_backups()) == before
    res = pipeline.run_phase5(profile, demo=True)  # real data exists, so demo is ignored
    assert res["demo"] is False and store.phase_state("phase5") == "done"
    assert analytics.load_engagement(demo=True).empty
    assert pipeline.analyse(profile)["refined"] and sum(pipeline.analyse(profile)["refined"].values()) == pytest.approx(1, abs=0.01)


def test_plugins_traceability_and_docs(profile):
    assert {"ai_offline", "ai_openai", "ai_anthropic", "export_taplio", "export_sheets", "export_ical", "import_analytics"} <= set(plugins.discover())
    assert len(TRACE) == 24
    for n, name, how, files in TRACE:
        for f in files:
            assert (ROOT / f).exists(), f"part {n} {name}: {f}"
    for f in folder_map.REQUIRED_DOCS:
        assert (ROOT / f).exists(), f
    for purpose_path in folder_map.FOLDER_PURPOSE:
        if purpose_path.startswith(("src/", "docs/", "tools/", "tests/", "templates/")) and not purpose_path.endswith("/"):
            assert (ROOT / purpose_path).exists(), purpose_path


def test_unchanged_files_still_identical():
    """The client approved these as they were; guard against accidental edits."""
    import hashlib
    sums = {"docs/01_REQUIREMENTS_DOCUMENT.md": "272b43968c0473f63f36d3d9ac128c17", "requirements.txt": "ac8280a43f68f1a6860096901c2827aa"}
    for rel, md5 in sums.items():
        assert hashlib.md5((ROOT / rel).read_bytes()).hexdigest() == md5, rel
    how = (ROOT / "HOW_TO_RUN.txt").read_text()
    assert how.startswith("LINKEDIN INFLUENCE LAB  -  HOW TO RUN") and "PROBLEMS?  docs/06_TROUBLESHOOTING_FAQ.md" in how
