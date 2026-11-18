@echo off
:: ============================================================
:: install_shortcut.bat
:: Double-click file ini untuk membuat shortcut "CCTV AI"
:: di Desktop Windows Anda (tanpa perlu buka PowerShell manual)
:: ============================================================

echo.
echo  ======================================================
echo   CCTV AI Detection - Instalasi Shortcut Desktop
echo  ======================================================
echo.

:: Jalankan PowerShell script yang ada di scripts/
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\create_desktop_shortcut.ps1"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo  Shortcut berhasil dibuat di Desktop Anda!
    echo  Klik ganda "CCTV AI" di Desktop untuk memulai.
) else (
    echo.
    echo  [ERROR] Gagal membuat shortcut. Pastikan PowerShell tersedia.
)

echo.
pause

