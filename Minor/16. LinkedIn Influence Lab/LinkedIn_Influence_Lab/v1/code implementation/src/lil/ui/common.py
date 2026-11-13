"""Helpers shared by every page."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from .. import llm, settings
from ..knowledge import PERSONAS


def get_profile() -> dict:
    return settings.load_profile()


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
