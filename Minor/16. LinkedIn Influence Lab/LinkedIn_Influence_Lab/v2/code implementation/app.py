"""LinkedIn Influence Lab: Streamlit entry point.  Run with:  streamlit run app.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import streamlit as st  # noqa: E402

from lil import paths, persona_content, samples, settings, theme  # noqa: E402
from lil.ui import (access, command_center, common, deliverables_page, docs_help, hub_job_seeker, hub_professional,  # noqa: E402
                    hub_thought_leader, inputs, persona_lab, phase1, phase2, phase3, phase4, phase5, plugins_page)

st.set_page_config(page_title="LinkedIn Influence Lab", page_icon="🚀", layout="wide")
theme.inject()

RENDER = {"command": command_center.render, "inputs": inputs.render, "plugins": plugins_page.render, "phase1": phase1.render,
          "phase2": phase2.render, "phase3": phase3.render, "phase4": phase4.render, "phase5": phase5.render,
          "hub_professional": hub_professional.render, "hub_job_seeker": hub_job_seeker.render, "hub_thought_leader": hub_thought_leader.render,
          "persona": persona_lab.render, "deliverables": deliverables_page.render, "docs": docs_help.render}

st.session_state.setdefault("workspace", "sample")  # first launch opens the sample workspace so every page has data


def _workspace_of_this_session():
    """Each browser session has its own workspace choice; outside a script run (no session) report nothing."""
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    return st.session_state.get("workspace", "sample") if get_script_run_ctx() else None


paths.set_resolver(_workspace_of_this_session)

with st.sidebar:
    st.markdown("## 🚀 Influence Lab")
    st.caption("AI-guided LinkedIn branding · LIL-2025-P1")
    ws = st.radio("Workspace", ["sample", "mine"], key="workspace", format_func=lambda k: "🧪 Sample data" if k == "sample" else "👤 My workspace",
                  help="Sample data is a complete fictional example. My workspace starts empty and holds only your own data.")
    if st.session_state.get("_ws_seen") != ws:
        common.clear_widget_state()
        st.session_state["_ws_seen"] = ws
    if ws == "sample" and not samples.is_seeded():
        with st.spinner("Preparing the sample workspace (about 5 seconds, once)..."):
            samples.ensure_seeded()
    profile = settings.load_profile()
    persona = profile["persona"]
    keys = persona_content.nav_keys(persona)
    labels = {persona_content.PAGES[k]: k for k in keys}
    if st.session_state.get("nav") not in labels:
        st.session_state["nav"] = persona_content.PAGES["command"]
    page = st.radio("Navigate", list(labels), key="nav", label_visibility="collapsed")
    st.markdown(f"<small>Path: <b>{common.persona_label(persona)}</b><br>Tabs shown are the ones this path needs.</small>", unsafe_allow_html=True)
    st.divider()
    access.render()
    st.divider()
    st.caption("Flow: Inputs → ChatGPT/AI → Taplio → LinkedIn → Analytics → back to Inputs")

common.sample_banner()
RENDER[labels[page]]()
