"""Plugin registry. Drop a new file into this folder that defines a PLUGIN dict and it
appears automatically on the Plugins page.

PLUGIN = {"id", "name", "category" (ai | export | import), "icon", "description",
          "fields": [{"key", "label", "type": text|password|select, "default", "help", "options"}]}
AI plugins implement   complete(cfg, system, prompt) -> str
Export plugins implement export(profile, calendar, drafts, out_dir) -> list[Path]
"""
from __future__ import annotations

import importlib
import pkgutil

from .. import settings


def discover() -> dict:
    found = {}
    for mod in pkgutil.iter_modules(__path__):
        if mod.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{mod.name}")
        meta = getattr(module, "PLUGIN", None)
        if meta:
            found[meta["id"]] = {"meta": meta, "module": module}
    return dict(sorted(found.items(), key=lambda kv: (kv[1]["meta"]["category"], kv[0])))


def plugin_config(plugin_id: str) -> dict:
    """Merged config: field defaults, then saved values."""
    reg = discover()
    meta = reg[plugin_id]["meta"]
    saved = settings.load_plugin_cfg()["plugins"].get(plugin_id, {})
    cfg = {f["key"]: f.get("default", "") for f in meta.get("fields", [])}
    cfg.update(saved.get("config", {}))
    return cfg


def is_enabled(plugin_id: str) -> bool:
    saved = settings.load_plugin_cfg()["plugins"].get(plugin_id)
    if saved is not None and "enabled" in saved:
        return bool(saved["enabled"])
    return bool(discover()[plugin_id]["meta"].get("default_enabled", False))


def enabled_exports() -> list[str]:
    return [pid for pid, p in discover().items() if p["meta"]["category"] == "export" and is_enabled(pid)]
