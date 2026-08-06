$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

$VenvDirectory = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvDirectory "Scripts\python.exe"
$RequirementsFile = Join-Path $ProjectRoot "requirements-dev.txt"
$AppFile = Join-Path $ProjectRoot "app.py"

function Assert-LastCommand {
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
        & python -c `
            "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" `
            *> $null
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
Write-Host "Live Scribe - First Source Start" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot"
Write-Host ""

if (-not (Test-Path $AppFile)) {
    throw "The Live Scribe source entry point is missing: $AppFile"
}

if (-not (Test-Path $RequirementsFile)) {
    throw "The source requirements file is missing: $RequirementsFile"
}

$Python = Find-Python311
if ($null -eq $Python) {
    Write-Host "Python 3.11 was not found." -ForegroundColor Red
    Write-Host ""
    Write-Host "Install Python 3.11 with:" -ForegroundColor Yellow
    Write-Host "winget install --exact --id Python.Python.3.11" `
        -ForegroundColor White
    Write-Host ""
    Write-Host "After installation, close and reopen PowerShell, then" `
        "start Live Scribe again." -ForegroundColor Yellow
    exit 2
}

$PythonCommand = $Python.Command
$PythonArguments = $Python.Arguments

Write-Host "Using Python 3.11:" -ForegroundColor Green
& $PythonCommand @PythonArguments -c `
    "import sys; print(sys.executable); print(sys.version)"
Assert-LastCommand -Description "Python 3.11 verification"

if (Test-Path $VenvDirectory) {
    if (-not (Test-Path $VenvPython)) {
        Write-Host ""
        Write-Host "Removing an incomplete .venv folder..." `
            -ForegroundColor Yellow
        Remove-Item -Path $VenvDirectory -Recurse -Force
    }
}

if (-not (Test-Path $VenvPython)) {
    Write-Host ""
    Write-Host "Creating the local Live Scribe environment..." `
        -ForegroundColor Yellow
    & $PythonCommand @PythonArguments -m venv $VenvDirectory
    Assert-LastCommand -Description "Virtual environment creation"
}

if (-not (Test-Path $VenvPython)) {
    throw "The local environment was not created: $VenvPython"
}

Write-Host ""
Write-Host "Updating the local installer tools..." `
    -ForegroundColor Yellow
& $VenvPython -m pip install --upgrade pip setuptools wheel
Assert-LastCommand -Description "Installer tools update"

Write-Host ""
Write-Host "Installing Live Scribe runtime dependencies..." `
    -ForegroundColor Yellow
Write-Host "This is required only for a new source folder." `
    -ForegroundColor DarkGray
& $VenvPython -m pip install -r $RequirementsFile
Assert-LastCommand -Description "Live Scribe dependency installation"

Write-Host ""
Write-Host "Checking the completed source environment..." `
    -ForegroundColor Yellow
& $VenvPython $AppFile --self-test
Assert-LastCommand -Description "Live Scribe source self-test"

Write-Host ""
Write-Host "Live Scribe source environment is ready." `
    -ForegroundColor Green
Write-Host "Future launches will skip this setup." `
    -ForegroundColor Green
exit 0
