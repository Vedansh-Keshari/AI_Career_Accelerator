# Canvas Studio 2.0 (desktop app) - Windows Test Document

Self-contained: this document, the one-click runner and the tracker spreadsheet are all inside `canvas-studio-desktop\shared\windows-tests`.

## 1. What has and has not been tested already

| Area | Status |
|---|---|
| Automated suites (engine 92 tests + desktop shell tests (6)) | **Passed on Linux** (2 engine tests are Windows-only and are skipped there) |
| Real-browser end-to-end test (17 steps: editor drag/resize, undo/redo, reorder, brand kit, conflict warning, sign-in, push, downloads, phone layout) | **Passed on Linux** (Chromium) |
| This Windows test script (`run-windows-tests.ps1`) | **Run under PowerShell 7 on Linux** from the unzipped package: logic proven - **not** a Windows run |
| Windows-specific behaviour (spaces/accents in paths, reserved names like CON, files locked by antivirus, BOM/CRLF files, busy ports) | Simulated and **passed** (`test_windows_compat.py`); 2 real-Windows-only tests run when you run the script on Windows |
| Standalone layout (no external shared folder, no CANVA_SHARED) | **Passed**: package extracted to a path with spaces, tests and browser test run from there |
| Packaged .exe (PyInstaller, desktop package) | Built and run on Linux earlier; the Windows build has not been run |
| Desktop window (WebView2), real Canva sign-in/push, real AI key | **Not testable here** |

**The Windows run is still needed.** Expect the automated part to pass; Windows surprises would show in the manual cases (section 5).

## 2. Test environments (record which you used)

| ID | Windows | Python | WebView2 | Account / profile | Notes |
|---|---|---|---|---|---|
| E1 | Windows 11 (current) | 3.12 | installed | standard user, normal profile | main run |
| E2 | Windows 10 22H2 | 3.10 | installed | standard user | oldest supported |
| E3 | Windows 11 clean VM | none (packaged exe, desktop package) | installed | new user | packaged app |
| E4 | Windows 10/11 | 3.12 | NOT installed | any | fallback to browser |
| E5 | Windows 11 | 3.13 | installed | profile on OneDrive, name with a space/accent | file-locking and path checks |

## 3. Run the automated checks (about 5-10 minutes, mostly downloads)

1. Extract `canvas-studio-desktop.zip`. Install Python 3.10-3.13 (tick **Add Python to PATH**).
2. Double-click `shared\windows-tests\run-windows-tests.bat` (add `-SkipBrowser` to skip the Chromium download).
3. Open `shared\windows-tests\windows-test-output\windows-test-report.md`. Every row should say PASS; warnings are explained in the "Environment checks" table.

PowerShell equivalent:

```powershell
cd shared\windows-tests
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-windows-tests.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\run-windows-tests.ps1 -SkipBrowser
python smoke_windows.py          # environment checks only
```

| Step | Proves |
|---|---|
| Package is complete | app.py, tests and the shared folder are together in one folder |
| Create environment and install libraries | the requirements install on this Windows/Python |
| Environment and Windows smoke checks | Python/bitness, libraries, fonts, writable data folder, free ports, **WebView2, Credential Manager, long paths**, reserved names, render/export/open round trip, server start |
| Shared engine tests | rendering, free-layout elements, .pptx/.docx content, Canva sign-in/push/fallbacks/retries, encrypted secrets, AI paths, versioning, golden images, Windows compatibility |
| Website tests / Desktop app tests | every server endpoint, or the window shell (whichever package you have) |
| Browser end-to-end test | the real UI in Chromium (editor, undo, reorder, brand kit, conflict banner, demo sign-in, push, downloads, phone layout) |
| Website launcher (website package) | the real `app.py` starts and answers HTTP |

If a step fails, zip the `windows-test-output` folder and send it (logs and screenshots, no passwords or keys).

## 4. Pass criteria

* Automated: **0 FAIL** (WARN allowed if understood and noted in section 7).
* Manual: every case in section 5 is Pass, or Fail/Blocked with a note. "Real Canva" cases need your Canva integration.
* Release is blocked by any Fail in W-01, W-03/W-04, W-08, W-09, W-10, W-13, W-15, W-25, W-26.

## 5. Manual test cases (Windows)

Result: **P**ass / **F**ail / **B**locked / **N**/A. The same list is in `windows-test-tracker.xlsx`.

| ID | Area | Steps | Expected | Result | Notes |
|---|---|---|---|---|---|
| W-01 | Install / start | Extract the zip to a normal folder. Double-click run.bat (website package) on a PC that has never run it. | A console opens, creates .venv, installs libraries (1-3 min), the browser opens at http://127.0.0.1:5000 showing 'New project'. No error text in the console. | | |
| W-02 | Install / start | Close it and double-click run.bat (website package) again. | Starts in a few seconds (no reinstall). Your earlier projects are listed. | | |
| W-03 | Desktop window | Double-click run.bat (desktop package). | A native 'Canvas Studio' window (not a browser tab) opens with the same interface. Closing the window ends the program. | | |
| W-04 | Desktop window | On a PC/VM without the WebView2 runtime (or rename it temporarily), run run.bat (desktop package). | Console says it could not open a window and opens the default browser instead; the app works there. | | |
| W-05 | Packaging | Run build_windows.bat (desktop package). Copy dist\CanvasStudio to a PC WITHOUT Python and double-click CanvasStudio.exe. | Build succeeds; the exe opens the window. Exports (PDF/PPTX/DOCX) and the editor work (this proves the bundled templates and fonts). | | |
| W-06 | Packaging | Open the unsigned exe from a downloaded zip. | Expected: Windows SmartScreen warning ('More info' -> 'Run anyway'). Record whether antivirus flags it. (Code-signing is the fix for wider distribution.) | | |
| W-07 | Network | Watch for a Windows Firewall prompt on first run of web and desktop apps. | No prompt (the server only listens on 127.0.0.1). If a prompt appears, click Cancel/Block and confirm the app still works. | | |
| W-08 | Downloads | In the DESKTOP window: Download -> PDF, PowerPoint, PNG zip; on a document: Word. Repeat in the website (Edge and Chrome). | Each file is saved (location noted) and opens. Desktop window: downloads work or - if the window blocks them - note exactly what happens. | | |
| W-09 | Office files | Open the exported .pptx in PowerPoint. | Slides have editable text boxes, bullets, shapes and the background picture; text fits its boxes. Note font substitution if Poppins is not installed. | | |
| W-10 | Office files | Open the exported .docx in Word. | Title, headings and bullet lists use real styles; text is editable; colours match the preview. | | |
| W-11 | Real Canva (website) | Settings -> paste your Canva client id/secret (after creating an integration and registering http://127.0.0.1:5000/oauth/callback with the scopes listed). Sign in. | Browser goes to canva.com/api/oauth/authorize, you type your email on Canva's page and approve, you return to the app showing 'Canva: <your name>'. If Canva rejects the http redirect, record its exact message. | | |
| W-12 | Real Canva (desktop) | Same, in the desktop app (redirect http://127.0.0.1:5001/oauth/callback). | Your normal browser opens for sign-in; after approving, the callback tab says 'Signed in' and the app window updates within a few seconds. | | |
| W-13 | Real Canva push | Push a deck, a document and a logo. | Deck and document appear in Canva with EDITABLE text (click a text box); logo arrives as an image design. Progress text shows in the Push button. 'Open it in Canva' works. | | |
| W-14 | Real Canva push | If Canva refuses the .pptx/.docx, note the message. | App falls back to page images and says so ('Canva did not accept the editable file...'). Send us the exact message. | | |
| W-15 | Secrets | After signing in, open Windows Credential Manager -> Windows Credentials. Also look in %USERPROFILE%\.canvas_studio. | An entry named CanvasStudio / master-key exists; secrets.enc is unreadable text; no plain tokens anywhere. Deleting the credential makes the app ask you to sign in again but not crash. | | |
| W-16 | Settings | Settings: save Canva keys, an AI key, a brand kit. Quit and restart the app. | All persist (keys shown as 'saved', never displayed). Brand kit can be applied from a project's Look tab. | | |
| W-17 | AI (optional) | With a real Anthropic key: New project -> From my idea. | Starter text is written by the AI (toast says so). With a wrong key: a plain message and template text is used. | | |
| W-18 | Editor | Slide -> Edit freely. Drag, resize with handles, add text/shape/picture, arrow keys, Delete, Ctrl+Z / Ctrl+Y. Try mouse AND touch/pen if available. | Boxes follow the pointer smoothly, preview matches after a moment, undo/redo step back and forth, nothing jumps or is lost. | | |
| W-19 | Display | Windows scaling 100%, 125%, 150%, 200%; move the window between two monitors. | Text is sharp, layout not cut off, boxes line up with the preview. | | |
| W-20 | Display | Windows dark mode on. | Interface is readable in both light and dark. | | |
| W-21 | Files | Use a profile whose Documents/home is redirected to OneDrive. | Saving works; if OneDrive briefly locks a file there is no error. (smoke check shows a WARN for OneDrive.) | | |
| W-22 | Files | Run from a Windows account whose name has spaces or accents, and unzip into a folder with spaces. | Everything works (projects, uploads, exports). | | |
| W-23 | Files | Unzip into a deeply nested folder (path over 200 characters). | Either works or the smoke check warns clearly. Record which. | | |
| W-24 | Ports | Start something on port 5000 (or 5001) first, then start the app. | A plain message explains the port is busy and what to do - no stack trace. | | |
| W-25 | Safety | Open the same project in two browser tabs and edit in both. | The second tab shows 'This project was changed somewhere else' with a Load button; no work is silently overwritten. | | |
| W-26 | Safety | Close the window/tab while 'Saving...' or during a push. | No corrupt project on reopen; Windows asks to confirm leaving if unsaved. | | |
| W-27 | Offline | Disconnect from the internet and use the demo mode. | Everything works (fonts are local). Real Canva/AI show a clear 'could not reach' message. | | |
| W-28 | Layout | Resize the browser to phone width (Edge DevTools device mode). | Single column; buttons reachable; preview visible. | | |
| W-29 | Cleanup | Delete %USERPROFILE%\.canvas_studio and the CanvasStudio credential. | App starts fresh with no errors. | | |
| W-30 | Installer (if built) | Install CanvasStudio-Setup.exe for the current user, launch from Start menu, then uninstall. | No admin rights needed; shortcut works; uninstall removes the program (your projects stay in .canvas_studio). | | |

## 6. What might go wrong on Windows (look here first)

1. **Desktop window downloads** may be blocked or silently saved by WebView2 (W-08). Fallback: use the website package for downloads.
2. **Canva redirect URL** - Canva may refuse a plain `http://127.0.0.1` redirect (W-11/12). Record its exact message.
3. **Canva import API** is a preview feature; if it rejects `.pptx`/`.docx` the app falls back to images and says so (W-14).
4. **Fonts in Office** - Poppins is mapped for PowerPoint; if not installed PowerPoint substitutes a font (W-09).
5. **Packaged exe** - unsigned: SmartScreen warning, occasional antivirus false positives (W-06).
6. **Python 3.13 + pywebview** installs a native component; if it fails the desktop run.bat retries without it (browser mode), or use Python 3.12.
7. **OneDrive/antivirus** can lock files; saving retries automatically (W-21).

## 7. Defect log

| # | Case ID | What happened | Severity | Screenshot / file | Status |
|---|---|---|---|---|---|
| | | | | | |

## 8. Sign-off

| Role | Name | Date | Environment IDs covered | Result |
|---|---|---|---|---|
| Tester | | | | |
| Reviewer | | | | |

---

# Appendix A - one-click launcher (`shared\windows-tests\run-windows-tests.bat`)

```bat
@echo off
REM Double-click to run all automated tests. Needs Python 3.10+ (python.org, "Add Python to PATH").
REM Add -SkipBrowser to skip the browser test (no Chromium download).
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-windows-tests.ps1" %*
echo.
echo Finished. The report is in windows-test-output\windows-test-report.md
pause
```

# Appendix B - test runner (`shared\windows-tests\run-windows-tests.ps1`)

```powershell
<#
.SYNOPSIS
  Runs every automated Canvas Studio test on this machine and writes a report.
.DESCRIPTION
  Creates a private Python environment, installs what the apps need, then runs: environment smoke checks, the
  shared/web/desktop test suites, a real-browser end-to-end test, and a launcher start-up check.
  Results go to windows-test-report.md (plus JUnit XML) in the output folder. Exit code 0 = no failures.
.PARAMETER SkipInstall  Reuse the environment from a previous run.
.PARAMETER SkipBrowser  Skip the browser end-to-end test (no Chromium download).
.PARAMETER OutDir       Where the environment, logs and report go (default: .\windows-test-output next to this script).
#>
param(
  [switch]$SkipInstall,
  [switch]$SkipBrowser,
  [string]$OutDir = (Join-Path $PSScriptRoot "windows-test-output")
)
$ErrorActionPreference = "Continue"
$isWin = if (Test-Path variable:IsWindows) { $IsWindows } else { $true }   # Windows PowerShell 5.1 has no $IsWindows
$Shared = Split-Path -Parent $PSScriptRoot
$Root = Split-Path -Parent $Shared            # the package folder (app.py, tests, shared all live here)
$ReqFile = Join-Path $Root "requirements.txt"
$isDeskPkg = (Test-Path $ReqFile) -and (Select-String -Path $ReqFile -Pattern "pywebview" -Quiet)
$WebDir = $Root; $DeskDir = $Root
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$Venv = Join-Path $OutDir "venv"
$Py = if ($isWin) { Join-Path $Venv "Scripts\python.exe" } else { Join-Path $Venv "bin/python" }
$Results = New-Object System.Collections.Generic.List[object]
$env:CANVAS_NO_KEYRING = "1"          # automated tests must not touch your real Credential Manager
$env:PYTHONIOENCODING = "utf-8"

function Add-Result($name, $status, $seconds, $detail) {
  $Results.Add([pscustomobject]@{ Step = $name; Status = $status; Seconds = [math]::Round($seconds, 1); Detail = $detail })
  $color = switch ($status) { "PASS" { "Green" } "FAIL" { "Red" } "SKIP" { "DarkGray" } default { "Yellow" } }
  Write-Host ("[{0}] {1} ({2:N1}s) {3}" -f $status, $name, $seconds, $detail) -ForegroundColor $color
}
function Run-Step($name, [scriptblock]$body, $log) {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  & $body *> $log
  $code = $LASTEXITCODE
  $sw.Stop()
  $tail = (Get-Content $log -Tail 3 -ErrorAction SilentlyContinue) -join " | "
  if ($code -eq 0) { Add-Result $name "PASS" $sw.Elapsed.TotalSeconds "log: $log" }
  else { Add-Result $name "FAIL" $sw.Elapsed.TotalSeconds "exit $code - $tail (log: $log)" }
}

Write-Host "Canvas Studio test run  |  root: $Root  |  output: $OutDir`n"

# ---- 0. layout
if (-not (Test-Path (Join-Path (Join-Path $Shared "studio") "__init__.py"))) { Write-Host "Cannot find shared\studio - run this from the shared\windows-tests folder." -ForegroundColor Red; exit 2 }
$hasApp = Test-Path (Join-Path $Root "app.py")
$hasWeb = $hasApp -and -not $isDeskPkg; $hasDesk = $hasApp -and $isDeskPkg
Add-Result "Package is complete (app.py, tests and shared folder in one folder)" $(if ($hasApp) { "PASS" } else { "FAIL" }) 0 "package: $(if ($isDeskPkg) { 'desktop' } else { 'web' })"

# ---- 1. python + venv + install
$SysPy = $null
foreach ($cand in @("py", "python", "python3")) { if (Get-Command $cand -ErrorAction SilentlyContinue) { $SysPy = $cand; break } }
if (-not $SysPy) { Write-Host "Python 3.10+ was not found. Install it from python.org (tick 'Add Python to PATH')." -ForegroundColor Red; exit 2 }
if (-not $SkipInstall) {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  if (-not (Test-Path $Py)) { if ($SysPy -eq "py") { & py -3 -m venv $Venv } else { & $SysPy -m venv $Venv } }
  $reqs = @(); if (Test-Path $ReqFile) { $reqs += @("-r", $ReqFile) }
  & $Py -m pip install -q --disable-pip-version-check @reqs pytest playwright 2>&1 | Tee-Object (Join-Path $OutDir "pip.log") | Out-Null
  $code = $LASTEXITCODE; $sw.Stop()
  Add-Result "Create environment and install libraries" $(if ($code -eq 0) { "PASS" } else { "FAIL" }) $sw.Elapsed.TotalSeconds "pip log: $(Join-Path $OutDir 'pip.log')"
  if ($code -ne 0) { Write-Host "Install failed; see pip.log." -ForegroundColor Red }
}
if (-not (Test-Path $Py)) { Write-Host "No environment at $Venv (run without -SkipInstall first)." -ForegroundColor Red; exit 2 }

# ---- 2. smoke checks
Run-Step "Environment and Windows smoke checks" { & $Py (Join-Path $PSScriptRoot "smoke_windows.py") --json (Join-Path $OutDir "smoke.json") } (Join-Path $OutDir "smoke.log")

# ---- 3. test suites
Push-Location $Root
Run-Step "Shared engine tests (render, Canva flow, export, secrets, AI, golden images, Windows compatibility)" {
  & $Py -m pytest (Join-Path $Shared "tests") -q -p no:cacheprovider --junitxml (Join-Path $OutDir "junit-shared.xml") } (Join-Path $OutDir "tests-shared.log")
if ($hasWeb) { Run-Step "Website tests" { & $Py -m pytest (Join-Path $WebDir "tests") -q -p no:cacheprovider --junitxml (Join-Path $OutDir "junit-web.xml") } (Join-Path $OutDir "tests-web.log") }
else { Add-Result "Website tests" "SKIP" 0 "not the website package" }
if ($hasDesk) { Run-Step "Desktop app tests" { & $Py -m pytest (Join-Path $DeskDir "tests") -q -p no:cacheprovider --junitxml (Join-Path $OutDir "junit-desktop.xml") } (Join-Path $OutDir "tests-desktop.log") }
else { Add-Result "Desktop app tests" "SKIP" 0 "not the desktop package" }
Pop-Location

# ---- 4. browser end to end
if ($SkipBrowser -or -not $hasApp) { Add-Result "Browser end-to-end test" "SKIP" 0 $(if ($hasApp) { "-SkipBrowser" } else { "app.py not found" }) }
else {
  Run-Step "Install Chromium for the browser test" { & $Py -m playwright install chromium } (Join-Path $OutDir "playwright-install.log")
  $env:E2E_PYTHON = $Py; $env:E2E_APP = (Join-Path (Join-Path $Shared "tests") "serve_web.py"); $env:E2E_SHOTS = (Join-Path $OutDir "screenshots")
  Run-Step "Browser end-to-end test (editor, undo, brand kit, push, downloads)" { & $Py (Join-Path (Join-Path $Shared "tests") "e2e_browser.py") } (Join-Path $OutDir "e2e.log")
}

# ---- 5. launcher start-up check (the exact thing a user double-clicks)
if ($hasWeb) {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $env:NO_BROWSER = "1"; $env:PORT = "5077"; $env:CANVA_STUDIO_HOME = (Join-Path $OutDir "launcher-home")
  $winHidden = if ($isWin) { @{ WindowStyle = "Hidden" } } else { @{} }
  $p = Start-Process -FilePath $Py -ArgumentList @((Join-Path $WebDir "app.py")) -PassThru @winHidden -RedirectStandardOutput (Join-Path $OutDir "launcher.out") -RedirectStandardError (Join-Path $OutDir "launcher.err")
  $ok = $false; $detail = ""
  for ($i = 0; $i -lt 40 -and -not $ok; $i++) {
    Start-Sleep -Milliseconds 500
    try { $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:5077/api/bootstrap" -TimeoutSec 3; if ($r.StatusCode -eq 200 -and $r.Content -match "examples") { $ok = $true } } catch { }
  }
  if ($ok) { try { $h = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:5077/" -TimeoutSec 3; $detail = "home page HTTP $($h.StatusCode), headers: X-Frame-Options=$($h.Headers['X-Frame-Options'])" } catch { $ok = $false; $detail = $_.Exception.Message } }
  try { if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force } } catch { }
  Remove-Item Env:\PORT, Env:\NO_BROWSER, Env:\CANVA_STUDIO_HOME -ErrorAction SilentlyContinue
  $sw.Stop()
  Add-Result "Website launcher starts and answers HTTP" $(if ($ok) { "PASS" } else { "FAIL" }) $sw.Elapsed.TotalSeconds $detail
}

if ($isDeskPkg) { Add-Result "Desktop window starts (WebView2)" "SKIP" 0 "needs a screen - do manual case W-03" }

# ---- 6. report
$pass = ($Results | Where-Object Status -eq "PASS").Count; $fail = ($Results | Where-Object Status -eq "FAIL").Count
$warn = ($Results | Where-Object Status -eq "WARN").Count; $skip = ($Results | Where-Object Status -eq "SKIP").Count
$osInfo = if ($isWin) { (Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue).Caption } else { "non-Windows (script logic check only)" }
$report = @("# Canvas Studio automated test report", "", "- Run: $(Get-Date -Format 'yyyy-MM-dd HH:mm')", "- Machine: $env:COMPUTERNAME  |  OS: $osInfo  |  PowerShell $($PSVersionTable.PSVersion)",
  "- Python: $(& $Py --version 2>&1)", "- Result: **$pass passed, $fail failed, $warn warnings, $skip skipped**", "", "| Step | Status | Seconds | Detail |", "|---|---|---|---|")
foreach ($r in $Results) { $report += "| $($r.Step) | $($r.Status) | $($r.Seconds) | $($r.Detail -replace '\|', '/') |" }
$smokePath = Join-Path $OutDir "smoke.json"
if (Test-Path $smokePath) {
  $report += @("", "## Environment checks", "", "| Check | Status | Detail |", "|---|---|---|")
  foreach ($c in (Get-Content $smokePath -Raw | ConvertFrom-Json).results) { $report += "| $($c.check) | $($c.status) | $($c.detail -replace '\|', '/') |" }
}
$report += @("", "Next: do the manual checks in WINDOWS_TEST_DOCUMENT.md (window, downloads, real Canva sign-in) and record results there.")
$reportPath = Join-Path $OutDir "windows-test-report.md"
Set-Content -Path $reportPath -Value $report -Encoding UTF8
Write-Host "`n$pass passed, $fail failed, $warn warnings, $skip skipped.  Report: $reportPath" -ForegroundColor $(if ($fail) { "Red" } else { "Green" })
exit $(if ($fail) { 1 } else { 0 })
```

# Appendix C - environment and Windows smoke checks (`shared\windows-tests\smoke_windows.py`)

```python
"""Environment and Windows-specific smoke checks for Canvas Studio.

Run:  python smoke_windows.py [--json results.json]
Works on any OS (Windows-only checks are marked SKIP elsewhere). Exit code 1 if anything FAILS.
PASS = fine, WARN = works but worth a look, FAIL = must be fixed, SKIP = not applicable here.
"""
from __future__ import annotations

import importlib
import json
import os
import platform
import socket
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHARED = HERE.parent
sys.path.insert(0, str(SHARED))
os.environ.setdefault("CANVAS_NO_KEYRING", "")
IS_WIN = sys.platform == "win32"
results: list[dict] = []


def record(name: str, status: str, detail: str = "") -> None:
    results.append({"check": name, "status": status, "detail": detail})
    print(f"  [{status:<4}] {name}" + (f" - {detail}" if detail else ""))


def check(name: str):
    def wrap(fn):
        try:
            out = fn()
            if isinstance(out, tuple):
                record(name, *out)
            else:
                record(name, "PASS", out or "")
        except Exception as exc:  # noqa: BLE001 - a smoke test reports, it never crashes
            record(name, "FAIL", f"{type(exc).__name__}: {exc}")
        return fn
    return wrap


print(f"Canvas Studio smoke checks on {platform.platform()} / Python {platform.python_version()}\n")


@check("Python 3.10 or newer, 64-bit")
def _():
    ok = sys.version_info >= (3, 10) and sys.maxsize > 2**32
    return ("PASS" if ok else "FAIL", f"{platform.python_version()} {platform.architecture()[0]}")


for mod, required in (("flask", True), ("PIL", True), ("requests", True), ("pptx", True), ("docx", True), ("waitress", True),
                      ("keyring", True), ("cryptography", True), ("webview", False)):
    @check(f"library '{mod}' installed")
    def _(mod=mod, required=required):
        try:
            m = importlib.import_module(mod)
        except ImportError:
            return ("FAIL" if required else "WARN", "missing" + ("" if required else " - desktop window will fall back to the browser"))
        return getattr(m, "__version__", getattr(m, "VERSION", "ok"))


@check("Pillow can draw text (FreeType) and was built with PNG/JPEG")
def _():
    from PIL import features
    need = {"freetype2": features.check("freetype2"), "zlib": features.check("zlib"), "jpg": features.check("jpg")}
    return ("PASS", "ok") if all(need.values()) else ("FAIL", str(need))


@check("bundled fonts are present")
def _():
    fonts = list((SHARED / "assets" / "fonts").glob("*.ttf"))
    return ("PASS", f"{len(fonts)} fonts") if len(fonts) >= 10 else ("FAIL", f"only {len(fonts)} found")


@check("data folder is writable (projects, uploads, secrets)")
def _():
    from studio.paths import studio_home
    home = studio_home()
    probe = home / "write-test.tmp"
    probe.write_text("x", encoding="utf-8")
    probe.unlink()
    notes = []
    low = str(home).lower()
    if "onedrive" in low:
        notes.append("home is inside OneDrive: sync can briefly lock files (the app retries saves)")
    if " " in str(home) or not str(home).isascii():
        notes.append("path has spaces or non-ASCII characters (supported)")
    return ("WARN" if "onedrive" in low else "PASS", f"{home}" + (" | " + "; ".join(notes) if notes else ""))


for port, who in ((5000, "website"), (5001, "desktop app sign-in"), (8765, "demo Canva")):
    @check(f"port {port} is free ({who})")
    def _(port=port, who=who):
        with socket.socket() as s:
            s.settimeout(0.3)
            busy = s.connect_ex(("127.0.0.1", port)) == 0
        return ("WARN", "in use - close the other program or change the port") if busy else ("PASS", "free")


@check("Windows: Edge WebView2 runtime installed (needed for the desktop window)")
def _():
    if not IS_WIN:
        return ("SKIP", "not Windows")
    import winreg
    guid = r"{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
    for hive, path in ((winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{guid}"),
                       (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{guid}"),
                       (winreg.HKEY_CURRENT_USER, rf"Software\Microsoft\EdgeUpdate\Clients\{guid}")):
        try:
            with winreg.OpenKey(hive, path) as k:
                return ("PASS", "version " + winreg.QueryValueEx(k, "pv")[0])
        except OSError:
            continue
    return ("WARN", "not found - install 'Evergreen WebView2 Runtime' from Microsoft; the app will open in your browser instead")


@check("Windows: Credential Manager holds the encryption key")
def _():
    if not IS_WIN:
        return ("SKIP", "not Windows")
    import keyring
    name = type(keyring.get_keyring()).__name__
    return ("PASS", name) if "WinVault" in name else ("WARN", f"backend is {name}; a key file is used instead")


@check("Windows: long paths enabled")
def _():
    if not IS_WIN:
        return ("SKIP", "not Windows")
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\FileSystem") as k:
            return ("PASS", "enabled") if winreg.QueryValueEx(k, "LongPathsEnabled")[0] else ("WARN", "disabled - keep the unzip folder path short (under ~200 characters)")
    except OSError:
        return ("WARN", "could not read the setting")


@check("Windows: reserved device names never become file names")
def _():
    from studio.models import slug
    bad = [n for n in ("CON", "PRN", "AUX", "NUL", "COM1", "LPT1") if not slug(n).startswith("design-")]
    return ("FAIL", f"not protected: {bad}") if bad else ("PASS", "ok")


@check("Windows: unzip location length")
def _():
    n = len(str(SHARED))
    return ("WARN", f"{n} characters - shorter than ~200 is safer on Windows") if n > 200 else ("PASS", f"{n} characters")


@check("pipeline: render, export .pptx/.docx and re-open them")
def _():
    import io

    from docx import Document
    from pptx import Presentation

    from studio import generator as G
    from studio import office
    from studio import render as R
    deck, doc = G.project_from_example("yoga-presentation"), G.project_from_example("workout-blog-refined")
    assert R.render_pages(deck, 0.3) and R.render_pages(doc, 0.3)
    assert len(Presentation(io.BytesIO(office.presentation_to_pptx(deck))).slides) == 6
    assert Document(io.BytesIO(office.document_to_docx(doc))).paragraphs[0].text == doc["title"]
    return "ok"


@check("server: starts on a free port and serves the app")
def _():
    from studio.desktop import make_server
    from studio.webapp import create_app
    with tempfile.TemporaryDirectory() as home:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        server = make_server(create_app(home=Path(home)), "127.0.0.1", port)
        t = threading.Thread(target=server.run, daemon=True)
        t.start()
        try:
            body = b""
            for _ in range(60):
                try:
                    body = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/bootstrap", timeout=2).read()
                    break
                except OSError:
                    time.sleep(0.1)
            assert b"examples" in body
            page = urllib.request.urlopen(f"http://127.0.0.1:{port}/static/app.js", timeout=2).read()
            assert len(page) > 10000
        finally:
            server.close()
            t.join(timeout=5)
    return "ok"


print()
counts = {k: sum(r["status"] == k for r in results) for k in ("PASS", "WARN", "FAIL", "SKIP")}
print("Summary: " + ", ".join(f"{v} {k}" for k, v in counts.items()))
if "--json" in sys.argv:
    out = Path(sys.argv[sys.argv.index("--json") + 1])
    out.write_text(json.dumps({"platform": platform.platform(), "python": platform.python_version(), "results": results}, indent=2), encoding="utf-8")
sys.exit(1 if counts["FAIL"] else 0)
```

# Appendix D - test files

| File | Contents |
|---|---|
| `shared\tests\test_shared.py` | rendering, generator, storage, Canva sign-in/push against the demo Canva |
| `shared\tests\test_improvements.py` | .pptx/.docx export, free-layout elements, retries, encrypted secrets, AI, versioning, golden images |
| `shared\tests\test_windows_compat.py` | paths with spaces/accents, reserved names, BOM/CRLF files, locked files, busy ports, threads (2 run only on Windows) |
| `shared\tests\e2e_browser.py` + `serve_web.py` | the real-browser test and the server it starts |
| `tests\test_desktop.py` | the desktop window shell |
