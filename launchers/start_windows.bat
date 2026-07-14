@echo off
setlocal
cd /d "%~dp0"
set "LIVE_SCRIBE_HOME=%~dp0"

if not exist "LiveScribe\LiveScribe.exe" (
    echo The portable application files are incomplete.
    echo Extract the entire ZIP before opening this launcher.
    pause
    exit /b 1
)

start "" "LiveScribe\LiveScribe.exe"
endlocal
