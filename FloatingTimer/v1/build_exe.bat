@echo off
rem Builds a single-file FloatingTimer.exe (no Python needed to run it).
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller || goto :fail
python -m PyInstaller --onefile --noconsole --name FloatingTimer floating_timer.py || goto :fail
echo.
echo Done. Your app is at: %~dp0dist\FloatingTimer.exe
pause
exit /b
:fail
echo Build failed. Make sure Python is installed and on PATH.
pause
