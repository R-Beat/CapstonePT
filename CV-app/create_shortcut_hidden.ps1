<#
create_shortcut_hidden.ps1
Creates a Desktop shortcut that launches `run-desktop-hidden.ps1` via PowerShell with a hidden window.
This results in the app opening without a visible intermediate PowerShell/terminal window.
#>

Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$targetScript = Join-Path $scriptDir 'run-desktop-hidden.ps1'

if (-not (Test-Path $targetScript)) {
    Write-Error "Could not find $targetScript. Make sure you're running this from the project root."
    exit 1
}

$desktop = [Environment]::GetFolderPath('Desktop')
$linkPath = Join-Path $desktop 'LabCV (Hidden).lnk'

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($linkPath)

$powershellExe = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$args = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$targetScript`""
$shortcut.TargetPath = $powershellExe
$shortcut.Arguments = $args
$shortcut.WorkingDirectory = $scriptDir

# Optionally set an icon if you add one later
# $shortcut.IconLocation = Join-Path $scriptDir 'static\app.ico'

$shortcut.Save()

Write-Host "Hidden desktop shortcut created: $linkPath"

cd "C:\Users\JS\Documents\GitHub\LabCV_sorted"
cd "C:\Users\JS\Documents\GitHub\LabCV_sorted"