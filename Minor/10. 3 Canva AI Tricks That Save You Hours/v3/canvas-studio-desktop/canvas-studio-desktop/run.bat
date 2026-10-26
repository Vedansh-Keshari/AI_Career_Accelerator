@echo off
setlocal
cd /d "%~dp0"
title Canvas Studio - desktop app
echo.
echo  Canvas Studio - desktop app
echo  ------------------------------------------------------------

REM ---- 1. find Python 3.10 or newer (the Microsoft Store "python" stub does not count)
set "PY="
where py >nul 2>nul && py -3 -c "import sys" >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && python -c "import sys" >nul 2>nul && set "PY=python"
if not defined PY goto nopython
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 goto oldpython

REM ---- 2. the shared folder is part of this package and must stay inside this folder
if exist "shared\studio\__init__.py" goto sharedok
goto noshared
:sharedok

REM ---- 3. private Python environment (first run only) and libraries
if exist ".venv\Scripts\python.exe" goto havevenv
echo  First run: creating a private Python environment...
%PY% -m venv .venv
if errorlevel 1 goto fail
:havevenv
echo  Checking libraries (the first time this takes a minute or two)...
".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto pipfail
:launch
echo  Starting...
echo.
".venv\Scripts\python.exe" app.py
if errorlevel 1 goto fail
goto end

:nopython
echo.
echo  PROBLEM: Python was not found.
echo  Install Python 3.12 from https://www.python.org/downloads/ and tick "Add python.exe to PATH" on the first screen,
echo  then double-click this file again.
echo  (If Python is installed but this still appears, turn off the Windows "App execution aliases" for python.exe in
echo   Settings ^> Apps ^> Advanced app settings.)
goto end

:oldpython
echo.
echo  PROBLEM: your Python is older than 3.10. Install Python 3.12 from https://www.python.org/downloads/
goto end

:noshared
echo.
echo  PROBLEM: the "shared" folder is missing from this program folder.
echo  Extract the WHOLE zip again - the "shared" folder must stay inside this folder, next to app.py.
echo  (This file is in: %CD%)
goto end

:pipfail
echo.
echo  A library failed to install. The window component (pywebview) is the usual cause on very new Python versions.
echo  Trying again without it - Canvas Studio will then open in your browser instead of its own window...
findstr /v /i "pywebview" requirements.txt > ".req-core.txt"
".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r ".req-core.txt"
if errorlevel 1 goto pipfail2
goto launch

:pipfail2
echo.
echo  PROBLEM: installing the libraries failed (see the red text above - usually no internet, a proxy, or antivirus).
echo  Fix that and double-click this file again.
goto end

:fail
echo.
echo  The program stopped with an error (see the text above).
echo  Common causes: another copy is already open (port 5001 busy), or the shared folder is incomplete.

:end
echo.
pause
endlocal
