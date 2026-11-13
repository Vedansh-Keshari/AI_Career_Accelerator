"""LinkedIn Influence Lab: Streamlit entry point.  Run with:  streamlit run app.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import streamlit as st  # noqa: E402

from lil import theme  # noqa: E402
from lil.ui import (command_center, deliverables_page, docs_help, inputs, persona_lab, phase1,  # noqa: E402
                    phase2, phase3, phase4, phase5, plugins_page)

st.set_page_config(page_title="LinkedIn Influence Lab", page_icon="🚀", layout="wide")
theme.inject()

PAGES = {
    "🏠 Command Center": command_center.render,
    "🧾 Inputs & Onboarding": inputs.render,
    "🔌 Plugins": plugins_page.render,
    "🧭 Phase 1 · Audit & Pillars": phase1.render,
    "💡 Phase 2 · Ideas & Drafts": phase2.render,
    "📅 Phase 3 · Calendar & Taplio": phase3.render,
    "🚀 Phase 4 · Publish & Track": phase4.render,
    "📈 Phase 5 · Analytics & Review": phase5.render,
    "🎭 Persona Lab": persona_lab.render,
    "📦 Deliverables & Backups": deliverables_page.render,
    "📚 Docs & Help": docs_help.render,
}

with st.sidebar:
    st.markdown("## 🚀 Influence Lab")
    st.caption("AI-guided LinkedIn branding · LIL-2025-P1")
    page = st.radio("Navigate", list(PAGES), label_visibility="collapsed", key="nav")
    st.divider()
    st.caption("Flow: Inputs → ChatGPT/AI → Taplio → LinkedIn → Analytics → back to Inputs")

PAGES[page]()
