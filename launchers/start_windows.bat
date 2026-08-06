@echo off
setlocal EnableExtensions

rem ============================================================
rem Live Scribe launcher for Windows
rem - Runs a packaged portable build when present.
rem - Runs an existing source .venv when present.
rem - Prepares a new source folder automatically on first start.
rem ============================================================

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%.") do set "SCRIPT_DIR=%%~fI"
set "APP_ROOT=%SCRIPT_DIR%"

rem In the source project this launcher is stored inside "launchers".
if exist "%SCRIPT_DIR%\..\app.py" (
    for %%I in ("%SCRIPT_DIR%\..") do set "APP_ROOT=%%~fI"
)

cd /d "%APP_ROOT%"
set "LIVE_SCRIBE_HOME=%APP_ROOT%"
set "LS_CACHE=%APP_ROOT%\.cache"

if not exist "%LS_CACHE%\temp" mkdir "%LS_CACHE%\temp" >nul 2>&1
if not exist "%LS_CACHE%\huggingface\hub" mkdir "%LS_CACHE%\huggingface\hub" >nul 2>&1
if not exist "%LS_CACHE%\huggingface\xet" mkdir "%LS_CACHE%\huggingface\xet" >nul 2>&1
if not exist "%LS_CACHE%\huggingface\assets" mkdir "%LS_CACHE%\huggingface\assets" >nul 2>&1
if not exist "%LS_CACHE%\xdg\cache" mkdir "%LS_CACHE%\xdg\cache" >nul 2>&1
if not exist "%LS_CACHE%\xdg\config" mkdir "%LS_CACHE%\xdg\config" >nul 2>&1
if not exist "%LS_CACHE%\xdg\data" mkdir "%LS_CACHE%\xdg\data" >nul 2>&1
if not exist "%LS_CACHE%\pycache" mkdir "%LS_CACHE%\pycache" >nul 2>&1

set "HF_HOME=%LS_CACHE%\huggingface"
set "HF_HUB_CACHE=%LS_CACHE%\huggingface\hub"
set "HF_XET_CACHE=%LS_CACHE%\huggingface\xet"
set "HF_ASSETS_CACHE=%LS_CACHE%\huggingface\assets"
set "XDG_CACHE_HOME=%LS_CACHE%\xdg\cache"
set "XDG_CONFIG_HOME=%LS_CACHE%\xdg\config"
set "XDG_DATA_HOME=%LS_CACHE%\xdg\data"
set "TMP=%LS_CACHE%\temp"
set "TEMP=%LS_CACHE%\temp"
set "TMPDIR=%LS_CACHE%\temp"
set "PYTHONPYCACHEPREFIX=%LS_CACHE%\pycache"
set "TOKENIZERS_PARALLELISM=false"
set "HF_HUB_DISABLE_TELEMETRY=1"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"
set "HF_HUB_DISABLE_XET=1"

set "PORTABLE_EXE=%APP_ROOT%\LiveScribe\LiveScribe.exe"
set "ROOT_EXE=%APP_ROOT%\LiveScribe.exe"
set "VENV_PYTHON=%APP_ROOT%\.venv\Scripts\python.exe"
set "SOURCE_APP=%APP_ROOT%\app.py"
set "SOURCE_SETUP=%APP_ROOT%\scripts\source_setup_windows.ps1"

echo.
echo Starting Live Scribe...
echo App folder: %APP_ROOT%
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

if exist "%VENV_PYTHON%" if exist "%SOURCE_APP%" (
    "%VENV_PYTHON%" "%SOURCE_APP%"
    set "EXIT_CODE=%ERRORLEVEL%"
    goto :finished
)

if exist "%SOURCE_APP%" if exist "%SOURCE_SETUP%" (
    echo This is a new Live Scribe source folder.
    echo The local Python environment will be prepared once.
    echo An internet connection is required for the first dependency install.
    echo.
    powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass ^
        -File "%SOURCE_SETUP%"
    set "SETUP_EXIT=%ERRORLEVEL%"

    if not "%SETUP_EXIT%"=="0" (
        echo.
        echo Live Scribe source setup did not complete.
        echo.
        if "%SETUP_EXIT%"=="2" (
            echo Python 3.11 is required.
            echo Install it with:
            echo   winget install --exact --id Python.Python.3.11
        ) else (
            echo Check the messages above for the failed dependency.
            echo Confirm that the internet connection is working.
        )
        echo.
        pause
        exit /b %SETUP_EXIT%
    )

    if exist "%VENV_PYTHON%" (
        echo.
        echo Starting Live Scribe with the prepared environment...
        "%VENV_PYTHON%" "%SOURCE_APP%"
        set "EXIT_CODE=%ERRORLEVEL%"
        goto :finished
    )
)

echo Live Scribe could not be started.
echo.
echo The folder contains neither:
echo   A packaged portable executable
echo nor
echo   A complete source project with its setup script
echo.
echo Expected portable file:
echo   %PORTABLE_EXE%
echo.
echo Expected source files:
echo   %SOURCE_APP%
echo   %SOURCE_SETUP%
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
