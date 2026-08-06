﻿$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$RepositoryUrl = "https://github.com/ajleveriza1108/Live-Scribe.git"
$CommitMessage = "Upgrade Live Scribe to v0.9.1"
function Assert-Exit([string]$Action) { if ($LASTEXITCODE -ne 0) { throw "$Action failed with exit code $LASTEXITCODE." } }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "Git is not installed." }
$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { if (Get-Command py -ErrorAction SilentlyContinue) { $Python = "py"; $PyArgs=@("-3.11") } else { throw "Python 3.11 or the project .venv is required." } } else { $PyArgs=@() }
& $Python @PyArgs ".\scripts\repository_preflight.py"; Assert-Exit "Repository preflight"
& $Python @PyArgs -m pytest -q --ignore=tests/test_ui_handlers.py --ignore=tests/test_media_import.py; Assert-Exit "Source tests"
if (-not (Test-Path ".git")) { & git init; Assert-Exit "Git initialization" }
& git branch -M main; Assert-Exit "Setting main branch"
$Remotes=@(& git remote)
if ($Remotes -contains "origin") { & git remote set-url origin $RepositoryUrl } else { & git remote add origin $RepositoryUrl }; Assert-Exit "Configuring origin"
$Runtime=@("data/hardware_profile.json","data/.first-run-complete","data/unfinished_session.json","data/sessions.sqlite3","data/sessions.sqlite3-shm","data/sessions.sqlite3-wal")
foreach($Path in $Runtime){ & git rm --cached --ignore-unmatch -- $Path *> $null; if($LASTEXITCODE -ne 0){throw "Removing $Path from tracking failed."} }
& git add .; Assert-Exit "Adding verified changes"
if (& git status --porcelain) { & git commit -m $CommitMessage; Assert-Exit "Creating commit" }
& git push -u origin main; Assert-Exit "Pushing main"
Write-Host "Live Scribe source was verified and pushed." -ForegroundColor Green
