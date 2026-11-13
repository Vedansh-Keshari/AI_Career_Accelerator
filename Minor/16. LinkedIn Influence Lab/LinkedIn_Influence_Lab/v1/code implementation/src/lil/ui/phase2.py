import pandas as pd
import streamlit as st

from ..compat import WIDE

from .. import drafting, pipeline, quality, theme
from ..knowledge import FORMATS, PILLARS
from . import common


def _drafts():
    return pipeline.load_drafts()


def _update(draft_id, fn):
    ds = _drafts()
    for d in ds:
        if d["id"] == draft_id:
            fn(d, ds)
    pipeline.save_drafts(ds)


def _cb_regen(draft_id):
    profile = common.get_profile()
    ideas = (pipeline.load("phase2", "ideas.json", {}) or {}).get("ideas", [])
    bump = st.session_state.get(f"bump_{draft_id}", 1) + 1
    st.session_state[f"bump_{draft_id}"] = bump

    def fn(d, ds):
        new = drafting.regenerate(profile, d, ideas, bump=bump)
        new["human_reviewed"] = False
        d.clear(); d.update(new)
        st.session_state[f"txt_{draft_id}"] = new["text"]
        st.session_state[f"rev_{draft_id}"] = False
    _update(draft_id, fn)


def _cb_rewrite(draft_id):
    profile = common.get_profile()

    def fn(d, ds):
        text, note = drafting.rewrite_tone(profile, st.session_state.get(f"txt_{draft_id}", d["text"]))
        drafting.apply_edit(d, text)
        st.session_state[f"txt_{draft_id}"] = d["text"]
        st.session_state["note"] = note
    _update(draft_id, fn)


def _cb_save(draft_id):
    def fn(d, ds):
        drafting.apply_edit(d, st.session_state.get(f"txt_{draft_id}", d["text"]))
        d["human_reviewed"] = bool(st.session_state.get(f"rev_{draft_id}", d.get("human_reviewed")))
    _update(draft_id, fn)


def render():
    profile = common.get_profile()
    theme.hero("Phase 2 · AI Ideation & Drafting", "Week 2: 15+ ideas, 10+ polished drafts, 2-3 pilot posts. You review every word.", "#F97316", "#EC4899", "💡")
    common.need_profile(profile)
    common.ai_banner()
    if st.button("▶ Run Phase 2 (ideas + drafts)", **WIDE):
        for k in [k for k in st.session_state if str(k).startswith(("txt_", "rev_", "bump_"))]:
            del st.session_state[k]
        bar = st.progress(0.0, text="Generating ideas and drafting")
        out = pipeline.run_phase2(profile, progress=lambda f: bar.progress(min(f, 1.0), text="Drafting posts"))
        bar.empty()
        w = out["ideas"]["warning"]
        if w:
            st.warning(w)
        st.success(f"{len(out['ideas']['ideas'])} ideas and {len(out['drafts'])} drafts created. {out['needs_personalisation']} need your real examples.")
    res = pipeline.load("phase2", "ideas.json")
    drafts = _drafts()
    if not res:
        st.info("Press **Run Phase 2** to generate ideas and drafts.")
        return
    if st.session_state.get("note"):
        st.info(st.session_state.pop("note"))
    t1, t2, t3 = st.tabs([f"💡 Ideas ({len(res['ideas'])})", f"📝 Drafts ({len(drafts)})", "🧰 Templates B & C"])
    with t1:
        st.caption(f"Source: {res['source']}. The last 3 are reserve ideas without a calendar slot.")
        df = pd.DataFrame([{"ID": i["id"], "Pillar": PILLARS[i["pillar"]]["label"], "Format": FORMATS[i["format"]]["label"],
                            "Hook": i["hook"], "Angle": i["angle"], "Slot": i["slot_id"] or "reserve"} for i in res["ideas"]])
        st.dataframe(df, **WIDE, hide_index=True)
    with t2:
        pilot = set(pipeline.load("phase2", "pilot.json", []))
        f1, f2 = st.columns(2)
        fp = f1.multiselect("Filter pillar", list(PILLARS), format_func=lambda k: PILLARS[k]["label"])
        ff = f2.multiselect("Filter format", list(FORMATS), format_func=lambda k: FORMATS[k]["label"])
        approved = sum(1 for d in drafts if d.get("human_reviewed"))
        st.progress(approved / max(1, len(drafts)), text=f"{approved} of {len(drafts)} drafts human-reviewed")
        with st.expander("Approve everything at once"):
            sure = st.checkbox("I have read and edited every draft myself")
            if st.button("Mark all as human-reviewed", disabled=not sure):
                ds = _drafts()
                for d in ds:
                    d["human_reviewed"] = True
                    st.session_state[f"rev_{d['id']}"] = True
                pipeline.save_drafts(ds)
                st.rerun()
        for d in drafts:
            if (fp and d["pillar"] not in fp) or (ff and d["format"] not in ff):
                continue
            q = quality.grade(d["quality"])
            title = f"{'⭐ ' if d['id'] in pilot else ''}{d['id']} · {PILLARS[d['pillar']]['emoji']} {PILLARS[d['pillar']]['label']} · {FORMATS[d['format']]['emoji']} {FORMATS[d['format']]['label']} · {d['quality']}/100 ({q})"
            with st.expander(title):
                st.session_state.setdefault(f"txt_{d['id']}", d["text"])
                st.text_area("Post text", height=280, key=f"txt_{d['id']}")
                if d.get("poll"):
                    st.caption("📊 Poll: " + d["poll"]["question"] + " | " + " / ".join(d["poll"]["options"]))
                if d.get("slides"):
                    st.caption("🎠 Slides: " + " › ".join(s["title"] for s in d["slides"]))
                for issue in d["issues"]:
                    st.warning(issue)
                if not d["issues"]:
                    st.success("No issues found.")
                st.session_state.setdefault(f"rev_{d['id']}", bool(d.get("human_reviewed", False)))
                st.checkbox("✅ Human reviewed (I edited this in my own voice)", key=f"rev_{d['id']}")
                c1, c2, c3 = st.columns(3)
                c1.button("💾 Save & re-check", key=f"s_{d['id']}", on_click=_cb_save, args=(d["id"],))
                c2.button("🔄 Regenerate", key=f"r_{d['id']}", on_click=_cb_regen, args=(d["id"],))
                c3.button("🎙️ Rewrite tone (B)", key=f"w_{d['id']}", on_click=_cb_rewrite, args=(d["id"],))
    with t3:
        st.markdown("**Template C: summarise an article into a post with 3 takeaways.** Always credit the source.")
        article = st.text_area("Paste the article text", height=180, key="art_text")
        source = st.text_input("Source (author, publication or link)", key="art_src")
        if st.button("Summarise into a post"):
            if len(article.split()) < 40:
                st.error("Paste at least a few paragraphs of the article.")
            else:
                text, note = drafting.article_to_post(profile, article, source)
                st.info(note)
                st.text_area("Result (edit before using)", text, height=220, key="art_out")
                st.caption(f"Quality check: {quality.check(text)['score']}/100")
