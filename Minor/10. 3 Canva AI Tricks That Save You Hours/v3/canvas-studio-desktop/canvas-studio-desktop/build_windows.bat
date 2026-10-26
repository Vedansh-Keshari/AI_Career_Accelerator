@echo off
REM Builds dist\CanvasStudio\CanvasStudio.exe (a double-clickable app, no Python needed on the target PC).
REM Needs: Python 3.10-3.13 on this PC. Optional: Inno Setup 6 for a Setup.exe.
cd /d "%~dp0"
if not exist .buildenv ( py -3 -m venv .buildenv || python -m venv .buildenv )
call .buildenv\Scripts\activate.bat
pip install -q -r requirements.txt pyinstaller
pyinstaller --noconfirm CanvasStudio.spec
if errorlevel 1 ( echo Build failed. & exit /b 1 )
echo.
echo Built: dist\CanvasStudio\CanvasStudio.exe
where ISCC >nul 2>nul && ( ISCC installer.iss && echo Installer: Output\CanvasStudio-Setup.exe ) || echo (Inno Setup not found - skipping Setup.exe. The dist\CanvasStudio folder can be zipped and shared as is.)
