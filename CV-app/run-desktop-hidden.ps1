<#
run-desktop-hidden.ps1
Launches the Flask server using the project's venv python hidden, then starts Electron directly so no console windows appear.
Use this when you want the app to behave like a normal desktop application.
#>

Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Push-Location $scriptDir

# Prefer venv python
$venvPython = Join-Path -Path $scriptDir -ChildPath '.venv\Scripts\python.exe'
if (Test-Path $venvPython) {
    $pythonExe = (Resolve-Path $venvPython).Path
} else {
    $pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
}

if (-not $pythonExe) {
    Write-Error "Python executable not found. Install Python or create a .venv in the project."
    Pop-Location
    exit 1
}

# Start Flask (app.py) hidden
$pythonArgs = 'app.py'
Start-Process -FilePath $pythonExe -ArgumentList $pythonArgs -WorkingDirectory $scriptDir -WindowStyle Hidden | Out-Null

# Locate electron executable (prefer local node_modules install)
$localElectron = Join-Path $scriptDir 'node_modules\electron\dist\electron.exe'
if (Test-Path $localElectron) {
    $electronExe = (Resolve-Path $localElectron).Path
} else {
    # fallback to electron in PATH
    $electronCmd = Get-Command electron -ErrorAction SilentlyContinue
    if ($electronCmd) {
        $electronExe = $electronCmd.Source
    } else {
        Write-Error "Electron executable not found. Run `npm install --save-dev electron` in the project first."
        Pop-Location
        exit 1
    }
}

# Start Electron (this creates the GUI window without an extra console window)
Start-Process -FilePath $electronExe -ArgumentList '.' -WorkingDirectory $scriptDir -WindowStyle Normal | Out-Null

Pop-Location
