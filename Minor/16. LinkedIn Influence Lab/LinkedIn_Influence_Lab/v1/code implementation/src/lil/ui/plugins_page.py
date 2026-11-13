import streamlit as st

from ..compat import WIDE

from .. import llm, plugins, settings, theme


def render():
    theme.hero("Plugins", "Plug in the tools you use. Turn things on, add your keys, and the flow adapts.", "#0EA5E9", "#10B981", "🔌")
    reg, cfg = plugins.discover(), settings.load_plugin_cfg()
    st.caption("Keys are stored only in data/inputs/plugins.json on this computer. They are never written into backups or reports.")
    ai_ids = [pid for pid, p in reg.items() if p["meta"]["category"] == "ai"]
    with st.form("plugins_form"):
        active = st.radio("Active AI engine", ai_ids, index=ai_ids.index(cfg["active_ai"]) if cfg["active_ai"] in ai_ids else 0,
                          format_func=lambda i: f"{reg[i]['meta']['icon']} {reg[i]['meta']['name']}", horizontal=False)
        new = {"active_ai": active, "plugins": {}}
        for cat, title in (("ai", "AI engines"), ("export", "Exports (Phase 3)"), ("import", "Analytics importers (Phase 4)")):
            st.subheader(title)
            for pid, p in reg.items():
                meta = p["meta"]
                if meta["category"] != cat:
                    continue
                with st.expander(f"{meta['icon']} {meta['name']}"):
                    st.write(meta["description"])
                    enabled = True if cat == "ai" else st.toggle("Enabled", plugins.is_enabled(pid), key=f"en_{pid}")
                    values = {}
                    current = plugins.plugin_config(pid)
                    for f in meta.get("fields", []):
                        values[f["key"]] = st.text_input(f["label"], current.get(f["key"], ""), type="password" if f["type"] == "password" else "default",
                                                         help=f.get("help") or None, key=f"pl_{pid}_{f['key']}")
                    new["plugins"][pid] = {"enabled": bool(enabled), "config": values}
        saved = st.form_submit_button("💾 Save plugin settings", **WIDE)
    if saved:
        settings.save_plugin_cfg(new)
        st.success("Plugin settings saved.")
    if cfg["active_ai"] != "ai_offline" and st.button("🔎 Test the active AI connection"):
        with st.spinner("Asking the model..."):
            out = llm.complete("Reply with the single word OK.")
        if out:
            st.success(f"Connected. Model replied: {out[:80]}")
        else:
            st.error("Could not reach the AI: " + (llm.LAST_ERROR["message"] or "unknown error") + ". The template engine will be used instead.")
    st.info("Want another tool? Add a file to src/lil/plugins/ with a PLUGIN dict and it shows up here automatically (see docs/03).")
