<#
run-desktop.ps1
Simple launcher script that sets the venv python (if present) and runs `npm start`.
Run this from the project folder or use the generated desktop shortcut which points to this script.
#>

Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Push-Location $scriptDir

# Prefer the project's venv python if available
$venvPython = Join-Path -Path $scriptDir -ChildPath '.venv\Scripts\python.exe'
if (Test-Path $venvPython) {
    $env:PYTHON = (Resolve-Path $venvPython).Path
}

Write-Host "Starting LabCV desktop app..."
Write-Host "Using PYTHON: $($env:PYTHON)"

# Start npm start in the current window so logs are visible
npm start

Pop-Location
