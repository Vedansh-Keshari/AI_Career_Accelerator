import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ..compat import WIDE

from .. import pipeline, store, theme
from ..knowledge import PILLARS
from . import common


def render():
    profile = common.get_profile()
    theme.hero("Phase 1 · Foundation: Audit & Pillars", "Week 1: benchmark your profile, then lock the 3-5 pillars everything else hangs from.", "#7C3AED", "#4F46E5", "🧭")
    common.need_profile(profile)
    common.ai_banner()
    if st.button("▶ Run Phase 1", **WIDE):
        with st.spinner("Auditing and building pillars..."):
            pipeline.run_phase1(profile)
        st.success("Phase 1 complete and backed up.")
    a, pl = pipeline.load("phase1", "audit.json"), pipeline.load("phase1", "pillars.json")
    if not a:
        common.empty_state("Phase 1 has not run yet", ["Press Run Phase 1 above (needs name, role, industry, audience, goal, skills).",
                                                       "Optional but better: paste your current headline and About, and tick what your profile already has (Inputs > Current profile)."])
        return
    t4_label = {"professional": "🤝 Peers to engage", "job_seeker": "🎯 Recruiters & role models", "thought_leader": "🏛️ Authorities to learn from"}[profile["persona"]]
    t1, t2, t3, t4 = st.tabs(["📊 Audit score", "✍️ Headline & About", "🥧 Content pillars", t4_label])
    with t1:
        fig = go.Figure(go.Indicator(mode="gauge+number", value=a["total"], title={"text": a["band"]},
                                     gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#EC4899"},
                                            "steps": [{"range": [0, 40], "color": "#FEE2E2"}, {"range": [40, 60], "color": "#FEF3C7"},
                                                      {"range": [60, 80], "color": "#DBEAFE"}, {"range": [80, 100], "color": "#D1FAE5"}]}))
        theme.plotly_style(fig, 260)
        st.plotly_chart(fig, **WIDE)
        for i in a["items"]:
            st.markdown(f"{'✅' if i['ok'] else '🔧'} **{i['label']}** — {i['score']}/{i['points']}" + ("" if i["ok"] else f"  \n&nbsp;&nbsp;&nbsp;&nbsp;_Fix: {i['fix']}_"))
    with t2:
        st.markdown("**Current headline**")
        st.code(a["current_headline"] or "(not provided)", language=None)
        st.markdown("**Optimized options**")
        for h in a["headline_options"]:
            st.code(h, language=None)
        st.markdown(f"**About draft** · _{a['about_source']}_")
        edited = st.text_area("Edit the About draft (placeholders in [brackets] need your real examples)", a["about_draft"], height=260, key="about_edit")
        if st.button("Save About edits"):
            a["about_draft"] = edited
            pipeline.save("phase1", "audit.json", a)
            st.success("Saved. It will appear in the Branding Audit Report next time you build deliverables.")
    with t3:
        pills = pl["pillars"]
        fig = px.pie(names=[p["label"] for p in pills], values=[p["weight"] for p in pills], hole=.55,
                     color=[p["label"] for p in pills], color_discrete_map={PILLARS[p["key"]]["label"]: PILLARS[p["key"]]["color"] for p in pills})
        theme.plotly_style(fig, 300)
        c1, c2 = st.columns([1, 2])
        c1.plotly_chart(fig, **WIDE)
        with c2:
            for p in pills:
                theme.card(f"{PILLARS[p['key']]['emoji']} {p['label']} · {round(p['weight'] * 100)}% · {p['posts']} posts", p["desc"],
                           PILLARS[p["key"]]["color"], "e.g. " + p["examples"][0])
    with t4:
        if a["role_models"]:
            for r in a["role_models"]:
                theme.card(r["name"], r["learn"], "#0EA5E9", r["url"])
        else:
            common.empty_state("No role models yet", ["Inputs > Role models: one per line as Name | profile URL | what you admire.",
                                                      "Example: Jane Doe | https://www.linkedin.com/in/jane-doe | clear weekly carousels"])
