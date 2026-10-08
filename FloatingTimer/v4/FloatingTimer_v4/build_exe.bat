@echo off
rem Builds FloatingTimer.exe (a standalone Windows app - no Python needed to run it).
cd /d "%~dp0"
set PY=python
where py >nul 2>nul && set PY=py

%PY% -m pip install --upgrade pyinstaller || goto :fail
%PY% -m PyInstaller --noconfirm --clean --onefile --noconsole --name FloatingTimer --icon FloatingTimer.ico floating_timer.py || goto :fail

copy /y "dist\FloatingTimer.exe" "FloatingTimer.exe" >nul || goto :fail
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q FloatingTimer.spec 2>nul

echo.
echo ===============================================================
echo  Done!  FloatingTimer.exe is now in this folder:
echo  %~dp0
echo  Double-click it to run. Right-click it ^> Pin to taskbar / Start.
echo ===============================================================
explorer /select,"%~dp0FloatingTimer.exe"
pause
exit /b 0

:fail
echo.
echo Build failed. If FloatingTimer.exe is open, close it (right-click the timer ^> Quit) and try again.
pause
exit /b 1
