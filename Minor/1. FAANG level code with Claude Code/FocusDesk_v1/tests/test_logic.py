from datetime import date, timedelta

import pytest

import logic
import storage

TODAY = date(2026, 10, 18)


def test_add_task_validation():
    d = logic.new_data()
    with pytest.raises(ValueError):
        logic.add_task(d, "   ")
    with pytest.raises(ValueError):
        logic.add_task(d, "x", priority="Urgent")
    t = logic.add_task(d, "  Write report ", "High", TODAY, today=TODAY)
    assert t["title"] == "Write report" and t["due"] == "2026-10-18"


def test_complete_reopen_delete():
    d = logic.new_data()
    t = logic.add_task(d, "A", today=TODAY)
    logic.complete_task(d, t["id"], today=TODAY)
    assert d["tasks"][0]["done"] and d["tasks"][0]["completed"] == "2026-10-18"
    logic.reopen_task(d, t["id"])
    assert not d["tasks"][0]["done"] and d["tasks"][0]["completed"] is None
    logic.delete_task(d, t["id"])
    assert d["tasks"] == []
    with pytest.raises(KeyError):
        logic.complete_task(d, "nope")


def test_sort_and_filter():
    d = logic.new_data()
    low = logic.add_task(d, "low", "Low", today=TODAY)
    high_late = logic.add_task(d, "high late", "High", TODAY + timedelta(days=5), today=TODAY)
    high_soon = logic.add_task(d, "high soon", "High", TODAY + timedelta(days=1), today=TODAY)
    done = logic.add_task(d, "done", "High", today=TODAY)
    logic.complete_task(d, done["id"], today=TODAY)
    order = [t["title"] for t in logic.sort_tasks(d["tasks"])]
    assert order == ["high soon", "high late", "low", "done"]
    assert [t["title"] for t in logic.filter_tasks(d["tasks"], "Open")] == ["high soon", "high late", "low"]
    assert [t["title"] for t in logic.filter_tasks(d["tasks"], "Done")] == ["done"]
    assert [t["title"] for t in logic.filter_tasks(d["tasks"], "All", ["Low"])] == ["low"]
    assert [t["title"] for t in logic.filter_tasks(d["tasks"], "All", None, "SOON")] == ["high soon"]


def test_overdue():
    d = logic.new_data()
    t = logic.add_task(d, "x", due=TODAY - timedelta(days=1), today=TODAY)
    assert logic.is_overdue(t, TODAY)
    logic.complete_task(d, t["id"], today=TODAY)
    assert not logic.is_overdue(t, TODAY)


def test_sessions_and_summary():
    d = logic.new_data()
    t = logic.add_task(d, "Study", today=TODAY)
    logic.add_session(d, 25, t["id"], "chapter 1", TODAY)
    logic.add_session(d, 60, None, "", TODAY - timedelta(days=3))
    logic.add_session(d, 40, None, "", TODAY - timedelta(days=20))
    for bad in (0, -5, 601, 2.5):
        with pytest.raises(ValueError):
            logic.add_session(d, bad)
    with pytest.raises(KeyError):
        logic.add_session(d, 10, "missing")
    s = logic.summary(d, TODAY)
    assert s["focus_week"] == 85 and s["focus_total"] == 125 and s["open"] == 1
    by_day = logic.focus_by_day(d, TODAY)
    assert len(by_day) == 7 and by_day[-1] == ("2026-10-18", 25) and sum(m for _, m in by_day) == 85


def test_deleting_task_keeps_session_title():
    d = logic.new_data()
    t = logic.add_task(d, "Temp", today=TODAY)
    logic.add_session(d, 10, t["id"], day=TODAY)
    logic.delete_task(d, t["id"])
    assert d["sessions"][0]["task_title"] == "Temp"


def test_format_minutes_and_csv():
    assert logic.format_minutes(45) == "45m" and logic.format_minutes(125) == "2h 05m"
    d = logic.new_data()
    logic.add_task(d, "Hello, world", today=TODAY)
    out = logic.tasks_to_csv(d["tasks"])
    assert out.splitlines()[0].startswith("id,title") and '"Hello, world"' in out


def test_storage_roundtrip_and_corruption(tmp_path, monkeypatch):
    f = tmp_path / "sub" / "d.json"
    monkeypatch.setenv("FOCUSDESK_DATA", str(f))
    assert storage.load() == logic.new_data()
    d = logic.new_data()
    logic.add_task(d, "Persist me", today=TODAY)
    storage.save(d)
    assert storage.load()["tasks"][0]["title"] == "Persist me"
    f.write_text("{not json")
    assert storage.load() == logic.new_data()
    assert f.with_suffix(".corrupt.json").exists()
