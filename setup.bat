@echo off
setlocal enabledelayedexpansion

:: ================================================================
:: setup.bat --- CCTV AI Detection: Smart Setup + Launcher
:: Windows launcher: setup otomatis jika belum, lalu langsung run.
:: Untuk Linux/Mac gunakan: bash setup.sh
:: ================================================================

cls
echo.
echo  +========================================================+
echo  ^|       CCTV AI Detection --- Smart Launcher            ^|
echo  ^|   Setup otomatis + jalankan sistem sekaligus          ^|
echo  +========================================================+
echo.

:: --- Cek apakah setup sudah pernah dilakukan ---
if exist "%~dp0.setup_done" (
    echo  [OK] Setup sudah selesai sebelumnya. Langsung menjalankan sistem...
    echo.
    goto RUN
)

:: --- Belum pernah setup: tanya mode instalasi ---
echo  Ini adalah instalasi pertama. Pilih mode:
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
echo  Proses berjalan step by step. Tekan Enter di setiap langkah.
echo  Tekan Ctrl+C kapan saja untuk membatalkan.
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
echo  Memperbarui pip ke versi terbaru.
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
echo  Waktu: 5-15 menit tergantung kecepatan internet.
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
    echo.
    pause
    goto LANGKAH5
)

echo  File .env belum ada. Isi konfigurasi dasar:
echo  (Tekan Enter tanpa mengetik apa pun untuk melewati tiap field)
echo.
pause
echo.

echo  +-- TELEGRAM BOT TOKEN ------------------------------------+
echo  ^| Dapatkan token dari @BotFather di Telegram.            ^|
echo  ^| Contoh: 123456789:ABCdefGHIjklMNOpqrSTUvwxYZ          ^|
echo  +----------------------------------------------------------+
set /p BOT_TOKEN="  Masukkan Telegram Bot Token: "
echo.

echo  +-- TELEGRAM CHAT ID --------------------------------------+
echo  ^| Dapatkan Chat ID dari @userinfobot di Telegram.        ^|
echo  ^| Contoh: -123456789 (grup) atau 123456789 (pribadi)     ^|
echo  +----------------------------------------------------------+
set /p CHAT_ID="  Masukkan Telegram Chat ID: "
echo.

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

echo  [OK] File .env berhasil dibuat.
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
    echo.
    pause
    goto TANDAI_SELESAI
)

set /p BUAT_SHORTCUT="  Buat shortcut 'CCTV AI' di Desktop? (y/n): "
if /i "!BUAT_SHORTCUT!"=="y" (
    echo.
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\create_desktop_shortcut.ps1"
    if %ERRORLEVEL% EQU 0 (
        echo  [OK] Shortcut berhasil dibuat di Desktop.
    ) else (
        echo  [PERINGATAN] Gagal membuat shortcut. Tidak masalah, bisa dilewati.
    )
) else (
    echo  Dilewati.
)
echo.
pause

:: ================================================================
:: Tandai setup selesai (sentinel file)
:: ================================================================
:TANDAI_SELESAI
echo setup_done > "%~dp0.setup_done"

cls
echo.
echo  +========================================================+
echo  ^|   Setup Selesai! Menjalankan sistem sekarang...       ^|
echo  +========================================================+
echo.
pause

:: ================================================================
:: RUN -- Jalankan program
:: ================================================================
:RUN
cls
echo.
echo  +========================================================+
echo  ^|       CCTV AI Detection --- Sistem Berjalan           ^|
echo  ^|   Dashboard: http://localhost:8000                     ^|
echo  ^|   Tekan Ctrl+C untuk menghentikan                     ^|
echo  +========================================================+
echo.
python "%~dp0run.py"
echo.
echo  [INFO] Sistem dihentikan.
pause
