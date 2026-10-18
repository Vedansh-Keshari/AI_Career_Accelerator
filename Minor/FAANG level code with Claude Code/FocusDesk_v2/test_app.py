"""UI tests that run the real app.py through Streamlit's AppTest."""
import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import storage

APP = str(Path(__file__).resolve().parent.parent / "app.py")
EMAIL = "vedansh@example.com"


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("FOCUSDESK_DATA_DIR", str(tmp_path / "data"))
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    return at


def button(at, label=None, key=None):
    for b in at.button:
        if (label and b.label == label) or (key and b.key == key):
            return b
    raise AssertionError(f"button not found: {label or key}")


def login(at, email=EMAIL):
    at.text_input(key="gate_email").set_value(email)
    button(at, "Enter FocusDesk").click().run()
    assert not at.exception
    return at


def html(at):
    return " ".join(m.value for m in at.markdown)


def card(at, label):
    m = re.search(re.escape(label) + r'</div><div class="fd-card-value">([^<]*)</div>', html(at))
    assert m, f"card not found: {label}"
    return m.group(1)


# ---------- email gate ----------
def test_gate_is_shown_first_and_hides_the_app(app):
    assert app.text_input(key="gate_email") is not None
    assert '<div class="fd-card"' not in html(app) and len(app.tabs) == 0
    assert any(b.label == "Enter FocusDesk" for b in app.button)


@pytest.mark.parametrize("bad,msg", [("", "required"), ("   ", "required"), ("not-an-email", "valid"),
                                     ("a@b", "valid"), ("a b@c.com", "valid")])
def test_bad_email_is_rejected(app, bad, msg):
    app.text_input(key="gate_email").set_value(bad)
    button(app, "Enter FocusDesk").click().run()
    assert app.error and msg in app.error[0].value.lower()
    assert len(app.tabs) == 0 and "user_email" not in app.session_state


def test_valid_email_opens_the_app(app):
    login(app, "  Vedansh@Example.COM ")
    assert app.session_state.user_email == EMAIL
    assert len(app.tabs) == 3 and '<div class="fd-card"' in html(app)
    assert EMAIL in html(app)  # shown in the sidebar chip
    assert (card(app, "Open tasks"), card(app, "Overdue"), card(app, "Done (7 days)")) == ("0", "0", "0")


def test_switch_user_returns_to_gate_and_separates_data(app):
    login(app)
    app.text_input(key="new_task_title").set_value("Alice only")
    button(app, "Add task").click().run()
    assert card(app, "Open tasks") == "1"
    button(app, key="switch_user").click().run()
    assert len(app.tabs) == 0 and app.text_input(key="gate_email") is not None
    login(app, "other@example.com")
    assert card(app, "Open tasks") == "0"  # a different user sees none of it
    button(app, key="switch_user").click().run()
    login(app, EMAIL)
    assert card(app, "Open tasks") == "1"  # and the first user's data is still there


# ---------- tasks ----------
def test_add_complete_delete_task_flow(app):
    login(app)
    app.text_input(key="new_task_title").set_value("Ship the app")
    button(app, "Add task").click().run()
    assert not app.exception
    assert storage.load(EMAIL)["tasks"][0]["title"] == "Ship the app"
    assert card(app, "Open tasks") == "1" and "Ship the app" in html(app)

    next(b for b in app.button if b.key and b.key.startswith("ok_")).click().run()
    assert storage.load(EMAIL)["tasks"][0]["done"] is True
    assert card(app, "Done (7 days)") == "1" and card(app, "Open tasks") == "0"

    app.radio(key="flt_status").set_value("All").run()
    next(b for b in app.button if b.key and b.key.startswith("del_")).click().run()
    assert storage.load(EMAIL)["tasks"] == []


def test_empty_title_shows_error(app):
    login(app)
    button(app, "Add task").click().run()
    assert app.error and "empty" in app.error[0].value.lower()
    assert storage.load(EMAIL)["tasks"] == []


def test_high_priority_task_gets_colour_chip(app):
    login(app)
    app.text_input(key="new_task_title").set_value("Urgent thing")
    app.selectbox(key="new_task_priority").set_value("High")
    button(app, "Add task").click().run()
    assert "fd-task high open" in html(app)


# ---------- focus log ----------
def test_log_focus_session(app):
    login(app)
    app.text_input(key="new_task_title").set_value("Deep work")
    button(app, "Add task").click().run()
    button(app, "Log session").click().run()
    assert not app.exception
    sessions = storage.load(EMAIL)["sessions"]
    assert len(sessions) == 1 and sessions[0]["minutes"] == 25
    assert card(app, "Focus (7 days)") == "25m"


# ---------- sample (model) data ----------
def test_load_and_remove_sample_data(app):
    login(app)
    assert button(app, key="remove_sample").disabled
    button(app, key="load_sample").click().run()
    assert not app.exception
    assert card(app, "Open tasks") == "8" and card(app, "Overdue") == "2"
    assert card(app, "Done (7 days)") == "2" and card(app, "Focus (7 days)") == "6h 05m"
    assert not button(app, key="remove_sample").disabled
    assert len(storage.load(EMAIL)["tasks"]) == 11

    button(app, key="remove_sample").click().run()
    assert card(app, "Open tasks") == "0" and storage.load(EMAIL)["tasks"] == []


def test_sample_data_with_special_characters_renders_safely(app):
    login(app)
    button(app, key="load_sample").click().run()
    page = html(app)
    assert "&lt;b&gt;budget&lt;/b&gt;" in page and "<b>budget</b>" not in page
    assert "&#36;5" in page and "overdue" in page


def test_insights_tab_with_sample_data(app):
    login(app)
    button(app, key="load_sample").click().run()
    page = html(app)
    assert card(app, "Total focus time") == "7h 05m"
    assert card(app, "Tasks completed (all time)") == "3"
    assert "fd-bar-fill" in page and len(app.get("vega_lite_chart")) == 1  # bar chart is drawn


def test_sample_does_not_touch_user_entries(app):
    login(app)
    app.text_input(key="new_task_title").set_value("Mine")
    button(app, "Add task").click().run()
    button(app, key="load_sample").click().run()
    button(app, key="remove_sample").click().run()
    assert [t["title"] for t in storage.load(EMAIL)["tasks"]] == ["Mine"]
