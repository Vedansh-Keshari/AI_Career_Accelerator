from datetime import date

import pandas as pd
import streamlit as st

from .. import hubs, pipeline, settings, store, theme
from ..compat import WIDE
from ..knowledge import FORMATS
from . import common


def render():
    profile = common.get_profile()
    theme.hero("Authority Studio", "Thought-leader toolkit: track inbound leads, plan series and turn carousel drafts into slide outlines.", "#C2410C", "#6D28D9", "🏛️")
    if profile["persona"] != "thought_leader":
        st.warning("This studio belongs to the Thought Leader / Entrepreneur path.")
        return
    t1, t2, t3 = st.tabs(["🎯 Lead & audience tracker", "🧵 Series planner", "🎠 Carousel studio"])
    with t1:
        st.caption("Log every inbound conversation and link it to the post that started it. That is how you learn which content builds a pipeline.")
        leads = hubs.load_table("leads.csv", hubs.LEAD_COLS)
        if leads.empty:
            common.empty_state("No leads logged yet", ["Add a row each time someone replies, DMs or emails about your work.",
                                                       "Example: 2026-11-18 | Sample Founder | BlueRiver Foods | Comment-to-DM | D04 | Call booked"])
            leads = pd.DataFrame([{"date": date.today().isoformat(), "who": "", "org": "", "lead_type": "Inbound DM", "source_post": "", "status": "New", "notes": ""}])
        edited = st.data_editor(leads, num_rows="dynamic", hide_index=True, key="lead_editor", **WIDE,
                                column_config={"lead_type": st.column_config.SelectboxColumn("Type", options=hubs.LEAD_TYPES, required=True),
                                               "status": st.column_config.SelectboxColumn("Status", options=hubs.LEAD_STATUS, required=True),
                                               "date": st.column_config.TextColumn("Date (YYYY-MM-DD)", max_chars=10),
                                               "source_post": st.column_config.TextColumn("Source post id (e.g. D04)", max_chars=6)})
        if st.button("Save leads"):
            clean = edited.fillna("")
            clean = clean[clean["who"].str.strip() != ""]
            hubs.save_table("leads.csv", clean)
            st.success(f"Saved {len(clean)} leads.")
            st.rerun()
        saved = hubs.load_table("leads.csv", hubs.LEAD_COLS)
        if not saved.empty:
            theme.kpi_row([("Leads", len(saved), "#C2410C"), ("Calls booked or later", int(saved["status"].isin(["Call booked", "Proposal", "Won"]).sum()), "#047857"),
                           ("Won", int((saved["status"] == "Won").sum()), "#6D28D9")])
            by_post = saved[saved["source_post"] != ""].groupby("source_post").size().sort_values(ascending=False)
            if len(by_post):
                st.markdown("**Posts that started the most conversations:** " + ", ".join(f"{k} ({v})" for k, v in by_post.head(3).items()))
    with t2:
        st.caption("A recognisable series builds a returning audience. Name it, give it a theme, and get episode hooks with a format for each.")
        cur = store.read_json(hubs.hub_dir() / "series.json", {}) or {}
        with st.form("series_form"):
            name = st.text_input("Series name", cur.get("name", ""), max_chars=60, placeholder="e.g. AI in Plain English")
            theme_txt = st.text_input("Theme", cur.get("theme", ""), max_chars=100, placeholder="e.g. AI adoption for mid-size companies")
            eps = st.slider("Episodes", 3, 6, int(cur.get("episodes", 5)))
            go = st.form_submit_button("Plan the series")
        if go:
            if len(name.strip()) < 3 or len(theme_txt.strip()) < 3:
                st.error("Give the series a name and a theme (3+ characters each).")
            else:
                store.write_json(hubs.hub_dir() / "series.json", {"name": name.strip(), "theme": theme_txt.strip(), "episodes": eps})
                st.rerun()
        if cur.get("name"):
            for ep in hubs.plan_series(profile, cur["name"], cur.get("theme", ""), int(cur.get("episodes", 5))):
                theme.step_card(f"Episode {ep['episode']} · {FORMATS[ep['format']]['emoji']} {FORMATS[ep['format']]['label']}", theme.esc(ep["hook"]), "#C2410C")
            st.caption("Pin an episode hook from 🎭 Persona Lab, or write it as a draft by hand.")
        else:
            common.empty_state("No series planned yet", ["Fill the form above. Example: name 'AI in Plain English', theme 'AI adoption for mid-size companies'."])
    with t3:
        drafts = [d for d in pipeline.load_drafts() if d.get("slides")]
        if not drafts:
            common.empty_state("No carousel drafts yet", ["Carousel drafts appear after Phase 2 for the Thought Leader path (about one in three posts).",
                                                          "Build each carousel as a PDF in your design tool using the slide outline."])
        else:
            pick = st.selectbox("Carousel draft", [d["id"] for d in drafts], format_func=lambda i: f"{i} · " + next(d["hook"] for d in drafts if d["id"] == i)[:70])
            d = next(x for x in drafts if x["id"] == pick)
            slides = []
            for n, s in enumerate(d["slides"], 1):
                c1, c2 = st.columns([1, 2])
                t = c1.text_input(f"Slide {n} title", s["title"], key=f"sl_t_{pick}_{n}", max_chars=80)
                b = c2.text_input(f"Slide {n} text", s["body"], key=f"sl_b_{pick}_{n}", max_chars=160)
                slides.append({"title": t, "body": b})
            if st.button("Save slide edits"):
                ds = pipeline.load_drafts()
                for x in ds:
                    if x["id"] == pick:
                        x["slides"] = slides
                pipeline.save_drafts(ds)
                st.success("Saved.")
            st.download_button("⬇ All carousel outlines (Markdown)", hubs.carousel_markdown(pipeline.load_drafts()), file_name="carousel_outlines.md", mime="text/markdown", key="dl_car_md")
            st.download_button("⬇ Slide table (CSV for Canva / PowerPoint)", pd.DataFrame(hubs.carousel_rows(pipeline.load_drafts())).to_csv(index=False), file_name="carousel_slides.csv", mime="text/csv", key="dl_car_csv")
