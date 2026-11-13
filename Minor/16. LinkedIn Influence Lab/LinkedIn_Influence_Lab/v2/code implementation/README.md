# 🚀 LinkedIn Influence Lab (LIL-2025-P1) - Industrial Capstone

An AI-guided personal-branding system: **Inputs → ChatGPT/AI → Taplio → LinkedIn → Analytics → back to Inputs**, automated end to end except the steps that must stay human (reviewing, publishing, reporting real numbers).

**Start:** double-click `run_app.bat` (Windows) or `./run_app.sh`. Full steps in `HOW_TO_RUN.txt`.

## What you get
- Branding audit with a scored checklist, optimized headline and About
- 3-5 content pillars with a target mix; all three user paths (professional, job seeker, thought leader) explored side by side
- 15+ ideas, 10+ drafts (text, poll, carousel, micro-story), quality/inclusivity/source checks, human-review gate
- 6-week calendar (.xlsx/.csv/.ics) and Taplio-ready queue
- Engagement tracking (manual or CSV import), dashboard, insights, self-scorecard on the brief's 30/25/20/15/10 criteria
- Five Word/Excel deliverables plus a combined capstone report
- Backup after every phase, plugin system (ChatGPT, Claude, exports, importers)

## Phases
| # | Phase | Week | Folder |
|---|---|---|---|
| 1 | Foundation: audit & pillars | 1 | `phases/phase_1_foundation` |
| 2 | AI ideation & drafting | 2 | `phases/phase_2_ideation_drafting` |
| 3 | Calendar & Taplio setup | 3 | `phases/phase_3_calendar_taplio` |
| 4 | Publish & track | 4-5 | `phases/phase_4_publish_track` |
| 5 | Analytics & review | 6 | `phases/phase_5_analytics_review` |

## Documentation
`docs/01` requirements · `02` architecture · `03` project structure · `04` beginner guide · `05` traceability to the 24 brief sections · `06` troubleshooting & support.

## New in 1.1
Sample workspace for every path · field-level data guidance · path-specific tabs (Consistency Hub, Recruiter Hub, Authority Studio) · Persona Lab with impact preview, benefits/setbacks and selectable hooks · download-all buttons · checksummed backups with snapshot restore · admin-only Folder map · professional report style. See `docs/08_RELEASE_NOTES_V1_1.md`.

## Honest notes
- Publishing on LinkedIn and scheduling in Taplio are manual by design; the app prepares everything for them.
- Demo data is simulated and always labelled; real metrics appear only after you publish and log them.
- AI plugins were tested with mocked API replies; connect your own key to use them live.
- The brief asks for "web-based, no installations"; this app needs Python locally, or free hosting (see HOW_TO_RUN.txt).
