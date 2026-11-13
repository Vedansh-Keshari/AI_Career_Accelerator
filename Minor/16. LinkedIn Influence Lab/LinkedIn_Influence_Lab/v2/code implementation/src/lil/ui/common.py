"""Helpers shared by every page."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from .. import llm, paths, settings, theme
from ..compat import WIDE
from ..knowledge import PERSONAS

KEEP_KEYS = {"workspace", "nav", "role", "failed_logins", "locked_until", "run_msg"}


def get_profile() -> dict:
    return settings.load_profile()


def is_admin() -> bool:
    return st.session_state.get("role") == "admin"


def clear_widget_state() -> None:
    """Forget page widget values (draft text boxes, form fields...) after the data underneath changed
    (switching workspace, re-seeding the sample, restoring a backup)."""
    for k in [k for k in st.session_state if k not in KEEP_KEYS and not str(k).startswith("_")]:
        del st.session_state[k]


def sample_banner() -> None:
    if paths.is_sample():
        st.markdown('<div class="sample-bar">🧪 <b>Sample workspace</b>: a fictional person and illustrative figures so every step has data. '
                    'Nothing here is yours. Switch to <b>👤 My workspace</b> in the sidebar to enter your own data.</div>', unsafe_allow_html=True)


def need_profile(profile: dict) -> None:
    miss = settings.missing_fields(profile)
    if miss:
        st.warning("Please complete these inputs first (🧾 Inputs & Onboarding): " + ", ".join(miss))
        st.stop()


def ai_banner() -> None:
    if llm.ai_enabled():
        st.success(f"AI plugin active: **{llm.active_plugin()}**. If a call fails the template engine takes over, so the flow never breaks.")
    else:
        st.info("Using the built-in template engine (no API key needed). Connect ChatGPT or Claude on the 🔌 Plugins page for richer writing.")


def persona_label(key: str) -> str:
    p = PERSONAS[key]
    return f"{p['emoji']} {p['label']}"


def download(path: Path, label: str | None = None, key: str | None = None) -> None:
    path = Path(path)
    if not path.exists():
        return
    mime = {".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".csv": "text/csv", ".png": "image/png", ".md": "text/markdown", ".txt": "text/plain",
            ".ics": "text/calendar", ".zip": "application/zip"}.get(path.suffix, "application/octet-stream")
    st.download_button(label or f"⬇ {path.name}", path.read_bytes(), file_name=path.name, mime=mime,
                       key=key or f"dl_{path.parent.name}_{path.name}")


def guide_table(rows: list[tuple], columns: list[str]) -> None:
    st.dataframe(pd.DataFrame(rows, columns=columns), hide_index=True, **WIDE)


def empty_state(title: str, needs: list[str], note: str = "") -> None:
    """Shown instead of an empty table: says what this step needs and where to get it."""
    body = "<ul style='margin:.3rem 0 0 1rem'>" + "".join(f"<li>{theme.esc(n)}</li>" for n in needs) + "</ul>"
    theme.step_card(title, body + (f"<small>{theme.esc(note)}</small>" if note else ""), "#F59E0B")
