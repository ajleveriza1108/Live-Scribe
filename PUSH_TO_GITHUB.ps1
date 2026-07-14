$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$RepositoryUrl = "https://github.com/ajleveriza1108/Live-Scribe.git"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is not installed. Install Git for Windows, then run this script again."
}

if (-not (Test-Path ".git")) {
    & git init
}

& git branch -M main

$remote = & git remote get-url origin 2>$null
if ($LASTEXITCODE -ne 0 -or -not $remote) {
    & git remote add origin $RepositoryUrl
} elseif ($remote -ne $RepositoryUrl) {
    & git remote set-url origin $RepositoryUrl
}

& git add .
$changes = & git status --porcelain
if ($changes) {
    & git commit -m "Release Live Scribe v0.3.2"
}

& git push -u origin main

Write-Host ""
Write-Host "Live Scribe was uploaded to:" -ForegroundColor Green
Write-Host $RepositoryUrl -ForegroundColor Cyan
