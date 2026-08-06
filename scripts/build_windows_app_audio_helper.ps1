$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VendorRoot = Join-Path $ProjectRoot ".cache\vendor\windows-classic-samples"
$Solution = Join-Path $VendorRoot "Samples\ApplicationLoopback\cpp\ApplicationLoopback.sln"
$Source = Join-Path $VendorRoot "Samples\ApplicationLoopback\cpp\LoopbackCapture.cpp"
$OutputFolder = Join-Path $ProjectRoot "engines\windows"
$OutputExe = Join-Path $OutputFolder "LiveScribeApplicationLoopback.exe"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is required to download Microsoft's official ApplicationLoopback sample."
}
if (-not (Get-Command msbuild -ErrorAction SilentlyContinue)) {
    throw "MSBuild was not found. Install Visual Studio Build Tools with the Desktop development with C++ workload, or use the GitHub Actions workflow."
}
if (-not (Get-Command nuget -ErrorAction SilentlyContinue)) {
    throw "NuGet CLI was not found. Use the GitHub Actions workflow or install nuget.exe."
}

if (-not (Test-Path $VendorRoot)) {
    New-Item (Split-Path $VendorRoot) -ItemType Directory -Force | Out-Null
    git clone --depth 1 --filter=blob:none --sparse `
        https://github.com/microsoft/Windows-classic-samples.git `
        $VendorRoot
    Push-Location $VendorRoot
    git sparse-checkout set Samples/ApplicationLoopback
    Pop-Location
}

nuget restore $Solution

$content = Get-Content $Source -Raw
$old = "CreateFile(m_outputFileName, GENERIC_WRITE, 0, NULL"
$new = "CreateFile(m_outputFileName, GENERIC_WRITE, FILE_SHARE_READ, NULL"
if ($content.Contains($old)) {
    Set-Content $Source ($content.Replace($old, $new)) -Encoding UTF8
} elseif (-not $content.Contains($new)) {
    throw "The expected Microsoft sample output-file line was not found."
}

msbuild $Solution /m /p:Configuration=Release /p:Platform=x64

$built = Get-ChildItem `
    (Split-Path $Solution) `
    -Recurse `
    -Filter "ApplicationLoopback.exe" |
    Where-Object { $_.FullName -match "x64.*Release|Release.*x64" } |
    Select-Object -First 1

if (-not $built) {
    throw "ApplicationLoopback.exe was not produced."
}

New-Item $OutputFolder -ItemType Directory -Force | Out-Null
Copy-Item $built.FullName $OutputExe -Force

Write-Host ""
Write-Host "Selected-application audio helper installed:" -ForegroundColor Green
Write-Host $OutputExe
