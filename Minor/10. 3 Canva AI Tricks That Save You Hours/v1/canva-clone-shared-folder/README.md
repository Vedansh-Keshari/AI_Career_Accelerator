# shared/

Used by both the website (`web/`) and the desktop app (`desktop/`). Keep this folder next to them.

* `studio/options.py` - the option lists from the notes (audience, 13 styles, lengths, 30 themes, 11 colours, formats, 15 document types) and colour palettes.
* `studio/render.py` - draws slides, document pages and logos (Pillow). 13 style looks, 4 logo layouts, 8 icons.
* `studio/generator.py` - template-based starter outlines and the plain-words "Refine" rules.
* `studio/models.py` - project format and saving (JSON files in `~/.canvas_studio/projects`).
* `studio/canva_client.py` - Canva Connect API: OAuth with PKCE, asset upload, design creation, design import.
* `studio/mock_canva.py` - the local demo Canva used when no keys are configured.
* `data/test_data.json` - the notes' scenarios as five ready-made example projects.
* `assets/fonts/` - Poppins (SIL Open Font License) and DejaVu Serif (free licence).
* `config.example.json` - copy to `config.json` and add your Canva client id and secret (never share that file).
* `tests/` - engine and Canva-flow tests.
