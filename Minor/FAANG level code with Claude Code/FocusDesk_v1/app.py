"""FocusDesk - a simple Streamlit productivity app: tasks, focus sessions, insights."""
from datetime import date

import pandas as pd
import streamlit as st

import logic
import storage

st.set_page_config(page_title="FocusDesk", page_icon="🎯", layout="wide")

PRIORITY_ICON = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}

if "data" not in st.session_state:
    st.session_state.data = storage.load()
data = st.session_state.data


def persist() -> None:
    storage.save(st.session_state.data)


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


# ---------- header ----------
st.title("🎯 FocusDesk")
st.caption("Plan your tasks, log focused work, and see your week at a glance. Data is saved locally.")

s = logic.summary(data)
m1, m2, m3, m4 = st.columns(4)
m1.metric("Open tasks", s["open"])
m2.metric("Overdue", s["overdue"])
m3.metric("Done (7 days)", s["done_week"])
m4.metric("Focus (7 days)", logic.format_minutes(s["focus_week"]))

tab_tasks, tab_focus, tab_insights = st.tabs(["✅ Tasks", "⏱️ Focus log", "📈 Insights"])

# ---------- tasks tab ----------
with tab_tasks:
    with st.form("add_task", clear_on_submit=True):
        c1, c2, c3 = st.columns([4, 1.5, 1.5])
        title = c1.text_input("New task", placeholder="e.g. Finish project proposal")
        priority = c2.selectbox("Priority", logic.PRIORITIES, index=1)
        has_due = c3.checkbox("Set due date")
        due = c3.date_input("Due", value=date.today(), label_visibility="collapsed")
        submitted = st.form_submit_button("Add task", type="primary")
    if submitted:
        try:
            logic.add_task(data, title, priority, due if has_due else None)
            persist()
            st.rerun()
        except ValueError as e:
            st.error(str(e))

    f1, f2, f3 = st.columns([1.5, 2, 3])
    status = f1.radio("Show", ["Open", "Done", "All"], horizontal=True)
    prios = f2.multiselect("Priority filter", logic.PRIORITIES, default=logic.PRIORITIES)
    query = f3.text_input("Search", placeholder="Search tasks...")

    shown = logic.filter_tasks(data["tasks"], status, prios, query)
    if not shown:
        st.info("No tasks to show. Add one above to get started.")
    for t in shown:
        row = st.columns([0.6, 5, 1.6, 0.6, 0.6])
        if t["done"]:
            row[0].button("↩️", key=f"re_{t['id']}", help="Reopen", on_click=cb_reopen, args=(t["id"],))
            row[1].markdown(f"~~{t['title']}~~")
        else:
            row[0].button("✅", key=f"ok_{t['id']}", help="Mark done", on_click=cb_complete, args=(t["id"],))
            row[1].markdown(f"**{t['title']}**")
        label = f"{PRIORITY_ICON[t['priority']]} {t['priority']}"
        if t["due"]:
            label += f" · due {t['due']}"
            if logic.is_overdue(t):
                label += " ⚠️ overdue"
        row[2].caption(label)
        row[4].button("🗑️", key=f"del_{t['id']}", help="Delete", on_click=cb_delete_task, args=(t["id"],))

    if data["tasks"]:
        st.download_button("⬇️ Export tasks (CSV)", logic.tasks_to_csv(data["tasks"]),
                           file_name="focusdesk_tasks.csv", mime="text/csv")

# ---------- focus tab ----------
with tab_focus:
    open_tasks = [t for t in logic.sort_tasks(data["tasks"]) if not t["done"]]
    options = {"(no specific task)": None}
    options.update({f"{t['title']} [{t['id']}]": t["id"] for t in open_tasks})
    with st.form("add_session", clear_on_submit=True):
        c1, c2, c3 = st.columns([1.2, 3, 1.5])
        minutes = c1.number_input("Minutes", min_value=1, max_value=logic.MAX_SESSION_MINUTES, value=25, step=5)
        task_label = c2.selectbox("Worked on", list(options.keys()))
        day = c3.date_input("Date", value=date.today(), max_value=date.today())
        note = st.text_input("Note (optional)")
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
        r = st.columns([1.4, 1.2, 5, 0.6])
        r[0].write(ses["date"])
        r[1].write(logic.format_minutes(ses["minutes"]))
        detail = ses["task_title"] or "General focus"
        if ses["note"]:
            detail += f" — {ses['note']}"
        r[2].write(detail)
        r[3].button("🗑️", key=f"ds_{ses['id']}", help="Delete session", on_click=cb_delete_session, args=(ses["id"],))

# ---------- insights tab ----------
with tab_insights:
    st.subheader("Focus minutes, last 7 days")
    by_day = logic.focus_by_day(data)
    df = pd.DataFrame(by_day, columns=["Day", "Minutes"]).set_index("Day")
    if df["Minutes"].sum() == 0:
        st.info("Log focus sessions to see your weekly chart.")
    else:
        st.bar_chart(df)
    a, b = st.columns(2)
    a.metric("Total focus time", logic.format_minutes(s["focus_total"]))
    b.metric("Tasks completed (all time)", sum(1 for t in data["tasks"] if t["done"]))
