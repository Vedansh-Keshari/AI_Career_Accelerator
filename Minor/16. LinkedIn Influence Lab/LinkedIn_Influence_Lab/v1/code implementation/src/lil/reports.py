"""All Word / Excel deliverables. Each function writes into its own deliverables sub-folder."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from . import analytics, charts, docx_kit as dk
from .knowledge import FORMATS, PERSONAS, PILLARS

RISKS = [
    ("Low engagement", "Adjust posting time and content type", "Insights page flags rate < 2% and suggests hook / format / time tests."),
    ("Free-tier limits in Taplio", "Supplement with manual LinkedIn analytics", "Manual entry form and a flexible CSV importer for LinkedIn or Taplio exports."),
    ("Over-reliance on AI", "Ensure human review for authenticity", "Every draft has a Human reviewed gate; the approved-only Taplio queue excludes the rest."),
    ("Consistency drop-off", "Use scheduling to avoid gaps", "Taplio queue, .ics reminders and a consistency score on the dashboard."),
]
ETHICS = ["Avoid over-automation: nothing is queued as approved until you tick Human reviewed.",
          "Inclusive and neutral language: the quality checker flags non-inclusive terms and suggests replacements.",
          "Attribute sources: statistics or studies without a named source are flagged; Template C always adds a Source line."]


def _meta(profile, extra=""):
    return [f"Prepared for: {profile.get('name') or 'Author'}   |   Persona: {PERSONAS[profile.get('persona', 'professional')]['label']}",
            f"Project code LIL-2025-P1   |   Generated {date.today().isoformat()}" + extra]


# ---------------------------------------------------------------- audit ----
def build_audit_report(profile, audit, pillars, personas_rows, out_dir: Path) -> Path:
    d = dk.new_doc()
    dk.cover(d, "Branding Audit Report", "Current vs optimized LinkedIn profile and positioning", _meta(profile), "#4C1D95", "#F97316")
    dk.h(d, "1. Profile health score")
    dk.para(d, f"{audit['total']} / 100  -  {audit['band']}", bold=True, size=16, color="#DB2777")
    dk.table(d, ["Checklist item", "Points", "Score", "Status", "How to fix"],
             [[i["label"], i["points"], i["score"], "OK" if i["ok"] else "Gap", "" if i["ok"] else i["fix"]] for i in audit["items"]],
             "#7C3AED", widths=[2.1, .6, .6, .6, 3.0])
    dk.h(d, "2. Headline: current vs optimized")
    dk.table(d, ["", "Headline"], [["Current", audit["current_headline"] or "(not provided)"]] +
             [[f"Option {n}", h] for n, h in enumerate(audit["headline_options"], 1)], "#EC4899", "#FDF2F8", [1.0, 5.8])
    dk.h(d, "3. About section: optimized draft")
    dk.callout(d, f"Source: {audit['about_source']}. Replace every [bracketed placeholder] with a real example.")
    for line in audit["about_draft"].split("\n"):
        d.add_paragraph(line)
    dk.h(d, "4. Content pillars")
    dk.table(d, ["Pillar", "Share", "Posts / 6 wks", "What it covers", "Example topic"],
             [[p["label"], f"{round(p['weight'] * 100)}%", p["posts"], p["desc"], p["examples"][0]] for p in pillars["pillars"]],
             "#F97316", "#FFF7ED", [1.4, .6, .8, 2.0, 2.2])
    if audit["role_models"]:
        dk.h(d, "5. Role-model benchmark")
        dk.table(d, ["Role model", "Profile", "What to learn"], [[r["name"], r["url"], r["learn"]] for r in audit["role_models"]], "#0EA5E9", "#F0F9FF")
    dk.h(d, "6. The three user-story paths compared")
    dk.table(d, ["Path", "Goal", "Weekly rhythm", "Pillar mix", "KPIs"],
             [[r["label"], r["goal"], r["days"], ", ".join(f"{k} {v}" for k, v in r["mix"].items()), ", ".join(r["kpis"])] for r in personas_rows],
             "#10B981", "#ECFDF5", [1.3, 1.5, .9, 2.2, 1.2])
    p = out_dir / "Branding_Audit_Report.docx"
    d.save(p)
    return p


# --------------------------------------------------------------- drafts ----
def build_drafts_files(profile, drafts, out_dir: Path) -> list[Path]:
    d = dk.new_doc()
    dk.cover(d, "Optimized Post Drafts", f"{len(drafts)} AI-assisted LinkedIn posts, ready for your review", _meta(profile), "#7C2D12", "#F59E0B")
    dk.callout(d, "Authenticity first: edit each draft in your own voice and tick 'Human reviewed' in the app before scheduling.")
    md = ["# Optimized Post Drafts\n"]
    for x in drafts:
        col = PILLARS[x["pillar"]]["color"]
        dk.h(d, f"{x['id']}  {PILLARS[x['pillar']]['label']}  -  {FORMATS[x['format']]['label']}", 2, col)
        dk.para(d, f"Quality {x['quality']}/100   |   Source: {x['source']}   |   Reviewed: {'yes' if x.get('human_reviewed') else 'no'}", italic=True, color="#6B7280", size=9)
        for block in x["text"].split("\n\n"):
            para = d.add_paragraph()
            for n, line in enumerate(block.split("\n")):
                run = para.add_run(line)
                if n < len(block.split("\n")) - 1:
                    run.add_break()
            para.paragraph_format.space_after = dk.Pt(6)
        if x.get("poll"):
            dk.callout(d, "Poll: " + x["poll"]["question"] + "  |  " + "  /  ".join(x["poll"]["options"]), "#FEF9C3", "#854D0E")
        if x.get("slides"):
            dk.callout(d, "Carousel slides: " + "  >  ".join(s["title"] for s in x["slides"]), "#CCFBF1", "#115E59")
        if x["issues"]:
            dk.para(d, "To fix: " + " ".join(x["issues"]), color="#B91C1C", size=9)
        md += [f"## {x['id']} {PILLARS[x['pillar']]['label']} ({x['format']})", "", x["text"], ""]
    p1, p2 = out_dir / "Optimized_Post_Drafts.docx", out_dir / "Optimized_Post_Drafts.md"
    d.save(p1)
    p2.write_text("\n".join(md), encoding="utf-8")
    return [p1, p2]


# ------------------------------------------------------------ dashboard ----
def build_dashboard(profile, enriched, m, out_dir: Path, demo: bool) -> Path:
    wb = Workbook()
    s = wb.active
    s.title = "Summary"
    s["A1"] = "Engagement Dashboard" + ("  (DEMO DATA - simulated)" if demo else "")
    s["A1"].font = Font(size=18, bold=True, color="FFFFFF")
    for c in range(1, 9):
        s.cell(row=1, column=c).fill = PatternFill("solid", fgColor="DB2777" if demo else "4C1D95")
    kp = [("Posts", m.get("posts", 0), "7C3AED"), ("Impressions", m.get("impressions", 0), "F97316"), ("Likes", m.get("likes", 0), "EC4899"),
          ("Comments", m.get("comments", 0), "0EA5E9"), ("Shares", m.get("shares", 0), "10B981"),
          ("Profile visits", m.get("profile_visits", 0), "F59E0B"), ("Engagement rate %", round(m.get("rate", 0), 2), "6366F1")]
    for i, (lab, val, col) in enumerate(kp):
        s.cell(row=3, column=i + 1, value=lab).font = Font(bold=True, color="FFFFFF")
        s.cell(row=3, column=i + 1).fill = PatternFill("solid", fgColor=col)
        s.cell(row=4, column=i + 1, value=val).font = Font(size=16, bold=True, color=col)
        s.column_dimensions[get_column_letter(i + 1)].width = 18
    if not m.get("empty"):
        raw = wb.create_sheet("Raw Data")
        cols = ["post_id", "published_date", "week", "pillar", "format", "weekday", "impressions", "likes", "comments", "shares", "profile_visits", "engagement", "rate", "source"]
        raw.append(cols)
        for _, r in enriched.iterrows():
            row = []
            for c in cols:
                v = r[c] if c in r else ""
                if c == "published_date":
                    v = v.date().isoformat() if pd.notna(v) else ""
                elif c == "rate":
                    v = round(float(v), 2)
                elif hasattr(v, "item"):
                    v = v.item()
                row.append("" if v is None or (isinstance(v, float) and v != v) else v)
            raw.append(row)
        for c in range(1, len(cols) + 1):
            raw.cell(row=1, column=c).font, raw.cell(row=1, column=c).fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="4C1D95")
            raw.column_dimensions[get_column_letter(c)].width = 14

        def sheet(name, df, key, color, chart_cls):
            ws = wb.create_sheet(name)
            ws.append([key.title(), "Posts", "Impressions", "Likes", "Comments", "Shares", "Rate %"])
            for _, r in df.iterrows():
                ws.append([r[key], r["posts"], r["impressions"], r["likes"], r["comments"], r["shares"], round(float(r["rate"]), 2)])
            for c in range(1, 8):
                ws.cell(row=1, column=c).font, ws.cell(row=1, column=c).fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor=color)
                ws.column_dimensions[get_column_letter(c)].width = 15
            ch = chart_cls()
            ch.title, ch.height, ch.width = f"Engagement rate % by {key}", 8, 16
            ch.add_data(Reference(ws, min_col=7, min_row=1, max_row=ws.max_row), titles_from_data=True)
            ch.set_categories(Reference(ws, min_col=1, min_row=2, max_row=ws.max_row))
            ws.add_chart(ch, "I2")

        sheet("Weekly", m["weekly"].rename(columns={"week": "week"}), "week", "EC4899", LineChart)
        sheet("By Pillar", m["by_pillar"], "pillar", "F97316", BarChart)
        sheet("By Format", m["by_format"], "format", "10B981", BarChart)
    tpl = wb.create_sheet("Tracking Template")
    tpl.append(["post_id", "published_date", "impressions", "likes", "comments", "shares", "profile_visits", "source"])
    for c in range(1, 9):
        tpl.cell(row=1, column=c).font, tpl.cell(row=1, column=c).fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="0EA5E9")
        tpl.column_dimensions[get_column_letter(c)].width = 16
    dv = DataValidation(type="list", formula1='"manual,taplio,linkedin"', allow_blank=True)
    tpl.add_data_validation(dv)
    dv.add("H2:H200")
    p = out_dir / ("Engagement_Dashboard_DEMO.xlsx" if demo else "Engagement_Dashboard.xlsx")
    wb.save(p)
    return p


# ---------------------------------------------------------- performance ----
def build_performance_report(profile, m, ins, score, new_weights, out_dir: Path, demo: bool, chart_dir: Path) -> Path:
    d = dk.new_doc()
    dk.cover(d, "Performance Review Report", "Engagement analysis, insights and next-cycle strategy", _meta(profile, "   |   DEMO DATA" if demo else ""), "#064E3B", "#10B981")
    if demo:
        dk.callout(d, "This report was generated from SIMULATED demo metrics to preview the layout. Replace with real engagement data and rebuild before submitting.", "#FEE2E2", "#991B1B")
    dk.h(d, "1. Executive summary", color="#065F46")
    if m.get("empty"):
        dk.para(d, "No engagement has been logged yet. Publish the pilot posts and log their metrics, then rebuild this report.")
    else:
        dk.table(d, ["Posts", "Impressions", "Likes", "Comments", "Shares", "Profile visits", "Engagement rate"],
                 [[m["posts"], f"{m['impressions']:,}", m["likes"], m["comments"], m["shares"], m["profile_visits"], f"{m['rate']:.2f}%"]], "#10B981", "#ECFDF5")
        charts.weekly(m, chart_dir / "weekly.png"); charts.pillar_chart(m, chart_dir / "by_pillar.png"); charts.format_chart(m, chart_dir / "by_format.png")
        dk.h(d, "2. Charts", color="#065F46")
        for f in ("weekly", "by_pillar", "by_format"):
            dk.image(d, chart_dir / f"{f}.png", 5.6)
        dk.h(d, "3. Top performing posts", color="#065F46")
        dk.table(d, ["Post", "Pillar", "Format", "Impressions", "Engagement", "Rate %"],
                 [[r["post_id"], PILLARS.get(r["pillar"], {}).get("label", ""), FORMATS.get(r["format"], {}).get("label", ""), r["impressions"], r["engagement"], f"{r['rate']:.1f}"] for _, r in m["top"].iterrows()],
                 "#0EA5E9", "#F0F9FF")
    dk.h(d, "4. Insights and recommendations", color="#065F46")
    dk.table(d, ["What we saw", "What to do next"], [[i["finding"], i["action"]] for i in ins], "#F97316", "#FFF7ED", [3.2, 3.6])
    dk.h(d, "5. Strategy refinement: next 6-week pillar mix", color="#065F46")
    dk.table(d, ["Pillar", "Next share"], [[PILLARS[k]["label"], f"{round(v * 100)}%"] for k, v in sorted(new_weights.items(), key=lambda kv: -kv[1])], "#7C3AED")
    dk.h(d, "6. Self-assessment against the evaluation criteria", color="#065F46")
    dk.table(d, ["Criterion", "Weight", "Score"], [[k, f"{v['weight']}%", v["score"]] for k, v in score["parts"].items()] + [["Overall" + (" (provisional)" if score["provisional"] else ""), "", score["total"]]], "#EC4899", "#FDF2F8")
    dk.h(d, "7. Risks and mitigations", color="#065F46")
    dk.table(d, ["Risk", "Mitigation (brief)", "How this project handles it"], [list(r) for r in RISKS], "#6366F1", "#EEF2FF")
    p = out_dir / ("Performance_Review_Report_DEMO.docx" if demo else "Performance_Review_Report.docx")
    d.save(p)
    return p


# -------------------------------------------------------------- capstone ----
def build_capstone(profile, b: dict, out_dir: Path, chart_dir: Path) -> Path:
    persona = PERSONAS[profile.get("persona", "professional")]
    d = dk.new_doc()
    dk.cover(d, "LinkedIn Influence Lab", "Industrial Capstone Report: AI-guided personal branding with ChatGPT and Taplio", _meta(profile), "#312E81", "#F97316")
    dk.h(d, "1. Executive summary")
    dk.para(d, (f"This capstone delivers a complete, reproducible personal-branding system for {profile.get('name') or 'the author'}. "
                f"It combines AI-assisted ideation, a 6-week content calendar, a Taplio scheduling queue and an analytics loop. "
                f"The primary path is '{persona['label']}'; the two alternative paths are fully supported and compared below."))
    dk.table(d, ["Deliverable", "Result"],
             [["Branding audit", f"{b['audit']['total']}/100 ({b['audit']['band']}); {len(b['audit']['gaps'])} gaps with fixes"],
              ["Content ideas", f"{len(b['ideas'])} generated (brief requires 15+)"],
              ["Post drafts", f"{len(b['drafts'])} drafts, average quality {sum(x['quality'] for x in b['drafts']) / max(1, len(b['drafts'])):.0f}/100 (brief requires 10+)"],
              ["Content calendar", f"{len(b['calendar'])} slots over 6 weeks"],
              ["Engagement tracking", "Awaiting your real metrics" if b["metrics"].get("empty") else f"{b['metrics']['posts']} posts, {b['metrics']['rate']:.2f}% engagement" + (" (DEMO)" if b["demo"] else "")]],
             "#7C3AED", widths=[1.8, 5.0])
    dk.h(d, "2. Project overview and client background")
    dk.para(d, "Purpose: help professionals build a strong personal brand on LinkedIn by combining Taplio's content workflow with ChatGPT-driven ideation and optimization.")
    dk.bullets(d, ["Outcomes: consistent content strategy, AI-assisted visibility, engagement monitoring, reproducible framework.",
                   "Client needs: professional visibility, a consistent content pipeline, a scalable system for ideation, scheduling and analytics.",
                   "Constraints: Taplio free tier (basic features), ChatGPT integration, business-ready reproducible deliverables."])
    dk.h(d, "3. Business problem")
    dk.para(d, "LinkedIn has over a billion users, yet most professionals fail to use it for career growth because of inconsistent posting, no content plan, and little time for engagement and analytics. This project answers with a structured, AI-guided lab that automates ideation, strategy alignment and performance monitoring.")
    dk.h(d, "4. User stories: all three paths explored")
    dk.table(d, ["Path", "User story", "Rhythm", "Pillar mix", "KPIs"],
             [[r["label"], r["story"], r["days"], ", ".join(f"{k} {v}" for k, v in r["mix"].items()), ", ".join(r["kpis"])] for r in b["personas"]],
             "#EC4899", "#FDF2F8", [1.1, 2.0, .7, 2.0, 1.1])
    dk.h(d, "5. Solution and AI-guided workflow")
    wf = chart_dir / "workflow.png"
    charts.workflow_diagram(wf)
    dk.image(d, wf, 6.5)
    dk.para(d, "Inputs (you) feed the AI plugin, whose drafts you review; approved posts go to Taplio, publish on LinkedIn, and their metrics return as analytics that refine the next cycle's inputs. The pipeline automates everything except the steps that must stay human: reviewing, publishing and reporting real numbers.")
    dk.h(d, "6. Phases, timeline and backups")
    dk.table(d, ["Phase", "When", "Goal", "Output folder", "Backup"],
             [[f"{p['n']}. {p['title']}", p["week"], p["goal"], f"phases/{p['folder']}", "backups/ (zip per run)"] for p in b["phases"]], "#0EA5E9", "#F0F9FF", [1.5, .7, 2.4, 1.6, .9])
    dk.h(d, "7. Branding and content strategy")
    dk.table(d, ["Pillar", "Share", "Posts", "What it covers"], [[p["label"], f"{round(p['weight'] * 100)}%", p["posts"], p["desc"]] for p in b["pillars"]["pillars"]], "#F97316", "#FFF7ED")
    dk.para(d, "Formats: text posts, carousels (built as a PDF in your design tool), polls and micro-stories. Engagement strategy: reply to every comment within two hours, comment on 5 peers' posts daily, share curated content with a source.")
    dk.h(d, "8. AI-guided prompt templates")
    dk.bullets(d, ["Template A: Generate 5 engaging LinkedIn post ideas about [industry/career topic].",
                   "Template B: Rewrite this draft in a professional but relatable tone.",
                   "Template C: Summarize this article into a LinkedIn post with 3 key takeaways."])
    dk.h(d, "9. Results and analytics")
    if b["metrics"].get("empty"):
        dk.callout(d, "Real engagement has not been logged yet. Phase 4 tracking is ready; log metrics and rebuild to fill this section.")
    else:
        if b["demo"]:
            dk.callout(d, "DEMO DATA: the numbers below are simulated for layout preview only.", "#FEE2E2", "#991B1B")
        charts.weekly(b["metrics"], chart_dir / "weekly.png"); dk.image(d, chart_dir / "weekly.png", 5.6)
        dk.table(d, ["What we saw", "What to do next"], [[i["finding"], i["action"]] for i in b["insights"]], "#10B981", "#ECFDF5")
    dk.table(d, ["Criterion", "Weight", "Score"], [[k, f"{v['weight']}%", v["score"]] for k, v in b["score"]["parts"].items()] + [["Overall" + (" (provisional)" if b["score"]["provisional"] else ""), "", b["score"]["total"]]], "#6366F1", "#EEF2FF")
    dk.h(d, "10. Bias and ethical considerations")
    dk.bullets(d, ETHICS)
    dk.h(d, "11. Risks and mitigations")
    dk.table(d, ["Risk", "Mitigation", "Implemented as"], [list(r) for r in RISKS], "#DB2777", "#FDF2F8")
    dk.h(d, "12. Technical architecture")
    dk.para(d, "Python 3.10+, Streamlit UI, pandas, openpyxl, python-docx, matplotlib and requests. Modules are layered: inputs and plugins, engines (ideation, drafting, quality, planner), phases and pipeline, reports and backups. Plugins (AI, export, import) are drop-in files. All paths come from one module (paths.py); every phase writes to its own folder and is zipped to backups/ when it finishes. See docs/03_PROJECT_STRUCTURE_GUIDE.md.")
    dk.h(d, "13. How to reproduce")
    dk.bullets(d, ["Run run_app.bat (Windows) or run_app.sh; open the local address shown.", "Fill Inputs, optionally connect an AI plugin, press Run full pipeline.",
                   "Review drafts, approve them, schedule in Taplio, log metrics, rebuild deliverables.", "Details: HOW_TO_RUN.txt and docs/04_USER_GUIDE_FOR_BEGINNERS.md"])
    dk.h(d, "14. Appendices")
    dk.bullets(d, ["Prompt templates A-C: templates/prompt_templates.md", "Content calendar sample: sample_data/ and deliverables/01_content_calendar", "Engagement tracking sheet: deliverables/03_engagement_dashboard", "Profile optimization checklist: templates/profile_optimization_checklist.md"])
    p = out_dir / "LinkedIn_Influence_Lab_Capstone_Report.docx"
    d.save(p)
    return p
