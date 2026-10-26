# Canvas Studio - desktop app

The same interface as the website, in its own window. Needs the `shared` folder next to this one.
Double-click `run.bat` (or `./run.sh`).

* The window uses the Microsoft Edge **WebView2** runtime (already on current Windows 10/11). If it is missing the app
  says so and opens in your browser instead; install "Evergreen WebView2 Runtime" from Microsoft to get the window.
* Sign-in to Canva opens your normal browser; the app listens on 127.0.0.1:5001 for Canva's redirect, so keep that port free.
* **Build a double-click app (no Python needed on the target PC):** run `build_windows.bat`. It produces
  `dist\CanvasStudio\CanvasStudio.exe` (zip that folder to share it) and, if Inno Setup 6 is installed, `Output\CanvasStudio-Setup.exe`.
  Unsigned apps trigger Windows SmartScreen ("More info" -> "Run anyway") and some antivirus tools flag PyInstaller apps;
  code-signing is the usual fix for wider distribution.
* A packaged .exe reads `config.json` from the folder next to it, or use Settings inside the app.

Tests: `python -m pytest tests -q`
