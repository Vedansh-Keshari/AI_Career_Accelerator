import streamlit as st

from ..compat import WIDE

from .. import analytics, backup, charts, paths, pipeline, settings, store, theme
from ..knowledge import PERSONAS
from . import common


def _acceptance(profile):
    drafts, cal = pipeline.load_drafts(), pipeline.load_calendar()
    ideas = (pipeline.load("phase2", "ideas.json", {}) or {}).get("ideas", [])
    real = analytics.load_engagement()
    return [
        ("15+ content ideas generated", len(ideas) >= 15, f"{len(ideas)} / 15"),
        ("10+ optimized post drafts", len(drafts) >= 10, f"{len(drafts)} / 10"),
        ("6-week content calendar delivered", len(cal) >= 10, f"{len(cal)} slots"),
        ("10+ posts published (real)", len(real) >= 10, f"{len(real)} / 10"),
        ("Engagement logged for every published post", len(real) > 0 and real[["impressions", "likes", "comments", "shares"]].notna().all().all(), f"{len(real)} logged"),
        ("Performance review built from real data", store.phase_state("phase5") == "done", store.get_status().get("phase5", {}).get("note", "not built")),
    ]


def render():
    profile = common.get_profile()
    persona = PERSONAS[profile["persona"]]
    theme.hero("LinkedIn Influence Lab", f"{persona['emoji']} {persona['label']} path"
               + (f" · {profile['name']}" if profile["name"] else "") + " · AI-guided personal branding, 6-week Phase 1",
               "#4F46E5", "#EC4899", "🚀")
    kind, msg = st.session_state.pop("run_msg", (None, None))
    if kind == "ok":
        st.success(msg)
        st.balloons()
    elif kind == "err":
        st.error(msg)
    status = store.get_status()
    cols = st.columns(5)
    for col, ph in zip(cols, paths.PHASES):
        state = status.get(ph["key"], {}).get("state", "not_started")
        color, label = theme.STATE_STYLE[state]
        with col:
            st.markdown(f'<div class="card" style="--c:{ph["color"]}"><h4>{ph["icon"]} Phase {ph["n"]}</h4>'
                        f'<b>{theme.esc(ph["title"])}</b><br><small>{ph["week"]}</small><br>'
                        f'{theme.chip(label, color)}</div>', unsafe_allow_html=True)
            note = status.get(ph["key"], {}).get("note")
            if note:
                st.caption(note)
    done = sum(1 for p in paths.PHASES if status.get(p["key"], {}).get("state") == "done")
    st.progress(done / 5, text=f"{done} of 5 phases complete")

    img = paths.state_dir() / "workflow.png"
    if not img.exists():
        charts.workflow_diagram(img)
    st.image(str(img), caption="The AI-guided loop this project automates")

    st.subheader("⚡ Run the whole flow")
    common.ai_banner()
    miss = settings.missing_fields(profile)
    if miss:
        st.warning("Fill these in on 🧾 Inputs & Onboarding first: " + ", ".join(miss))
    c1, c2 = st.columns(2)
    use_ai = c1.checkbox("Use my AI plugin when one is connected", True)
    demo = c2.checkbox("Preview analytics with simulated demo data (clearly labelled)", False,
                       help="Real metrics only exist after you publish. Demo data lets you see the dashboard and report layout now.")
    if st.button("▶ Run full pipeline (Phases 1-5 + all deliverables)", disabled=bool(miss), **WIDE):
        bar = st.progress(0.0, text="Starting")
        try:
            res = pipeline.run_all(settings.load_profile(), use_ai=use_ai, demo=demo, progress=lambda f, m: bar.progress(min(f, 1.0), text=m))
            st.session_state["run_msg"] = ("ok", f"Done. {len(res['made'])} deliverable sets built; full snapshot saved as {res['snapshot']}.")
        except Exception as exc:  # shown to the user and logged
            store.log(f"pipeline failed: {exc}")
            st.session_state["run_msg"] = ("err", f"The pipeline stopped: {exc}")
        st.rerun()

    st.subheader("✅ Acceptance criteria tracker")
    for label, ok, detail in _acceptance(profile):
        st.markdown(f"{'🟢' if ok else '🟠'} **{label}** — {detail}")

    st.subheader("👉 What only you can do (the automation stops here on purpose)")
    drafts = pipeline.load_drafts()
    steps = [("Fill in Inputs, stories and plugins", not settings.missing_fields(profile)),
             ("Review and personalise drafts, tick Human reviewed", bool(drafts) and all(d.get("human_reviewed") for d in drafts)),
             ("Schedule approved posts in Taplio (queue in deliverables/06_taplio_queue)", False),
             ("Publish and log likes, comments, shares, impressions in Phase 4", len(analytics.load_engagement()) >= 10),
             ("Rebuild deliverables with real data and submit the capstone", store.phase_state("phase5") == "done")]
    for text, ok in steps:
        st.markdown(f"{'✅' if ok else '⬜'} {text}")
    st.caption(f"Backups so far: {len(backup.list_backups())} (every phase run saves a zip in backups/).")
