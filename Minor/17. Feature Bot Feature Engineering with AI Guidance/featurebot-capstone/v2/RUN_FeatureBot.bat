@echo off
setlocal
cd /d "%~dp0"
title FeatureBot - one-click run
echo ============================================================
echo   FeatureBot: Feature Engineering with AI Guidance
echo ============================================================
echo.

rem --- 1. Find Python -------------------------------------------------------
set "PY="
py -3 --version >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if not defined PY (
  python --version >nul 2>nul
  if not errorlevel 1 set "PY=python"
)
if not defined PY (
  echo Python was not found on this computer.
  echo Opening the Python download page. Install it, and TICK "Add python.exe to PATH"
  echo on the first installer screen, then double-click this file again.
  start "" "https://www.python.org/downloads/"
  pause
  exit /b 1
)

rem --- 2. One-time setup (creates a private .venv folder, about 1-2 minutes) --
if not exist ".venv\Scripts\python.exe" (
  echo [1/4] First run: setting up the environment. Please wait...
  %PY% -m venv .venv
  if errorlevel 1 goto :fail
)
echo [1/4] Installing / checking libraries...
".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto :fail

rem --- 3. Make sure the dataset file exists -----------------------------------
if not exist "adult.csv" (
  echo [2/4] adult.csv not found, building it from Resources_Dataset.xlsx...
  ".venv\Scripts\python.exe" prepare_data.py
  if errorlevel 1 goto :fail
) else (
  echo [2/4] adult.csv found.
)

rem --- 4. Run the pipeline and the extended experiments -----------------------
echo [3/4] Running the FeatureBot pipeline (about 10 seconds)...
echo.
".venv\Scripts\python.exe" featurebot_adult_income.py
if errorlevel 1 goto :fail
echo.
echo [4/4] Running the extended experiments (about 1-2 minutes)...
echo.
".venv\Scripts\python.exe" analysis\extended_experiments.py
if errorlevel 1 goto :fail

echo.
echo ============================================================
echo   DONE. Results are saved in:
echo     featurebot_outputs\experiments_log.csv
echo     results\extended_experiments.csv
echo ============================================================
start "" "%~dp0featurebot_outputs"
pause
exit /b 0

:fail
echo.
echo Something went wrong. Please copy the message above and send it for help.
pause
exit /b 1
