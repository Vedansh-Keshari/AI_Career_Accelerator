import plotly.express as px
import streamlit as st

from ..compat import WIDE

from .. import pipeline, theme
from ..knowledge import FORMATS, PILLARS
from . import common


def render():
    profile = common.get_profile()
    theme.hero("Phase 5 · Analytics & Review", "Week 6: see what worked, refine the strategy, and generate the review.", "#10B981", "#0EA5E9", "📈")
    common.need_profile(profile)
    demo = st.checkbox("Preview with simulated demo data if I have no real data yet", False)
    if st.button("▶ Run analytics & review", **WIDE):
        res = pipeline.run_phase5(profile, demo=demo)
        st.session_state["p5"] = res
    res = st.session_state.get("p5")
    if not res:
        st.info("Press **Run analytics & review**.")
        return
    m = res["metrics"]
    if res["demo"]:
        st.error("DEMO DATA: these numbers are simulated for layout preview only.")
    if m.get("empty"):
        st.info("No engagement logged yet. Log your pilot posts in Phase 4, then run this again.")
        return
    theme.kpi_row([("Posts", m["posts"], "#7C3AED"), ("Impressions", f"{m['impressions']:,}", "#F97316"), ("Likes", m["likes"], "#EC4899"),
                   ("Comments", m["comments"], "#0EA5E9"), ("Shares", m["shares"], "#10B981"), ("Engagement", f"{m['rate']:.2f}%", "#6366F1")])
    c1, c2 = st.columns(2)
    w = m["weekly"]
    c1.plotly_chart(px.bar(w, x="week", y="impressions", title="Weekly impressions", color_discrete_sequence=["#A78BFA"]), **WIDE)
    c2.plotly_chart(px.line(w, x="week", y="rate", markers=True, title="Engagement rate % by week", color_discrete_sequence=["#EC4899"]), **WIDE)
    bp, bf = m["by_pillar"].copy(), m["by_format"].copy()
    bp["Pillar"] = bp["pillar"].map(lambda k: PILLARS[k]["label"])
    bf["Format"] = bf["format"].map(lambda k: FORMATS[k]["label"])
    c3, c4 = st.columns(2)
    c3.plotly_chart(px.bar(bp, x="rate", y="Pillar", orientation="h", title="By pillar", color="pillar",
                           color_discrete_map={k: v["color"] for k, v in PILLARS.items()}), **WIDE)
    c4.plotly_chart(px.bar(bf, x="rate", y="Format", orientation="h", title="By format", color="format",
                           color_discrete_map={k: v["color"] for k, v in FORMATS.items()}), **WIDE)
    st.subheader("💡 Insights and next actions")
    for i in res["insights"]:
        theme.card(f"{i['icon']} {i['finding']}", i["action"], "#F97316")
    st.subheader("🎯 Self-assessment (evaluation criteria)")
    sc = res["score"]
    for k, v in sc["parts"].items():
        st.progress(min(1.0, v["score"] / 100), text=f"{k} · weight {v['weight']}% · {v['score']}/100")
    st.markdown(f"**Overall: {sc['total']}/100**" + (" _(provisional: some criteria need more data)_" if sc["provisional"] else ""))
    st.subheader("🔁 Refined pillar mix for the next 6 weeks")
    st.plotly_chart(px.pie(names=[PILLARS[k]["label"] for k in res["refined"]], values=list(res["refined"].values()), hole=.5,
                           color=[PILLARS[k]["label"] for k in res["refined"]],
                           color_discrete_map={PILLARS[k]["label"]: PILLARS[k]["color"] for k in res["refined"]}), **WIDE)
