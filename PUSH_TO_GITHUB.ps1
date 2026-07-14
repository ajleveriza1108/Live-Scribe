﻿$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$RepositoryUrl = "https://github.com/ajleveriza1108/Live-Scribe.git"
$CommitMessage = "Polish top notice layout and header"

function Assert-GitSuccess {
    param([Parameter(Mandatory = $true)][string]$Action)

    if ($LASTEXITCODE -ne 0) {
        throw "$Action failed with exit code $LASTEXITCODE."
    }
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is not installed. Install Git for Windows, then run this script again."
}

if (-not (Test-Path ".git")) {
    Write-Host "Initializing Git repository..." -ForegroundColor Yellow
    & git init
    Assert-GitSuccess -Action "Git initialization"
}

& git branch -M main
Assert-GitSuccess -Action "Setting the main branch"

$RemoteNames = @(& git remote)
if ($RemoteNames -contains "origin") {
    $CurrentRemote = (& git remote get-url origin).Trim()
    Assert-GitSuccess -Action "Reading the origin remote"

    if ($CurrentRemote -ne $RepositoryUrl) {
        Write-Host "Updating origin..." -ForegroundColor Yellow
        & git remote set-url origin $RepositoryUrl
        Assert-GitSuccess -Action "Updating the origin remote"
    }
}
else {
    Write-Host "Adding origin..." -ForegroundColor Yellow
    & git remote add origin $RepositoryUrl
    Assert-GitSuccess -Action "Adding the origin remote"
}

Write-Host "Adding changed files..." -ForegroundColor Yellow
& git add .
Assert-GitSuccess -Action "Adding changed files"

$Changes = & git status --porcelain
if ($Changes) {
    Write-Host "Creating commit..." -ForegroundColor Yellow
    & git commit -m $CommitMessage
    Assert-GitSuccess -Action "Creating the commit"
}
else {
    Write-Host "No uncommitted changes were found." -ForegroundColor DarkGray
}

Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
& git push -u origin main
Assert-GitSuccess -Action "Pushing to GitHub"

Write-Host ""
Write-Host "Live Scribe was uploaded successfully:" -ForegroundColor Green
Write-Host $RepositoryUrl -ForegroundColor Cyan
