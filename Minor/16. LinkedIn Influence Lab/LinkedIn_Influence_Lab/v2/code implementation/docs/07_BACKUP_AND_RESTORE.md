# Backups, Snapshots and Restore

## 1. What is used to store things? (no database)
The project deliberately uses **no database**. All data is kept in ordinary files inside the active workspace, which makes it portable, inspectable and easy to archive.

| Data | Format | Location (inside the workspace) |
|---|---|---|
| Your inputs (profile) | JSON | `data/inputs/profile.json` |
| API keys and plugin switches | JSON, **never backed up or exported** | `data/inputs/plugins.json` |
| Phase working data: ideas, drafts, calendar, engagement, metrics | JSON, CSV | `phases/<phase folder>/` |
| Path hub data: peer log, opportunities, leads, series | CSV, JSON | `data/hub/` |
| Phase status ledger, last run log | JSON | `data/state/` |
| Client files | DOCX, XLSX, CSV, ICS, PNG | `deliverables/<set>/` |
| Backups | ZIP containing `MANIFEST.json` (SHA-256 per file) | `backups/` |
| Admin passcode (outside any workspace) | Salted PBKDF2 hash, JSON | `data/admin.json` |

The workspace is `<project>/` for your own data and `<project>/sample_workspace/` for the sample data. The two never share files or backups.

If you outgrow files (many users, many accounts), the natural next step is SQLite behind the same functions in `store.py`; nothing else in the app would need to change.

## 2. Two kinds of backup
**Phase backup** - `phase_N_<name>__<timestamp>[__tag].zip`
- Created every time a phase runs.
- Contains that phase's working files and your profile.
- Phase 2 and 3 also create a `before_rerun` backup first, so hand-edited drafts or statuses are never lost when you re-run them.
- The newest 12 per phase are kept; older ones are removed automatically.

**Full snapshot** - `FULL_SNAPSHOT__<timestamp>[__tag].zip`
- Created at the end of the automated pipeline, when you press **Create a full snapshot now**, and automatically before every restore (`before_restore`).
- Contains: `phases/`, `deliverables/`, `data/hub/`, `data/state/` and `data/inputs/profile.json`.
- Never contains: API keys, the admin passcode, or other backups.
- Never deleted automatically.

Every zip carries a `MANIFEST.json`: type, creation time, workspace, tag, and for each file its path, size and SHA-256 checksum.

## 3. How a restore works
1. **Verify.** Each file in the zip is re-read and its SHA-256 compared with the manifest. If anything is missing or changed the restore is refused.
2. **Safety snapshot.** The current state is saved as `FULL_SNAPSHOT__..__before_restore.zip`, so a restore can be undone by restoring that snapshot.
3. **Clear.** The folders the backup covers are emptied: one phase folder for a phase backup; `phases/`, `deliverables/`, `data/hub/` and `data/state/` for a snapshot. This makes the result match the backup exactly instead of mixing old and new files.
4. **Extract.** Files are written back. Paths outside the allowed list, absolute paths and `..` paths are ignored (zip-slip protection).

## 4. Doing it in the app
Open **📦 Deliverables & Backups**:
- **Select a backup** to see its type, date, file count and which folders it covers.
- **Verify integrity** to re-check checksums without restoring.
- **Download this backup** to keep a copy elsewhere.
- **Import a backup made elsewhere** to bring a zip from another computer (it must have a valid manifest and pass the checksum test).
- **Restore selected backup** after ticking the confirmation box.

## 5. Doing it by hand
A backup is a normal zip. To inspect: open it and read `MANIFEST.json`. To restore manually: close the app, copy the zip's `phases/`, `deliverables/` and `data/` folders over the workspace, start the app.

## 6. Good practice
- Download a full snapshot before submitting deliverables or handing the project to a client.
- Keep a copy on a different drive or cloud folder: backups in the project folder do not protect against losing the computer.
- If a restore is refused, the backup is damaged. Use another one; the newest phase backups are usually enough.
