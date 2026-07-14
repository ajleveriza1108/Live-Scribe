@echo off
setlocal EnableExtensions

rem ============================================================
rem Live Scribe launcher for Windows
rem Works with:
rem   - Source project: .venv\Scripts\python.exe + app.py
rem   - Portable build: LiveScribe\LiveScribe.exe
rem ============================================================

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%.") do set "SCRIPT_DIR=%%~fI"

set "APP_ROOT=%SCRIPT_DIR%"

rem In the source project this file is stored inside "launchers".
if exist "%SCRIPT_DIR%\..\app.py" (
    for %%I in ("%SCRIPT_DIR%\..") do set "APP_ROOT=%%~fI"
)

cd /d "%APP_ROOT%"
set "LIVE_SCRIBE_HOME=%APP_ROOT%"

set "PORTABLE_EXE=%APP_ROOT%\LiveScribe\LiveScribe.exe"
set "ROOT_EXE=%APP_ROOT%\LiveScribe.exe"
set "VENV_PYTHON=%APP_ROOT%\.venv\Scripts\python.exe"
set "SOURCE_APP=%APP_ROOT%\app.py"

echo.
echo Starting Live Scribe...
echo.

if exist "%PORTABLE_EXE%" (
    "%PORTABLE_EXE%"
    set "EXIT_CODE=%ERRORLEVEL%"
    goto :finished
)

if exist "%ROOT_EXE%" (
    "%ROOT_EXE%"
    set "EXIT_CODE=%ERRORLEVEL%"
    goto :finished
)

if exist "%VENV_PYTHON%" (
    if exist "%SOURCE_APP%" (
        "%VENV_PYTHON%" "%SOURCE_APP%"
        set "EXIT_CODE=%ERRORLEVEL%"
        goto :finished
    )
)

echo Live Scribe could not be started.
echo.
echo Source mode requires:
echo   %VENV_PYTHON%
echo   %SOURCE_APP%
echo.
echo Portable mode requires:
echo   %PORTABLE_EXE%
echo.
echo For source development, run:
echo   powershell -ExecutionPolicy Bypass -File ".\scripts\dev_setup_windows.ps1"
echo.
pause
exit /b 1

:finished
if not defined EXIT_CODE set "EXIT_CODE=0"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Live Scribe closed with exit code %EXIT_CODE%.
    echo Keep this window open when requesting support.
    echo.
    pause
)

exit /b %EXIT_CODE%
