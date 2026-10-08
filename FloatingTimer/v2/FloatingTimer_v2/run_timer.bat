@echo off
rem Runs the timer from the Python source (no console window).
cd /d "%~dp0"
where pyw >nul 2>nul && (start "" pyw floating_timer.py & exit /b)
where pythonw >nul 2>nul && (start "" pythonw floating_timer.py & exit /b)
echo Python was not found. Install it from https://www.python.org/downloads/ and run this again.
pause
