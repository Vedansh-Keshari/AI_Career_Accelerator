# For developers

```
pip install -r shared/dev/requirements-dev.txt
ruff check shared app.py tests --config shared/pyproject.toml     # lint
cd shared && mypy --config-file pyproject.toml                   # types
python -m pytest shared/tests tests -q         # automated tests (about 2 minutes)
python -m playwright install chromium && python shared/tests/e2e_browser.py   # real-browser test
```

* `github-ci.yml` - copy to `.github/workflows/ci.yml` for Windows + macOS + Linux builds on every push.
* Golden images: `shared/tests/golden/` holds reference pictures. After an *intended* look change run
  `UPDATE_GOLDEN=1 python -m pytest shared/tests -k golden` and commit the new pictures.
* Windows testing: see `shared/windows-tests/WINDOWS_TEST_DOCUMENT.md`.
* Packaging (desktop package only): `build_windows.bat` builds `CanvasStudio.exe` (PyInstaller) and, if Inno Setup is installed, a Setup.exe.

Project layout of the engine (`shared/studio/`): `render/` (base, decor, slides, free, documents, logos, output),
`models.py` (project format, saving, revisions), `elements.py` (free-layout boxes), `office.py` (.pptx/.docx),
`canva_client.py` (OAuth + Canva API), `secrets_store.py` (encrypted secrets), `ai.py`, `generator.py`, `webapp.py`
(server), `desktop.py` (window), `mock_canva.py` (demo Canva).
