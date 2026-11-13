import json
from datetime import date, time

import streamlit as st

from .. import guidance, paths, settings, theme
from ..knowledge import PERSONAS, PILLARS, TIMEZONES, TONES, WEEKDAYS
from . import common

TEXT_KEYS = ["name", "email", "linkedin_url", "taplio_account", "google_email", "current_role", "company", "industry", "years_experience",
             "skills", "target_audience", "goal", "target_roles", "offer", "story_win", "story_mistake", "story_lesson", "achievements",
             "current_headline", "current_about", "role_models"]
G = {row[0]: row for row in guidance.FIELD_GUIDE}


def _help(key: str) -> str:
    r = G[key]
    return f"Type: {r[2]}. {r[3]} Example: {r[4]}. Why: {r[5]}" + ("" if r[6] else " (optional)")


def _fill(p: dict) -> None:
    """Write a profile into the form widgets (used on first load and by 'Fill with sample')."""
    ss = st.session_state
    ss["in_persona"] = p["persona"]
    ss["in_reset"] = False
    for k in TEXT_KEYS:
        ss[f"in_{k}"] = str(p.get(k, "") or "")
    ss["in_tone"] = p.get("tone") if p.get("tone") in TONES else TONES[0]
    ss["in_pillars"] = p.get("pillars") or [k for k, _ in sorted(PERSONAS[p["persona"]]["weights"].items(), key=lambda kv: -kv[1])[:4]]
    for k in ("followers", "connections", "posts_per_month_now"):
        ss[f"in_{k}"] = int(p.get(k) or 0)
    for k in settings.CHECK_KEYS:
        ss[f"in_check_{k}"] = bool(p["checks"].get(k))
    ss["in_days"] = p.get("days") or PERSONAS[p["persona"]]["default_days"]
    hh, mm = (str(p.get("time", "08:30")).split(":") + ["0"])[:2]
    ss["in_time"] = time(int(hh), int(mm))
    ss["in_timezone"] = p.get("timezone") if p.get("timezone") in TIMEZONES else TIMEZONES[0]
    ss["in_start_date"] = date.fromisoformat(p["start_date"])


def _cb_sample(persona_key: str):
    from .. import samples
    prof = samples.sample_profile(persona_key)
    prof["start_date"] = settings.next_monday().isoformat()  # a form sample should start in the future
    _fill(prof)
    st.session_state["in_filled"] = "sample"


def _cb_clear():
    blank = settings.default_profile()
    _fill(blank)
    st.session_state["in_pillars"] = []
    st.session_state["in_days"] = []
    st.session_state["in_filled"] = "blank"


def render():
    theme.hero("Inputs & Onboarding", "Tell the lab who you are. Everything downstream is built from this page.", "#6D28D9", "#EA580C", "🧾")
    if st.session_state.get("in_flash"):
        st.success(st.session_state.pop("in_flash"))
    p = settings.load_profile()
    sig = json.dumps(p, sort_keys=True, default=str)
    if st.session_state.get("in_sig") != (paths.workspace(), sig):
        _fill(p)
        st.session_state["in_sig"] = (paths.workspace(), sig)
        st.session_state.pop("in_filled", None)
    st.caption("Never type passwords here. Taplio and LinkedIn log-ins stay in your browser; this app only needs IDs and (optional) API keys.")

    with st.expander("📋 Data guide: what to type in each field, in which format, and why", expanded=False):
        common.guide_table([(r[1], r[2], r[3], r[4], r[5], "Yes" if r[6] else "No") for r in guidance.FIELD_GUIDE],
                           ["Field", "Type", "Rule", "Example", "Why we ask", "Required"])
    c1, c2, c3 = st.columns([2, 1.3, 1])
    pick = c1.selectbox("Try it with sample values (fills the form only; nothing is saved until you press Save)", list(PERSONAS),
                        format_func=common.persona_label, key="in_sample_pick")
    c2.button("Fill form with sample values", on_click=_cb_sample, args=(pick,))
    c3.button("Clear the form", on_click=_cb_clear)
    if st.session_state.get("in_filled") == "sample":
        st.info("The form holds sample values (a fictional person). Replace them with your own before saving.")

    with st.form("inputs_form"):
        t1, t2, t3, t4, t5, t6, t7 = st.tabs(["🪪 You & IDs", "🎯 Role & goals", "🎨 Voice & pillars", "📖 Your stories",
                                              "🔍 Current profile", "🌟 Role models", "🗓️ Posting plan"])
        with t1:
            persona = st.selectbox("Which path are you on? *", list(PERSONAS), format_func=common.persona_label, key="in_persona", help=_help("persona"))
            st.caption(PERSONAS[persona]["story"])
            st.checkbox("Reset pillars and posting days to this path's recommended defaults", key="in_reset")
            c1, c2 = st.columns(2)
            c1.text_input("Full name *", key="in_name", max_chars=80, help=_help("name"), placeholder="e.g. Riya Mehta")
            c2.text_input("Email ID", key="in_email", max_chars=120, help=_help("email"), placeholder="name@domain.com")
            c1.text_input("LinkedIn profile URL", key="in_linkedin_url", help=_help("linkedin_url"), placeholder="https://www.linkedin.com/in/your-name")
            c2.text_input("Taplio account (email or username)", key="in_taplio_account", max_chars=80, help=_help("taplio_account"), placeholder="email or username, never a password")
            c1.text_input("Google account for Drive/Sheets sharing", key="in_google_email", max_chars=120, help=_help("google_email"), placeholder="name@gmail.com")
        with t2:
            c1, c2 = st.columns(2)
            c1.text_input("Current role *", key="in_current_role", max_chars=80, help=_help("current_role"), placeholder="e.g. Senior Operations Analyst")
            c2.text_input("Company / organisation", key="in_company", max_chars=80, help=_help("company"), placeholder="leave blank if between roles")
            c1.text_input("Industry / niche *", key="in_industry", max_chars=80, help=_help("industry"), placeholder="e.g. supply chain analytics")
            c2.text_input("Years of experience", key="in_years_experience", max_chars=2, help=_help("years_experience"), placeholder="digits only, e.g. 6")
            st.text_area("Key skills * (comma separated, most important first)", key="in_skills", help=_help("skills"), placeholder="Excel, SQL, Power BI", max_chars=600)
            c1.text_input("Target audience *", key="in_target_audience", max_chars=100, help=_help("target_audience"), placeholder="who should read your posts")
            c2.text_input("Main goal *", key="in_goal", max_chars=160, help=_help("goal"), placeholder="one sentence, e.g. land interviews for BI roles")
            c1.text_input("Target roles (job seekers)", key="in_target_roles", max_chars=100, help=_help("target_roles"), placeholder="e.g. Business Intelligence Analyst")
            c2.text_input("What you offer (founders / thought leaders)", key="in_offer", max_chars=120, help=_help("offer"), placeholder="e.g. AI adoption workshops")
        with t3:
            st.selectbox("Brand voice *", TONES, key="in_tone", help=_help("tone"))
            st.multiselect("Content pillars * (choose 3-5)", list(PILLARS), key="in_pillars", format_func=lambda k: f"{PILLARS[k]['emoji']} {PILLARS[k]['label']}", help=_help("pillars"))
        with t4:
            st.caption("Real examples make posts sound like you. Anything left blank becomes a [placeholder] that the quality check flags. Max 400 characters each.")
            st.text_area("A recent win", key="in_story_win", max_chars=400, help=_help("story_win"), placeholder="One true sentence with a result if possible")
            st.text_area("A mistake you learned from", key="in_story_mistake", max_chars=400, help=_help("story_mistake"), placeholder="One honest sentence")
            st.text_area("A lesson you would tell your younger self", key="in_story_lesson", max_chars=400, help=_help("story_lesson"), placeholder="What you now do differently")
            st.text_area("Achievements with numbers (one per line, max 8)", key="in_achievements", help=_help("achievements"), placeholder="Trained 12 teammates on pivot tables")
        with t5:
            st.text_input("Current LinkedIn headline", key="in_current_headline", max_chars=220, help=_help("current_headline"))
            st.text_area("Current About section", key="in_current_about", height=140, max_chars=2600, help=_help("current_about"))
            c1, c2, c3 = st.columns(3)
            c1.number_input("Followers", 0, 10_000_000, key="in_followers", help=_help("followers"))
            c2.number_input("Connections", 0, 100_000, key="in_connections", help=_help("connections"))
            c3.number_input("Posts per month right now", 0, 300, key="in_posts_per_month_now", help=_help("posts_per_month_now"))
            vis_label = {"job_seeker": "Open to Work (recruiters only) is on", "thought_leader": "Creator mode / Follow button is on",
                         "professional": "Contact info and a call to action are set"}[persona]
            labels = {"photo": "Professional photo", "banner": "Banner states my value", "custom_url": "Custom profile URL",
                      "featured": "Featured section filled", "skills_15": "15+ skills, top 3 pinned", "recs_3": "3+ recommendations",
                      "experience_metrics": "Experience bullets have numbers", "visibility": vis_label}
            cols = st.columns(2)
            for i, (k, lbl) in enumerate(labels.items()):
                cols[i % 2].checkbox(lbl, key=f"in_check_{k}")
        with t6:
            st.caption("One per line: Name | profile URL | what you admire. Used for the benchmark and the peer list.")
            st.text_area("Role models / competitors", key="in_role_models", height=150, help=_help("role_models"), placeholder="Jane Doe | https://www.linkedin.com/in/jane-doe | clear weekly carousels")
        with t7:
            st.multiselect("Posting days * (2-5)", WEEKDAYS, key="in_days", help=_help("days"))
            st.time_input("Posting time *", key="in_time", help=_help("time"))
            st.selectbox("Time zone *", TIMEZONES, key="in_timezone", help=_help("timezone"))
            st.date_input("First posting date *", key="in_start_date", help=_help("start_date"))
        saved = st.form_submit_button("💾 Save inputs")

    if saved:
        ss = st.session_state
        persona = ss["in_persona"]
        new = {**p, "persona": persona, "tone": ss["in_tone"], "followers": int(ss["in_followers"]), "connections": int(ss["in_connections"]),
               "posts_per_month_now": int(ss["in_posts_per_month_now"]), "checks": {k: bool(ss[f"in_check_{k}"]) for k in settings.CHECK_KEYS},
               "time": ss["in_time"].strftime("%H:%M"), "timezone": ss["in_timezone"], "start_date": ss["in_start_date"].isoformat(),
               "pillars": [] if ss["in_reset"] else list(ss["in_pillars"]), "days": PERSONAS[persona]["default_days"] if ss["in_reset"] else list(ss["in_days"])}
        for k in TEXT_KEYS:
            new[k] = str(ss[f"in_{k}"]).strip()
        errors, warns = guidance.validate_profile({**new, "pillars": new["pillars"] or [k for k, _ in sorted(PERSONAS[persona]["weights"].items(), key=lambda kv: -kv[1])[:4]]})
        if date.fromisoformat(new["start_date"]) < date.today() and not paths.is_sample():
            warns.append("The first posting date is in the past; posts dated before today will count as already due.")
        if errors:
            st.error("Not saved. Please fix:")
            for e in errors:
                st.markdown(f"- {e}")
            return
        settings.save_profile(new)
        st.session_state["in_sig"] = (paths.workspace(), json.dumps(settings.load_profile(), sort_keys=True, default=str))
        for w in warns:
            st.warning(w)
        missing = settings.missing_fields(new)
        st.success("Inputs saved." + (f" Still needed to run the pipeline: {', '.join(missing)}." if missing else " You can now run the pipeline from the Command Center.")
                   + (" (Saved in the sample workspace only.)" if paths.is_sample() else ""))
        if persona != p["persona"]:
            st.session_state["in_flash"] = "Inputs saved. You changed path, so the sidebar tabs now match it. Rebuild from the Command Center to refresh drafts and the calendar for the new path."
            st.rerun()
