@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%\..") do set "APP_ROOT=%%~fI"
set "SETUP_SCRIPT=%APP_ROOT%\scripts\source_setup_windows.ps1"

if not exist "%SETUP_SCRIPT%" (
    echo Live Scribe source setup script was not found:
    echo   %SETUP_SCRIPT%
    echo.
    pause
    exit /b 1
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass ^
    -File "%SETUP_SCRIPT%"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
    echo Source setup completed successfully.
    echo Run launchers\start_windows.bat to open Live Scribe.
) else (
    echo Source setup ended with exit code %EXIT_CODE%.
)
echo.
pause
exit /b %EXIT_CODE%
