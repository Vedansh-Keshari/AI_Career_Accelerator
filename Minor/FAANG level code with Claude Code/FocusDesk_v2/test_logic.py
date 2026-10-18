import json
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


def test_priority_counts():
    d = logic.new_data()
    logic.add_task(d, "a", "High", today=TODAY)
    logic.add_task(d, "b", "High", today=TODAY)
    c = logic.add_task(d, "c", "Low", today=TODAY)
    logic.complete_task(d, c["id"], today=TODAY)
    assert logic.priority_counts(d) == {"High": 2, "Medium": 0, "Low": 0}


@pytest.mark.parametrize("raw,expected", [
    ("vedansh@example.com", "vedansh@example.com"),
    ("  Vedansh.K+work@Example.CO.IN ", "vedansh.k+work@example.co.in"),
    ("a_b-c@sub.domain.org", "a_b-c@sub.domain.org"),
])
def test_valid_emails(raw, expected):
    assert logic.validate_email(raw) == expected


@pytest.mark.parametrize("raw", [
    "", "   ", None, "plainaddress", "@example.com", "name@", "name@example",
    "name@@example.com", "na me@example.com", "name@exa mple.com", "name@example.c",
    "a..b@example.com", "name@example..com", "x" * 250 + "@example.com",
])
def test_invalid_emails(raw):
    with pytest.raises(ValueError):
        logic.validate_email(raw)


def test_email_error_messages():
    with pytest.raises(ValueError, match="required"):
        logic.validate_email("  ")
    with pytest.raises(ValueError, match="valid email"):
        logic.validate_email("nope")


# ---------- storage ----------
@pytest.fixture
def datadir(tmp_path, monkeypatch):
    monkeypatch.setenv("FOCUSDESK_DATA_DIR", str(tmp_path / "data"))
    return tmp_path / "data"


def test_storage_roundtrip_and_owner(datadir):
    email = "Vedansh@Example.com"
    assert storage.load(email) == logic.new_data()
    d = logic.new_data()
    logic.add_task(d, "Persist me", today=TODAY)
    logic.add_session(d, 30, d["tasks"][0]["id"], "note", TODAY)
    storage.save(d, email)
    again = storage.load("vedansh@example.com")  # same user, different case
    assert again["tasks"][0]["title"] == "Persist me" and again["sessions"][0]["minutes"] == 30
    raw = json.loads(storage.user_file(email).read_text())
    assert raw["owner"] == "vedansh@example.com"
    assert "vedansh" not in storage.user_file(email).name  # file name is hashed


def test_each_email_has_its_own_data(datadir):
    a, b = logic.new_data(), logic.new_data()
    logic.add_task(a, "Alice task", today=TODAY)
    storage.save(a, "alice@example.com")
    storage.save(b, "bob@example.com")
    assert [t["title"] for t in storage.load("alice@example.com")["tasks"]] == ["Alice task"]
    assert storage.load("bob@example.com")["tasks"] == []
    assert storage.user_file("alice@example.com") != storage.user_file("bob@example.com")


def test_corrupt_file_is_backed_up(datadir):
    email = "x@example.com"
    storage.save(logic.new_data(), email)
    f = storage.user_file(email)
    f.write_text("{not json")
    assert storage.load(email) == logic.new_data()
    assert f.with_suffix(".corrupt.json").exists()


def test_load_drops_malformed_records(datadir):
    email = "x@example.com"
    datadir.mkdir(parents=True)
    storage.user_file(email).write_text(json.dumps({
        "tasks": [
            {"id": "ok1", "title": "Good", "priority": "Bogus"},   # priority repaired
            {"id": "bad1"}, "junk", {"title": "no id"}, {"id": "x", "title": "  "},
        ],
        "sessions": [
            {"id": "s1", "date": "2026-10-18", "minutes": 20},
            {"id": "s2", "date": "2026-10-18", "minutes": "20"},
            {"id": "s3", "date": "2026-10-18", "minutes": 0},
            {"id": "s4", "date": "2026-10-18", "minutes": True},
        ],
    }))
    d = storage.load(email)
    assert len(d["tasks"]) == 1 and d["tasks"][0]["priority"] == "Medium"
    assert d["tasks"][0]["done"] is False and d["tasks"][0]["due"] is None
    assert [s_["id"] for s_ in d["sessions"]] == ["s1"]
    logic.sort_tasks(d["tasks"])  # must not crash on repaired data


def test_non_dict_file_gives_empty_data(datadir):
    datadir.mkdir(parents=True)
    storage.user_file("x@example.com").write_text("[1, 2, 3]")
    assert storage.load("x@example.com") == logic.new_data()


def test_v1_data_is_adopted_once(datadir):
    datadir.mkdir(parents=True)
    d = logic.new_data()
    logic.add_task(d, "From v1", today=TODAY)
    (datadir / storage.LEGACY_FILE).write_text(json.dumps(d))
    first = storage.load("first@example.com")
    assert first["tasks"][0]["title"] == "From v1"
    assert (datadir / storage.LEGACY_BACKUP).exists() and not (datadir / storage.LEGACY_FILE).exists()
    assert storage.load("second@example.com") == logic.new_data()  # not copied to a second user
    assert storage.load("first@example.com")["tasks"][0]["title"] == "From v1"
