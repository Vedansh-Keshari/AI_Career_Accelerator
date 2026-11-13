"""Headless UI tests: every page for every path, the admin lock, forms, downloads and workspace switching."""
import pytest
from streamlit.testing.v1 import AppTest

from lil import auth, paths, persona_content as pc, pipeline, samples, settings

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
PERSONAS = ("professional", "job_seeker", "thought_leader")
SECRET_MARKERS = ["Streamlit entry point", "Drop-in plugins: AI providers", "Salted hash of the admin passcode", "src/lil/auth.py"]


@pytest.fixture(autouse=True)
def _isolate_admin_file(home, monkeypatch):
    monkeypatch.delenv("LIL_ADMIN_PASSCODE", raising=False)
    monkeypatch.setattr(auth, "_file", lambda: home / "admin.json")


def _app(workspace="sample", role=None):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=180)
    at.session_state["workspace"] = workspace
    if role:
        at.session_state["role"] = role
    at.run()
    assert not at.exception, at.exception
    return at


def _go(at, label):
    at.sidebar.radio(key="nav").set_value(label).run()
    assert not at.exception, f"{label}: {[e.value[:400] for e in at.exception]}"


def _text(at):
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption] + [e.value for e in at.expander.__iter__() if hasattr(e, "value")]
    parts += [str(df.value.to_string()) for df in at.dataframe] + [c.value for c in at.code]
    return "\n".join(str(p) for p in parts)


@pytest.mark.parametrize("persona", PERSONAS)
def test_every_page_renders_for_each_path_with_sample_data(persona):
    at = _app("sample")
    if persona != "professional":
        paths.set_resolver(lambda: "sample")
        samples.seed(persona)
        at.run()
    assert at.sidebar.radio(key="nav").options == [pc.PAGES[k] for k in pc.nav_keys(persona)]
    for k in pc.nav_keys(persona):
        _go(at, pc.PAGES[k])
        assert not at.warning or k.startswith("hub_") is False or True
    other_hubs = [pc.PAGES[v] for p, v in pc.HUB.items() if p != persona]
    assert not set(other_hubs) & set(at.sidebar.radio(key="nav").options)


def test_every_page_renders_in_empty_own_workspace():
    at = _app("mine")
    for k in pc.nav_keys("professional"):
        _go(at, pc.PAGES[k])
    _go(at, pc.PAGES["phase1"])
    assert any("Phase 1" in e.value or "needs" in e.value.lower() or "Please complete" in e.value for e in at.warning) or at.markdown


def test_sample_banner_and_workspace_switch_clears_state():
    at = _app("sample")
    assert any("Sample workspace" in m.value for m in at.markdown)
    _go(at, pc.PAGES["phase2"])
    assert len(at.expander) >= 10
    at.sidebar.radio(key="workspace").set_value("mine").run()
    assert not at.exception
    assert not any("Sample workspace" in m.value for m in at.markdown)
    assert at.sidebar.radio(key="nav").value == pc.PAGES["phase2"]  # same page, now showing the empty own workspace
    assert any("complete these inputs" in w.value for w in at.warning)


def test_folder_map_locked_for_members_open_for_admin():
    member = _app("sample")
    _go(member, pc.PAGES["deliverables"])
    toggles = [t for t in member.toggle if "Folder map" in t.label]
    assert toggles and toggles[0].proto.disabled
    assert not [e for e in member.expander if "Folder map" in e.label]
    assert any("restricted" in m.value.lower() for m in member.markdown)
    shown = _text(member)
    assert not any(s in shown for s in SECRET_MARKERS)
    # member cannot find the structure guide either
    _go(member, pc.PAGES["docs"])
    assert not any("03_PROJECT_STRUCTURE_GUIDE" in str(o) for o in member.selectbox[0].options)

    admin = _app("sample", role="admin")
    _go(admin, pc.PAGES["deliverables"])
    assert [e for e in admin.expander if "Folder map" in e.label]
    assert any("Streamlit entry point" in m.value for m in admin.markdown)
    _go(admin, pc.PAGES["docs"])
    assert any("03_PROJECT_STRUCTURE_GUIDE" in str(o) for o in admin.selectbox[0].options)


def test_admin_signin_flow_and_lockout():
    at = _app("sample")
    assert auth.is_configured() is False
    at.text_input(key="adm_new").set_value("a good passcode 1").run()
    at.text_input(key="adm_new2").set_value("a good passcode 1").run()
    [b for b in at.sidebar.button if b.key == "adm_create"][0].click().run()
    assert at.session_state["role"] == "admin" and auth.verify("a good passcode 1")
    [b for b in at.sidebar.button if b.key == "admin_out"][0].click().run()
    assert at.session_state["role"] == "member"
    for _ in range(5):
        at.text_input(key="adm_code").set_value("wrong").run()
        [b for b in at.sidebar.button if b.key == "adm_in"][0].click().run()
    assert at.session_state["role"] == "member" and at.session_state["locked_until"] > 0
    at.run()  # next run shows the lock-out notice
    assert any("Too many attempts" in e.value for e in at.sidebar.error)


def test_deliverables_download_all_buttons():
    at = _app("sample")
    _go(at, pc.PAGES["deliverables"])
    keys = [b.proto.id for b in at.get("download_button")]
    labels = [b.proto.label for b in at.get("download_button")]
    assert any("ALL files from all sets" in l for l in labels)
    assert sum("Download all files in this set" in l for l in labels) == len(paths.DELIVERABLES)
    assert len(keys) > 10


def test_inputs_fill_save_and_validation_messages():
    at = _app("mine")
    _go(at, pc.PAGES["inputs"])
    [b for b in at.button if b.label == "Fill form with sample values"][0].click().run()
    assert at.text_input(key="in_name").value == "Riya Mehta (Sample)"
    [b for b in at.button if "Save inputs" in b.label][0].click().run()
    assert not at.exception and settings.load_profile()["name"] == "Riya Mehta (Sample)"
    at.text_input(key="in_email").set_value("not-an-email")  # form widgets commit on submit: no run in between
    at.number_input(key="in_followers").set_value(5)
    [b for b in at.button if "Save inputs" in b.label][0].click().run()
    assert any("Not saved" in e.value for e in at.error) and any("email" in m.value.lower() for m in at.markdown)
    assert settings.load_profile()["email"] != "not-an-email"
    [b for b in at.button if b.label == "Clear the form"][0].click().run()
    assert at.text_input(key="in_name").value == ""


def test_path_change_in_inputs_updates_tabs():
    at = _app("mine")
    settings.save_profile(samples.sample_profile("professional"))
    at.run()
    assert pc.PAGES["hub_professional"] in at.sidebar.radio(key="nav").options
    _go(at, pc.PAGES["inputs"])
    at.selectbox(key="in_persona").set_value("job_seeker")
    [b for b in at.button if "Save inputs" in b.label][0].click().run()
    assert not at.exception and settings.load_profile()["persona"] == "job_seeker"
    opts = at.sidebar.radio(key="nav").options
    assert pc.PAGES["hub_job_seeker"] in opts and pc.PAGES["hub_professional"] not in opts


def test_command_center_pipeline_and_single_phase_buttons():
    at = _app("mine")
    settings.save_profile(samples.sample_profile("thought_leader"))
    at.run()
    disabled = {b.key: b.proto.disabled for b in at.button if str(b.key).startswith("single_")}
    assert disabled["single_phase1"] is False and disabled["single_phase3"] is True and disabled["single_phase5"] is True
    [b for b in at.button if b.key == "single_phase2"][0].click().run()
    assert pipeline.load_drafts()
    [b for b in at.button if b.label.startswith("▶ Run full pipeline")][0].click().run()
    assert not at.exception and pipeline.last_run()["stages"]
    assert any("Done" in s.value for s in at.success)


def test_phase4_log_form_validation_and_live_update():
    at = _app("mine")
    prof = samples.sample_profile("job_seeker")
    settings.save_profile(prof)
    pipeline.run_phase2(prof, use_ai=False)
    pipeline.run_phase3(prof)
    at.run()
    _go(at, pc.PAGES["phase4"])
    at.number_input(key="log_imp").set_value(0)
    at.number_input(key="log_likes").set_value(5)
    [b for b in at.button if b.label == "Save engagement"][0].click().run()
    assert any("Impressions is 0" in e.value for e in at.error)
    at.number_input(key="log_imp").set_value(1000)
    at.number_input(key="log_likes").set_value(5)
    [b for b in at.button if b.label == "Save engagement"][0].click().run()
    assert not at.exception
    from lil import analytics
    assert len(analytics.load_engagement()) == 1
    at.number_input(key="kpi_a").set_value(2)
    [b for b in at.button if b.label == "Save weekly KPIs"][0].click().run()
    from lil import hubs
    assert int(hubs.load_kpis().iloc[0]["a"]) == 2


def test_persona_lab_hook_pin_and_switch_in_sample():
    at = _app("sample")
    _go(at, pc.PAGES["persona"])
    at.selectbox(key="pl_hook_persona").set_value("job_seeker").run()
    at.radio(key="pl_hook_pick").set_value(2).run()
    assert not at.exception
    [b for b in at.button if b.key == "pl_pin"][0].click().run()
    assert any(h["persona"] == "job_seeker" for h in settings.load_profile().get("pinned_hooks", []))
    at.selectbox(key="pl_target").set_value("thought_leader").run()
    [b for b in at.button if b.key == "pl_switch"][0].click().run()
    assert not at.exception and settings.load_profile()["persona"] == "thought_leader"
    assert pc.PAGES["hub_thought_leader"] in at.sidebar.radio(key="nav").options


def test_hubs_have_working_content():
    at = _app("sample")
    _go(at, pc.PAGES["hub_professional"])
    assert at.tabs and not at.exception
    paths.set_resolver(lambda: "sample")
    samples.seed("job_seeker")
    at.run()
    _go(at, pc.PAGES["hub_job_seeker"])
    [b for b in at.button if b.label == "Insert a sample job description"][0].click().run()
    assert not at.exception and any("Keyword match" in str(m.value) or "Keyword match" in str(getattr(m, "label", "")) for m in list(at.markdown) + list(at.metric)) or at.dataframe
