# shared/

The engine this program runs on. It is part of this package - **keep it inside this folder, next to `app.py`** (nothing else needs to be set up).

* `studio/` - the code (see `dev/README.md` for a map) and `studio/static/` - the web interface.
* `data/test_data.json` - the notes' scenarios as five ready-made example projects.
* `assets/fonts/` - Poppins (SIL Open Font License) and DejaVu fonts (free licence).
* `config.example.json` - optional: copy to `config.json` with your Canva client id/secret (Settings inside the app is easier).
* `tests/` - automated tests. `windows-tests/` - the Windows test pack. `dev/` - developer notes, CI recipe, lint/type configuration.
