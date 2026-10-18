"""The model test data: known inputs with known expected results."""
from datetime import date

import logic
import sample_data
import storage

TODAY = date(2026, 10, 18)


def fresh():
    d = logic.new_data()
    sample_data.load_sample(d, TODAY)
    return d


def test_expected_headline_numbers():
    d = fresh()
    s = logic.summary(d, TODAY)
    assert s == {"open": 8, "overdue": 2, "done_week": 2, "focus_week": 365, "focus_total": 425}
    assert logic.priority_counts(d) == {"High": 2, "Medium": 3, "Low": 3}
    assert sum(1 for t in d["tasks"] if t["done"]) == 3
    assert len(d["tasks"]) == 11 and len(d["sessions"]) == 10


def test_expected_focus_chart():
    by_day = dict(logic.focus_by_day(fresh(), TODAY))
    assert by_day["2026-10-18"] == 75 and by_day["2026-10-17"] == 45
    assert by_day["2026-10-16"] == 90 and by_day["2026-10-15"] == 55
    assert by_day["2026-10-14"] == 60 and by_day["2026-10-13"] == 0
    assert by_day["2026-10-12"] == 40 and sum(by_day.values()) == 365


def test_expected_sorting_and_filters():
    d = fresh()
    open_order = [t["title"] for t in logic.filter_tasks(d["tasks"], "Open")]
    assert open_order[:2] == ["Prepare Q4 project proposal", "Reply to client emails"]  # High first, soonest due
    assert open_order[-1] == "Organise project folders"  # no due date sorts last within Low... after dated Low
    assert [t["title"] for t in logic.filter_tasks(d["tasks"], "Done")][0] == "Submit expense report"
    assert len(logic.filter_tasks(d["tasks"], "All", ["High"])) == 3
    assert len(logic.filter_tasks(d["tasks"], "All", None, "pull")) == 1


def test_records_are_consistent():
    d = fresh()
    ids = [t["id"] for t in d["tasks"]] + [s["id"] for s in d["sessions"]]
    assert len(ids) == len(set(ids))
    task_ids = {t["id"]: t["title"] for t in d["tasks"]}
    for s in d["sessions"]:
        if s["task_id"]:
            assert task_ids[s["task_id"]] == s["task_title"]
    assert all(r["sample"] for r in d["tasks"] + d["sessions"])


def test_load_is_idempotent_and_remove_keeps_user_data():
    d = logic.new_data()
    mine = logic.add_task(d, "My own task", today=TODAY)
    logic.add_session(d, 15, mine["id"], "mine", TODAY)
    sample_data.load_sample(d, TODAY)
    sample_data.load_sample(d, TODAY)  # twice must not duplicate
    assert len(d["tasks"]) == 12 and len(d["sessions"]) == 11
    assert sample_data.has_sample(d)
    removed = sample_data.remove_sample(d)
    assert removed == 21 and not sample_data.has_sample(d)
    assert [t["title"] for t in d["tasks"]] == ["My own task"] and len(d["sessions"]) == 1


def test_sample_survives_storage_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("FOCUSDESK_DATA_DIR", str(tmp_path))
    d = fresh()
    storage.save(d, "demo@example.com")
    back = storage.load("demo@example.com")
    assert len(back["tasks"]) == 11 and len(back["sessions"]) == 10
    assert logic.summary(back, TODAY) == logic.summary(d, TODAY)


def test_csv_export_handles_special_characters():
    out = logic.tasks_to_csv(fresh()["tasks"])
    assert "Check <b>budget</b> & costs ($5 + $10)" in out
    assert "sample" not in out.splitlines()[0]  # extra keys are not exported
