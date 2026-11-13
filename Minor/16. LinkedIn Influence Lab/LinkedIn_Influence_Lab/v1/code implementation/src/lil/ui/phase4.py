from datetime import date

import pandas as pd
import streamlit as st

from ..compat import WIDE

from .. import analytics, pipeline, theme
from . import common


def render():
    profile = common.get_profile()
    theme.hero("Phase 4 · Publish & Track", "Weeks 4-5: post consistently and log what happened. Real numbers only; demo data is kept separate.", "#0EA5E9", "#10B981", "🚀")
    cal = pipeline.load_calendar()
    if not cal:
        st.info("Build the calendar in Phase 3 first.")
        return
    df = analytics.load_engagement()
    theme.kpi_row([("Posts logged", len(df), "#0EA5E9"), ("Target (min)", 10, "#7C3AED"), ("Planned slots", len(cal), "#F97316"),
                   ("Impressions", int(df["impressions"].sum()) if not df.empty else 0, "#10B981")])
    st.progress(min(1.0, len(df) / 10), text=f"{len(df)} of 10+ posts logged")
    t1, t2, t3, t4 = st.tabs(["✍️ Log a post", "📥 Import CSV", "🗂️ Logged data", "🧪 Demo data"])
    with t1:
        by = {r["draft_id"]: r for r in cal}
        pid = st.selectbox("Which post?", list(by), format_func=lambda k: f"{k} · {by[k]['date']} · {by[k]['pillar_label']} · {by[k]['status']}")
        with st.form("log_form"):
            c1, c2, c3 = st.columns(3)
            pub = c1.date_input("Published on", date.fromisoformat(by[pid]["date"]))
            imp = c2.number_input("Impressions", 0, step=10)
            vis = c3.number_input("Profile visits", 0)
            l, co, sh = st.columns(3)
            likes, comments, shares = l.number_input("Likes / reactions", 0), co.number_input("Comments", 0), sh.number_input("Shares / reposts", 0)
            src = st.selectbox("Where did you read these numbers?", ["manual", "taplio", "linkedin"])
            ok = st.form_submit_button("Save engagement", **WIDE)
        if ok:
            analytics.add_entry(pid, pub, imp, likes, comments, shares, vis, src)
            pipeline.mark_published()
            pipeline.run_phase4(profile)
            st.success(f"Saved for {pid}.")
            st.rerun()
    with t2:
        st.caption("Upload a Taplio or LinkedIn analytics export. Column names like Impressions, Reactions, Comments, Reposts and Profile views are recognised.")
        up = st.file_uploader("CSV file", type="csv")
        if up is not None and st.button("Import into the tracking sheet"):
            try:
                merged, warns = analytics.import_csv(up, [r["draft_id"] for r in cal])
                pipeline.mark_published()
                pipeline.run_phase4(profile)
                for w in warns:
                    st.warning(w)
                st.success(f"Imported. {len(merged)} posts now logged.")
            except Exception as exc:
                st.error(f"Could not read that file: {exc}")
    with t3:
        if df.empty:
            st.info("Nothing logged yet.")
        else:
            st.dataframe(df, **WIDE, hide_index=True)
            drop = st.multiselect("Remove entries", list(df["post_id"]))
            if drop and st.button("Delete selected"):
                analytics.save_engagement(df[~df["post_id"].isin(drop)])
                st.rerun()
    with t4:
        st.warning("Demo data is simulated. It exists only so you can preview the dashboard and reports before you have real numbers. It is never mixed into your real log.")
        c1, c2 = st.columns(2)
        if c1.button("Create demo data"):
            analytics.make_demo(cal)
            st.success("Demo data created. Tick 'demo' on the Phase 5 page to preview it.")
        if c2.button("Delete demo data"):
            analytics.engagement_path(True).unlink(missing_ok=True)
            st.success("Demo data removed.")
