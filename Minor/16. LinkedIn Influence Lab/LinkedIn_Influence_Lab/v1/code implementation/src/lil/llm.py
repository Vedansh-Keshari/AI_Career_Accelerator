"""Thin wrapper that calls whichever AI plugin is active, never raising into the UI."""
from __future__ import annotations

from . import plugins, settings, store
from .knowledge import SYSTEM_PROMPT

LAST_ERROR = {"message": ""}


def active_plugin() -> str:
    return settings.load_plugin_cfg().get("active_ai", "ai_offline")


def ai_enabled() -> bool:
    return active_plugin() != "ai_offline" and active_plugin() in plugins.discover()


def complete(prompt: str, system: str = SYSTEM_PROMPT) -> str | None:
    """Return the model's text, or None if offline mode / any failure (error kept in LAST_ERROR)."""
    LAST_ERROR["message"] = ""
    if not ai_enabled():
        return None
    pid = active_plugin()
    try:
        text = plugins.discover()[pid]["module"].complete(plugins.plugin_config(pid), system, prompt)
        return text or None
    except Exception as exc:  # network, auth, quota... the template engine takes over
        LAST_ERROR["message"] = f"{pid}: {exc}"
        store.log(f"AI call failed -> offline fallback ({pid}): {exc}")
        return None


def extract_json(text: str):
    """Pull the first JSON array/object out of a model reply (tolerates code fences)."""
    import json
    if not text:
        return None
    cleaned = text.replace("```json", "```").replace("```", "")
    for open_c, close_c in (("[", "]"), ("{", "}")):
        a, b = cleaned.find(open_c), cleaned.rfind(close_c)
        if a != -1 and b > a:
            try:
                return json.loads(cleaned[a:b + 1])
            except json.JSONDecodeError:
                continue
    return None
