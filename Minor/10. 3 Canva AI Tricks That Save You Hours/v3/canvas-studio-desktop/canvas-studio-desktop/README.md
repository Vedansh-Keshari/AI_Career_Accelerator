# Canvas Studio 2.0 - desktop app (complete package)

Everything this program needs is inside this folder - **no other folders, zips or settings are required**.

```
canvas-studio-desktop/
  app.py  run.bat  run.sh  requirements.txt
  shared/   <- the engine, fonts, example data, tests and Windows test pack (keep it here)
  tests/
```

## Start it (Windows)
1. Install Python 3.10-3.13 from python.org (tick "Add python.exe to PATH") if you do not have it.
2. Extract the zip anywhere (a short path such as `C:\canvas-studio-desktop` is best).
3. Double-click **run.bat** - a Canvas Studio window opens (needs the Edge WebView2 runtime, already on current Windows 10/11; otherwise it opens in your browser).

The first run creates a private Python environment and installs the libraries (a minute or two, needs internet). Mac/Linux: `./run.sh`.
Your projects live in `%USERPROFILE%\.canvas_studio`.

## Make a double-click app (no Python needed on the target PC)
Run `build_windows.bat`. It produces `dist\CanvasStudio\CanvasStudio.exe` (zip that folder to share it) and, if Inno Setup 6 is installed,
`Output\CanvasStudio-Setup.exe`. Unsigned apps trigger Windows SmartScreen ("More info" -> "Run anyway"); some antivirus tools flag
PyInstaller apps; code-signing is the usual fix. A packaged .exe reads `config.json` from the folder next to it, or use Settings.

## Canva connection
It runs in **demo mode** by default (a local stand-in for Canva with an email box). For your real account open **Settings**, paste the client id and
secret from canva.com/developers, register the redirect URL shown there, enable the listed scopes, then sign in. You type your email on Canva's own page;
the app never sees your password.

## Good to know
* Not affiliated with Canva. Real Canva sign-in/push and a real AI key are untested here (no account/keys); everything was tested against the built-in demo Canva.
* Windows itself was not available for testing: run **shared\windows-tests\run-windows-tests.bat** and follow **shared\windows-tests\WINDOWS_TEST_DOCUMENT.md**
  (a results tracker spreadsheet is in the same folder).
* If `run.bat` closes or shows a problem, it tells you what is wrong (Python missing, shared folder missing, library install failed).
