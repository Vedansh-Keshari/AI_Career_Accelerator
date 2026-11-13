# Requirements Document - LinkedIn Influence Lab (LIL-2025-P1)

Version 1.0 · Phase 1 (6 weeks) · Department: Career Development & Digital Branding

## 1. Purpose and scope
Help professionals build a strong personal brand on LinkedIn by combining AI-assisted content creation (ChatGPT or another model) with Taplio's scheduling workflow, then closing the loop with analytics. This repository is a working implementation: a Streamlit application plus generated deliverables, documentation and tests.

In scope: profile audit, content pillars, idea and draft generation, 6-week calendar, Taplio-ready queue, engagement tracking, analytics, performance review, backups, documentation.
Out of scope: posting to LinkedIn automatically (LinkedIn and Taplio do not offer a free public API for this, and automation would break the authenticity requirement), storing LinkedIn or Taplio passwords, paid-tier Taplio features.

## 2. Stakeholders and user paths
| Path | Story (from the brief) | What changes in the product |
|---|---|---|
| Working professional | Guided workflow to post consistently and grow a personal brand | Balanced pillar mix, Tue-Thu rhythm, KPI: impressions, comments, profile visits |
| Job seeker | Optimize presence to attract recruiters and opportunities | More tips and personal journey, Open-to-Work checks, recruiter-focused CTAs, KPI: profile visits, recruiter messages |
| Thought leader / entrepreneur | Scale influence with AI content in my brand voice | Thought-leadership and trends weighted up, carousel-heavy, debate CTAs, KPI: followers, shares, leads |

## 3. Functional requirements
| ID | Requirement | Brief part | Implemented in |
|---|---|---|---|
| FR-01 | Collect inputs: profile, audience/industry, role models, IDs, stories, cadence | 10 | `ui/inputs.py`, `settings.py` |
| FR-02 | Never ask for passwords; keys stored locally only and excluded from backups | 9 | `settings.py`, `backup.py` |
| FR-03 | Branding audit with a scored checklist and current-vs-optimized headline/About | 7.1, 8 | `audit.py` |
| FR-04 | Define 3-5 content pillars with target mix | 7.2, 16 | `audit.build_pillars`, `context.effective_weights` |
| FR-05 | Generate at least 15 ideas (Template A) | 5, 17 | `ideation.py` |
| FR-06 | Produce 10+ drafts in text, poll, carousel and micro-story formats | 5, 8, 16 | `drafting.py` |
| FR-07 | Template B tone rewrite and Template C article-to-post | 17 | `drafting.rewrite_tone`, `article_to_post` |
| FR-08 | Score every draft for quality, inclusivity and source attribution; human-review gate | 19 | `quality.py`, `ui/phase2.py` |
| FR-09 | Plan 2-3 pilot posts | 7.5 | `planner.py` (first three slots) |
| FR-10 | 6-week calendar (.xlsx/.csv) with dates, themes, draft content | 7.6, 8 | `calendar_builder.py` |
| FR-11 | Taplio-ready queue, copy-paste pack, Sheets CSV, .ics reminders | 7.4, 9, 15 | `plugins/export_*.py` |
| FR-12 | Track likes, comments, shares, impressions, profile visits per post; manual entry and CSV import | 5, 18 | `analytics.py`, `ui/phase4.py` |
| FR-13 | Weekly dashboard, top posts, pillar/format/weekday analysis | 18 | `analytics.py`, `reports.build_dashboard` |
| FR-14 | Actionable insights and next-cycle pillar mix | 7.7, 15 | `analytics.insights`, `refine_weights` |
| FR-15 | Performance Review Report, Branding Audit Report, Optimized Drafts (.docx), Capstone Report | 8 | `reports.py` |
| FR-16 | Self-scorecard on the 30/25/20/15/10 evaluation weights | 11 | `analytics.scorecard` |
| FR-17 | One-click automated pipeline for Phases 1-5 plus deliverables | 3, 14 | `pipeline.py` |
| FR-18 | Backup after every phase run, full snapshots, safe restore | project request | `backup.py` |
| FR-19 | Plugin system for AI engines, exports and importers | project request | `plugins/` |
| FR-20 | Compare all three user paths side by side and switch path | 4 | `personas.py`, `ui/persona_lab.py` |
| FR-21 | Risk mitigations built in (low engagement, free-tier limits, AI over-reliance, drop-off) | 23 | `analytics.insights`, `quality.py`, `plugins`, `.ics` |

## 4. Non-functional requirements
- **Usability:** colourful, guided UI; every page explains the next step; errors are plain language.
- **Reliability:** if an AI call fails the template engine takes over; the pipeline never stops for that reason. Failures are written to `logs/lil.log`.
- **Reproducibility:** one command starts the app; outputs are deterministic for the same inputs when using the template engine.
- **Modularity:** one module per responsibility, one folder per phase and per deliverable set.
- **Privacy:** data stays on the user's computer. API keys are in `data/inputs/plugins.json` only.
- **Honesty:** demo data is always labelled, stored separately and never mixed with real metrics.

## 5. Technical requirements
- Python 3.10 or newer (tested on 3.12). Packages: see `requirements.txt` (streamlit, pandas, openpyxl, python-docx, plotly, matplotlib, requests).
- Optional: an OpenAI or Anthropic API key; a Taplio free account; a Google account for Drive/Sheets.
- Browser: any modern browser.
- **Known conflict with the brief:** the brief asks for a web-based tool with no additional installations. A Python app needs Python on the computer. Options: run locally (default), or deploy the same code to a free host such as Streamlit Community Cloud so reviewers open a link.

## 6. Constraints and assumptions
- Taplio free-tier limits (reduced analytics, some features paid). The product therefore supports manual entry and CSV import so analytics never depend on a paid feature. Check your own plan: Taplio changes plans over time.
- ChatGPT is optional but supported via the OpenAI plugin; Claude is also supported.
- Real engagement only exists after real posting; the dashboards stay empty (or show clearly labelled demo data) until then.

## 7. Acceptance criteria and where they are checked
| Criterion (brief part 5 and 21) | Check |
|---|---|
| 15+ ideas | Command Center tracker; `tests/test_engines.py` |
| 10+ posts published | Tracker counts real logged posts (needs your posting) |
| Metrics tracked per post | Phase 4 page; tracker |
| 6-week calendar | Phase 3 output; `tests/test_pipeline.py` |
| Performance review with recommendations | Phase 5 and `05_performance_review_report` |
| 10+ optimized drafts, branding audit | Phase 2, Phase 1 and `tests` |

## 8. Known limitations (read before submitting)
- The template engine writes sound first drafts from your inputs, but they need your real examples and voice. Drafts with `[placeholders]` are flagged and score lower until fixed.
- AI plugins were verified with mocked API responses (success, malformed reply, error and fallback). They were not exercised against live OpenAI or Anthropic servers because that needs your keys.
- LinkedIn publishing and Taplio scheduling remain manual steps by design.
