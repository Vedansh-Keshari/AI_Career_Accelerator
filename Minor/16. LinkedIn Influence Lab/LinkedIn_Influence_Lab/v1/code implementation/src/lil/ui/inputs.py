import re
from datetime import date, time

import streamlit as st

from ..compat import WIDE

from .. import settings, theme
from ..knowledge import PERSONAS, PILLARS, TIMEZONES, TONES, WEEKDAYS
from ..paths import home
from ..store import read_json
from . import common

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _load_sample():
    sample = read_json(home() / "sample_data" / "sample_profile.json", {})
    if sample:
        settings.save_profile({**settings.default_profile(), **sample})
        st.success("Sample inputs loaded. Replace them with your own details.")
        st.rerun()


def render():
    theme.hero("Inputs & Onboarding", "Tell the lab who you are. Everything downstream is built from this page.", "#7C3AED", "#F97316", "🧾")
    p = settings.load_profile()
    left, right = st.columns([3, 1])
    left.caption("Never type passwords here. Taplio and LinkedIn log-ins stay in your browser; this app only needs IDs and (optional) API keys.")
    if right.button("Load sample inputs"):
        _load_sample()

    with st.form("inputs_form"):
        t1, t2, t3, t4, t5, t6, t7 = st.tabs(["🪪 You & IDs", "🎯 Role & goals", "🎨 Voice & pillars", "📖 Your stories",
                                              "🔍 Current profile", "🌟 Role models", "🗓️ Posting plan"])
        with t1:
            persona = st.selectbox("Which path are you on?", list(PERSONAS), index=list(PERSONAS).index(p["persona"]),
                                   format_func=common.persona_label)
            st.caption(PERSONAS[persona]["story"])
            reset = st.checkbox("Reset pillars and posting days to this path's recommended defaults")
            c1, c2 = st.columns(2)
            name = c1.text_input("Full name *", p["name"])
            email = c2.text_input("Email ID", p["email"])
            linkedin_url = c1.text_input("LinkedIn profile URL", p["linkedin_url"], placeholder="https://www.linkedin.com/in/your-name")
            taplio_account = c2.text_input("Taplio account (email or username)", p["taplio_account"])
            google_email = c1.text_input("Google account for Drive/Sheets sharing", p["google_email"])
        with t2:
            c1, c2 = st.columns(2)
            role = c1.text_input("Current role *", p["current_role"])
            company = c2.text_input("Company / organisation", p["company"])
            industry = c1.text_input("Industry / niche *", p["industry"])
            years = c2.text_input("Years of experience", p["years_experience"])
            skills = st.text_area("Key skills * (comma separated, most important first)", p["skills"])
            audience = c1.text_input("Target audience *", p["target_audience"], placeholder="e.g. early-career data analysts")
            goal = c2.text_input("Main goal *", p["goal"], placeholder="e.g. get noticed by hiring managers")
            target_roles = c1.text_input("Target roles (job seekers)", p["target_roles"])
            offer = c2.text_input("What you offer (founders / thought leaders)", p["offer"])
        with t3:
            tone = st.selectbox("Brand voice", TONES, index=TONES.index(p["tone"]) if p["tone"] in TONES else 0)
            default_pillars = p["pillars"] or [k for k, _ in sorted(PERSONAS[persona]["weights"].items(), key=lambda kv: -kv[1])[:4]]
            pillars = st.multiselect("Content pillars (choose 3-5)", list(PILLARS), default=default_pillars,
                                     format_func=lambda k: f"{PILLARS[k]['emoji']} {PILLARS[k]['label']}")
        with t4:
            st.caption("Real examples make posts sound like you. Anything left blank becomes a [placeholder] that the quality check flags.")
            win = st.text_area("A recent win", p["story_win"])
            mistake = st.text_area("A mistake you learned from", p["story_mistake"])
            lesson = st.text_area("A lesson you would tell your younger self", p["story_lesson"])
            achievements = st.text_area("Achievements with numbers (one per line)", p["achievements"])
        with t5:
            headline = st.text_input("Current LinkedIn headline", p["current_headline"])
            about = st.text_area("Current About section", p["current_about"], height=140)
            c1, c2, c3 = st.columns(3)
            followers = c1.number_input("Followers", 0, value=int(p["followers"] or 0))
            connections = c2.number_input("Connections", 0, value=int(p["connections"] or 0))
            ppm = c3.number_input("Posts per month right now", 0, value=int(p["posts_per_month_now"] or 0))
            vis_label = {"job_seeker": "Open to Work (recruiters only) is on", "thought_leader": "Creator mode / Follow button is on",
                         "professional": "Contact info and a call to action are set"}[persona]
            labels = {"photo": "Professional photo", "banner": "Banner states my value", "custom_url": "Custom profile URL",
                      "featured": "Featured section filled", "skills_15": "15+ skills, top 3 pinned", "recs_3": "3+ recommendations",
                      "experience_metrics": "Experience bullets have numbers", "visibility": vis_label}
            cols = st.columns(2)
            checks = {k: cols[i % 2].checkbox(lbl, bool(p["checks"].get(k))) for i, (k, lbl) in enumerate(labels.items())}
        with t6:
            st.caption("One per line: Name | profile URL | what you admire. Used for the benchmark in the audit.")
            role_models = st.text_area("Role models / competitors", p["role_models"], height=150)
        with t7:
            days = st.multiselect("Posting days (2-5)", WEEKDAYS, default=p["days"])
            hh, mm = (p["time"].split(":") + ["0"])[:2]
            when = st.time_input("Posting time", time(int(hh), int(mm)))
            tz = st.selectbox("Time zone", TIMEZONES, index=TIMEZONES.index(p["timezone"]) if p["timezone"] in TIMEZONES else 0)
            start = st.date_input("First posting date", date.fromisoformat(p["start_date"]))
        saved = st.form_submit_button("💾 Save inputs", **WIDE)

    if saved:
        errors, warns = [], []
        if not name.strip():
            errors.append("Full name is required.")
        if not 3 <= len(pillars) <= 5:
            errors.append("Choose between 3 and 5 content pillars.")
        if not 2 <= len(days) <= 5:
            errors.append("Choose between 2 and 5 posting days.")
        if email and not EMAIL.match(email):
            errors.append("That email address does not look right.")
        if linkedin_url and "linkedin.com/" not in linkedin_url:
            warns.append("The LinkedIn URL should contain linkedin.com/in/.")
        if errors:
            for e in errors:
                st.error(e)
            return
        new = {**p, "persona": persona, "name": name.strip(), "email": email.strip(), "linkedin_url": linkedin_url.strip(),
               "taplio_account": taplio_account.strip(), "google_email": google_email.strip(), "current_role": role.strip(),
               "company": company.strip(), "industry": industry.strip(), "years_experience": years.strip(), "skills": skills.strip(),
               "target_audience": audience.strip(), "goal": goal.strip(), "target_roles": target_roles.strip(), "offer": offer.strip(),
               "tone": tone, "pillars": [] if reset else pillars, "story_win": win.strip(), "story_mistake": mistake.strip(),
               "story_lesson": lesson.strip(), "achievements": achievements.strip(), "current_headline": headline.strip(),
               "current_about": about.strip(), "followers": int(followers), "connections": int(connections),
               "posts_per_month_now": int(ppm), "checks": checks, "role_models": role_models.strip(),
               "days": PERSONAS[persona]["default_days"] if reset else days, "time": when.strftime("%H:%M"),
               "timezone": tz, "start_date": start.isoformat()}
        settings.save_profile(new)
        for w in warns:
            st.warning(w)
        missing = settings.missing_fields(new)
        st.success("Inputs saved." + (f" Still needed to run the pipeline: {', '.join(missing)}." if missing else " You can now run the pipeline from the Command Center."))
