@echo off
setlocal EnableExtensions

rem ============================================================
rem Live Scribe launcher for Windows
rem Supports:
rem   1. Portable build: LiveScribe\LiveScribe.exe
rem   2. Portable build: LiveScribe.exe
rem   3. Source build:   .venv\Scripts\python.exe app.py
rem ============================================================

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%.") do set "SCRIPT_DIR=%%~fI"

set "APP_ROOT=%SCRIPT_DIR%"

rem Also support this launcher inside a launchers subfolder.
if not exist "%APP_ROOT%\app.py" (
    if exist "%SCRIPT_DIR%\..\app.py" (
        for %%I in ("%SCRIPT_DIR%\..") do set "APP_ROOT=%%~fI"
    )
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
    goto :finished
)

if exist "%ROOT_EXE%" (
    "%ROOT_EXE%"
    goto :finished
)

if exist "%VENV_PYTHON%" (
    if exist "%SOURCE_APP%" (
        "%VENV_PYTHON%" "%SOURCE_APP%"
        goto :finished
    )
)

echo Live Scribe could not be started.
echo.
echo No portable executable or prepared Python environment was found.
echo.
echo For the source version, first run:
echo   powershell -ExecutionPolicy Bypass -File ".\scripts\dev_setup_windows.ps1"
echo.
echo Then open this launcher again.
echo.
pause
exit /b 1

:finished
set "APP_EXIT=%ERRORLEVEL%"

if not "%APP_EXIT%"=="0" (
    echo.
    echo Live Scribe closed with exit code %APP_EXIT%.
    echo Keep this message when requesting support.
    echo.
    pause
)

exit /b %APP_EXIT%
