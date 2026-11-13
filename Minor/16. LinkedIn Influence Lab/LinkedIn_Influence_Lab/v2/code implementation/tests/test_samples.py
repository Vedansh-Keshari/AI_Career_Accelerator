import pytest

from lil import analytics, hubs, paths, persona_content as pc, pipeline, samples, settings, store


def test_sample_workspace_is_isolated_and_complete(home):
    paths.set_resolver(lambda: "sample")
    assert samples.ensure_seeded() is True and samples.ensure_seeded() is False
    assert paths.home() == home / "sample_workspace"
    st = store.get_status()
    assert [st[f"phase{i}"]["state"] for i in range(1, 6)] == ["done", "done", "waiting", "done", "done"], st  # phase 3 waits: a few drafts still need your review
    assert len(analytics.load_engagement()) >= 10 and len(pipeline.load_drafts()) >= 10
    paths.set_resolver(lambda: "mine")
    assert paths.home() == home and store.get_status() == {} and settings.load_profile()["name"] == ""
    assert not (home / "data" / "inputs" / "profile.json").exists()


@pytest.mark.parametrize("persona", samples.PERSONAS)
def test_every_step_has_data_for_each_path(sample_ws, persona):
    samples.seed(persona)
    prof = settings.load_profile()
    assert prof["persona"] == persona and "(Sample)" in prof["name"]
    drafts = pipeline.load_drafts()
    assert not any("Placeholder" in i for d in drafts for i in d["issues"])
    assert 0 < sum(d["human_reviewed"] for d in drafts) < len(drafts)  # review gate visible: some approved, some waiting
    assert any(d["format"] == "carousel" for d in drafts) and any(d["format"] == "poll" for d in drafts)
    assert not hubs.load_kpis().empty and len(hubs.load_kpis()) == 5
    for stage in ("phase1", "phase2", "phase3", "phase4", "phase5"):
        assert list(paths.phase_dir(stage).glob("*.json")) or list(paths.phase_dir(stage).glob("*.csv")), stage
    assert all(any(paths.deliverable_dir(k).glob("*.*")) for k in paths.DELIVERABLES)
    # context-correct hub data: only the data that belongs to this path exists
    names = {p.name for p in hubs.hub_dir().glob("*")}
    expected = {"professional": {"peer_log.csv"}, "job_seeker": {"opportunities.csv"}, "thought_leader": {"leads.csv", "series.json"}}[persona]
    assert names == expected
    own_hub = pc.HUB[persona]
    assert own_hub in pc.nav_keys(persona)
    # sample data is stamped as such in the reports
    cap = next(paths.deliverable_dir("capstone").glob("*.docx"))
    from docx import Document
    text = "\n".join(p.text for p in Document(cap).paragraphs) + "\n".join(c.text for t in Document(cap).tables for r in t.rows for c in r.cells)
    assert "SAMPLE DATA" in text and persona.replace("_", " ").title().split()[0] in text.replace("Working ", "")


def test_sample_loader_refuses_real_workspace(home):
    paths.set_resolver(lambda: "mine")
    with pytest.raises(RuntimeError):
        samples.seed("professional")
    with pytest.raises(RuntimeError):
        samples.reset_workspace()


def test_hub_sample_rows_reference_real_posts(sample_ws):
    samples.seed("job_seeker")
    ids = {d["id"] for d in pipeline.load_drafts()}
    opp = hubs.load_table("opportunities.csv", hubs.OPP_COLS)
    assert all(x in ids for x in opp["linked_post"] if x) and set(opp["stage"]) <= set(hubs.OPP_STAGES)
    samples.seed("thought_leader")
    leads = hubs.load_table("leads.csv", hubs.LEAD_COLS)
    assert set(leads["lead_type"]) <= set(hubs.LEAD_TYPES) and set(leads["status"]) <= set(hubs.LEAD_STATUS)
