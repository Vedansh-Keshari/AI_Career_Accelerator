import streamlit as st

from .. import personas, settings, theme
from ..knowledge import PERSONAS
from . import common


def render():
    profile = common.get_profile()
    theme.hero("Persona Lab", "The brief names three users. Compare how the strategy changes for each, using your own details.", "#4F46E5", "#10B981", "🎭")
    common.need_profile(profile)
    rows = personas.compare(profile)
    cols = st.columns(3)
    for col, r in zip(cols, rows):
        with col:
            active = "  (your path)" if profile["persona"] == r["key"] else ""
            theme.card(f"{r['emoji']} {r['label']}{active}", r["story"], r["color"], f"Goal: {r['goal']}")
            st.markdown(f"**Rhythm:** {r['days']} · {r['slots']} posts in 6 weeks")
            st.markdown("**Pillar mix**")
            for k, v in r["mix"].items():
                st.progress(int(v.rstrip("%")) / 100, text=f"{k} {v}")
            st.markdown(f"**Format rotation:** {r['formats']}")
            st.markdown(f"**KPIs:** {', '.join(r['kpis'])}")
            st.markdown("**Sample headline**")
            st.code(r["headline"], language=None)
            st.markdown("**Sample first hook**")
            st.info(r["sample_hook"])
            if profile["persona"] != r["key"] and st.button(f"Switch my profile to {r['label']}", key=f"sw_{r['key']}"):
                profile.update(persona=r["key"], pillars=[], days=PERSONAS[r["key"]]["default_days"])
                settings.save_profile(profile)
                st.success("Switched. Re-run the pipeline from the Command Center to rebuild everything for this path.")
                st.rerun()
