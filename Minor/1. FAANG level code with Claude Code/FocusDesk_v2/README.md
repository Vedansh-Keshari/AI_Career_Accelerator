# 🎯 FocusDesk (v2)

A colourful, local-first productivity app built with **Python + Streamlit**. Manage tasks, log focused work sessions, and see your week at a glance. No external APIs, and your data never leaves your machine.

## What's new in v2
- **Email required to enter**: the app opens on an email screen; nothing else is reachable until a valid email is entered.
- **Per-user data**: each email gets its own data file, so several people can share one computer.
- **Colourful UI**: gradient banner, four coloured headline cards, priority-coloured task cards, colour-coded chips, coloured charts and sidebar.
- **Sample (model) data**: one click loads realistic tasks and sessions so you can test every feature; one click removes them again.
- **Safer rendering and loading**: user text is HTML-escaped, and hand-edited or damaged data files are repaired or backed up instead of crashing the app.
- **Docs bundle**: `information.txt` (what every file does), `commands.doc` (Claude Code command reference) and `commands_flowchart.png` (visual command map).

## Features
- **Tasks**: priority (High / Medium / Low), optional due date; mark done, reopen, delete.
- **Smart ordering**: open tasks sorted by priority, then soonest due date; overdue tasks flagged in red.
- **Filters & search**: by status and priority, plus free-text search.
- **Focus log**: record sessions (minutes, date, task, note).
- **Insights**: 7-day focus chart, open-tasks-by-priority bars, totals.
- **CSV export** of your tasks.
- **Safe persistence**: JSON files with atomic writes.

## Requirements
- Python 3.10 or newer
- `streamlit`, `pandas` (and `pytest` for the tests), all listed in `requirements.txt`

## Installation
```bash
cd focusdesk
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

## Usage
```bash
streamlit run app.py
```
If that command isn't found (environment or PATH issues):
```bash
python -m streamlit run app.py
```
Open the **Local URL** printed in the terminal (usually http://localhost:8501).

1. **Enter your email** on the first screen (required).
2. Add a task, pick a priority, click **Add task**. Use ✅ to complete it.
3. Log work in **Focus log**; see charts in **Insights**.
4. Want to explore first? Click **Load sample data** in the sidebar (and **Remove sample data** when done).
5. **Switch user** in the sidebar returns to the email screen.

> **About the email:** FocusDesk checks that it is a correctly formatted address. It does *not* send a confirmation message or verify ownership (there is no mail server). It is used only to keep each person's data separate, and is stored only on your computer.

### Where is my data?
In the `data/` folder, one file per email (`user_<hash>.json`; the file name is a hash, the email is stored inside as `owner`). To use another folder:
```bash
FOCUSDESK_DATA_DIR=/path/to/folder streamlit run app.py
```
*Upgrading from v1?* On the first login, an existing `data/focusdesk.json` from v1 is adopted by that user and kept as `focusdesk.v1-backup.json`.

## Supported Priorities
`High`, `Medium`, `Low`. Edit `PRIORITIES` in `logic.py` (and `PRIORITY_STYLE` in `theme.py`) to change them.

## Application Structure
```
focusdesk/
├── app.py               # Streamlit UI: email gate, tabs, forms, callbacks
├── logic.py             # Business logic: email check, tasks, sessions, stats
├── storage.py           # Per-user JSON persistence, v1 migration, safe loading
├── theme.py             # Colours, CSS and HTML helpers (all text escaped)
├── sample_data.py       # Model data: load / remove sample tasks and sessions
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   └── config.toml      # Streamlit colour theme
├── tests/
│   ├── conftest.py      # Lets tests import the project modules
│   ├── test_logic.py    # Logic, email rules, storage
│   ├── test_sample_data.py  # Model data with known expected results
│   ├── test_theme.py    # HTML helpers and escaping
│   └── test_app.py      # UI tests driving the real app (AppTest)
├── docs/
│   ├── information.txt          # What every file is and does
│   ├── commands.doc             # Claude Code command reference
│   └── commands_flowchart.png   # Visual map of those commands
└── data/                # Created on first save (git-ignored)
```

## How It Works
1. `app.py` shows the email screen until `logic.validate_email()` accepts an address.
2. `storage.load(email)` reads that user's file; UI actions call pure functions in `logic.py`, then `storage.save()`.
3. Streamlit re-runs the script and redraws the cards, lists and charts using helpers from `theme.py`.

Keeping logic separate from the UI makes it easy to modify and extend (tags, recurring tasks, a Pomodoro countdown...).

## Testing
```bash
python -m pytest -q
```
The tests cover the email gate (empty, malformed and valid emails), per-user data separation, v1 migration, sample data with known expected numbers (8 open, 2 overdue, 2 done this week, 365 focus minutes), HTML escaping and the full add / complete / delete / log flows in the real app.

## Screenshots
Run the app and add screenshots to `docs/`, then link them here:
`![Tasks tab](docs/tasks.png)`

## Contributing
1. Fork the repository and create a feature branch.
2. Add or update tests for your change.
3. Run `python -m pytest -q` and make sure everything passes.
4. Open a pull request describing what and why.

## License
MIT. Free to use, modify, and distribute. Add a `LICENSE` file with the standard MIT text before publishing.
