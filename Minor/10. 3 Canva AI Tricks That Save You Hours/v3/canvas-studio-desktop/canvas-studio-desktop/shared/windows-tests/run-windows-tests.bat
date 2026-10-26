@echo off
REM Double-click to run all automated tests. Needs Python 3.10+ (python.org, "Add Python to PATH").
REM Add -SkipBrowser to skip the browser test (no Chromium download).
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-windows-tests.ps1" %*
echo.
echo Finished. The report is in windows-test-output\windows-test-report.md
pause
