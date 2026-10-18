# 🎯 FocusDesk

A simple, local-first productivity app built with **Python + Streamlit**. Manage tasks, log focused work sessions, and see your week at a glance. No accounts, no external APIs, and your data never leaves your machine.

## Features
- **Tasks**: add tasks with priority (High / Medium / Low) and optional due dates; mark done, reopen, or delete.
- **Smart ordering**: open tasks sorted by priority, then soonest due date; overdue tasks are flagged.
- **Filters & search**: filter by status and priority, search by title.
- **Focus log**: record focus sessions (minutes, date, task, note).
- **Insights**: weekly metrics and a 7-day focus chart.
- **CSV export** of your tasks.
- **Safe persistence**: data saved to a local JSON file using atomic writes; a corrupt file is backed up rather than overwritten.

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
Then open the **Local URL** printed in the terminal (usually http://localhost:8501).

**Quick start:** type a task, pick a priority, click **Add task**. Use ✅ to complete it. Log work in the **Focus log** tab and check the **Insights** tab.

### Where is my data?
`data/focusdesk.json` inside the project folder. To store it elsewhere, set an environment variable before launching:
```bash
FOCUSDESK_DATA=/path/to/my_data.json streamlit run app.py
```

## Supported Priorities
`High`, `Medium`, `Low`. Edit `PRIORITIES` in `logic.py` to change them.

## Application Structure
```
focusdesk/
├── app.py            # Streamlit UI (tabs, forms, callbacks)
├── logic.py          # Business logic: tasks, sessions, stats (no UI code)
├── storage.py        # JSON persistence with atomic writes
├── requirements.txt
├── tests/
│   ├── test_logic.py # Unit tests for logic + storage
│   └── test_app.py   # UI tests driving the real app via Streamlit AppTest
└── data/             # Created on first save (git-ignored)
```

## How It Works
1. `app.py` loads data once per session via `storage.load()`.
2. UI actions call pure functions in `logic.py` and then `storage.save()`.
3. Streamlit re-runs the script and redraws metrics, lists, and charts from the updated data.

Keeping logic separate from the UI makes it easy to modify and extend (for example, add tags, recurring tasks, or a Pomodoro countdown).

## Testing
```bash
python -m pytest -q
```

## Screenshots
Run the app and add screenshots to a `docs/` folder, then link them here:
`![Tasks tab](docs/tasks.png)`

## Contributing
1. Fork the repository and create a feature branch.
2. Add or update tests for your change.
3. Run `python -m pytest -q` and make sure everything passes.
4. Open a pull request describing what and why.

## License
MIT. Free to use, modify, and distribute. Add a `LICENSE` file with the standard MIT text before publishing.
