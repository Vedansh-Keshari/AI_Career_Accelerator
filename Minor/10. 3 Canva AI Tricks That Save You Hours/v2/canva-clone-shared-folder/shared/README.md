# shared/

The engine used by both the website (`web/`) and the desktop app (`desktop/`). Keep this folder next to them.

* `studio/` - the code (see `dev/README.md` for a map): rendering, project format, Canva client, server, desktop window, AI.
* `studio/static/` - the web interface (HTML, CSS, JavaScript) shown by both apps.
* `data/test_data.json` - the notes' scenarios as five ready-made example projects.
* `assets/fonts/` - Poppins (SIL Open Font License) and DejaVu fonts (free licence).
* `config.example.json` - optional: copy to `config.json` with your Canva client id/secret. Settings inside the app is easier.
* `tests/` - automated tests (engine, Canva flow, export, secrets, AI, golden images, Windows compatibility, browser test).
* `windows-tests/` - **the Windows test pack**: one-click runner, environment checks and the test document.
* `dev/` - developer notes, CI recipe, lint/type configuration.
