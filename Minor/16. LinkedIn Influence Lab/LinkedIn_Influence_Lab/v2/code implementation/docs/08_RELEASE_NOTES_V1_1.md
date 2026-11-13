# Release Notes: Version 1.1

Version 1.1 keeps everything from 1.0 and adds the items below. The requirements document (`01`) is unchanged; the additional requirements are listed here so nothing is lost.

## What changed, in the order requested
| Request | What you will see |
|---|---|
| Sample data for every step | On first launch the app opens a **🧪 Sample data** workspace: a complete fictional person for each of the three paths, with ideas, drafts, calendar, logged engagement, weekly KPIs and path-specific data. Switch to **👤 My workspace** (sidebar) for your own, empty workspace. Sample and real data never mix. |
| Guidance on what type of data to enter | The Inputs page has a data guide (type, rule, example, why), tooltips and placeholders on every field, character limits, and clear validation messages. Phase 4, the CSV importer, Template C, the job-description matcher and plugin keys show the expected format too. Fill-the-form samples, a blank CSV template and an example export are provided. |
| Professional capstone report | New cover page and document control, contents page, running header and footer with page numbers, refined tables, KPI tiles, numbered figures, glossary, traceability appendix and sign-off page. All reports share the same house style. |
| More professional diagrams | Same hues in deeper shades and a cleaner flat style: workflow, phase dependencies and architecture. |
| Pipeline details | The Command Center explains what each phase does, needs, depends on, produces and hands on; shows a readiness check; offers run-one-phase buttons that respect dependencies; and keeps a log of the last full run. |
| Persona Lab: major change | Each path now sees **only its own tabs** (Consistency Hub, Recruiter Hub or Authority Studio), its own weekly KPIs and targets, review focus and rhythm. The Persona Lab shows exactly what changes in every phase if you switch, benefits and setbacks of each path, and a set of selectable first hooks you can preview and pin. |
| Downloads | Each deliverable set has a **Download all (ZIP)** button, and one button downloads every file from every set. |
| Snapshot and restore | Checksummed backups, integrity check, snapshot restore, backup download and import, and an in-app explanation. See `docs/07_BACKUP_AND_RESTORE.md`. Storage is plain files; no database. |
| Admin-only Folder map | The toggle is visible to everyone but only an administrator can open it. The project structure guide (`03`) is restricted in the same way inside the app. |
| Docs & Help | Both tabs unchanged. Two documents were added to the list. |

## Additional requirements (continuing the numbering of document 01)
| ID | Requirement | Implemented in |
|---|---|---|
| FR-22 | Separate sample workspace with complete fictional data for each path | `samples.py`, `paths.py`, `sample_data/` |
| FR-23 | Field guidance and validation for every input | `guidance.py`, `ui/inputs.py` |
| FR-24 | Empty states that say what a step needs; sample helpers; blank templates | `ui/*`, `sample_data/` |
| FR-25 | Pipeline guide, readiness check, single-phase runs, last-run log | `phase_spec.py`, `ui/command_center.py`, `pipeline.py` |
| FR-26 | Path-specific navigation and hubs | `persona_content.py`, `hubs.py`, `ui/hub_*.py` |
| FR-27 | Weekly path KPIs with targets, progress and insights | `hubs.py`, `ui/phase4.py`, `ui/phase5.py` |
| FR-28 | Persona Lab: impact preview, benefits/setbacks, hook options and pinning | `personas.py`, `ui/persona_lab.py` |
| FR-29 | Live dashboards in Phases 4 and 5; apply the refined mix to the next cycle | `pipeline.analyse`, `context.py` |
| FR-30 | Download-all per set and for all sets | `exports.py`, `ui/deliverables_page.py` |
| FR-31 | Checksummed backups with verify, snapshot restore, import and download | `backup.py` |
| FR-32 | Admin role with restricted Folder map | `auth.py`, `ui/access.py` |
| FR-33 | Professional report house style | `docx_kit.py`, `reports.py` |
| FR-34 | Refreshed diagrams | `charts.py` |

## Admin access: what it is and is not
The first person to open **🔐 Admin access** on a new installation creates the admin passcode (8+ characters). It is stored only as a salted PBKDF2 hash in `data/admin.json`. For hosted deployments set the `LIL_ADMIN_PASSCODE` environment variable instead. This protects the **interface**. It is not file-system security: anyone who can open the project folder on the computer can still read its files. Use operating-system permissions for that.

## Known limits (unchanged from 1.0)
Publishing on LinkedIn and scheduling in Taplio remain manual. AI plugins were verified with mocked responses, not live accounts. Demo/sample numbers are fictional.
