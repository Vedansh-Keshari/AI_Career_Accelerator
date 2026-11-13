from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from .. import analytics, guidance, hubs, paths, pipeline, settings, theme
from ..compat import WIDE
from ..knowledge import FORMATS, PILLARS
from ..persona_content import KPI_FIELDS
from ..plugins import import_analytics
from . import common


def _cb_example():
    ss = st.session_state
    ss.update(log_imp=1140, log_likes=52, log_comments=9, log_shares=3, log_vis=26, log_src="manual")


def _cb_kpi_example(persona):
    base = {"professional": (31, 14, 8), "job_seeker": (1, 2, 1), "thought_leader": (40, 1, 1)}[persona]
    st.session_state.update(kpi_a=base[0], kpi_b=base[1], kpi_c=base[2], kpi_notes="Example week")


def render():
    profile = common.get_profile()
    persona = profile["persona"]
    theme.hero("Phase 4 · Publish & Track", "Weeks 4-5: post consistently and log what happened. The dashboard below updates the moment you save.", "#0369A1", "#047857", "🚀")
    cal = pipeline.load_calendar()
    if not cal:
        common.empty_state("Phase 4 needs the Phase 3 calendar", ["The calendar supplies the post ids and dates you log numbers against.",
                                                                  "Run Phase 2 and Phase 3 first (🏠 Command Center > Run one phase at a time)."])
        return
    df = analytics.load_engagement()
    theme.kpi_row([("Posts logged", len(df), "#0369A1"), ("Target (min)", 10, "#6D28D9"), ("Planned slots", len(cal), "#C2410C"),
                   ("Impressions", f"{int(df['impressions'].sum()):,}" if not df.empty else 0, "#047857")])
    st.progress(min(1.0, len(df) / 10), text=f"{len(df)} of 10+ posts logged" + (" (sample data)" if paths.is_sample() else ""))
    t1, t2, t3, t4, t5 = st.tabs(["✍️ Log a post", "📥 Import CSV", "🧮 Weekly path KPIs", "📊 Live dashboard", "🗂️ Logged data"])
    with t1:
        with st.expander("What to enter (type and where to find it)"):
            common.guide_table(guidance.LOG_GUIDE, ["Field", "Type", "Where to find it", "Example"])
        by = {r["draft_id"]: r for r in cal}
        logged = set(df["post_id"])
        due = [k for k, r in by.items() if r["date"] <= date.today().isoformat() and k not in logged]
        pid = st.selectbox("Which post?", list(by), index=list(by).index(due[0]) if due else 0,
                           format_func=lambda k: f"{k} · {by[k]['date']} · {by[k]['pillar_label']} · {'logged' if k in logged else by[k]['status']}")
        st.button("Fill example numbers", on_click=_cb_example, help="Fills the form only; nothing is saved until you press Save.")
        with st.form("log_form"):
            c1, c2, c3 = st.columns(3)
            pub = c1.date_input("Published on", date.fromisoformat(by[pid]["date"]), help="The day the post went live.")
            imp = c2.number_input("Impressions", 0, 100_000_000, step=10, key="log_imp", help="Whole number >= 0. LinkedIn: post > View analytics > Impressions.")
            vis = c3.number_input("Profile visits", 0, 100_000_000, key="log_vis", help="Whole number >= 0.")
            l, co, sh = st.columns(3)
            likes = l.number_input("Likes / reactions", 0, 100_000_000, key="log_likes", help="All reaction types added together.")
            comments = co.number_input("Comments", 0, 100_000_000, key="log_comments", help="Comments on the post, not your replies.")
            shares = sh.number_input("Shares / reposts", 0, 100_000_000, key="log_shares", help="Reposts with and without a comment.")
            src = st.selectbox("Where did you read these numbers?", ["manual", "taplio", "linkedin"], key="log_src")
            ok = st.form_submit_button("Save engagement")
        if ok:
            eng = likes + comments + shares
            if imp == 0 and eng > 0:
                st.error("Impressions is 0 but there are likes, comments or shares. Impressions must be at least as large as their sum.")
            else:
                if imp and eng / imp > 0.3:
                    st.warning(f"Engagement rate is {eng / imp * 100:.0f}%, which is unusually high. Please double-check the numbers.")
                analytics.add_entry(pid, pub, imp, likes, comments, shares, vis, src)
                pipeline.mark_published()
                pipeline.run_phase4(profile)
                st.success(f"Saved for {pid}: engagement rate {eng / imp * 100:.2f}%." if imp else f"Saved for {pid}.")
                st.rerun()
    with t2:
        st.caption("Upload a Taplio or LinkedIn analytics export. Recognised columns:")
        common.guide_table(guidance.IMPORT_GUIDE, ["Column", "Type", "Notes"])
        c1, c2 = st.columns(2)
        tpl = paths.sample_dir() / "engagement_import_template.csv"
        sample = paths.sample_dir() / f"sample_engagement_{persona}.csv"
        if tpl.exists():
            c1.download_button("⬇ Blank template (CSV)", tpl.read_bytes(), file_name=tpl.name, mime="text/csv", key="dl_tpl")
        if sample.exists():
            c2.download_button("⬇ Example export (to see the format)", sample.read_bytes(), file_name=sample.name, mime="text/csv", key="dl_smp")
        up = st.file_uploader("CSV file", type="csv")
        if up is not None:
            try:
                raw = pd.read_csv(up)
                st.markdown("**Preview of what will be imported** (columns after mapping):")
                st.dataframe(import_analytics.map_columns(raw).head(8), hide_index=True, **WIDE)
                up.seek(0)
                if st.button("Import into the tracking sheet"):
                    merged, warns = analytics.import_csv(up, [r["draft_id"] for r in cal])
                    pipeline.mark_published()
                    pipeline.run_phase4(profile)
                    for w in warns:
                        st.warning(w)
                    st.success(f"Imported. {len(merged)} posts now logged.")
            except Exception as exc:
                st.error(f"Could not read that file: {exc}. It must be a CSV with a header row.")
    with t3:
        fields = KPI_FIELDS[persona]
        st.caption("Once a week, log the numbers that matter for your path. Whole numbers, 0 or more.")
        common.guide_table([(f["label"], "Whole number >= 0", f["help"], f["target"]) for f in fields], ["KPI", "Type", "How to count it", "Default 6-week target"])
        st.button("Fill example numbers", key="kpi_ex", on_click=_cb_kpi_example, args=(persona,))
        with st.form("kpi_form"):
            week = st.selectbox("Week", [1, 2, 3, 4, 5, 6], help="Week of the 6-week plan (1 = first posting week).")
            cs = st.columns(3)
            vals = [c.number_input(f["label"], 0, 1_000_000, key=f"kpi_{f['key']}", help=f["help"]) for c, f in zip(cs, fields)]
            notes = st.text_input("Notes (optional)", key="kpi_notes", max_chars=160)
            if st.form_submit_button("Save weekly KPIs"):
                hubs.save_kpi(week, *vals, notes)
                pipeline.run_phase4(profile)
                st.success(f"Week {week} saved.")
                st.rerun()
        prog = hubs.kpi_progress(profile)
        for r in prog:
            st.progress(r["pct"] / 100, text=f"{r['label']}: {r['total']} of {r['target']} ({r['pct']}%)")
        with st.expander("Change my 6-week targets"):
            cur = hubs.kpi_targets(profile)
            new = {f["key"]: st.number_input(f"Target: {f['label']}", 1, 1_000_000, int(cur[f["key"]]), key=f"tgt_{f['key']}") for f in fields}
            if st.button("Save targets"):
                prof = settings.load_profile()
                prof["kpi_targets"] = new
                settings.save_profile(prof)
                st.rerun()
        k = hubs.load_kpis()
        if not k.empty:
            st.dataframe(k.rename(columns={"a": fields[0]["label"], "b": fields[1]["label"], "c": fields[2]["label"]}), hide_index=True, **WIDE)
        else:
            common.empty_state("No weekly KPIs logged yet", ["Fill the form above once a week. Use 'Fill example numbers' to see how it looks."])
    with t4:
        res = pipeline.analyse(profile)
        m = res["metrics"]
        if m.get("empty"):
            common.empty_state("The dashboard fills as you log posts", ["Log your first post in the ✍️ tab, or import a CSV.",
                                                                         "Switch the sidebar to 🧪 Sample data to see a complete example."])
        else:
            st.caption("Live view: recalculated from your logged data on every visit. Phase 5 adds insights and saves the report.")
            theme.kpi_row([("Posts", m["posts"], "#6D28D9"), ("Impressions", f"{m['impressions']:,}", "#C2410C"), ("Likes", m["likes"], "#BE185D"),
                           ("Comments", m["comments"], "#0369A1"), ("Engagement", f"{m['rate']:.2f}%", "#047857")])
            w = m["weekly"]
            c1, c2 = st.columns(2)
            c1.plotly_chart(theme.plotly_style(px.bar(w, x="week", y="impressions", title="Weekly impressions"), 300), **WIDE)
            c2.plotly_chart(theme.plotly_style(px.line(w, x="week", y="rate", markers=True, title="Engagement rate % by week"), 300), **WIDE)
    with t5:
        if df.empty:
            common.empty_state("Nothing logged yet", ["Use the ✍️ tab or 📥 Import CSV. Your real numbers are stored in phases/phase_4_publish_track/engagement.csv."])
        else:
            st.dataframe(df, hide_index=True, **WIDE)
            drop = st.multiselect("Remove entries", list(df["post_id"]))
            if drop and st.button("Delete selected"):
                analytics.save_engagement(df[~df["post_id"].isin(drop)])
                st.rerun()
