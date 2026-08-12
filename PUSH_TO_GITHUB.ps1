$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$RepositoryUrl = "https://github.com/ajleveriza1108/Live-Scribe.git"
$CommitMessage = "Add Call Mode and global English profiles"

function Assert-Exit([string]$Action) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Action failed with exit code $LASTEXITCODE."
    }
}

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $Python = "py"
        $PyArgs = @("-3.11")
    }
    else {
        throw "Python 3.11 or the project .venv is required."
    }
}
else {
    $PyArgs = @()
}

if (-not (Test-Path ".git")) {
    throw "This folder is not connected to the Live Scribe Git repository."
}

& git fetch origin main
Assert-Exit "Fetching origin/main"

$Comparison = (& git rev-list --left-right --count "origin/main...HEAD").Trim()
Assert-Exit "Comparing local and remote history"
$Parts = $Comparison -split "\s+"
if ([int]$Parts[0] -gt 0) {
    throw "origin/main contains newer commits. Pull and review them before publishing."
}

$Runtime = @(
    "data/hardware_profile.json",
    "data/.first-run-complete",
    "data/unfinished_session.json",
    "data/sessions.sqlite3",
    "data/sessions.sqlite3-shm",
    "data/sessions.sqlite3-wal",
    "data/settings.json",
    "data/interview_profiles.json"
)
foreach ($Path in $Runtime) {
    & git rm --cached --ignore-unmatch -- $Path *> $null
    if ($LASTEXITCODE -ne 0) { throw "Removing $Path from tracking failed." }
}

& git add --all
Assert-Exit "Staging source"

& $Python @PyArgs ".\scripts\repository_preflight.py"
Assert-Exit "Repository preflight"

& $Python @PyArgs -m pytest -q --ignore=tests/test_ui_handlers.py --ignore=tests/test_media_import.py
Assert-Exit "Source tests"

& git diff --cached --check
Assert-Exit "Checking staged patch"

if (& git diff --cached --quiet) {
    Write-Host "No source changes are waiting to be committed." -ForegroundColor DarkGray
}
else {
    & git commit -m $CommitMessage
    Assert-Exit "Creating commit"
}

& git push -u origin main
Assert-Exit "Pushing main"

Write-Host "Live Scribe source was verified and pushed." -ForegroundColor Green
