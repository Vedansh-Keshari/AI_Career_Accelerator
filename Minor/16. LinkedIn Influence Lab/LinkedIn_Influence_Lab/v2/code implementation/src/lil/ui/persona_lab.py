import pandas as pd
import streamlit as st

from .. import drafting, personas, persona_content as pc, samples, settings, theme
from ..compat import WIDE
from ..knowledge import FORMATS, PERSONAS, PILLARS
from . import common


def _switch(profile: dict, target: str) -> None:
    """My workspace: change path and keep the user's data. Sample workspace: load that path's sample."""
    if profile["persona"] == target:
        return
    from .. import paths
    if paths.is_sample():
        samples.seed(target)
    else:
        profile.update(persona=target, pillars=[], days=PERSONAS[target]["default_days"])
        profile.pop("custom_weights", None)
        profile.pop("kpi_targets", None)
        settings.save_profile(profile)
    common.clear_widget_state()


def render():
    profile = common.get_profile()
    theme.hero("Persona Lab", "Compare the three paths, preview what would change if you switch, and choose your first hook.", "#4F46E5", "#059669", "🎭")
    common.need_profile(profile)
    now = profile["persona"]
    t1, t2, t3, t4 = st.tabs(["🧭 Compare paths", "🔀 What changes if I switch", "🪝 Hook options", "⚖️ Benefits & setbacks"])
    with t1:
        rows = {r["key"]: r for r in personas.compare(profile)}
        cols = st.columns(3)
        for col, (key, r) in zip(cols, rows.items()):
            with col:
                theme.card(f"{r['emoji']} {r['label']}" + ("  (your path)" if key == now else ""), r["story"], r["color"], f"Goal: {r['goal']}")
                st.markdown(f"**Rhythm:** {r['days']} · {r['slots']} posts in 6 weeks")
                for k, v in r["mix"].items():
                    st.progress(int(v.rstrip("%")) / 100, text=f"{k} {v}")
                st.markdown(f"**Format rotation:** {r['formats']}")
                st.markdown(f"**Weekly KPIs:** {', '.join(f['label'] for f in pc.KPI_FIELDS[key])}")
                st.markdown(f"**Own tab:** {pc.PAGES[pc.HUB[key]]}")
                st.markdown("**Sample headline**")
                st.code(r["headline"], language=None)
    with t2:
        st.markdown("After all five phases, **each path is a different working setup**: its own extra tab, pillar mix, posting rhythm, call-to-action style, weekly KPIs and review focus. "
                    "Only the tabs and tools your path needs are shown; the other paths' tools are hidden.")
        target = st.selectbox("Preview switching to", [k for k in PERSONAS if k != now], format_func=common.persona_label, key="pl_target")
        st.dataframe(pd.DataFrame(personas.impact(profile, target)), hide_index=True, **WIDE)
        shown, hidden = pc.nav_keys(target), [k for k in pc.nav_keys(now) if k not in pc.nav_keys(target)]
        st.markdown("**Sidebar after switching:** " + " · ".join(pc.PAGES[k] for k in shown))
        if hidden:
            st.markdown("**Tabs that would disappear:** " + ", ".join(pc.PAGES[k] for k in hidden))
        st.markdown("**What stays the same:** your inputs and stories, the five phases and their order, the Taplio export, quality checks, backups and all deliverable types.")
        from .. import paths
        st.warning("Switching in the sample workspace loads that path's complete sample. Switching in your own workspace keeps your inputs, resets pillars and posting days to the new path's defaults, "
                   "and asks you to rebuild from the Command Center. A backup of your current state is not touched.") if not paths.is_sample() else \
            st.info("In the sample workspace, switching rebuilds the whole sample for that path (takes a few seconds).")
        if st.button(f"Switch to {PERSONAS[target]['label']}", key="pl_switch"):
            _switch(profile, target)
            st.rerun()
    with t3:
        who = st.selectbox("Choose hooks for", list(PERSONAS), index=list(PERSONAS).index(now), format_func=common.persona_label, key="pl_hook_persona")
        opts = personas.hook_options(profile, who)
        st.markdown("A hook is the first line of a post. Pick one, preview it as a full post, and pin the ones you like: pinned hooks are used first the next time ideas are generated.")
        pick = st.radio("First-hook options", range(len(opts)), format_func=lambda i: f"{PILLARS[opts[i]['pillar']]['emoji']} {PILLARS[opts[i]['pillar']]['label']}: {opts[i]['hook']}", key="pl_hook_pick")
        fmt = st.selectbox("Preview as", list(FORMATS), format_func=lambda k: f"{FORMATS[k]['emoji']} {FORMATS[k]['label']}", key="pl_hook_fmt")
        o = opts[pick]
        idea = {"id": "I00", "slot_id": None, "pillar": o["pillar"], "format": fmt, "hook": o["hook"], "angle": o["angle"]}
        draft = drafting.finalize(drafting.offline_draft({**profile, "persona": who}, idea, 1))
        st.markdown("**Preview**")
        st.text_area("Post preview (not saved)", draft["text"], height=260, key=f"pl_prev_{who}_{pick}_{fmt}", disabled=True)
        st.caption(f"Quality check: {draft['quality']}/100" + (" · " + " ".join(draft["issues"]) if draft["issues"] else ""))
        pins = profile.get("pinned_hooks", [])
        already = any(h["persona"] == who and h["hook"] == o["hook"] for h in pins)
        if st.button("📌 Pin this hook" if not already else "Already pinned", disabled=already, key="pl_pin"):
            profile["pinned_hooks"] = pins + [{"persona": who, "pillar": o["pillar"], "hook": o["hook"]}]
            settings.save_profile(profile)
            st.success("Pinned. Run Phase 2 again to use it. See 💡 Phase 2 > Pinned hooks.")
            st.rerun()
    with t4:
        cols = st.columns(3)
        for col, key in zip(cols, PERSONAS):
            with col:
                meta = PERSONAS[key]
                theme.card(f"{meta['emoji']} {meta['label']}" + ("  (your path)" if key == now else ""), meta["goal"], meta["color"])
                st.markdown("**Benefits**")
                for b in pc.BENEFITS[key]:
                    st.markdown(f"✅ {b}")
                st.markdown("**Setbacks**")
                for s_ in pc.SETBACKS[key]:
                    st.markdown(f"⚠️ {s_}")
