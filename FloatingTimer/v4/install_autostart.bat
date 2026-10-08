@echo off
rem Makes FloatingTimer.exe start automatically every time you sign in to Windows.
cd /d "%~dp0"
if not exist "%~dp0FloatingTimer.exe" (
  echo FloatingTimer.exe was not found next to this file. Run build_exe.bat first.
  pause
  exit /b 1
)
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v FloatingTimer /t REG_SZ /d "\"%~dp0FloatingTimer.exe\"" /f
if errorlevel 1 (
  echo Could not add the startup entry.
  pause
  exit /b 1
)
echo.
echo Done. FloatingTimer will now start when you sign in.
echo Keep FloatingTimer.exe in this folder. If you move it, run this file again.
pause
