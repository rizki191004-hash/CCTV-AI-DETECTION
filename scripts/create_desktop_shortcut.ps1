# scripts/create_desktop_shortcut.ps1
# Creates exactly ONE Desktop Shortcut to Start/Stop CCTV AI Detection without console window

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

# 2. Clean up any existing duplicate in Public Desktop so there is only 1 shortcut
$publicDesktop = [Environment]::GetFolderPath('CommonDesktopDirectory')
if ($publicDesktop) {
    $publicLnk = Join-Path $publicDesktop "CCTV AI.lnk"
    if (Test-Path $publicLnk) {
        Remove-Item $publicLnk -Force -ErrorAction SilentlyContinue
    }
}

# 3. Determine the single primary Desktop folder for the current user
$TargetDesktop = [Environment]::GetFolderPath('Desktop')
if (-not $TargetDesktop -or -not (Test-Path $TargetDesktop)) {
    $userProfile = [Environment]::GetFolderPath('UserProfile')
    if ($userProfile -and (Test-Path (Join-Path $userProfile "Desktop"))) {
        $TargetDesktop = Join-Path $userProfile "Desktop"
    }
}

if (-not $TargetDesktop -or -not (Test-Path $TargetDesktop)) {
    Write-Host "  [PERINGATAN] Folder Desktop tidak ditemukan."
    exit 1
}

# 4. Create exactly 1 shortcut in the primary desktop
try {
    $ShortcutPath = Join-Path $TargetDesktop "CCTV AI.lnk"
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $PythonwPath
    $Shortcut.Arguments = "`"$ProjectRoot\cctv.pyw`""
    $Shortcut.WorkingDirectory = $ProjectRoot
    $Shortcut.Description = "CCTV AI Detection - Double-click to Start or Stop"
    $Shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,19"
    $Shortcut.Save()
    Write-Host "  [OK] Shortcut tunggal dibuat di: $ShortcutPath"
    exit 0
} catch {
    Write-Host "  [ERROR] Gagal membuat shortcut: $_"
    exit 1
}
