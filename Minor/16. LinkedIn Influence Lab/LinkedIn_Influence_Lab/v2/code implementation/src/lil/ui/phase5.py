import plotly.express as px
import streamlit as st

from .. import context, hubs, paths, pipeline, settings, theme
from ..compat import WIDE
from ..knowledge import FORMATS, PERSONAS, PILLARS
from . import common


def render():
    profile = common.get_profile()
    theme.hero("Phase 5 · Analytics & Review", "Week 6: see what worked, refine the strategy, and generate the review. Everything below is live.", "#047857", "#0369A1", "📈")
    common.need_profile(profile)
    res = pipeline.analyse(profile)
    m = res["metrics"]
    if res["demo"] and paths.is_sample():
        st.info("Sample data: these figures belong to the fictional sample person.")
    if m.get("empty"):
        common.empty_state("Phase 5 needs logged engagement (Phase 4)", ["Log at least one post's impressions, likes, comments and shares in 🚀 Phase 4.",
                                                                          "Nothing is estimated: without data this page stays empty on purpose.",
                                                                          "To see a complete example, switch the sidebar to 🧪 Sample data."])
        return
    theme.kpi_row([("Posts", m["posts"], "#6D28D9"), ("Impressions", f"{m['impressions']:,}", "#C2410C"), ("Likes", m["likes"], "#BE185D"),
                   ("Comments", m["comments"], "#0369A1"), ("Shares", m["shares"], "#047857"), ("Engagement", f"{m['rate']:.2f}%", "#4F46E5")])
    w = m["weekly"]
    c1, c2 = st.columns(2)
    c1.plotly_chart(theme.plotly_style(px.bar(w, x="week", y="impressions", title="Weekly impressions", color_discrete_sequence=["#A78BFA"]), 320), **WIDE)
    c2.plotly_chart(theme.plotly_style(px.line(w, x="week", y="rate", markers=True, title="Engagement rate % by week", color_discrete_sequence=["#BE185D"]), 320), **WIDE)
    bp, bf = m["by_pillar"].copy(), m["by_format"].copy()
    bp["Pillar"] = bp["pillar"].map(lambda k: PILLARS[k]["label"])
    bf["Format"] = bf["format"].map(lambda k: FORMATS[k]["label"])
    c3, c4 = st.columns(2)
    c3.plotly_chart(theme.plotly_style(px.bar(bp, x="rate", y="Pillar", orientation="h", title="Engagement rate % by pillar", color="pillar",
                                              color_discrete_map={k: v["color"] for k, v in PILLARS.items()}).update_layout(showlegend=False), 300), **WIDE)
    c4.plotly_chart(theme.plotly_style(px.bar(bf, x="rate", y="Format", orientation="h", title="Engagement rate % by format", color="format",
                                              color_discrete_map={k: v["color"] for k, v in FORMATS.items()}).update_layout(showlegend=False), 300), **WIDE)

    persona = PERSONAS[profile["persona"]]
    st.subheader(f"{persona['emoji']} {persona['label']} KPIs")
    prog = hubs.kpi_progress(profile)
    cols = st.columns(len(prog))
    for col, r in zip(cols, prog):
        col.metric(r["label"], f"{r['total']} / {r['target']}", f"{r['pct']}% of target")
        col.progress(r["pct"] / 100)
    if hubs.load_kpis().empty:
        st.caption("Log weekly path KPIs in 🚀 Phase 4 > Weekly path KPIs to fill this panel.")

    st.subheader("💡 Insights and next actions")
    for i in res["insights"]:
        theme.card(f"{i['icon']} {i['finding']}", i["action"], "#C2410C")
    st.subheader("🎯 Self-assessment (evaluation criteria)")
    sc = res["score"]
    for k, v in sc["parts"].items():
        st.progress(min(1.0, v["score"] / 100), text=f"{k} · weight {v['weight']}% · {v['score']}/100")
    st.markdown(f"**Overall: {sc['total']}/100**" + (" _(provisional: some criteria need more data)_" if sc["provisional"] else ""))

    st.subheader("🔁 Close the loop: pillar mix for the next 6 weeks")
    cur, new = context.effective_weights(profile), res["refined"]
    pcols = st.columns(2)
    pcols[0].plotly_chart(theme.plotly_style(px.pie(names=[PILLARS[k]["label"] for k in cur], values=list(cur.values()), hole=.55, title="Current mix",
                                                    color=[PILLARS[k]["label"] for k in cur], color_discrete_map={PILLARS[k]["label"]: PILLARS[k]["color"] for k in cur}), 300), **WIDE)
    pcols[1].plotly_chart(theme.plotly_style(px.pie(names=[PILLARS[k]["label"] for k in new], values=list(new.values()), hole=.55, title="Recommended mix",
                                                    color=[PILLARS[k]["label"] for k in new], color_discrete_map={PILLARS[k]["label"]: PILLARS[k]["color"] for k in new}), 300), **WIDE)
    st.caption("Best pillar +10 points, weakest -5. Applying it saves the mix to your inputs; the next Phase 2 run uses it for the new calendar.")
    b1, b2, b3 = st.columns(3)
    if b1.button("Apply recommended mix to my inputs"):
        prof = settings.load_profile()
        prof["custom_weights"] = new
        settings.save_profile(prof)
        st.success("Saved. Run Phase 2 again from the Command Center to start the next cycle with this mix.")
    if b2.button("Reset to the default mix"):
        prof = settings.load_profile()
        prof.pop("custom_weights", None)
        settings.save_profile(prof)
        st.success("Default mix restored.")
    if b3.button("💾 Save this analysis and rebuild deliverables"):
        with st.spinner("Writing Phase 5 files, reports and a backup..."):
            made = pipeline.build_deliverables(profile)
        st.success(f"Saved. Rebuilt: {', '.join(made)}. Download them in 📦 Deliverables & Backups.")
