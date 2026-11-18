@echo off
setlocal enabledelayedexpansion

:: ================================================================
:: setup.bat --- CCTV AI Detection: Auto-Setup untuk Perangkat Baru
:: Double-click file ini untuk install semua kebutuhan otomatis.
:: Prasyarat: Python 3.11+ sudah terinstall di perangkat ini.
:: ================================================================

cls
echo.
echo  +========================================================+
echo  ^|       CCTV AI Detection --- Setup Otomatis            ^|
echo  ^|   Menyiapkan semua kebutuhan di perangkat ini...      ^|
echo  +========================================================+
echo.
echo  Pilih mode instalasi:
echo.
echo    [1]  Install Lengkap  (deps + konfigurasi Telegram + shortcut Desktop)
echo    [2]  Install Minimal  (deps saja, konfigurasi dan shortcut dilewati)
echo.
:PILIH_MODE
set /p INSTALL_MODE="  Masukkan pilihan (1/2) lalu tekan Enter: "
if "!INSTALL_MODE!"=="1" goto MULAI
if "!INSTALL_MODE!"=="2" goto MULAI
echo  [!] Pilihan tidak valid. Ketik 1 atau 2.
goto PILIH_MODE

:MULAI
echo.
if "!INSTALL_MODE!"=="1" (
    echo  Mode: Install Lengkap dipilih.
) else (
    echo  Mode: Install Minimal dipilih.
)
echo.
echo  Proses akan berjalan step by step.
echo  Tekan Enter di setiap langkah untuk melanjutkan,
echo  atau tekan Ctrl+C kapan saja untuk membatalkan.
echo.
pause

:: ================================================================
:: LANGKAH 1 -- Cek Python
:: ================================================================
cls
echo.
echo  +========================================================+
echo  ^|  Langkah 1 / 5 : Memeriksa instalasi Python           ^|
echo  +========================================================+
echo.
echo  Memastikan Python 3.11+ sudah terinstall dan ada di PATH.
echo.
pause
echo.
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [ERROR] Python tidak ditemukan!
    echo.
    echo  Silakan install Python 3.11 atau lebih baru dari:
    echo  https://www.python.org/downloads/
    echo.
    echo  PENTING: Centang "Add Python to PATH" saat instalasi!
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>&1') do set PYVER=%%v
echo  [OK] Python !PYVER! ditemukan.
echo.
pause

:: ================================================================
:: LANGKAH 2 -- Upgrade pip
:: ================================================================
cls
echo.
echo  +========================================================+
echo  ^|  Langkah 2 / 5 : Memperbarui pip                      ^|
echo  +========================================================+
echo.
echo  Memperbarui pip ke versi terbaru agar instalasi berjalan
echo  dengan benar dan tidak ada masalah kompatibilitas.
echo.
pause
echo.
python -m pip install --upgrade pip --quiet
echo  [OK] pip berhasil diperbarui.
echo.
pause

:: ================================================================
:: LANGKAH 3 -- Install dependensi
:: ================================================================
cls
echo.
echo  +========================================================+
echo  ^|  Langkah 3 / 5 : Menginstall dependensi               ^|
echo  +========================================================+
echo.
echo  Menginstall semua library dari requirements.txt.
echo  Proses ini membutuhkan koneksi internet dan bisa memakan
echo  waktu 5-15 menit tergantung kecepatan internet.
echo.
pause
echo.
python -m pip install -r "%~dp0requirements.txt"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Gagal menginstall dependensi!
    echo  Pastikan koneksi internet aktif, lalu coba lagi.
    echo.
    pause
    exit /b 1
)
echo.
echo  [OK] Semua dependensi berhasil diinstall.
echo.
pause

:: ================================================================
:: LANGKAH 4 -- Konfigurasi .env  (hanya mode Lengkap)
:: ================================================================
cls
echo.
echo  +========================================================+
echo  ^|  Langkah 4 / 5 : Konfigurasi aplikasi (.env)          ^|
echo  +========================================================+
echo.

if "!INSTALL_MODE!"=="2" (
    echo  [--] Mode Minimal -- langkah ini dilewati.
    echo  Edit file .env secara manual untuk mengatur Telegram, dll.
    echo.
    pause
    goto LANGKAH5
)

if exist "%~dp0.env" (
    echo  File .env sudah ada -- konfigurasi dilewati.
    echo  Edit "%~dp0.env" jika ingin mengubah pengaturan.
    echo.
    pause
    goto LANGKAH5
)

echo  File .env belum ada. Mari isi konfigurasi dasar.
echo  (Tekan Enter tanpa mengetik apa pun untuk melewati tiap field)
echo.
pause
echo.

:: -- Telegram Bot Token --
echo  +-- TELEGRAM BOT TOKEN ------------------------------------+
echo  ^| Dapatkan token dari @BotFather di Telegram.            ^|
echo  ^| Contoh: 123456789:ABCdefGHIjklMNOpqrSTUvwxYZ          ^|
echo  ^| (Kosongkan = isi nanti di file .env)                   ^|
echo  +----------------------------------------------------------+
set /p BOT_TOKEN="  Masukkan Telegram Bot Token: "
echo.

:: -- Telegram Chat ID --
echo  +-- TELEGRAM CHAT ID --------------------------------------+
echo  ^| Dapatkan Chat ID dari @userinfobot di Telegram.        ^|
echo  ^| Contoh: -123456789 (grup) atau 123456789 (pribadi)     ^|
echo  ^| (Kosongkan = isi nanti di file .env)                   ^|
echo  +----------------------------------------------------------+
set /p CHAT_ID="  Masukkan Telegram Chat ID: "
echo.

:: -- Tulis ke .env menggunakan redirect >> per baris --
set ENVFILE=%~dp0.env
echo # CCTV AI Detection --- Konfigurasi dibuat oleh setup.bat> "!ENVFILE!"
echo TELEGRAM_BOT_TOKEN=!BOT_TOKEN!>> "!ENVFILE!"
echo TELEGRAM_CHAT_ID=!CHAT_ID!>> "!ENVFILE!"
echo.>> "!ENVFILE!"
echo # Cloudflare Tunnel (kosongkan = pakai Quick Tunnel gratis)>> "!ENVFILE!"
echo # CLOUDFLARE_TUNNEL_TOKEN=>> "!ENVFILE!"
echo.>> "!ENVFILE!"
echo # PIN Dashboard (kosongkan = tanpa PIN)>> "!ENVFILE!"
echo # DASHBOARD_PIN=>> "!ENVFILE!"

echo  [OK] File .env berhasil dibuat di: %~dp0.env
echo.
pause

:: ================================================================
:: LANGKAH 5 -- Shortcut Desktop  (hanya mode Lengkap)
:: ================================================================
:LANGKAH5
cls
echo.
echo  +========================================================+
echo  ^|  Langkah 5 / 5 : Shortcut Desktop (opsional)          ^|
echo  +========================================================+
echo.

if "!INSTALL_MODE!"=="2" (
    echo  [--] Mode Minimal -- langkah ini dilewati.
    echo  Jalankan install_shortcut.bat kapan saja untuk membuat shortcut.
    echo.
    pause
    goto SELESAI
)

echo  Membuat shortcut "CCTV AI" di Desktop agar mudah diakses.
echo.
set /p BUAT_SHORTCUT="  Buat shortcut di Desktop? (y/n) lalu tekan Enter: "
if /i "!BUAT_SHORTCUT!"=="y" (
    echo.
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\create_desktop_shortcut.ps1"
    if %ERRORLEVEL% EQU 0 (
        echo  [OK] Shortcut berhasil dibuat di Desktop.
    ) else (
        echo  [PERINGATAN] Gagal membuat shortcut.
        echo  Jalankan install_shortcut.bat secara manual kapan saja.
    )
) else (
    echo  Dilewati. Jalankan install_shortcut.bat kapan saja.
)
echo.
pause

:: ================================================================
:: SELESAI
:: ================================================================
:SELESAI
cls
echo.
echo  +========================================================+
echo  ^|           Setup Selesai! Cara Menjalankan:            ^|
echo  ^|                                                        ^|
echo  ^|  1. Double-click "CCTV AI" di Desktop (jika dibuat)   ^|
echo  ^|  2. ATAU double-click run.py di folder ini             ^|
echo  ^|  3. ATAU buka CMD dan ketik: python run.py             ^|
echo  ^|                                                        ^|
echo  ^|  Dashboard buka otomatis di: http://localhost:8000     ^|
echo  +========================================================+
echo.
pause
