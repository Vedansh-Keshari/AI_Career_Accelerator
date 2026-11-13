import pandas as pd
import streamlit as st

from .. import analytics, backup, charts, paths, persona_content, pipeline, plugins, settings, store, theme
from ..compat import WIDE
from ..knowledge import PERSONAS
from ..phase_spec import PHASE_SPEC
from . import common


def _acceptance(profile):
    drafts, cal = pipeline.load_drafts(), pipeline.load_calendar()
    ideas = (pipeline.load("phase2", "ideas.json", {}) or {}).get("ideas", [])
    real = analytics.load_engagement()
    tag = " (sample data)" if paths.is_sample() else ""
    return [
        ("15+ content ideas generated", len(ideas) >= 15, f"{len(ideas)} / 15"),
        ("10+ optimized post drafts", len(drafts) >= 10, f"{len(drafts)} / 10"),
        ("6-week content calendar delivered", len(cal) >= 10, f"{len(cal)} slots"),
        ("10+ posts published" + tag, len(real) >= 10, f"{len(real)} / 10"),
        ("Engagement logged for every published post", len(real) > 0 and real[["impressions", "likes", "comments", "shares"]].notna().all().all(), f"{len(real)} logged"),
        ("Performance review built" + tag, store.phase_state("phase5") == "done", store.get_status().get("phase5", {}).get("note", "not built")),
    ]


def _diagrams():
    out = {}
    for name, fn in (("workflow.png", charts.workflow_diagram), ("dependency.png", charts.dependency_diagram)):
        p = paths.state_dir() / name
        if not p.exists():
            fn(p)
        out[name] = p
    return out


def _run_single(key, profile, use_ai):
    ok, msg = pipeline.phase_ready(key)
    if not ok:
        st.session_state["run_msg"] = ("err", f"Phase {key[-1]} cannot run yet: {msg}")
        return
    try:
        {"phase1": lambda: pipeline.run_phase1(profile, use_ai), "phase2": lambda: pipeline.run_phase2(profile, use_ai),
         "phase3": lambda: pipeline.run_phase3(profile), "phase4": lambda: pipeline.run_phase4(profile),
         "phase5": lambda: pipeline.run_phase5(profile)}[key]()
        st.session_state["run_msg"] = ("ok", f"Phase {key[-1]} finished and was backed up. State: {theme.STATE_STYLE[store.phase_state(key)][1]}.")
    except Exception as exc:
        store.log(f"{key} failed: {exc}")
        st.session_state["run_msg"] = ("err", f"Phase {key[-1]} stopped: {exc}")


def render():
    profile = common.get_profile()
    persona = PERSONAS[profile["persona"]]
    theme.hero("LinkedIn Influence Lab", f"{persona['emoji']} {persona['label']} path"
               + (f" · {profile['name']}" if profile["name"] else "") + " · AI-guided personal branding, 6-week Phase 1",
               "#312E81", "#BE185D", "🚀")
    kind, msg = st.session_state.pop("run_msg", (None, None))
    if kind == "ok":
        st.success(msg)
    elif kind == "err":
        st.error(msg)
    status = store.get_status()
    cols = st.columns(5)
    for col, ph in zip(cols, paths.PHASES):
        state = status.get(ph["key"], {}).get("state", "not_started")
        color, label = theme.STATE_STYLE[state]
        with col:
            st.markdown(f'<div class="card" style="--c:{ph["color"]}"><h4>{ph["icon"]} Phase {ph["n"]}</h4>'
                        f'<b>{theme.esc(ph["title"])}</b><br><small>{ph["week"]}</small><br>{theme.chip(label, color)}</div>', unsafe_allow_html=True)
            note = status.get(ph["key"], {}).get("note")
            if note:
                st.caption(note)
    done = sum(1 for p in paths.PHASES if status.get(p["key"], {}).get("state") == "done")
    st.progress(done / 5, text=f"{done} of 5 phases complete")

    st.subheader("🧭 How the whole flow works")
    imgs = _diagrams()
    st.image(str(imgs["workflow.png"]), caption="The AI-guided loop this project automates. 'Automated' steps are done by the app; 'You' steps need a person.")
    st.markdown("**How the five phases connect.** Each phase writes files that the next phase reads. "
                "Solid arrows are hard requirements (the next phase refuses to run without them); the dashed arrow is a soft link.")
    st.image(str(imgs["dependency.png"]), caption="Phase dependencies and the feedback loop that starts the next cycle")
    tabs = st.tabs([f"{p['icon']} Phase {p['n']}" for p in paths.PHASES])
    for tab, ph in zip(tabs, paths.PHASES):
        spec = PHASE_SPEC[ph["key"]]
        ready, why = pipeline.phase_ready(ph["key"])
        with tab:
            st.markdown(f"#### {ph['title']} · {ph['week']}")
            st.caption(ph["goal"])
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**What it does**")
                for line in spec["does"]:
                    st.markdown(f"- {line}")
                st.markdown("**Needs**")
                for line in spec["needs"]:
                    st.markdown(f"- {line}")
                st.markdown(f"**Depends on:** {spec['dependency']}")
            with c2:
                st.markdown("**Produces**  \n" + "  \n".join(f"`{x}`" for x in spec["produces"]))
                st.markdown(f"**Hands on to the next step:** {spec['feeds']}")
                st.markdown(f"**Your part:** {spec['human']}")
                st.markdown(("✅ Ready to run now." if ready else f"⏳ Not ready: {why}"))

    st.subheader("⚡ Run the flow")
    common.ai_banner()
    miss = settings.missing_fields(profile)
    st.markdown("**Readiness check**")
    checks = [(not miss, "Required inputs complete" if not miss else "Missing inputs: " + ", ".join(miss) + " (🧾 Inputs & Onboarding)"),
              (True, f"AI engine: {'ChatGPT/Claude plugin' if plugins.is_enabled('ai_openai') or plugins.is_enabled('ai_anthropic') else 'built-in template engine'} (active: {settings.load_plugin_cfg()['active_ai']})"),
              ("export_taplio" in plugins.enabled_exports(), "Taplio export plugin is on" if "export_taplio" in plugins.enabled_exports() else "Taplio export plugin is off (🔌 Plugins)"),
              (True, "Workspace: " + ("🧪 sample data (safe to experiment)" if paths.is_sample() else "👤 your own data"))]
    for ok, text in checks:
        st.markdown(f"{'✅' if ok else '⚠️'} {text}")
    use_ai = st.checkbox("Use my AI plugin when one is connected", True)
    st.markdown("**When you press Run full pipeline:** Phase 1 audits and defines pillars, then Phase 2 builds ideas and drafts, then Phase 3 builds the calendar and Taplio files, "
                "then Phase 4 prepares tracking and marks logged posts as published, then Phase 5 analyses whatever is logged and rebuilds every deliverable. "
                "A backup is saved after each phase and a full snapshot at the end. It stops with a clear message if an input is missing.")
    if st.button("▶ Run full pipeline (Phases 1-5 + all deliverables)", disabled=bool(miss), **WIDE):
        bar = st.progress(0.0, text="Starting")
        try:
            res = pipeline.run_all(settings.load_profile(), use_ai=use_ai, progress=lambda f, m: bar.progress(min(f, 1.0), text=m))
            st.session_state["run_msg"] = ("ok", f"Done. {len(res['made'])} deliverable sets built; full snapshot saved as {res['snapshot']}.")
        except Exception as exc:
            store.log(f"pipeline failed: {exc}")
            st.session_state["run_msg"] = ("err", f"The pipeline stopped: {exc}")
        st.rerun()
    st.markdown("**Or run one phase at a time** (each button is disabled until its required earlier phase has run):")
    bcols = st.columns(5)
    for col, ph in zip(bcols, paths.PHASES):
        ready, why = pipeline.phase_ready(ph["key"])
        col.button(f"Run Phase {ph['n']}", key=f"single_{ph['key']}", disabled=not ready, help=why, on_click=_run_single, args=(ph["key"], profile, use_ai), **WIDE)

    run = pipeline.last_run()
    if run:
        st.subheader("🧾 Last full run")
        st.caption(f"Started {run['started']} · finished {run['finished']} · workspace: {run.get('workspace', 'mine')} · snapshot {run['snapshot']}")
        st.dataframe(pd.DataFrame([{"Phase": s["title"], "Seconds": s["seconds"], "Result": s["summary"], "State now": theme.STATE_STYLE[store.phase_state(s["phase"])][1]} for s in run["stages"]]),
                     hide_index=True, **WIDE)

    st.subheader("✅ Acceptance criteria tracker")
    for label, ok, detail in _acceptance(profile):
        st.markdown(f"{'🟢' if ok else '🟠'} **{label}** — {detail}")

    st.subheader("👉 What only you can do (the automation stops here on purpose)")
    drafts = pipeline.load_drafts()
    hub = persona_content.PAGES[persona_content.HUB[profile["persona"]]]
    steps = [("Fill in Inputs, stories and plugins", not settings.missing_fields(profile)),
             ("Review and personalise drafts, tick Human reviewed", bool(drafts) and all(d.get("human_reviewed") for d in drafts)),
             ("Schedule approved posts in Taplio (queue in deliverables/06_taplio_queue)", False),
             ("Publish and log likes, comments, shares, impressions in Phase 4", len(analytics.load_engagement()) >= 10),
             (f"Use {hub} for your path-specific routine", False),
             ("Apply the refined pillar mix in Phase 5, then rebuild and submit the deliverables", store.phase_state("phase5") == "done")]
    for text, ok in steps:
        st.markdown(f"{'✅' if ok else '⬜'} {text}")
    st.caption(f"Backups in this workspace: {len(backup.list_backups())}. Every phase run saves a zip in backups/.")
