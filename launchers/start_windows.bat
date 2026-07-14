@echo off
setlocal EnableExtensions

rem ============================================================
rem Live Scribe portable launcher for Windows
rem Keep this launcher with the complete Live Scribe folder.
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

set "PORTABLE_EXE=%APP_ROOT%\LiveScribe\LiveScribe.exe"
set "ROOT_EXE=%APP_ROOT%\LiveScribe.exe"
set "VENV_PYTHON=%APP_ROOT%\.venv\Scripts\python.exe"
set "SOURCE_APP=%APP_ROOT%\app.py"

echo.
echo Starting Live Scribe in portable mode...
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

echo Live Scribe could not be started.
echo.
echo Keep the complete portable folder together. Do not copy only the EXE.
echo Source mode requires:
echo   %VENV_PYTHON%
echo   %SOURCE_APP%
echo.
echo Portable mode requires:
echo   %PORTABLE_EXE%
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
