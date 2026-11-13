import io
import zipfile

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
    for f in paths.deliverable_dir("capstone").glob("*.docx"):
        assert len(Document(f).paragraphs) > 20
    wb = load_workbook(paths.deliverable_dir("calendar") / "Content_Calendar_6_Weeks.xlsx")
    assert wb.sheetnames[:2] == ["6-Week Calendar", "Week View"] and wb.active.max_row >= 12
    st = store.get_status()
    assert st["phase1"]["state"] == "done" and st["phase5"]["state"] == "preview"
    assert len(list(paths.backups_dir().glob("phase_*"))) >= 5 and res["snapshot"].startswith("FULL")
    assert any(paths.deliverable_dir("dashboard").glob("*DEMO*.xlsx"))


def test_missing_inputs_rejected(home):
    with pytest.raises(ValueError):
        pipeline.run_all(settings.default_profile())


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
    audit_file = paths.phase_dir("phase1") / "audit.json"
    original = audit_file.read_text()
    audit_file.write_text("corrupted")
    backup.restore(zips[0].name)
    assert audit_file.read_text() == original
    with pytest.raises(FileNotFoundError):
        backup.restore("missing.zip")


def test_rerun_phase2_backs_up_edits(profile):
    pipeline.run_phase2(profile, use_ai=False)
    ds = pipeline.load_drafts()
    ds[0]["text"] = "MY EDIT"
    pipeline.save("phase2", "drafts.json", ds)
    pipeline.run_phase2(profile, use_ai=False)
    assert any("before_rerun" in b["file"] for b in backup.list_backups())


def test_analytics_import_and_real_vs_demo(profile):
    pipeline.run_phase2(profile, use_ai=False)
    pipeline.run_phase3(profile)
    cal = pipeline.load_calendar()
    csv = (ROOT / "sample_data" / "sample_engagement.csv").read_text()
    merged, warns = analytics.import_csv(io.StringIO(csv), [r["draft_id"] for r in cal])
    assert len(merged) == 3 and merged["likes"].tolist() == [31, 52, 40] and warns
    pipeline.mark_published()
    assert [r["status"] for r in pipeline.load_calendar()[:3]] == ["Published"] * 3
    res = pipeline.run_phase5(profile, demo=True)  # real data exists, so demo is ignored
    assert res["demo"] is False and res["metrics"]["posts"] == 3
    assert store.phase_state("phase5") == "waiting"  # fewer than 10 real posts
    assert analytics.load_engagement(demo=True).empty


def test_plugins_and_traceability(profile):
    assert {"ai_offline", "ai_openai", "ai_anthropic", "export_taplio", "export_sheets", "export_ical", "import_analytics"} <= set(plugins.discover())
    assert len(TRACE) == 24
    for n, name, how, files in TRACE:
        for f in files:
            assert (ROOT / f).exists(), f"part {n} {name}: {f}"
    for f in folder_map.REQUIRED_DOCS:
        assert (ROOT / f).exists(), f
