# Canvas Studio - website

Needs the `shared` folder next to this one (see the top-level README). Double-click `run.bat`
(or `./run.sh`), then use http://127.0.0.1:5000

Environment variables: `PORT` (default 5000), `HOST` (default 127.0.0.1 - keep it local), `NO_BROWSER=1`.
If you change the port, add the matching redirect URL in your Canva integration and in `shared/config.json`.

Tests: `python -m pytest tests -q`
