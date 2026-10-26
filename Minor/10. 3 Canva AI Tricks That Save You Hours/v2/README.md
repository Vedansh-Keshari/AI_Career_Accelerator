# Canvas Studio 2.0

A Canva-style maker for **presentations, documents and logos**, built from the scenarios in
"3 Canva AI Tricks That Save You Hours" (yoga deck, daily-workout blog post, cafe-bookstore logo).
Open an example or describe your own idea, edit everything (including moving and resizing boxes on a slide),
then **push it to your Canva account** with editable text.

```
canva-clone/
  shared/                  <- the engine, fonts, example data, tests, Windows test pack (used by BOTH apps)
  canva-clone-web.zip      <- the website  (unzips to web/)      - opens in your browser
  canva-clone-desktop.zip  <- the desktop app (unzips to desktop/) - opens in its own window
```

Unzip both zips **next to the `shared` folder** so you have `shared/`, `web/` and `desktop/` side by side.
(Elsewhere? Set the `CANVA_SHARED` environment variable to the shared folder's path.)

## Start it (Windows)
* Website: open `web`, double-click **run.bat** - your browser opens at http://127.0.0.1:5000
* Desktop app: open `desktop`, double-click **run.bat** - a Canvas Studio window opens.

First run creates a private Python environment and installs the libraries (needs Python 3.10-3.13 from
python.org with "Add Python to PATH"). Mac/Linux: `run.sh`. Want a double-click `.exe` with no Python? Run
`desktop\build_windows.bat` (details in `desktop/README.md`).

Your projects live in `%USERPROFILE%\.canvas_studio` and are shared by both apps.

## What's new in 2.0
* **Editable pushes.** Decks go to Canva as a real PowerPoint and documents as a real Word file, so text stays
  editable in Canva (falls back to page images if Canva refuses, and tells you). Also downloadable as .pptx / .docx.
* **Free-layout editor.** On any slide choose *Edit freely*: drag boxes, resize with handles, add text/shapes/pictures,
  reorder layers, arrow-key nudge, Delete. **Undo / redo** (Ctrl+Z / Ctrl+Y) covers every edit. Drag slide pictures to reorder.
* **AI-written starter text (optional).** Paste an Anthropic API key in Settings; without one, templates are used.
* **One interface for both apps.** The desktop app is the same UI in a native window - no second UI to maintain.
* **Safer storage.** Sign-in tokens and keys are encrypted (key held in Windows Credential Manager when available).
  Keys are entered in **Settings** - no JSON editing. Real server (waitress) instead of the development server.
* **Safer saving.** Versioned project files, a "Saved" indicator, a warning if another tab/window changed the same
  project, automatic retry when Windows briefly locks a file, old unused uploads cleaned up.
* **Brand kit, font picker, drag-to-reorder slides.**
* **Engineering.** Split renderer, lint + type checks clean, golden-image tests, CI recipe, progress and retries for pushes.

## Canva connection
Out of the box it runs in **demo mode** (a local stand-in for Canva with an email box). To use your real account:
open **Settings**, paste the client id and secret from canva.com/developers, register the redirect URL shown there,
enable the listed scopes, then sign in. You type your email on **Canva's own page**; the apps never see your password.

## Honest limits
* **Not affiliated with Canva.** Canva's own AI generation is not in its public API.
* **Real Canva sign-in is untested** (no account or keys here). Everything was tested against the built-in demo Canva,
  which follows Canva's documented endpoints. Canva marks its design-import API as a preview.
* **Windows:** the automated checks were run on Linux (and the Windows test script's logic under PowerShell on Linux).
  Nothing could be executed on Windows itself, so use the Windows test pack in `shared/windows-tests/`.

## Testing
* **Windows (for the team):** double-click `shared\windows-tests\run-windows-tests.bat`, then work through
  `shared\windows-tests\WINDOWS_TEST_DOCUMENT.md` (manual checks + sign-off table) or the tracker spreadsheet.
* Developers: see `shared/dev/README.md`.
