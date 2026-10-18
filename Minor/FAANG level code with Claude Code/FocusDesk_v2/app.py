"""FocusDesk v2 - colourful Streamlit productivity app.

Email is required to enter. Tabs: Tasks, Focus log, Insights.
"""
from datetime import date

import pandas as pd
import streamlit as st

import logic
import sample_data
import storage
import theme

st.set_page_config(page_title="FocusDesk", page_icon="🎯", layout="wide")
st.markdown(theme.CSS, unsafe_allow_html=True)


# ---------- email gate (mandatory) ----------
def show_gate() -> None:
    st.markdown(theme.banner("🎯 FocusDesk", "Plan your tasks, log focused work, and see your week at a glance."),
                unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.subheader("🔐 Enter your email to continue")
        with st.form("email_gate"):
            email = st.text_input("Email address", key="gate_email", placeholder="you@example.com")
            go = st.form_submit_button("Enter FocusDesk", type="primary")
        if go:
            try:
                clean = logic.validate_email(email)
            except ValueError as e:
                st.error(str(e))
            else:
                st.session_state.user_email = clean
                st.session_state.data = storage.load(clean)
                st.rerun()
        st.caption("An email address is required to open the app. It is used only to keep your tasks "
                   "separate from other users on this computer and is never sent anywhere.")


if not st.session_state.get("user_email"):
    show_gate()
    st.stop()

email = st.session_state.user_email
if "data" not in st.session_state:
    st.session_state.data = storage.load(email)
data = st.session_state.data


def persist() -> None:
    storage.save(st.session_state.data, st.session_state.user_email)


# ---------- callbacks ----------
def cb_complete(task_id: str) -> None:
    logic.complete_task(st.session_state.data, task_id)
    persist()


def cb_reopen(task_id: str) -> None:
    logic.reopen_task(st.session_state.data, task_id)
    persist()


def cb_delete_task(task_id: str) -> None:
    logic.delete_task(st.session_state.data, task_id)
    persist()


def cb_delete_session(session_id: str) -> None:
    logic.delete_session(st.session_state.data, session_id)
    persist()


def cb_load_sample() -> None:
    sample_data.load_sample(st.session_state.data)
    persist()


def cb_remove_sample() -> None:
    sample_data.remove_sample(st.session_state.data)
    persist()


def cb_switch_user() -> None:
    for key in ("user_email", "data"):
        st.session_state.pop(key, None)


# ---------- sidebar ----------
with st.sidebar:
    st.markdown(theme.user_chip(email), unsafe_allow_html=True)
    st.button("🔄 Switch user", key="switch_user", on_click=cb_switch_user)
    st.divider()
    st.subheader("🧪 Try with sample data")
    st.caption("Adds model tasks and focus sessions (some overdue, some done) so you can explore every "
               "feature. Your own entries are never touched.")
    st.button("Load sample data", key="load_sample", on_click=cb_load_sample)
    st.button("Remove sample data", key="remove_sample", on_click=cb_remove_sample,
              disabled=not sample_data.has_sample(data))

# ---------- header + headline cards ----------
st.markdown(theme.banner("🎯 FocusDesk", "Plan your tasks, log focused work, and see your week at a glance."),
            unsafe_allow_html=True)
s = logic.summary(data)
c1, c2, c3, c4 = st.columns(4)
c1.markdown(theme.metric_card("Open tasks", s["open"], theme.CARD_BLUE, "📝"), unsafe_allow_html=True)
c2.markdown(theme.metric_card("Overdue", s["overdue"], theme.CARD_RED, "⏰"), unsafe_allow_html=True)
c3.markdown(theme.metric_card("Done (7 days)", s["done_week"], theme.CARD_GREEN, "✅"), unsafe_allow_html=True)
c4.markdown(theme.metric_card("Focus (7 days)", logic.format_minutes(s["focus_week"]), theme.CARD_ORANGE, "🔥"),
            unsafe_allow_html=True)

tab_tasks, tab_focus, tab_insights = st.tabs(["✅ Tasks", "⏱️ Focus log", "📈 Insights"])

# ---------- tasks tab ----------
with tab_tasks:
    with st.form("add_task", clear_on_submit=True):
        a, b, c = st.columns([4, 1.5, 1.5])
        title = a.text_input("New task", key="new_task_title", placeholder="e.g. Finish project proposal")
        priority = b.selectbox("Priority", logic.PRIORITIES, index=1, key="new_task_priority")
        has_due = c.checkbox("Set due date", key="new_task_has_due")
        due = c.date_input("Due", value=date.today(), label_visibility="collapsed", key="new_task_due")
        submitted = st.form_submit_button("Add task", type="primary")
    if submitted:
        try:
            logic.add_task(data, title, priority, due if has_due else None)
            persist()
            st.rerun()
        except ValueError as e:
            st.error(str(e))

    f1, f2, f3 = st.columns([1.5, 2, 3])
    status = f1.radio("Show", ["Open", "Done", "All"], horizontal=True, key="flt_status")
    prios = f2.multiselect("Priority filter", logic.PRIORITIES, default=logic.PRIORITIES, key="flt_prio")
    query = f3.text_input("Search", placeholder="Search tasks...", key="flt_query")

    shown = logic.filter_tasks(data["tasks"], status, prios, query)
    st.caption(f"Showing {len(shown)} of {len(data['tasks'])} tasks")
    if not shown:
        st.info("No tasks to show. Add one above, or load sample data from the sidebar.")
    for t in shown:
        col_btn, col_card, col_del = st.columns([0.7, 8, 0.7], vertical_alignment="center")
        if t["done"]:
            col_btn.button("↩️", key=f"re_{t['id']}", help="Reopen", on_click=cb_reopen, args=(t["id"],))
        else:
            col_btn.button("✅", key=f"ok_{t['id']}", help="Mark done", on_click=cb_complete, args=(t["id"],))
        col_card.markdown(theme.task_card(t, logic.is_overdue(t)), unsafe_allow_html=True)
        col_del.button("🗑️", key=f"del_{t['id']}", help="Delete", on_click=cb_delete_task, args=(t["id"],))

    if data["tasks"]:
        st.download_button("⬇️ Export tasks (CSV)", logic.tasks_to_csv(data["tasks"]),
                           file_name="focusdesk_tasks.csv", mime="text/csv", key="export_csv")

# ---------- focus tab ----------
with tab_focus:
    open_tasks = [t for t in logic.sort_tasks(data["tasks"]) if not t["done"]]
    options = {"(no specific task)": None}
    options.update({f"{t['title']} [{t['id']}]": t["id"] for t in open_tasks})
    with st.form("add_session", clear_on_submit=True):
        a, b, c = st.columns([1.2, 3, 1.5])
        minutes = a.number_input("Minutes", min_value=1, max_value=logic.MAX_SESSION_MINUTES, value=25,
                                 step=5, key="ses_minutes")
        task_label = b.selectbox("Worked on", list(options.keys()), key="ses_task")
        day = c.date_input("Date", value=date.today(), max_value=date.today(), key="ses_date")
        note = st.text_input("Note (optional)", key="ses_note")
        logged = st.form_submit_button("Log session", type="primary")
    if logged:
        try:
            logic.add_session(data, int(minutes), options[task_label], note, day)
            persist()
            st.rerun()
        except (ValueError, KeyError) as e:
            st.error(str(e))

    st.subheader("Recent sessions")
    sessions = sorted(data["sessions"], key=lambda x: x["date"], reverse=True)[:15]
    if not sessions:
        st.info("No sessions yet. Log your first focused block above.")
    for ses in sessions:
        col_card, col_del = st.columns([8.7, 0.7], vertical_alignment="center")
        col_card.markdown(theme.session_card(ses, logic.format_minutes(ses["minutes"])), unsafe_allow_html=True)
        col_del.button("🗑️", key=f"ds_{ses['id']}", help="Delete session", on_click=cb_delete_session,
                       args=(ses["id"],))

# ---------- insights tab ----------
with tab_insights:
    left, right = st.columns(2)
    with left:
        st.subheader("Focus minutes, last 7 days")
        by_day = logic.focus_by_day(data)
        df = pd.DataFrame(by_day, columns=["Day", "Minutes"]).set_index("Day")
        if df["Minutes"].sum() == 0:
            st.info("Log focus sessions to see your weekly chart.")
        else:
            st.bar_chart(df, color=theme.PURPLE)
    with right:
        st.subheader("Open tasks by priority")
        counts = logic.priority_counts(data)
        top = max(counts.values())
        if top == 0:
            st.info("No open tasks right now.")
        else:
            bars = "".join(theme.priority_bar(p, counts[p], top, theme.PRIORITY_STYLE[p][2])
                           for p in logic.PRIORITIES)
            st.markdown(f"<div>{bars}</div>", unsafe_allow_html=True)
    x, y = st.columns(2)
    x.markdown(theme.metric_card("Total focus time", logic.format_minutes(s["focus_total"]),
                                 theme.CARD_PURPLE, "⏱️"), unsafe_allow_html=True)
    y.markdown(theme.metric_card("Tasks completed (all time)", sum(1 for t in data["tasks"] if t["done"]),
                                 theme.CARD_TEAL, "🏆"), unsafe_allow_html=True)
