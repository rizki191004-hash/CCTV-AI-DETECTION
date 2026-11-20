# scripts/create_desktop_shortcut.ps1
# Creates a 1-click Desktop Shortcut to Start/Stop CCTV AI Detection without console window
# Supports OneDrive Desktop, Local Desktop, and Public Desktop dynamically on any Windows machine.

$ErrorActionPreference = 'SilentlyContinue'

$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$WshShell = New-Object -ComObject WScript.Shell

# 1. Dynamically locate pythonw.exe (or fallback to python.exe)
$PythonwPath = $null
try {
    $PythonDir = python -c "import os, sys; print(os.path.dirname(sys.executable))" 2>$null
    if ($PythonDir -and (Test-Path (Join-Path $PythonDir "pythonw.exe"))) {
        $PythonwPath = Join-Path $PythonDir "pythonw.exe"
    }
} catch {}

if (-not $PythonwPath) {
    $cmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($cmd) { $PythonwPath = $cmd.Source }
}

if (-not $PythonwPath) {
    $cmdPy = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmdPy) { $PythonwPath = $cmdPy.Source }
}

if (-not $PythonwPath) {
    $PythonwPath = "pythonw.exe"
}

# 2. Collect all active Desktop directories (Local, OneDrive, and Registry)
$CandidateDesktops = @()

# Environment desktop
$envDesktop = [Environment]::GetFolderPath('Desktop')
if ($envDesktop) { $CandidateDesktops += $envDesktop }

# User Profile desktop
$userProfile = [Environment]::GetFolderPath('UserProfile')
if ($userProfile) {
    $CandidateDesktops += (Join-Path $userProfile "Desktop")
    $CandidateDesktops += (Join-Path $userProfile "OneDrive\Desktop")
}

# Registry User Shell Folders Desktop
try {
    $regDesktop = (Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders" -Name "Desktop" -ErrorAction SilentlyContinue).Desktop
    if ($regDesktop) {
        $expandedReg = [Environment]::ExpandEnvironmentVariables($regDesktop)
        $CandidateDesktops += $expandedReg
    }
} catch {}

# Public desktop (if accessible)
$publicDesktop = [Environment]::GetFolderPath('CommonDesktopDirectory')
if ($publicDesktop) { $CandidateDesktops += $publicDesktop }

# Filter to unique, existing folders
$UniqueDesktops = $CandidateDesktops | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique

# 3. Create shortcut in all valid desktop locations
$CreatedCount = 0
foreach ($dir in $UniqueDesktops) {
    try {
        $ShortcutPath = Join-Path $dir "CCTV AI.lnk"
        $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
        $Shortcut.TargetPath = $PythonwPath
        $Shortcut.Arguments = "`"$ProjectRoot\cctv.pyw`""
        $Shortcut.WorkingDirectory = $ProjectRoot
        $Shortcut.Description = "CCTV AI Detection - Double-click to Start or Stop"
        # Camera / recording icon from shell32.dll (index 19 is video/camera icon)
        $Shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,19"
        $Shortcut.Save()
        $CreatedCount++
        Write-Host "  [OK] Shortcut dibuat di: $ShortcutPath"
    } catch {}
}

if ($CreatedCount -gt 0) {
    exit 0
} else {
    exit 1
}
