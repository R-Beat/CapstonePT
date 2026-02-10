<#
build_installer.ps1
Builds a Windows installer that includes both the bundled backend and Electron frontend.
This script:
1. Runs build_backend.ps1 to create the native Python exe
2. Uses electron-builder to package everything into a Windows installer
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Split-Path -Parent $scriptDir

# Build the backend first
Write-Host "Building backend..."
& "$scriptDir\build_backend.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Backend build failed"
    exit 1
}

# Build the Electron installer
Write-Host "Building Electron installer..."
Push-Location $projectRoot
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Error "Electron build failed"
    exit 1
}
Pop-Location

Write-Host "Build complete. Installer should be in dist/ directory."