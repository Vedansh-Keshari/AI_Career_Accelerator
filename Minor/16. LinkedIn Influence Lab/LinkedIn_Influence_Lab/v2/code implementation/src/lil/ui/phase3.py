import pandas as pd
import streamlit as st

from ..compat import WIDE

from .. import paths, pipeline, plugins, theme
from ..knowledge import FORMATS, PILLARS, WEEKDAYS
from . import common


def _grid(cal):
    weeks = sorted({r["week"] for r in cal})
    head = "".join(f"<th>{d[:3]}</th>" for d in WEEKDAYS)
    rows = ""
    for w in weeks:
        cells = ""
        for d in WEEKDAYS:
            hit = next((r for r in cal if r["week"] == w and r["weekday"] == d), None)
            if hit:
                col = PILLARS[hit["pillar"]]["color"]
                tag = " ⭐" if hit["is_pilot"] else ""
                cells += (f'<td style="background:{col}22;border-top:4px solid {col}"><b>{theme.esc(hit["date"][5:])}{tag}</b><br>'
                          f'{theme.esc(PILLARS[hit["pillar"]]["label"])}<br>{FORMATS[hit["format"]]["emoji"]} {theme.esc(FORMATS[hit["format"]]["label"])}'
                          f'<br>{"✅" if hit["human_reviewed"] else "📝"} {theme.esc(hit["status"])}</td>')
            else:
                cells += "<td></td>"
        rows += f"<tr><th>W{w}</th>{cells}</tr>"
    return f'<table class="cal"><tr><th></th>{head}</tr>{rows}</table>'


def render():
    profile = common.get_profile()
    theme.hero("Phase 3 · Calendar & Taplio Setup", "Week 3: a 6-week calendar plus a Taplio-ready queue you can schedule from.", "#EC4899", "#F97316", "📅")
    common.need_profile(profile)
    if not pipeline.load_drafts():
        common.empty_state("Phase 3 needs Phase 2 first", ["Phase 2 creates the slot plan and drafts that this phase turns into a calendar.",
                                                           "Go to 💡 Phase 2 and press Run Phase 2 (or run both from the Command Center)."])
        return
    if st.button("▶ Run Phase 3 (build calendar + export files)", **WIDE):
        pipeline.run_phase3(profile)
        st.success("Calendar built, files exported, phase backed up.")
    cal = pipeline.load_calendar()
    if not cal:
        common.empty_state("Phase 3 has not run yet", ["Press Run Phase 3 above to merge your slots and drafts into the 6-week calendar and Taplio files."])
        return
    st.markdown(theme.chip("⭐ = pilot post", "#F59E0B") + theme.chip("✅ reviewed", "#10B981") + theme.chip("📝 needs review", "#6B7280"), unsafe_allow_html=True)
    st.markdown(_grid(cal), unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["📋 Schedule table", "📤 Taplio queue", "🧭 Taplio setup steps"])
    with t1:
        df = pd.DataFrame([{"Draft": r["draft_id"], "Date": r["date"], "Day": r["weekday"], "Time": r["time"], "Pillar": r["pillar_label"],
                            "Format": r["format"], "Pilot": r["is_pilot"], "Quality": r["quality"], "Reviewed": r["human_reviewed"],
                            "Status": r["status"]} for r in cal])
        edited = st.data_editor(df, hide_index=True, **WIDE, disabled=[c for c in df.columns if c != "Status"],
                                column_config={"Status": st.column_config.SelectboxColumn(options=["Planned", "Published", "Skipped", "Rescheduled"])})
        if st.button("Save status changes"):
            for r, s in zip(cal, edited["Status"]):
                r["status"] = s
            pipeline.save("phase3", "calendar.json", cal)
            st.success("Statuses saved.")
    with t2:
        approved = sum(1 for r in cal if r["human_reviewed"])
        st.write(f"**{approved} of {len(cal)}** posts are human-reviewed. Only those go in the approved-only queue.")
        tdir = paths.deliverable_dir("taplio")
        for f in sorted(tdir.glob("*")):
            common.download(f)
        for f in sorted(paths.deliverable_dir("calendar").glob("*")):
            common.download(f)
        st.markdown("**What each file is for**")
        common.guide_table([("taplio_queue_approved_only.csv", "Only posts you ticked Human reviewed. Schedule these.", "CSV: date, time, text, notes"),
                            ("taplio_queue_all_needs_review.csv", "Every post with a Reviewed column (Y/N). Use while editing.", "CSV"),
                            ("copy_paste_pack.txt", "Each post as plain text to paste into Taplio's composer.", "Text"),
                            ("Content_Calendar_6_Weeks.xlsx", "The 6-week calendar with a week view and status drop-downs.", "Excel"),
                            ("calendar_for_google_sheets.csv", "Same calendar for Google Sheets (File > Import).", "CSV"),
                            ("linkedin_posting_reminders.ics", "Calendar reminders for every slot (Google, Outlook, Apple).", "iCalendar")],
                           ["File", "Purpose", "Format"])
        if "export_taplio" not in plugins.enabled_exports():
            st.warning("The Taplio export plugin is switched off on the 🔌 Plugins page.")
    with t3:
        st.markdown("""
1. Sign in to Taplio in your browser and connect your LinkedIn account (log-ins stay with Taplio, never in this app).
2. Open `copy_paste_pack.txt` or the approved-only CSV. Each post has its date, time and notes.
3. In Taplio's composer paste the text, choose the date/time, and schedule. Plans differ, so check what your tier allows (some features may be paid).
4. For polls and carousels, follow the **Notes** column: polls are created as native LinkedIn polls, carousels as a PDF you build in your design tool.
5. Import `linkedin_posting_reminders.ics` into your calendar so you have a nudge even if scheduling is manual.
6. After each post goes live, log its numbers in Phase 4.
""")
