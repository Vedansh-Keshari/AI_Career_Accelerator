@echo off
REM LinkedIn Influence Lab - Windows launcher. Double-click this file.
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.10+ from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
  pause
  exit /b 1
)
if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
echo Installing packages (first run only takes a minute)...
python -m pip install -q -r requirements.txt
echo Starting LinkedIn Influence Lab - your browser will open.
python -m streamlit run app.py
pause
