# Architecture and Design

## 1. The automated flow
```
Inputs (you) -> ChatGPT / AI plugin -> Taplio -> LinkedIn -> Analytics -> back to Inputs
```
`pipeline.run_all()` automates everything except the steps that must stay human: reviewing drafts, publishing, and reporting real numbers. A picture of the loop is generated to `deliverables/03_engagement_dashboard/charts/workflow.png` and shown on the Command Center.

## 2. Layers
```
UI            app.py  ->  src/lil/ui/*.py  (one page per file)  + theme.py, compat.py
Orchestration pipeline.py (run_phase1..5, build_deliverables, run_all)   backup.py
Engines       audit  ideation  drafting  quality  planner  analytics  personas  calendar_builder
Output        reports.py  charts.py  docx_kit.py
Plugins       plugins/ai_*  plugins/export_*  plugins/import_*   llm.py (safe AI wrapper)
Foundation    paths.py  store.py  settings.py  context.py  knowledge.py  folder_map.py  trace.py
Data          data/ (inputs, state)  phases/  deliverables/  backups/  logs/
```
Rule of thumb: UI calls pipeline or engines; engines never import the UI; content (wording, hooks, weights) lives only in `knowledge.py`.

## 3. Phases, timeline and backups
| Phase | Brief timeline | Output folder | Backup |
|---|---|---|---|
| 1 Foundation: audit and pillars | Week 1 | `phases/phase_1_foundation` | zip in `backups/` |
| 2 AI ideation and drafting (pilot picked) | Week 2 | `phases/phase_2_ideation_drafting` | zip, plus a `before_rerun` zip if drafts already exist |
| 3 Calendar and Taplio setup | Week 3 | `phases/phase_3_calendar_taplio` | zip |
| 4 Publish and track | Weeks 4-5 | `phases/phase_4_publish_track` | zip |
| 5 Analytics and review | Week 6 | `phases/phase_5_analytics_review` | zip |

A phase is **Complete** when its acceptance work is finished, **Waiting on you** when the app has done its part and needs your action (for example drafts still contain placeholders, or fewer than 10 real posts are logged) and **Preview** when built from demo data. Backups keep the 12 newest zips per phase; `FULL_SNAPSHOT__*.zip` is never pruned.

## 4. Data model (all plain JSON/CSV, safe to open by hand)
- `data/inputs/profile.json`: your inputs. `plugins.json`: plugin switches and keys.
- `data/state/status.json`: phase ledger.
- Phase 2: `slots.json` (date, pillar, format), `ideas.json`, `drafts.json` (text, quality, `human_reviewed`).
- Phase 3: `calendar.json` (slot + draft id + status). Phase 4: `engagement.csv` (real), `engagement_demo.csv` (simulated).
- Phase 5: `metrics_summary.json`, `insights.json`, `scorecard.json`, `refined_weights.json`.

## 5. Plugin contract
Create `src/lil/plugins/my_plugin.py`:
```python
PLUGIN = {"id": "export_notion", "name": "Notion pack", "category": "export", "icon": "📓",
          "description": "...", "fields": [{"key": "token", "label": "Token", "type": "password", "default": ""}]}
def export(profile, calendar, drafts, out_dir): ...   # return list of written Paths
```
AI plugins implement `complete(cfg, system, prompt) -> str`. Importers expose a mapping function. Nothing else needs editing: the registry (`plugins/__init__.py`) discovers files automatically and the Plugins page renders the fields.

## 6. How the numbers are computed
**Slot plan.** Pillars follow a smooth weighted round-robin so the mix matches the weights and no pillar repeats back to back. Formats follow the path's rotation; the first three slots are the pilot (text, poll, micro-story) so the pilot tests three formats.

**Quality score (0-100, start at 100).** -10 hook over 140 chars; -12 too short (500 chars; 250 for polls/carousels; 400 for micro-stories); -10 over 2,600 chars; -20 placeholder left; -10 no call to action; -6 more than 5 hashtags; -5 more than 3 emojis; -6 long sentences; -4 per non-inclusive term; -8 statistic without named source; -6 impersonal voice. Bands: 90+ Excellent, 75+ Good, 60+ Needs work.

**Audit score (0-100).** Twelve checklist items with weights (photo 8, banner 6, headline 14, About 14, custom URL 4, Featured 8, skills 6, recommendations 8, experience numbers 12, visibility 6, cadence 8, network 6). Headline scores by length and structure; About by length and a call to action.

**Engagement rate** = (likes + comments + shares) / impressions.

**Scorecard** (brief part 11): Content Quality 30% = average draft quality; Consistency 25% = logged posts / posts due so far; Engagement Growth 20% = 50 + 0.5 x percent change in weekly rate from first to latest week, capped 0-100; Branding Alignment 15% = 100 x (1 - total variation distance between planned and target pillar mix); Documentation 10% = required docs present. Criteria without data yet are skipped and the total is marked provisional.

**Next-cycle mix.** Best pillar +10 points, weakest -5 (floor 5), then renormalised.

## 7. Design decisions
- Template engine first, AI second: the product works offline and in demos; AI improves it when available.
- Human-review gate instead of silent automation: protects authenticity (brief part 19).
- Demo data separated from real data so reports can never accidentally present simulated numbers as results.
- All locations in `paths.py` and `LIL_HOME` override so tests and clients can relocate the workspace.

## 8. Version 1.1 additions
**Workspaces.** `paths.home()` returns the active workspace: your own (`<project>/`) or the sample one (`<project>/sample_workspace/`). The Streamlit app registers a resolver so each browser session picks its own. Program files (docs, templates, sample data) always come from `paths.app_root()`.

**Roles.** Member (default) and Admin (passcode, `auth.py`). The only admin-gated items are the Folder map and the project structure guide. This is interface-level gating, not file-system security.

**Path-specific navigation.** `persona_content.nav_keys(persona)` decides which tabs the sidebar shows: the common pages plus that path's hub (`hubs.py`, `ui/hub_*.py`). Weekly path KPIs live in `phases/phase_4_publish_track/persona_kpis.csv`; hub data lives in `data/hub/`.

**Phase guide.** `phase_spec.py` is the single description of what each phase does, needs, produces and hands on. `pipeline.phase_ready()` enforces the hard dependencies (Phase 3 needs Phase 2, Phase 4 needs Phase 3, Phase 5 needs logged engagement). Phase 1 to Phase 2 is a soft link.

**Closing the loop.** `pipeline.analyse()` is read-only and powers the live dashboards. Applying the recommended mix stores `custom_weights` in the profile; `context.effective_weights()` uses it on the next Phase 2 run. Pinned hooks (`pinned_hooks` in the profile) are used first by `ideation.py`.

**Backups.** Checksummed zips; see `docs/07_BACKUP_AND_RESTORE.md`.

**Reports.** `docx_kit.py` is the house style (cover, document control, header/footer with page numbers, tables, tiles, callouts, sign-off); `reports.py` fills it; `charts.py` draws the diagrams and charts.
