$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

$VenvDirectory = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvDirectory "Scripts\python.exe"
$RequirementsFile = Join-Path $ProjectRoot "requirements-build.txt"

function Test-NativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Description
    )

    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

function Find-Python311 {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.11 -c "import sys; print(sys.executable)" *> $null
        if ($LASTEXITCODE -eq 0) {
            return @{
                Command = "py"
                Arguments = @("-3.11")
            }
        }
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        & python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" *> $null
        if ($LASTEXITCODE -eq 0) {
            return @{
                Command = "python"
                Arguments = @()
            }
        }
    }

    return $null
}

Write-Host ""
Write-Host "Live Scribe - Windows Development Setup" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot"
Write-Host ""

$Python = Find-Python311

if ($null -eq $Python) {
    Write-Host "Python 3.11 was not found." -ForegroundColor Red
    Write-Host ""
    Write-Host "Install it with this PowerShell command:" -ForegroundColor Yellow
    Write-Host "winget install --exact --id Python.Python.3.11" -ForegroundColor White
    Write-Host ""
    Write-Host "After installation:" -ForegroundColor Yellow
    Write-Host "1. Close this PowerShell window."
    Write-Host "2. Open a new PowerShell window."
    Write-Host "3. Return to the Live Scribe project folder."
    Write-Host "4. Run this setup script again."
    Write-Host ""
    Write-Host "You can verify the installation with:" -ForegroundColor Yellow
    Write-Host "py -3.11 --version" -ForegroundColor White
    exit 1
}

$PythonCommand = $Python.Command
$PythonArguments = $Python.Arguments

Write-Host "Using Python 3.11:" -ForegroundColor Green
& $PythonCommand @PythonArguments -c "import sys; print(sys.executable); print(sys.version)"
Test-NativeCommand -Description "Python verification"

if (Test-Path $VenvDirectory) {
    if (-not (Test-Path $VenvPython)) {
        Write-Host ""
        Write-Host "Removing an incomplete .venv folder..." -ForegroundColor Yellow
        Remove-Item -Path $VenvDirectory -Recurse -Force
    }
}

if (-not (Test-Path $VenvPython)) {
    Write-Host ""
    Write-Host "Creating the local development environment..." -ForegroundColor Yellow
    & $PythonCommand @PythonArguments -m venv $VenvDirectory
    Test-NativeCommand -Description "Virtual environment creation"
}

if (-not (Test-Path $VenvPython)) {
    throw "The virtual environment was not created correctly: $VenvPython"
}

if (-not (Test-Path $RequirementsFile)) {
    throw "The requirements file was not found: $RequirementsFile"
}

Write-Host ""
Write-Host "Updating pip and installer tools..." -ForegroundColor Yellow
& $VenvPython -m pip install --upgrade pip setuptools wheel
Test-NativeCommand -Description "Installer tools update"

Write-Host ""
Write-Host "Installing Live Scribe dependencies..." -ForegroundColor Yellow
& $VenvPython -m pip install -r $RequirementsFile
Test-NativeCommand -Description "Dependency installation"

Write-Host ""
Write-Host "Running the Live Scribe self-test..." -ForegroundColor Yellow
& $VenvPython (Join-Path $ProjectRoot "app.py") --self-test
Test-NativeCommand -Description "Live Scribe self-test"

Write-Host ""
Write-Host "Development environment ready." -ForegroundColor Green
Write-Host ""
Write-Host "Run the app with:" -ForegroundColor Cyan
Write-Host "& `"$VenvPython`" `"$ProjectRoot\app.py`"" -ForegroundColor White
Write-Host ""
Write-Host "Run automated tests with:" -ForegroundColor Cyan
Write-Host "& `"$VenvPython`" -m pytest" -ForegroundColor White
