<#
build_backend.ps1
Builds the Flask backend into a standalone Windows executable using PyInstaller.
This script:
1. Ensures PyInstaller is installed in the project's venv
2. Builds the backend using app.spec (creates dist/labcv_backend.exe)
3. Copies the exe to the project root for Electron to find
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Split-Path -Parent $scriptDir

# Ensure we're in the project root
Push-Location $projectRoot

# Use the project's venv if it exists
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    Write-Error "Python venv not found at $venvPython. Create it first: python -m venv .venv"
    exit 1
}

Write-Host "Installing PyInstaller in venv..."
& $venvPython -m pip install pyinstaller

Write-Host "Building backend with PyInstaller..."
& $venvPython -m PyInstaller --noconfirm app.spec

# Copy the exe to project root for Electron
$builtExe = Join-Path $projectRoot 'dist\labcv_backend.exe'
if (Test-Path $builtExe) {
    Copy-Item $builtExe -Destination $projectRoot -Force
    Write-Host "Backend exe copied to: $projectRoot\labcv_backend.exe"
} else {
    Write-Error "Build failed - exe not found at: $builtExe"
    exit 1
}

Pop-Location