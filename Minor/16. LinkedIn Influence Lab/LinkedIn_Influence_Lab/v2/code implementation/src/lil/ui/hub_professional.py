from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from .. import analytics, hubs, pipeline, theme
from ..compat import WIDE
from . import common


def render():
    profile = common.get_profile()
    theme.hero("Consistency Hub", "Working-professional toolkit: stay consistent and build visibility through steady posting and peer engagement.", "#4F46E5", "#047857", "🔁")
    if profile["persona"] != "professional":
        st.warning("This hub belongs to the Working Professional path.")
        return
    cal, eng = pipeline.load_calendar(), analytics.load_engagement()
    t1, t2 = st.tabs(["📆 Consistency dashboard", "🤝 Peer engagement planner"])
    with t1:
        if not cal:
            common.empty_state("The consistency dashboard needs the Phase 3 calendar", ["Run Phases 2 and 3, then log posts in Phase 4.", "Switch the sidebar to 🧪 Sample data to see a complete example."])
        else:
            c = hubs.consistency(cal, eng)
            theme.kpi_row([("Current streak (posts in a row)", c["streak"], "#047857"), ("Longest gap between posts (days)", c["longest_gap"], "#C2410C"),
                           ("Posts due so far", c["due"], "#6D28D9"), ("Consistency", "n/a" if c["rate"] is None else f"{c['rate']}%", "#BE185D")])
            wk = c["weeks"].melt(id_vars="week", value_vars=["planned", "logged"], var_name="type", value_name="posts")
            fig = px.bar(wk, x="week", y="posts", color="type", barmode="group", title="Planned vs logged posts by week",
                         color_discrete_map={"planned": "#C7BDF0", "logged": "#047857"})
            st.plotly_chart(theme.plotly_style(fig, 320), **WIDE)
            st.caption("Streak counts consecutive due posts you have logged, newest first. A gap longer than a week is the usual sign of drop-off: use the .ics reminders and the Taplio queue.")
    with t2:
        st.markdown("**Goal: 5 thoughtful comments a day on other people's posts.** Consistent peer visibility lifts your own reach over time.")
        day = st.date_input("Plan for", date.today(), key="peer_day")
        for i, item in enumerate(hubs.daily_peer_plan(profile, day), 1):
            theme.step_card(f"{i}. {item['peer']}", theme.esc(item["starter"]), "#4F46E5")
        st.markdown("**Log today's engagement**")
        with st.form("peer_form"):
            c1, c2, c3 = st.columns(3)
            d = c1.date_input("Date", date.today(), key="peer_log_date")
            n = c2.number_input("Comments you made", 0, 200, 5, help="Whole number >= 0.")
            r = c3.number_input("Replies to your own post within 2 hours", 0, 200, 0, help="Whole number >= 0.")
            note = st.text_input("Note (optional)", max_chars=160)
            if st.form_submit_button("Save to peer log"):
                log = hubs.load_table("peer_log.csv", hubs.PEER_COLS)
                log = pd.concat([log[log["date"] != d.isoformat()], pd.DataFrame([{"date": d.isoformat(), "comments_made": str(int(n)), "replies_within_2h": str(int(r)), "notes": note}])])
                hubs.save_table("peer_log.csv", log.sort_values("date"))
                st.rerun()
        log = hubs.load_table("peer_log.csv", hubs.PEER_COLS)
        if log.empty:
            common.empty_state("No peer engagement logged yet", ["Use the plan above, then save how many comments you wrote. Example: 5 comments, 3 replies within 2 hours."])
        else:
            nums = log.assign(comments_made=pd.to_numeric(log["comments_made"]), replies_within_2h=pd.to_numeric(log["replies_within_2h"]))
            theme.kpi_row([("Days logged", len(nums), "#4F46E5"), ("Comments made", int(nums["comments_made"].sum()), "#047857"),
                           ("Replies within 2h", int(nums["replies_within_2h"].sum()), "#BE185D")])
            st.dataframe(log.sort_values("date", ascending=False), hide_index=True, **WIDE)
