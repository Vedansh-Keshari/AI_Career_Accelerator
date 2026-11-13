import pytest

from lil import audit, context, drafting, ideation, llm, planner, quality, settings
from lil.knowledge import PERSONAS


@pytest.mark.parametrize("persona", list(PERSONAS))
@pytest.mark.parametrize("n_days", [2, 3, 5])
def test_ideas_drafts_meet_brief(profile, persona, n_days):
    profile.update(persona=persona, pillars=[], days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"][:n_days])
    slots = planner.plan_slots(profile)
    assert len(slots) >= 10
    ideas = ideation.generate_ideas(profile, slots)["ideas"]
    assert len(ideas) >= 15
    drafts = drafting.build_drafts(profile, ideas)
    assert len(drafts) == len(slots) >= 10
    assert all(d["text"].strip() and 0 <= d["quality"] <= 100 for d in drafts)


def test_no_adjacent_same_pillar_and_pilot(profile):
    slots = planner.plan_slots(profile)
    assert all(a["pillar"] != b["pillar"] for a, b in zip(slots, slots[1:]))
    assert [s["is_pilot"] for s in slots[:4]] == [True, True, True, False]
    assert {s["pillar"] for s in slots} <= set(context.effective_weights(profile))


def test_quality_flags():
    bad = quality.check("Hey guys, 80% of studies say you are a rockstar [add example]")
    joined = " ".join(bad["issues"])
    assert "Placeholder" in joined and "guys" in joined and "source" in joined.lower()
    assert quality.check("")["score"] == 0


def test_audit_scores_and_bounds(profile):
    a = audit.run_audit(profile)
    assert 0 <= a["total"] <= 100 and len(a["headline_options"]) == 3
    full = {**profile, "current_headline": "Data Analyst | Helping finance teams make faster decisions with SQL | Power BI",
            "current_about": "x" * 1300 + " DM me", "posts_per_month_now": 10, "connections": 900,
            "checks": {k: True for k in settings.CHECK_KEYS}}
    assert audit.score_profile(full)["total"] == 100


def test_apply_edit_splits_hashtags(profile):
    d = {"id": "D01", "hook": "h", "format": "text", "body": "", "hashtags": []}
    drafting.apply_edit(d, "Hook line\n\nI think so. What do you think?\n\n#A #B")
    assert d["hashtags"] == ["A", "B"] and d["text"].endswith("#A #B")


def test_ai_success_and_fallback(profile, monkeypatch):
    import json
    from lil import plugins
    settings.save_plugin_cfg({"active_ai": "ai_openai", "plugins": {"ai_openai": {"enabled": True, "config": {"api_key": "k"}}}})
    slots = planner.plan_slots(profile)
    n = len(slots) + 3
    reply = json.dumps([{"hook": f"AI hook {i}", "angle": "a"} for i in range(n)])
    mod = plugins.discover()["ai_openai"]["module"]
    monkeypatch.setattr(mod, "complete", lambda cfg, s, p: reply)
    res = ideation.generate_ideas(profile, slots)
    assert res["source"].startswith("AI plugin") and res["ideas"][0]["hook"] == "AI hook 0"

    def boom(cfg, s, p):
        raise RuntimeError("401 unauthorised")
    monkeypatch.setattr(mod, "complete", boom)
    res = ideation.generate_ideas(profile, slots)
    assert res["source"] == "Template engine" and "401" in res["warning"]
    assert llm.LAST_ERROR["message"]
    assert len(drafting.build_drafts(profile, res["ideas"])) == len(slots)  # drafting also falls back


def test_template_b_and_c_offline(profile):
    text, note = drafting.rewrite_tone(profile, "We will leverage synergy. I do not know.")
    assert "use" in text and "don't" in text
    post, _ = drafting.article_to_post(profile, "Data teams ship faster when reports are checked early. " * 8 + "Clear owners matter for quality work. " * 6, "Example Weekly")
    assert "Source: Example Weekly" in post
