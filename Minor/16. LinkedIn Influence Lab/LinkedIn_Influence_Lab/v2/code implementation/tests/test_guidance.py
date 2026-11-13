import pytest

from lil import guidance, samples, settings


def _ok():
    p = settings.default_profile()
    p.update(name="Riya Mehta", current_role="Analyst", industry="logistics", skills="Excel, SQL", target_audience="ops pros",
             goal="Be known in logistics", pillars=["career_insights", "actionable_tips", "personal_journey"])
    return p


def test_valid_profile_has_no_errors():
    assert guidance.validate_profile(_ok())[0] == []


@pytest.mark.parametrize("field,value,fragment", [
    ("name", "", "required"), ("name", "R", "short"), ("email", "nope", "email"), ("years_experience", "six", "whole number"),
    ("skills", "Excel", "at least 2"), ("skills", "", "required"), ("time", "8:30am", "HH:MM"), ("timezone", "Mars/Base", "time zone"),
    ("pillars", ["career_insights"], "3 and 5"), ("days", ["Monday"], "2 and 5"), ("story_win", "x" * 401, "too long"),
    ("achievements", "\n".join(["a"] * 9), "at most 8"), ("goal", "abc", "short")])
def test_validation_errors(field, value, fragment):
    p = _ok()
    p[field] = value
    errors, _ = guidance.validate_profile(p)
    assert any(fragment.lower() in e.lower() for e in errors), errors


def test_warnings_for_path_gaps():
    p = _ok()
    p.update(persona="job_seeker", linkedin_url="https://example.com/me", achievements="Helped a lot of people")
    _, warns = guidance.validate_profile(p)
    text = " ".join(warns)
    assert "Target roles" in text and "linkedin.com/in" in text and "number" in text


@pytest.mark.parametrize("persona", samples.PERSONAS)
def test_sample_profiles_are_valid_and_labelled(persona):
    p = samples.sample_profile(persona)
    assert guidance.validate_profile(p)[0] == []
    assert "(Sample)" in p["name"] and p["persona"] == persona


def test_guide_covers_every_profile_field():
    keys = {r[0] for r in guidance.FIELD_GUIDE}
    for k in ("name", "skills", "pillars", "days", "start_date", "role_models", "story_win"):
        assert k in keys
