<#
create_shortcut.ps1
Creates a Windows desktop shortcut that launches `run-desktop.ps1` with PowerShell.
Run this script from the project folder (or double-click it) to place a "LabCV.lnk" on the current user's desktop.
#>

Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$targetScript = Join-Path $scriptDir 'run-desktop.ps1'

if (-not (Test-Path $targetScript)) {
    Write-Error "Could not find $targetScript. Make sure you're running this from the project root."
    exit 1
}

$desktop = [Environment]::GetFolderPath('Desktop')
$linkPath = Join-Path $desktop 'LabCV.lnk'

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($linkPath)

$powershellExe = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$shortcut.TargetPath = $powershellExe
$shortcut.Arguments = "-ExecutionPolicy Bypass -NoProfile -WindowStyle Normal -File `"$targetScript`""
$shortcut.WorkingDirectory = $scriptDir

# Optionally set an icon if you add one later; leave blank to use default
# $shortcut.IconLocation = Join-Path $scriptDir 'static\app.ico'

$shortcut.Save()

Write-Host "Desktop shortcut created: $linkPath"
