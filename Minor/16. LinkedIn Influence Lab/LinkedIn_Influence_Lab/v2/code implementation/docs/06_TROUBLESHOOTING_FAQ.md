# Troubleshooting FAQ and Support

## Support (from the project brief)
Contact: [Your Name], [Email], [Slack/Teams Channel] (fill in for your client).
| Request | Target response |
|---|---|
| Content ideation requests | 1 business day |
| Post drafting / refinement | 2-3 days |
| Analytics reporting | Weekly |

## Start-up problems
**`python` is not recognised (Windows).** Reinstall Python and tick "Add python.exe to PATH", then double-click `run_app.bat` again.
**The browser did not open.** Open http://localhost:8501. If the port is busy run `python -m streamlit run app.py --server.port 8502`.
**Package install fails.** Check the internet connection, then run `python -m pip install -r requirements.txt` in the project folder.
**Black window closes immediately.** Run `run_app.bat` from a Command Prompt to read the message.

## Using the app
**"Please complete these inputs first".** Required inputs are name, role, industry, audience, goal and key skills.
**Drafts contain [add your real example here].** Add a win, mistake, lesson and achievements in Inputs, then re-run Phase 2, or replace the text by hand. Placeholders lower the quality score on purpose.
**Posts feel generic.** Add real stories and numbers, connect an AI plugin, then use Regenerate and Rewrite tone. Always edit in your voice.
**The AI plugin does nothing.** Use Test the active AI connection. Common causes: no key, wrong model name, no credit or no internet. The error is shown and also written to `logs/lil.log`. The template engine is used meanwhile.
**The Taplio approved-only queue is empty.** Posts only go there after you tick Human reviewed. Press Run Phase 3 again afterwards.
**Taplio does not accept my CSV.** Taplio's features depend on your plan. Use `copy_paste_pack.txt` and paste posts into Taplio's composer.
**Analytics import looks wrong.** The importer recognises columns such as Impressions, Reactions or Likes, Comments, Reposts or Shares, Profile views. Without a post id column rows are matched to your posts in calendar order; check the warning shown.
**Dashboard says DEMO.** It is built from simulated data. Log real posts in Phase 4 and press Run analytics again.
**Phase 4 or 5 shows "Waiting on you".** Fewer than 10 real posts are logged. This is intentional.
**Charts or report look empty.** No real engagement is logged yet.
**I overwrote something.** Open Deliverables & Backups and restore the phase backup (the current state is backed up first).

## Where to look
| Symptom | Look at |
|---|---|
| Any error | `logs/lil.log` |
| Wrong content wording | `src/lil/knowledge.py` |
| Wrong dates or pillar mix | `src/lil/planner.py`, `context.py` |
| Report layout | `src/lil/reports.py`, `docx_kit.py` |
| Colours or layout of pages | `src/lil/theme.py`, `.streamlit/config.toml` |
| A new tool or export | `src/lil/plugins/` |
| Folder locations | `src/lil/paths.py` |

## Run the automated tests
`python -m pip install pytest` then `python -m pytest tests -q`. Tests use a temporary workspace and never touch your data.

## New in 1.1
**Which workspace am I in?** The sidebar radio and, in the sample workspace, a coloured bar at the top of every page.
**My pages are empty.** You are probably in 👤 My workspace with no data yet. Each page says what it needs. Switch to 🧪 Sample data to see a complete example.
**Reset the sample.** Persona Lab > What changes if I switch > pick another path and switch, or delete the `sample_workspace` folder while the app is stopped; it is rebuilt on the next launch.
**I forgot the admin passcode.** Stop the app, delete `data/admin.json`, start the app and create a new passcode. (Whoever can do this has file access to the installation. That is why this is interface-level gating only.)
**Folder map is locked.** Only an admin can open it. Sign in under 🔐 Admin access.
**A restore was refused.** The backup failed its checksum test. Use another backup; see `docs/07_BACKUP_AND_RESTORE.md`.
**Switching path changed my sidebar.** By design: each path shows only its own tools.
