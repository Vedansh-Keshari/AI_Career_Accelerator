import pandas as pd

from lil import hubs, paths, persona_content as pc, personas, planner
from lil.knowledge import PERSONAS

JD = ("We are hiring a Business Intelligence Analyst with strong SQL, Power BI and Excel skills. You will build dashboards, automate reports with Python "
      "and present insights to stakeholders. Experience with data modelling and A/B testing is a plus. You will work with merchandising teams every week to "
      "define metrics and data quality checks and explain results in plain language.")


def test_navigation_is_targeted_per_path():
    hubs_all = set(pc.HUB.values())
    for persona in PERSONAS:
        keys = pc.nav_keys(persona)
        assert pc.HUB[persona] in keys and not (hubs_all - {pc.HUB[persona]}) & set(keys)
        assert keys[:8] == pc.CORE_BEFORE and keys[-3:] == pc.CORE_AFTER


def test_impact_covers_every_phase_and_differs(profile):
    for target in ("professional", "thought_leader"):
        rows = personas.impact(profile, target)
        areas = " ".join(r["Area"] for r in rows)
        for n in range(1, 6):
            assert f"Phase {n}" in areas
        assert all(r["Now"] != r["If you switch"] for r in rows if r["Area"] in ("Pillar mix", "Posting days", "Weekly path KPIs", "Extra tab in the sidebar"))


def test_hook_options_per_path(profile):
    for persona in PERSONAS:
        opts = personas.hook_options(profile, persona)
        assert 5 <= len(opts) <= 8 and len({o["hook"] for o in opts}) == len(opts)
        assert not any("{" in o["hook"] for o in opts)
    assert any("Business Intelligence" in o["hook"] for o in personas.hook_options(profile, "job_seeker"))


def test_keyword_match(profile):
    kws = hubs.extract_keywords(JD, 15, ["Power BI", "SQL"])
    assert "power bi" in kws and "sql" in kws and "the" not in kws
    res = hubs.keyword_match({**profile, "skills": "SQL, Excel", "current_headline": "", "current_about": "", "achievements": ""}, JD, [])
    assert "sql" not in res["missing"] and "dashboards" in res["missing"] and 0 <= res["score"] < 100


def test_consistency_streak_and_gap(home):
    cal = [{"week": 1, "date": "2026-10-05", "draft_id": "D01"}, {"week": 1, "date": "2026-10-07", "draft_id": "D02"},
           {"week": 2, "date": "2026-10-12", "draft_id": "D03"}, {"week": 2, "date": "2026-10-14", "draft_id": "D04"}]
    eng = pd.DataFrame({"post_id": ["D01", "D02", "D04"]})
    from datetime import date
    c = hubs.consistency(cal, eng, today=date(2026, 10, 20))
    assert c["due"] == 4 and c["logged_due"] == 3 and c["streak"] == 1 and c["longest_gap"] == 7 and c["rate"] == 75


def test_kpi_log_targets_and_insights(sample_ws, profile):
    for persona in PERSONAS:
        prof = {**profile, "persona": persona}
        hubs.save_kpi(1, 3, 2, 1, "n")
        hubs.save_kpi(1, 5, 2, 1)  # same week replaces
        assert len(hubs.load_kpis()) == 1 and hubs.load_kpis().iloc[0]["a"] == 5
        prog = hubs.kpi_progress(prof)
        assert [p["label"] for p in prog] == [f["label"] for f in pc.KPI_FIELDS[persona]] and all(0 <= p["pct"] <= 100 for p in prog)
        assert hubs.kpi_insights(prof, {"empty": True})
    assert hubs.kpi_targets({"persona": "job_seeker", "kpi_targets": {"a": 9}})["a"] == 9


def test_series_templates_carousel(profile):
    eps = hubs.plan_series(profile, "AI in Plain English", "AI adoption", 4)
    assert len(eps) == 4 and eps[0]["hook"].startswith("AI in Plain English #1")
    assert len(hubs.recruiter_templates(profile)) == 5 and "Business Intelligence Analyst" in hubs.recruiter_templates(profile)[0][1]
    d = [{"id": "D01", "hook": "h", "slides": [{"title": "T", "body": "B"}]}, {"id": "D02", "hook": "x"}]
    assert "D01" in hubs.carousel_markdown(d) and len(hubs.carousel_rows(d)) == 1


def test_pillar_mix_differs_between_paths(profile):
    mixes = {}
    for persona in PERSONAS:
        slots = planner.plan_slots({**profile, "persona": persona, "pillars": []})
        mixes[persona] = tuple(sorted({s["pillar"]: sum(1 for x in slots if x["pillar"] == s["pillar"]) for s in slots}.items()))
    assert len(set(mixes.values())) == 3
