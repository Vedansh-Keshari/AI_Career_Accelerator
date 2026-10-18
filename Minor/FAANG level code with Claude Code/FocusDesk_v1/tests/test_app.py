"""UI tests that run the real app.py through Streamlit's AppTest."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import storage

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("FOCUSDESK_DATA", str(tmp_path / "d.json"))
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    return at


def test_loads_clean(app):
    assert app.title[0].value.endswith("FocusDesk")
    assert [m.value for m in app.metric][:3] == ["0", "0", "0"]


def test_add_complete_delete_task_flow(app):
    app.text_input[0].set_value("Ship the app")
    app.button[0].click().run()  # "Add task"
    assert not app.exception
    assert storage.load()["tasks"][0]["title"] == "Ship the app"
    assert app.metric[0].value == "1"

    next(b for b in app.button if b.key and b.key.startswith("ok_")).click().run()
    assert storage.load()["tasks"][0]["done"] is True

    app.radio[0].set_value("All").run()
    next(b for b in app.button if b.key and b.key.startswith("del_")).click().run()
    assert storage.load()["tasks"] == []


def test_empty_title_shows_error(app):
    app.button[0].click().run()
    assert app.error and "empty" in app.error[0].value.lower()
    assert storage.load()["tasks"] == []


def test_log_focus_session(app):
    app.text_input[0].set_value("Deep work")
    app.button[0].click().run()
    log = next(b for b in app.button if b.label == "Log session")
    log.click().run()
    assert not app.exception
    sessions = storage.load()["sessions"]
    assert len(sessions) == 1 and sessions[0]["minutes"] == 25
    assert app.metric[3].value == "25m"
