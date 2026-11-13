from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from .. import guidance, hubs, paths, pipeline, theme
from ..compat import WIDE
from . import common


def _cb_sample_jd():
    st.session_state["jd_text"] = (paths.sample_dir() / "sample_job_description.txt").read_text(encoding="utf-8")


def render():
    profile = common.get_profile()
    theme.hero("Recruiter Hub", "Job-seeker toolkit: match job descriptions, track opportunities and reply to recruiters with confidence.", "#BE185D", "#C2410C", "🎯")
    if profile["persona"] != "job_seeker":
        st.warning("This hub belongs to the Job Seeker path.")
        return
    t1, t2, t3 = st.tabs(["🔎 Job description matcher", "🗂️ Opportunity tracker", "✉️ Outreach templates"])
    with t1:
        st.caption("Paste a job description. The matcher lists its main keywords and shows where each one already appears in your skills, headline, About and drafts. Missing keywords are your edit list.")
        st.caption("What to paste: " + guidance.JD_GUIDE)
        st.button("Insert a sample job description", on_click=_cb_sample_jd)
        jd = st.text_area("Job description", key="jd_text", height=220, placeholder="Paste the whole posting (60+ words)")
        if jd and len(jd.split()) < 60:
            st.warning("That is quite short. Paste the full posting (at least 60 words) for a useful match.")
        elif jd:
            res = hubs.keyword_match(profile, jd, pipeline.load_drafts())
            theme.kpi_row([("Keyword match", f"{res['score']}%", "#BE185D"), ("Keywords checked", len(res["rows"]), "#6D28D9"), ("Missing", len(res["missing"]), "#C2410C")])
            st.dataframe(pd.DataFrame(res["rows"])[["keyword", "found_in"]].rename(columns={"keyword": "Keyword", "found_in": "Found in"}), hide_index=True, **WIDE)
            if res["missing"]:
                st.markdown("**Add these where they are true for you:** " + ", ".join(f"`{k}`" for k in res["missing"][:10]))
                st.caption("Best places: the Skills section (up to 3 pinned), the headline, one bullet in the About section, and a proof-of-work post.")
            else:
                st.success("Every keyword appears somewhere in your profile text.")
    with t2:
        st.caption("Track every opportunity from saved to offer. Edit cells directly, then save.")
        opp = hubs.load_table("opportunities.csv", hubs.OPP_COLS)
        if opp.empty:
            common.empty_state("No opportunities yet", ["Add a row: company, role, where you found it, stage, and your next step.",
                                                        "Example: Brightmart Retail | Business Intelligence Analyst | LinkedIn job post | Applied | Follow up Friday"])
            opp = pd.DataFrame([{"company": "", "role": "", "source": "", "stage": "Saved", "date_added": date.today().isoformat(), "next_step": "", "linked_post": "", "notes": ""}])
        edited = st.data_editor(opp, num_rows="dynamic", hide_index=True, key="opp_editor", **WIDE,
                                column_config={"stage": st.column_config.SelectboxColumn("Stage", options=hubs.OPP_STAGES, required=True),
                                               "company": st.column_config.TextColumn("Company", max_chars=80), "role": st.column_config.TextColumn("Role", max_chars=100),
                                               "date_added": st.column_config.TextColumn("Date added (YYYY-MM-DD)", max_chars=10),
                                               "linked_post": st.column_config.TextColumn("Linked post id (e.g. D03)", max_chars=6)})
        if st.button("Save opportunities"):
            clean = edited.fillna("")
            clean = clean[(clean["company"].str.strip() != "") | (clean["role"].str.strip() != "")]
            hubs.save_table("opportunities.csv", clean)
            st.success(f"Saved {len(clean)} opportunities.")
            st.rerun()
        saved = hubs.load_table("opportunities.csv", hubs.OPP_COLS)
        if not saved.empty:
            counts = saved["stage"].value_counts().reindex(hubs.OPP_STAGES).fillna(0).reset_index()
            counts.columns = ["stage", "count"]
            st.plotly_chart(theme.plotly_style(px.bar(counts, x="stage", y="count", title="Opportunities by stage", color_discrete_sequence=["#BE185D"]), 280), **WIDE)
    with t3:
        st.caption("Fill the [bracketed] parts, keep it short, and send from LinkedIn messages or email. Your own win and skills are already filled in.")
        for title, text in hubs.recruiter_templates(profile):
            with st.expander(title):
                st.code(text, language=None)
