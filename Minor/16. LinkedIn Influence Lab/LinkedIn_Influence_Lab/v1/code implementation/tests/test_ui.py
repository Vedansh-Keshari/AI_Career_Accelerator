"""Headless UI smoke test: every page must render without an exception."""
import pytest
from streamlit.testing.v1 import AppTest

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
PAGES = ["🏠 Command Center", "🧾 Inputs & Onboarding", "🔌 Plugins", "🧭 Phase 1 · Audit & Pillars", "💡 Phase 2 · Ideas & Drafts",
         "📅 Phase 3 · Calendar & Taplio", "🚀 Phase 4 · Publish & Track", "📈 Phase 5 · Analytics & Review", "🎭 Persona Lab",
         "📦 Deliverables & Backups", "📚 Docs & Help"]


def _app():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
    at.run()
    return at


def _go(at, page):
    at.sidebar.radio[0].set_value(page).run()
    assert not at.exception, f"{page}: {at.exception}"


@pytest.mark.parametrize("page", PAGES)
def test_pages_render_empty_workspace(home, page):
    _go(_app(), page)


def test_full_walkthrough(profile):
    at = _app()
    for btn in ("▶ Run full pipeline"):
        pass
    cmd = [b for b in at.button if b.label.startswith("▶ Run full pipeline")][0]
    cmd.click().run()
    assert not at.exception
    for page in PAGES:
        _go(at, page)
    _go(at, "💡 Phase 2 · Ideas & Drafts")
    assert len(at.expander) >= 10  # one expander per draft
    _go(at, "📈 Phase 5 · Analytics & Review")
    [b for b in at.button if b.label.startswith("▶ Run analytics")][0].click().run()
    assert not at.exception


def test_inputs_form_saves(home):
    at = _app()
    _go(at, "🧾 Inputs & Onboarding")
    [b for b in at.button if b.label == "Load sample inputs"][0].click().run()
    at.session_state  # sample loaded and page re-rendered
    assert not at.exception
    from lil import settings
    assert settings.load_profile()["name"] == "Aarav Sharma"
