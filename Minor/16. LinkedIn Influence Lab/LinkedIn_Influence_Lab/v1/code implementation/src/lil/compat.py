"""Streamlit renamed use_container_width=True to width="stretch". Pick whichever this install supports."""
import inspect

import streamlit as st


def _stretch_ok(fn) -> bool:
    try:
        p = inspect.signature(fn).parameters.get("width")
    except (TypeError, ValueError):
        return False
    s = str(p.annotation) if p is not None else ""
    return "stretch" in s or "Width" in s


_CHECK = [st.button, st.download_button, st.form_submit_button, st.dataframe, st.data_editor, st.plotly_chart]
WIDE = {"width": "stretch"} if all(_stretch_ok(f) for f in _CHECK) else {"use_container_width": True}
