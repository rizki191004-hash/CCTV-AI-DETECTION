# scripts/create_desktop_shortcut.ps1
# Creates a 1-click Desktop Shortcut to Start/Stop CCTV AI Detection without console window

$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath('Desktop')
$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$PythonwPath = "C:\Users\RizXenzs\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe"
if (-not (Test-Path $PythonwPath)) {
    $PythonwPath = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
}

$ShortcutPath = Join-Path $DesktopPath "CCTV AI.lnk"
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $PythonwPath
$Shortcut.Arguments = "`"$ProjectRoot\cctv.pyw`""
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.Description = "CCTV AI Detection - Double-click to Start or Stop"
# Camera / recording icon from shell32.dll (index 19 is a video/cctv camera icon)
$Shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,19"
$Shortcut.Save()

Write-Output "✅ Desktop shortcut created: $ShortcutPath"

