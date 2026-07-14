$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & ".\scripts\dev_setup_windows.ps1"
}

& ".venv\Scripts\python.exe" ".\scripts\build_portable.py"
