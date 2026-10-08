@echo off
rem Double-click to start the timer with no console window.
cd /d "%~dp0"
where pythonw >nul 2>nul && (start "" pythonw floating_timer.py & exit /b)
where pyw >nul 2>nul && (start "" pyw floating_timer.py & exit /b)
echo Python was not found. Install it from https://www.python.org/downloads/ (tick "Add Python to PATH"), then run this again.
pause
