"""All Word / Excel deliverables. Each function writes into its own deliverables sub-folder."""
from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from . import analytics, charts, hubs, paths
from . import docx_kit as dk
from .knowledge import FORMATS, PERSONAS, PILLARS
from .persona_content import BENEFITS, KPI_FIELDS, SETBACKS
from .phase_spec import PHASE_SPEC
from .trace import TRACE

RISKS = [
    ("Low engagement", "Adjust posting time and content type", "The insights flag a rate below 2% and suggest hook, format and time tests."),
    ("Free-tier limits in Taplio", "Supplement with manual LinkedIn analytics", "Manual entry and a flexible CSV importer for LinkedIn or Taplio exports."),
    ("Over-reliance on AI", "Ensure human review for authenticity", "A Human reviewed gate on every draft; only approved posts enter the approved-only Taplio queue."),
    ("Consistency drop-off", "Use scheduling to avoid gaps", "Taplio queue, .ics reminders, and a consistency score and streak on the dashboard."),
]
ETHICS = ["Avoid over-automation: nothing is queued as approved until the author ticks Human reviewed.",
          "Inclusive and neutral language: the quality checker flags non-inclusive terms and suggests replacements.",
          "Attribute sources: statistics or studies without a named source are flagged; Template C always adds a Source line."]
GLOSSARY = [("Pillar", "One of 3-5 recurring topics a profile posts about."), ("Hook", "The first line of a post; it decides whether readers open 'see more'."),
            ("Engagement rate", "(Likes + comments + shares) divided by impressions."), ("Pilot", "The first 2-3 posts, used to test formats before the full run."),
            ("Human reviewed", "The author's confirmation that a draft was read, edited and approved."), ("Taplio queue", "The CSV and copy-paste pack used to schedule posts in Taplio."),
            ("Plugin", "A drop-in file that adds an AI engine, an export target or an importer."), ("Workspace", "A self-contained set of data folders: your own, or the sample one.")]


def _stamp() -> str:
    if paths.is_sample():
        return "SAMPLE DATA. This report was generated from a fictional person and illustrative figures so you can see the finished format. It is not a real result."
    return ""


def _label(demo: bool) -> str:
    return "SAMPLE DATA" if paths.is_sample() else ("DEMO DATA" if demo else "")


def _open(profile: dict, running: str, title: str, subtitle: str, extra: list[tuple[str, str]] | None = None, demo: bool = False, doc_name: str | None = None):
    persona = PERSONAS[profile.get("persona", "professional")]
    doc = dk.new_doc(running, "LIL-2025-P1", _label(demo))
    tmp = tempfile.mkdtemp()
    banner = Path(tmp) / "banner.png"
    charts.cover_banner(banner)
    stamp = _stamp() or ("DEMO DATA. Metrics in this report are simulated to preview the layout. Replace them with real data before submitting." if demo else None)
    rows = [("Project", "LinkedIn Influence Lab (Phase 1, 6 weeks)"), ("Project code", "LIL-2025-P1"), ("Document", doc_name or title),
            ("Prepared for", f"{profile.get('name') or 'Author'}" + (f", {profile['current_role']}" if profile.get("current_role") else "")),
            ("Learning path", persona["label"]), ("Version / date", f"1.1  ·  {date.today().strftime('%d %B %Y')}"),
            ("Classification", "Confidential: client use")] + (extra or [])
    dk.cover(doc, banner, title, subtitle, rows, stamp or None)
    return doc


# ------------------------------------------------------------------ audit ------------------
def build_audit_report(profile, audit, pillars, personas_rows, out_dir: Path) -> Path:
    d = _open(profile, "Branding Audit Report", "Branding Audit Report", "Current versus optimized LinkedIn profile and positioning")
    dk.h1(d, "1. Summary")
    gaps = sorted(audit["gaps"], key=lambda i: -(i["points"] - i["score"]))
    dk.tiles(d, [("Profile health score", f"{audit['total']}/100", dk.VIOLET), ("Assessment", audit["band"], dk.PINK),
                 ("Checklist gaps", len(audit["gaps"]), dk.ORANGE), ("Content pillars", len(pillars["pillars"]), dk.EMERALD)])
    dk.para(d, f"The profile scores {audit['total']} out of 100 against a 12-point checklist drawn from the project brief. "
               f"{len(audit['gaps'])} items need attention; the five highest-value fixes are listed in section 3.")
    dk.h1(d, "2. Profile checklist")
    dk.table(d, ["Checklist item", "Points", "Score", "Status", "Recommended fix"],
             [[i["label"], i["points"], i["score"], "OK" if i["ok"] else "Gap", "" if i["ok"] else i["fix"]] for i in audit["items"]],
             dk.INDIGO, [4.4, 1.3, 1.3, 1.3, 8.5], size=8.5)
    dk.h1(d, "3. Priority actions")
    dk.numbered(d, [f"{g['label']}: {g['fix']}  (up to +{g['points'] - g['score']} points)" for g in gaps[:5]] or ["No gaps found."])
    dk.h1(d, "4. Headline: current and optimized")
    dk.table(d, ["", "Headline"], [["Current", audit["current_headline"] or "(not provided)"]] + [[f"Option {n}", h] for n, h in enumerate(audit["headline_options"], 1)],
             dk.PINK, [2.3, 14.5], bold_first=True, size=9.5)
    dk.h1(d, "5. About section: optimized draft")
    dk.callout(d, f"Source: {audit['about_source']}. Replace every [bracketed placeholder] with a real, verifiable example before publishing.", "warn", "Before you use it")
    for block in audit["about_draft"].split("\n\n"):
        d.add_paragraph(block)
    dk.h1(d, "6. Content pillars")
    with tempfile.TemporaryDirectory() as tmp:
        donut = Path(tmp) / "mix.png"
        charts.mix_donut({p["key"]: p["weight"] for p in pillars["pillars"]}, donut, "Target pillar mix")
        dk.figure(d, donut, "Figure 1. Target pillar mix for the six-week plan", 10.5)
    dk.table(d, ["Pillar", "Share", "Posts in 6 weeks", "What it covers", "Example topic"],
             [[p["label"], f"{round(p['weight'] * 100)}%", p["posts"], p["desc"], p["examples"][0]] for p in pillars["pillars"]],
             dk.ORANGE, [2.9, 1.3, 1.9, 4.6, 6.1], bold_first=True, size=8.5)
    if audit["role_models"]:
        dk.h1(d, "7. Role-model benchmark")
        dk.table(d, ["Role model", "Profile", "What to learn"], [[r["name"], r["url"], r["learn"]] for r in audit["role_models"]], dk.SKY, [4.0, 6.0, 6.8], size=9)
    dk.h1(d, "8. The three user paths compared")
    dk.table(d, ["Path", "Goal", "Rhythm", "Pillar mix", "KPIs"],
             [[r["label"], r["goal"], r["days"], ", ".join(f"{k} {v}" for k, v in r["mix"].items()), ", ".join(r["kpis"])] for r in personas_rows],
             dk.EMERALD, [2.6, 3.4, 1.8, 5.6, 3.4], bold_first=True, size=8.5)
    p = out_dir / "Branding_Audit_Report.docx"
    d.save(p)
    return p


# ------------------------------------------------------------------ drafts -----------------
def build_drafts_files(profile, drafts, out_dir: Path) -> list[Path]:
    d = _open(profile, "Optimized Post Drafts", "Optimized Post Drafts", f"{len(drafts)} AI-assisted LinkedIn posts ready for your review")
    dk.h1(d, "1. How to use this document")
    dk.callout(d, "Edit each draft in your own voice, replace any [placeholder] with a real example, then tick Human reviewed in the app before scheduling.", "info", "Authenticity first")
    avg = sum(x["quality"] for x in drafts) / max(1, len(drafts))
    dk.tiles(d, [("Drafts", len(drafts), dk.VIOLET), ("Average quality", f"{avg:.0f}/100", dk.EMERALD),
                 ("Human reviewed", sum(1 for x in drafts if x.get("human_reviewed")), dk.PINK), ("Need fixes", sum(1 for x in drafts if x["issues"]), dk.ORANGE)])
    dk.table(d, ["Draft", "Pillar", "Format", "Quality", "Reviewed", "Source"],
             [[x["id"], PILLARS[x["pillar"]]["label"], FORMATS[x["format"]]["label"], x["quality"], "Yes" if x.get("human_reviewed") else "No", x["source"]] for x in drafts],
             dk.INDIGO, [1.6, 4.4, 3.0, 2.0, 2.4, 3.4], size=8.5)
    dk.h1(d, "2. Drafts", new_page=True)
    md = ["# Optimized Post Drafts\n"]
    for x in drafts:
        extras = []
        if x.get("poll"):
            extras.append(("Poll", x["poll"]["question"] + "  |  " + " / ".join(x["poll"]["options"])))
        if x.get("slides"):
            extras.append(("Carousel slides", "  >  ".join(s["title"] for s in x["slides"])))
        dk.draft_card(d, f"{x['id']}  ·  {PILLARS[x['pillar']]['label']}  ·  {FORMATS[x['format']]['label']}",
                      f"Quality {x['quality']}/100   |   Source: {x['source']}   |   Human reviewed: {'yes' if x.get('human_reviewed') else 'no'}",
                      x["text"].split("\n"), dk.__dict__.get({"career_insights": "VIOLET", "thought_leadership": "ORANGE", "personal_journey": "PINK",
                                                              "industry_trends": "SKY", "actionable_tips": "EMERALD"}[x["pillar"]]),
                      extras, " ".join(x["issues"]))
        md += [f"## {x['id']} {PILLARS[x['pillar']]['label']} ({x['format']})", "", x["text"], ""]
    p1, p2 = out_dir / "Optimized_Post_Drafts.docx", out_dir / "Optimized_Post_Drafts.md"
    d.save(p1)
    p2.write_text("\n".join(md), encoding="utf-8")
    return [p1, p2]


# ------------------------------------------------------------------ dashboard --------------
def build_dashboard(profile, enriched, m, out_dir: Path, demo: bool) -> Path:
    wb = Workbook()
    s = wb.active
    s.title = "Summary"
    label = _label(demo)
    s["A1"] = "Engagement Dashboard" + (f"  ({label})" if label else "")
    s["A1"].font = Font(size=18, bold=True, color="FFFFFF")
    for c in range(1, 9):
        s.cell(row=1, column=c).fill = PatternFill("solid", fgColor="BE185D" if label else "312E81")
    kp = [("Posts", m.get("posts", 0), "6D28D9"), ("Impressions", m.get("impressions", 0), "C2410C"), ("Likes", m.get("likes", 0), "BE185D"),
          ("Comments", m.get("comments", 0), "0369A1"), ("Shares", m.get("shares", 0), "047857"),
          ("Profile visits", m.get("profile_visits", 0), "B45309"), ("Engagement rate %", round(m.get("rate", 0), 2), "4F46E5")]
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
            raw.cell(row=1, column=c).font, raw.cell(row=1, column=c).fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="312E81")
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

        sheet("Weekly", m["weekly"], "week", "BE185D", LineChart)
        sheet("By Pillar", m["by_pillar"], "pillar", "C2410C", BarChart)
        sheet("By Format", m["by_format"], "format", "047857", BarChart)
    kp_df = hubs.load_kpis()
    if not kp_df.empty:
        ws = wb.create_sheet("Path KPIs")
        labels = [f["label"] for f in KPI_FIELDS[profile.get("persona", "professional")]]
        ws.append(["Week"] + labels + ["Notes"])
        for _, r in kp_df.iterrows():
            ws.append([int(r["week"]), int(r["a"]), int(r["b"]), int(r["c"]), r["notes"]])
        for c in range(1, 6):
            ws.cell(row=1, column=c).font, ws.cell(row=1, column=c).fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="0369A1")
            ws.column_dimensions[get_column_letter(c)].width = 26
    tpl = wb.create_sheet("Tracking Template")
    tpl.append(["post_id", "published_date", "impressions", "likes", "comments", "shares", "profile_visits", "source"])
    for c in range(1, 9):
        tpl.cell(row=1, column=c).font, tpl.cell(row=1, column=c).fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="0369A1")
        tpl.column_dimensions[get_column_letter(c)].width = 16
    dv = DataValidation(type="list", formula1='"manual,taplio,linkedin"', allow_blank=True)
    tpl.add_data_validation(dv)
    dv.add("H2:H200")
    p = out_dir / (f"Engagement_Dashboard_{label.split()[0]}.xlsx" if label else "Engagement_Dashboard.xlsx")
    wb.save(p)
    return p


# ------------------------------------------------------------------ performance ------------
def _kpi_rows(profile):
    return [[r["label"], r["total"], r["target"], f"{r['pct']}%"] for r in hubs.kpi_progress(profile)]


def build_performance_report(profile, m, ins, score, new_weights, out_dir: Path, demo: bool, chart_dir: Path) -> Path:
    d = _open(profile, "Performance Review Report", "Performance Review Report", "Engagement analysis, insights and next-cycle strategy", demo=demo)
    dk.h1(d, "1. Executive summary")
    if m.get("empty"):
        dk.callout(d, "No engagement has been logged yet. Publish the pilot posts and log their metrics, then rebuild this report. Nothing here is estimated.", "warn")
    else:
        dk.tiles(d, [("Posts analysed", m["posts"], dk.VIOLET), ("Impressions", f"{m['impressions']:,}", dk.ORANGE), ("Likes", m["likes"], dk.PINK),
                     ("Comments", m["comments"], dk.SKY), ("Engagement rate", f"{m['rate']:.2f}%", dk.EMERALD)])
        bp = m["by_pillar"].iloc[0]
        bf = m["by_format"].iloc[0]
        trend = "" if m["growth_pct"] is None else f" The weekly engagement rate moved {m['growth_pct']:+.0f}% from the first to the latest week."
        dk.para(d, f"Across {m['posts']} posts the profile earned {m['impressions']:,} impressions at an engagement rate of {m['rate']:.2f}%. "
                   f"The strongest pillar was {PILLARS[bp['pillar']]['label']} ({bp['rate']:.1f}%) and the strongest format was {FORMATS[bf['format']]['label']} ({bf['rate']:.1f}%).{trend}")
        charts.weekly(m, chart_dir / "weekly.png"); charts.pillar_chart(m, chart_dir / "by_pillar.png"); charts.format_chart(m, chart_dir / "by_format.png")
        dk.h1(d, "2. Performance charts")
        dk.figure(d, chart_dir / "weekly.png", "Figure 1. Weekly reach and engagement rate", 15)
        dk.figure(d, chart_dir / "by_pillar.png", "Figure 2. Engagement rate by content pillar", 12.5)
        dk.figure(d, chart_dir / "by_format.png", "Figure 3. Engagement rate by post format", 12.5)
        dk.h1(d, "3. Top performing posts")
        dk.table(d, ["Post", "Pillar", "Format", "Impressions", "Engagement", "Rate %"],
                 [[r["post_id"], PILLARS.get(r["pillar"], {}).get("label", ""), FORMATS.get(r["format"], {}).get("label", ""), f"{int(r['impressions']):,}", int(r["engagement"]), f"{r['rate']:.1f}"] for _, r in m["top"].iterrows()],
                 dk.SKY, [1.6, 4.6, 3.2, 2.6, 2.6, 2.2], size=9)
    dk.h1(d, f"4. {PERSONAS[profile.get('persona', 'professional')]['label']} KPIs")
    dk.table(d, ["Weekly path KPI", "Logged", "Six-week target", "Progress"], _kpi_rows(profile), dk.PINK, [8.0, 2.6, 3.4, 2.8], bold_first=True)
    dk.h1(d, "5. Insights and recommendations")
    dk.table(d, ["What we saw", "What to do next"], [[i["finding"], i["action"]] for i in ins], dk.ORANGE, [8.0, 8.8], size=9)
    dk.h1(d, "6. Strategy refinement: next six-week pillar mix")
    with tempfile.TemporaryDirectory() as tmp:
        donut = Path(tmp) / "next.png"
        charts.mix_donut(new_weights, donut, "Recommended pillar mix for the next cycle")
        dk.figure(d, donut, "Figure 4. Recommended pillar mix (best pillar +10 points, weakest -5)", 10.5)
    dk.h1(d, "7. Self-assessment against the evaluation criteria")
    dk.table(d, ["Criterion", "Weight", "Score"], [[k, f"{v['weight']}%", v["score"]] for k, v in score["parts"].items()] +
             [["Overall" + (" (provisional)" if score["provisional"] else ""), "", score["total"]]], dk.INDIGO, [9.0, 3.0, 4.8], bold_first=True)
    dk.h1(d, "8. Risks and mitigations")
    dk.table(d, ["Risk", "Mitigation (brief)", "How this project handles it"], [list(r) for r in RISKS], dk.INDIGO, [3.6, 4.6, 8.6], bold_first=True, size=9)
    p = out_dir / (f"Performance_Review_Report_{_label(demo).split()[0]}.docx" if _label(demo) else "Performance_Review_Report.docx")
    d.save(p)
    return p


# ------------------------------------------------------------------ capstone ---------------
def build_capstone(profile, b: dict, out_dir: Path, chart_dir: Path) -> Path:
    key = profile.get("persona", "professional")
    persona = PERSONAS[key]
    d = _open(profile, "LinkedIn Influence Lab: Capstone Report", "LinkedIn Influence Lab",
              "Industrial capstone report: AI-guided personal branding with ChatGPT and Taplio", demo=b["demo"], doc_name="Industrial Capstone Report")
    dk.contents(d, [("1", "Executive summary", "Results at a glance and the deliverables produced"),
                    ("2", "Project overview and client background", "Purpose, outcomes, client needs and constraints"),
                    ("3", "Business problem and objectives", "Why a guided workflow is needed and what it must deliver"),
                    ("4", "User paths", "Professional, job seeker and thought leader compared, with benefits and setbacks"),
                    ("5", "Solution and AI-guided workflow", "The loop from inputs to analytics and back"),
                    ("6", "Phases, dependencies and backups", "What each phase does, needs and hands on"),
                    ("7", "Branding and content strategy", "Pillars, formats and engagement strategy"),
                    ("8", "Prompt templates", "Templates A, B and C and how they are used"),
                    ("9", "Results and analytics", "Metrics, insights and the self-assessment scorecard"),
                    ("10", "Path-specific results", "KPIs that matter for the selected path"),
                    ("11", "Ethics and bias", "Authenticity, inclusive language and attribution"),
                    ("12", "Risks and mitigations", "Four risks and how each is handled"),
                    ("13", "Technical architecture", "Layers, plugins and storage"),
                    ("14", "Operations", "Running, backing up and restoring"),
                    ("15", "Limitations and assumptions", "What this system does not do"),
                    ("A-C", "Appendices", "Glossary, traceability to the brief, document approval")])
    avg = sum(x["quality"] for x in b["drafts"]) / max(1, len(b["drafts"]))
    dk.h1(d, "1. Executive summary")
    dk.para(d, f"This capstone delivers a complete, reproducible personal-branding system for {profile.get('name') or 'the author'}. It combines AI-assisted ideation, "
               f"a six-week content calendar, a Taplio scheduling queue and an analytics loop. The primary path is {persona['label']}; the two alternative paths are fully supported and compared in section 4.")
    m = b["metrics"]
    dk.tiles(d, [("Audit score", f"{b['audit']['total']}/100", dk.VIOLET), ("Ideas", len(b["ideas"]), dk.ORANGE), ("Drafts", len(b["drafts"]), dk.PINK),
                 ("Calendar slots", len(b["calendar"]), dk.SKY), ("Posts logged", "none yet" if m.get("empty") else m["posts"], dk.EMERALD),
                 ("Engagement", "n/a" if m.get("empty") else f"{m['rate']:.2f}%", dk.INDIGO)])
    dk.table(d, ["Deliverable", "Result", "Brief requirement"],
             [["Branding audit", f"{b['audit']['total']}/100 ({b['audit']['band']}); {len(b['audit']['gaps'])} gaps with fixes", "Branding audit report"],
              ["Content ideas", f"{len(b['ideas'])} generated", "15 or more"],
              ["Post drafts", f"{len(b['drafts'])}; average quality {avg:.0f}/100", "10 or more optimized drafts"],
              ["Content calendar", f"{len(b['calendar'])} slots over six weeks", "Six-week calendar"],
              ["Engagement dashboard", "Awaiting real metrics" if m.get("empty") else f"{m['posts']} posts, {m['rate']:.2f}% engagement", "Weekly dashboard"],
              ["Performance review", "Generated with recommendations", "Performance review report"]], dk.VIOLET, [4.0, 7.6, 5.2], bold_first=True)
    dk.h1(d, "2. Project overview and client background", new_page=True)
    dk.para(d, "Purpose: help professionals build a strong personal brand on LinkedIn by combining Taplio's content workflow with ChatGPT-driven ideation and optimization.")
    dk.h3(d, "Outcomes")
    dk.bullets(d, ["A consistent content strategy aligned with career goals", "AI-assisted content creation that increases visibility", "Engagement monitoring that informs the next cycle", "A reproducible framework for a sustainable personal brand"])
    dk.h3(d, "Client needs and constraints")
    dk.bullets(d, ["Needs: professional visibility, a consistent content pipeline, and a scalable system for ideation, scheduling and analytics.",
                   "Constraints: Taplio free-tier limits, ChatGPT integration, and business-ready, reproducible deliverables."])
    dk.h1(d, "3. Business problem and objectives")
    dk.para(d, "LinkedIn has more than a billion users, yet most professionals do not use it effectively for career growth. Typical causes are inconsistent posting, no content plan, and little time for engagement and analytics. "
               "This project answers with a structured, AI-guided lab that automates ideation, strategy alignment and performance monitoring.")
    dk.bullets(d, ["Build an AI-guided content ideation workflow", "Create a six-week content calendar with scheduling", "Draft optimized posts aligned with the personal brand", "Track engagement and derive actionable insights"])
    dk.h1(d, "4. User paths", new_page=True)
    dk.table(d, ["Path", "User story", "Rhythm", "Pillar mix", "KPIs"],
             [[r["label"], r["story"], r["days"], ", ".join(f"{k} {v}" for k, v in r["mix"].items()), ", ".join(r["kpis"])] for r in b["personas"]],
             dk.PINK, [2.4, 4.4, 1.7, 5.0, 3.3], bold_first=True, size=8.5)
    dk.h3(d, f"Benefits and setbacks of the selected path ({persona['label']})")
    dk.table(d, ["Benefits", "Setbacks"], [[BENEFITS[key][i] if i < len(BENEFITS[key]) else "", SETBACKS[key][i] if i < len(SETBACKS[key]) else ""] for i in range(max(len(BENEFITS[key]), len(SETBACKS[key])))],
             dk.EMERALD, [8.4, 8.4], size=9)
    dk.h1(d, "5. Solution and AI-guided workflow", new_page=True)
    charts.workflow_diagram(chart_dir / "workflow.png")
    dk.figure(d, chart_dir / "workflow.png", "Figure 1. The AI-guided loop: inputs, AI, Taplio, LinkedIn, analytics, back to inputs", 16.5)
    dk.para(d, "Inputs feed the AI plugin, whose drafts the author reviews. Approved posts go to Taplio and are published on LinkedIn; their metrics return as analytics that refine the next cycle's inputs. "
               "The pipeline automates everything except the steps that must stay human: reviewing, publishing and reporting real numbers.")
    dk.h1(d, "6. Phases, dependencies and backups")
    charts.dependency_diagram(chart_dir / "dependency.png")
    dk.figure(d, chart_dir / "dependency.png", "Figure 2. Phase dependencies: solid arrows are hard requirements, dashed are soft", 16.5)
    dk.table(d, ["Phase", "When", "What it does", "Depends on", "Produces"],
             [[f"{p['n']}. {p['title']}", p["week"], PHASE_SPEC[p["key"]]["does"][0], PHASE_SPEC[p["key"]]["dependency"], ", ".join(PHASE_SPEC[p["key"]]["produces"][:3])] for p in b["phases"]],
             dk.SKY, [2.8, 1.5, 5.2, 3.6, 3.7], bold_first=True, size=8)
    dk.para(d, "Every phase run saves a checksummed zip backup; a full snapshot is created after the automated pipeline.")
    dk.h1(d, "7. Branding and content strategy", new_page=True)
    with tempfile.TemporaryDirectory() as tmp:
        donut = Path(tmp) / "mix.png"
        charts.mix_donut({p["key"]: p["weight"] for p in b["pillars"]["pillars"]}, donut, "Target pillar mix")
        dk.figure(d, donut, "Figure 3. Target pillar mix", 10.5)
    dk.table(d, ["Pillar", "Share", "Posts", "What it covers"], [[p["label"], f"{round(p['weight'] * 100)}%", p["posts"], p["desc"]] for p in b["pillars"]["pillars"]], dk.ORANGE, [3.6, 1.6, 1.6, 10.0], bold_first=True)
    dk.para(d, "Formats: text posts, carousels (built as a PDF in a design tool), polls and micro-stories. Engagement strategy: reply to every comment within two hours, comment on five peers' posts daily, and share curated content with its source.")
    dk.h1(d, "8. Prompt templates")
    dk.table(d, ["Template", "Prompt", "Used for"], [["A", "Generate 5 engaging LinkedIn post ideas about [industry/career topic].", "Phase 2 ideation"],
                                                      ["B", "Rewrite this draft in a professional but relatable tone.", "Rewrite tone button on each draft"],
                                                      ["C", "Summarize this article into a LinkedIn post with 3 key takeaways.", "Template C tool; always credits the source"]], dk.INDIGO, [2.0, 9.0, 5.8], bold_first=True, size=9)
    dk.h1(d, "9. Results and analytics", new_page=True)
    if m.get("empty"):
        dk.callout(d, "Real engagement has not been logged yet. Phase 4 tracking is ready; log metrics and rebuild this report to fill this section.", "warn")
    else:
        if _label(b["demo"]):
            dk.callout(d, "The figures below are illustrative sample data.", "alert", _label(b["demo"]))
        charts.weekly(m, chart_dir / "weekly.png")
        dk.figure(d, chart_dir / "weekly.png", "Figure 4. Weekly reach and engagement rate", 15)
        dk.table(d, ["What we saw", "What to do next"], [[i["finding"], i["action"]] for i in b["insights"]], dk.EMERALD, [8.0, 8.8], size=9)
    dk.table(d, ["Criterion", "Weight", "Score"], [[k, f"{v['weight']}%", v["score"]] for k, v in b["score"]["parts"].items()] +
             [["Overall" + (" (provisional)" if b["score"]["provisional"] else ""), "", b["score"]["total"]]], dk.INDIGO, [9.0, 3.0, 4.8], bold_first=True)
    dk.h1(d, "10. Path-specific results")
    dk.table(d, [f"{persona['label']} KPI", "Logged", "Six-week target", "Progress"], _kpi_rows(profile), dk.PINK, [8.0, 2.6, 3.4, 2.8], bold_first=True)
    dk.h1(d, "11. Ethics and bias")
    dk.bullets(d, ETHICS)
    dk.h1(d, "12. Risks and mitigations")
    dk.table(d, ["Risk", "Mitigation (brief)", "Implemented as"], [list(r) for r in RISKS], dk.PINK, [3.6, 4.6, 8.6], bold_first=True, size=9)
    dk.h1(d, "13. Technical architecture", new_page=True)
    charts.architecture_diagram(chart_dir / "architecture.png")
    dk.figure(d, chart_dir / "architecture.png", "Figure 5. Layered architecture; no database, only files", 15.5)
    dk.para(d, "Python 3.10+, Streamlit, pandas, openpyxl, python-docx, matplotlib, plotly and requests. Plugins (AI, export, import) are drop-in files. "
               "All folders are resolved by one module, and the sample workspace is physically separate from the user's own workspace.")
    dk.h1(d, "14. Operations")
    dk.bullets(d, ["Run: run_app.bat (Windows) or run_app.sh; open the local address shown.", "Back up: every phase run and the pipeline create zip backups with a SHA-256 manifest in backups/.",
                   "Restore: verify, take a safety snapshot of the current state, clear the covered folders, extract.", "Details: HOW_TO_RUN.txt and docs/07_BACKUP_AND_RESTORE.md."])
    dk.h1(d, "15. Limitations and assumptions")
    dk.bullets(d, ["Publishing on LinkedIn and scheduling in Taplio remain manual by design.", "Drafts from the built-in engine are first drafts; they depend on the author's real examples.",
                   "AI plugins require the user's own API key; they were validated with mocked responses.", "Taplio plan limits vary; manual entry and CSV import cover analytics gaps."])
    dk.h1(d, "Appendix A. Glossary", new_page=True)
    dk.table(d, ["Term", "Meaning"], [list(g) for g in GLOSSARY], dk.INDIGO, [4.0, 12.8], bold_first=True, size=9)
    dk.h1(d, "Appendix B. Traceability to the project brief")
    dk.table(d, ["#", "Brief section", "How it is covered"], [[n, name, how] for n, name, how, files in TRACE], dk.VIOLET, [1.0, 5.0, 10.8], size=8)
    dk.h1(d, "Appendix C. Document approval")
    dk.signoff(d, ["Prepared by", "Reviewed by", "Approved by"])
    p = out_dir / "LinkedIn_Influence_Lab_Capstone_Report.docx"
    d.save(p)
    return p
