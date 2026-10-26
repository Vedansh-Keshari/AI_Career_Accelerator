# Canvas Studio - desktop app

Needs the `shared` folder next to this one (see the top-level README). Double-click `run.bat` (or `./run.sh`).
Windows and macOS include tkinter with Python; on Linux install `python3-tk`.

Sign-in opens your browser; the app listens on 127.0.0.1:5001 for Canva's redirect, so keep that port free.

Tests (needs a display): `python -m pytest tests -q`
