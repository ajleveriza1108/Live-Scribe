$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$RepositoryUrl = "https://github.com/ajleveriza1108/Live-Scribe.git"
$CommitMessage = "Update Live Scribe"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is not installed. Install Git for Windows, then run this script again."
}

if (-not (Test-Path ".git")) {
    Write-Host "Initializing Git repository..." -ForegroundColor Yellow
    & git init

    if ($LASTEXITCODE -ne 0) {
        throw "Git could not initialize the repository."
    }
}

& git branch -M main

$remoteExists = $false
$existingRemotes = @(& git remote)

if ($existingRemotes -contains "origin") {
    $remoteExists = $true
}

if (-not $remoteExists) {
    Write-Host "Adding the GitHub repository..." -ForegroundColor Yellow
    & git remote add origin $RepositoryUrl

    if ($LASTEXITCODE -ne 0) {
        throw "The GitHub repository could not be added as origin."
    }
}
else {
    $currentRemote = (& git remote get-url origin).Trim()

    if ($currentRemote -ne $RepositoryUrl) {
        Write-Host "Correcting the GitHub repository address..." -ForegroundColor Yellow
        & git remote set-url origin $RepositoryUrl

        if ($LASTEXITCODE -ne 0) {
            throw "The origin repository address could not be updated."
        }
    }
}

Write-Host "Adding changed files..." -ForegroundColor Yellow
& git add .

if ($LASTEXITCODE -ne 0) {
    throw "Git could not add the changed files."
}

$changes = & git status --porcelain

if ($changes) {
    Write-Host "Creating commit..." -ForegroundColor Yellow
    & git commit -m $CommitMessage

    if ($LASTEXITCODE -ne 0) {
        throw "Git could not create the commit."
    }
}
else {
    Write-Host "No new file changes need to be committed." -ForegroundColor DarkGray
}

Write-Host "Uploading to GitHub..." -ForegroundColor Yellow
& git push -u origin main

if ($LASTEXITCODE -ne 0) {
    throw "Git could not push the project to GitHub."
}

Write-Host ""
Write-Host "Live Scribe was successfully uploaded." -ForegroundColor Green
Write-Host $RepositoryUrl -ForegroundColor Cyan