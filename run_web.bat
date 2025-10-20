@echo off
REM Launch the ExileCraft web interface from Windows Explorer or Command Prompt.
cd /d %~dp0

REM Pick whichever Python launcher is available.
where py >nul 2>nul
if %errorlevel%==0 (
    set "EXILECRAFT_PY=py"
) else (
    set "EXILECRAFT_PY=python"
)

%EXILECRAFT_PY% main.py --web %*
echo.
echo The server is running. Open http://127.0.0.1:5000/ in your browser.
echo Press Ctrl+C in this window to stop the server.
pause >nul
