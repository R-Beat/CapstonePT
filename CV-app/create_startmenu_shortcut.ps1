<#
create_startmenu_shortcut.ps1
Creates a Windows Start Menu shortcut for LabCV that makes it searchable from Windows search bar.
Run this script with admin rights to add the app to all users, or without for current user only.
#>

Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$targetScript = Join-Path $scriptDir 'run-desktop-hidden.ps1'

if (-not (Test-Path $targetScript)) {
    Write-Error "Could not find $targetScript. Make sure you're running this from the project root."
    exit 1
}

# Determine Start Menu folder (current user)
$startMenuPath = [Environment]::GetFolderPath('StartMenu')
$programsFolder = Join-Path $startMenuPath 'Programs'

# Create Programs folder if it doesn't exist
if (-not (Test-Path $programsFolder)) {
    New-Item -ItemType Directory -Path $programsFolder -Force | Out-Null
}

$linkPath = Join-Path $programsFolder 'LabCV.lnk'

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($linkPath)

$powershellExe = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$shortcut.TargetPath = $powershellExe
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$targetScript`""
$shortcut.WorkingDirectory = $scriptDir
$shortcut.Description = "LabCV - Equipment Management System"

# Optional: Set icon if available
$iconPath = Join-Path $scriptDir 'icon.ico'
if (Test-Path $iconPath) {
    $shortcut.IconLocation = $iconPath
}

$shortcut.Save()

Write-Host "✓ Start Menu shortcut created: $linkPath"
Write-Host "✓ App is now searchable from Windows search bar!"
Write-Host ""
Write-Host "To find it, press Windows key and type 'LabCV'"
