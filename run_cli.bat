@echo off
REM Launch the ExileCraft CLI from Windows Explorer or Command Prompt.
cd /d %~dp0

REM Pick whichever Python launcher is available.
where py >nul 2>nul
if %errorlevel%==0 (
    set "EXILECRAFT_PY=py"
) else (
    set "EXILECRAFT_PY=python"
)

%EXILECRAFT_PY% main.py --cli %*
echo.
echo Press any key to close this window.
pause >nul
