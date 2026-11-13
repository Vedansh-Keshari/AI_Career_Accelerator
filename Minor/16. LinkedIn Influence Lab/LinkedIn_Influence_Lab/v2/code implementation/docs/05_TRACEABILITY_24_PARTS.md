# Traceability: the 24 parts of the project brief

| # | Brief section | How it is covered | Where |
|---|---|---|---|
| 1 | Project Overview | Purpose and outcomes are the top of the README and the Command Center hero. | `README.md`, `docs/01_REQUIREMENTS_DOCUMENT.md` |
| 2 | Client Background | Needs and constraints captured as inputs and requirements (Taplio free tier, ChatGPT, reproducible). | `src/lil/ui/inputs.py`, `docs/01_REQUIREMENTS_DOCUMENT.md` |
| 3 | Business Problem Statement | The AI-guided workflow: ChatGPT/AI > Taplio > LinkedIn > analytics > inputs, automated by one pipeline. | `src/lil/pipeline.py`, `src/lil/charts.py` |
| 4 | User Story | All three paths (professional, job seeker, thought leader) change pillars, cadence, CTAs and KPIs. | `src/lil/knowledge.py`, `src/lil/personas.py`, `src/lil/ui/persona_lab.py` |
| 5 | Acceptance Criteria | Live tracker: 15+ ideas, 10+ posts, metrics per post, 6-week calendar, review report. | `src/lil/ui/command_center.py`, `src/lil/phase_spec.py` |
| 6 | Project Objectives | Ideation workflow, calendar, optimized drafts, engagement insights map to phases 2, 3, 2, 5. | `src/lil/pipeline.py` |
| 7 | Project Tasks (Phase 1) | Seven tasks implemented as five phases with a backup after each. | `src/lil/paths.py`, `src/lil/pipeline.py`, `src/lil/backup.py` |
| 8 | Deliverables | Calendar, drafts, dashboard, audit report, performance report (+ capstone report, Taplio queue). | `src/lil/reports.py`, `src/lil/calendar_builder.py` |
| 9 | Technical Requirements | Web-based Python app, no extra installs beyond pip packages; Taplio/ChatGPT/Sheets supported. | `requirements.txt`, `docs/01_REQUIREMENTS_DOCUMENT.md` |
| 10 | Input Information | Profile, audience/industry, role models, plus your IDs, stories and plugin keys. | `src/lil/ui/inputs.py`, `src/lil/settings.py`, `src/lil/guidance.py` |
| 11 | Evaluation Criteria | Self-scorecard with the exact 30/25/20/15/10 weights. | `src/lil/analytics.py` |
| 12 | Getting Started | HOW_TO_RUN.txt and the beginner guide; first-run checklist in the Command Center. | `HOW_TO_RUN.txt`, `docs/04_USER_GUIDE_FOR_BEGINNERS.md` |
| 13 | Support | Troubleshooting FAQ with the response-time targets (1 day / 2-3 days / weekly). | `docs/06_TROUBLESHOOTING_FAQ.md` |
| 14 | Solution Overview | Pipeline: ideas > drafts > scheduling, engagement monitoring, iterative refinement. | `docs/02_ARCHITECTURE.md` |
| 15 | Technical Approach | Ideation, scheduling queue, analytics, and the feedback loop (refined pillar mix). | `src/lil/ideation.py`, `src/lil/calendar_builder.py`, `src/lil/analytics.py` |
| 16 | Branding & Content Strategy | 5 pillars, 4 formats, engagement strategy in the capstone report. | `src/lil/audit.py`, `src/lil/knowledge.py` |
| 17 | AI-Guided Workflow | Templates A, B, C wired to AI plugins with offline fallbacks. | `src/lil/knowledge.py`, `src/lil/llm.py`, `src/lil/drafting.py` |
| 18 | Analytics & Reporting | Metrics, weekly dashboard, monthly-style performance report. | `src/lil/analytics.py`, `src/lil/reports.py` |
| 19 | Bias & Ethical Considerations | Human-review gate, inclusive-language check, source attribution check. | `src/lil/quality.py` |
| 20 | Technical Documentation for End Users | Step-by-step guide, prompt templates, example calendar, FAQ. | `docs/04_USER_GUIDE_FOR_BEGINNERS.md`, `templates/prompt_templates.md` |
| 21 | Quality & Acceptance Criteria | Automated tests plus the Command Center acceptance tracker. | `tests/test_engines.py`, `tests/test_pipeline.py` |
| 22 | Project Plan & Timeline | Phase catalogue mirrors the Week 1-6 plan. | `src/lil/paths.py`, `docs/02_ARCHITECTURE.md` |
| 23 | Risks & Mitigations | Four risks, each with a built-in mitigation and an insight rule. | `src/lil/reports.py`, `src/lil/analytics.py` |
| 24 | Appendices | Prompt templates, calendar sample, tracking sheet, profile checklist. | `templates/prompt_templates.md`, `templates/profile_optimization_checklist.md`, `sample_data/profile_professional.json` |
