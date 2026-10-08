@echo off
rem Stops FloatingTimer from starting automatically with Windows.
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v FloatingTimer /f
echo.
echo Done. FloatingTimer will no longer start automatically.
pause
