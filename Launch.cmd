@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" goto missing
start "" ".venv\Scripts\pythonw.exe" "scripts\launcher.py"
exit /b
:missing
echo Setup is required. Double-click Setup.cmd first.
pause
