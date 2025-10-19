@echo off
REM Launch the ExileCraft CLI from Windows Explorer or Command Prompt.
cd /d %~dp0
python main.py %*
echo.
echo Press any key to close this window.
pause >nul
