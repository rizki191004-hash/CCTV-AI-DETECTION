@echo off
setlocal enabledelayedexpansion

:: ================================================================
:: setup.bat --- CCTV AI Detection: Smart Setup & Launcher
:: Windows launcher: setup otomatis jika belum, lalu langsung run.
:: ================================================================

title CCTV AI Detection - Launcher
cd /d "%~dp0"

:CEK_STATUS
cls
echo.
echo  +========================================================+
echo  ^|       CCTV AI Detection --- Smart Setup ^& Launcher     ^|
echo  +========================================================+
echo.

if exist "%~dp0.setup_done" (
    echo  [PEMBERITAHUAN STATUS]
    echo  --------------------------------------------------------
    echo  STATUS: SISTEM SUDAH TERINSTALL SEBELUMNYA.
    echo  Semua dependensi dan konfigurasi sudah siap digunakan.
    echo  --------------------------------------------------------
    echo.
    echo  Pilih opsi:
    echo    [1] Langsung Jalankan CCTV AI (Rekomendasi)
    echo    [2] Install Ulang / Perbarui Dependensi (Setup Ulang)
    echo    [3] Keluar
    echo.
    set /p PILIHAN_SUDAH="  Masukkan pilihan (1/2/3) [Default 1]: "
    if "!PILIHAN_SUDAH!"=="" set PILIHAN_SUDAH=1
    if "!PILIHAN_SUDAH!"=="1" goto JALANKAN_SISTEM
    if "!PILIHAN_SUDAH!"=="2" goto KONFIRMASI_SETUP_ULANG
    if "!PILIHAN_SUDAH!"=="3" goto KELUAR
    echo.
    echo  [!] Pilihan tidak valid. Silakan ketik 1, 2, atau 3.
    timeout /t 2 >nul
    goto CEK_STATUS
) else (
    echo  [PEMBERITAHUAN STATUS]
    echo  --------------------------------------------------------
    echo  STATUS: SISTEM BELUM TERINSTALL DI PERANGKAT INI.
    echo  Sistem akan memandu instalasi otomatis step-by-step.
    echo  --------------------------------------------------------
    echo.
    echo  Pilih mode instalasi:
    echo    [1] Install Lengkap (Dependensi + Konfigurasi .env + Shortcut)
    echo    [2] Install Cepat   (Hanya Dependensi, skip konfigurasi/shortcut)
    echo    [3] Keluar / Batalkan
    echo.
    set /p INSTALL_MODE="  Masukkan pilihan (1/2/3) [Default 1]: "
    if "!INSTALL_MODE!"=="" set INSTALL_MODE=1
    if "!INSTALL_MODE!"=="1" goto MULAI_SETUP
    if "!INSTALL_MODE!"=="2" goto MULAI_SETUP
    if "!INSTALL_MODE!"=="3" goto KELUAR
    echo.
    echo  [!] Pilihan tidak valid. Silakan ketik 1, 2, atau 3.
    timeout /t 2 >nul
    goto CEK_STATUS
)

:KONFIRMASI_SETUP_ULANG
echo.
echo  --------------------------------------------------------
echo  [KONFIRMASI] Anda memilih Setup Ulang / Perbarui.
echo  --------------------------------------------------------
del /f /q "%~dp0.setup_done" >nul 2>&1
echo  Penanda instalasi lama telah dibersihkan.
echo  Memulai proses instalasi baru...
timeout /t 2 >nul
goto CEK_STATUS

:MULAI_SETUP
echo.
echo  ========================================================
echo  [INFO] MEMULAI PROSES INSTALASI OTOMATIS
echo  ========================================================
if "!INSTALL_MODE!"=="1" (
    echo  Mode Terpilih: [1] Install Lengkap
) else (
    echo  Mode Terpilih: [2] Install Cepat (Minimal)
)
echo.
echo  Tekan tombol apa saja untuk memulai instalasi...
pause >nul

:: --- LANGKAH 1: Cek Python ---
echo.
echo  --------------------------------------------------------
echo  [Langkah 1/5] Memeriksa Instalasi Python...
echo  --------------------------------------------------------
python --version 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Python tidak ditemukan di PATH sistem Anda!
    echo.
    echo  Silakan download dan install Python 3.11+ dari:
    echo  https://www.python.org/downloads/
    echo.
    echo  PENTING: Centang kotak "Add Python to PATH" saat instalasi.
    goto GAGAL
)
python -c "import sys; print(f'Versi Python terdeteksi: {sys.version.split()[0]}')"
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [PERINGATAN] Versi Python di bawah 3.10. Disarankan Python 3.11 atau lebih baru.
) else (
    echo  [OK] Versi Python memenuhi syarat.
)

:: --- LANGKAH 2: Update pip ---
echo.
echo  --------------------------------------------------------
echo  [Langkah 2/5] Memeriksa & Memperbarui pip...
echo  --------------------------------------------------------
python -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 (
    echo  [PERINGATAN] Pembaruan pip gagal atau dibatasi. Melanjutkan dengan pip yang ada.
) else (
    echo  [OK] pip siap digunakan.
)

:: --- LANGKAH 3: Install Dependensi ---
echo.
echo  --------------------------------------------------------
echo  [Langkah 3/5] Menginstall Dependensi (requirements.txt)...
echo  --------------------------------------------------------
echo  Mengunduh dan memasang library AI (OpenCV, YOLO, PyTorch, FastAPI, dll).
echo  Proses ini memerlukan koneksi internet aktif.
echo  Harap jangan menutup jendela ini hingga instalasi selesai...
echo.
python -m pip install -r "%~dp0requirements.txt"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Instalasi dependensi requirements.txt gagal!
    echo  Pastikan koneksi internet terhubung dan coba ulangi kembali.
    goto GAGAL
)
echo.
echo  [OK] Seluruh dependensi berhasil diinstall!

:: --- LANGKAH 4: Konfigurasi .env ---
echo.
echo  --------------------------------------------------------
echo  [Langkah 4/5] Konfigurasi Pengaturan (.env)...
echo  --------------------------------------------------------
if "!INSTALL_MODE!"=="2" (
    echo  [INFO] Mode Cepat aktif: Konfigurasi dilewati.
    goto LANGKAH_SHORTCUT
)

if exist "%~dp0.env" (
    echo  [OK] File .env sudah ada (konfigurasi yang ada dipertahankan).
    goto LANGKAH_SHORTCUT
)

echo  Mengatur konfigurasi awal Telegram Notifier:
echo  (Tekan Enter jika ingin melewati dan mengisi nanti di file .env)
echo.
set /p BOT_TOKEN="  1. Masukkan Telegram Bot Token (opsional): "
set /p CHAT_ID="  2. Masukkan Telegram Chat ID   (opsional): "

set ENVFILE=%~dp0.env
echo # CCTV AI Detection --- Konfigurasi otomatis> "!ENVFILE!"
echo TELEGRAM_BOT_TOKEN=!BOT_TOKEN!>> "!ENVFILE!"
echo TELEGRAM_CHAT_ID=!CHAT_ID!>> "!ENVFILE!"
echo.>> "!ENVFILE!"
echo # Cloudflare Quick Tunnel (kosongkan = otomatis gratis)>> "!ENVFILE!"
echo # CLOUDFLARE_TUNNEL_TOKEN=>> "!ENVFILE!"
echo.>> "!ENVFILE!"
echo # PIN Dashboard Mobile (kosongkan = tanpa PIN)>> "!ENVFILE!"
echo # DASHBOARD_PIN=>> "!ENVFILE!"

echo.
echo  [OK] File konfigurasi .env berhasil dibuat!

:: --- LANGKAH 5: Shortcut Desktop ---
:LANGKAH_SHORTCUT
echo.
echo  --------------------------------------------------------
echo  [Langkah 5/5] Membuat Shortcut Desktop (Opsional)...
echo  --------------------------------------------------------
if "!INSTALL_MODE!"=="2" (
    echo  [INFO] Mode Cepat aktif: Pembuatan shortcut dilewati.
    goto SELESAI_SETUP
)

set /p BUAT_SC="  Buat shortcut 'CCTV AI' di Desktop? (y/n) [Default y]: "
if "!BUAT_SC!"=="" set BUAT_SC=y
if /i "!BUAT_SC!"=="y" (
    if exist "%~dp0scripts\create_desktop_shortcut.ps1" (
        powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\create_desktop_shortcut.ps1"
        if %ERRORLEVEL% EQU 0 (
            echo  [OK] Shortcut "CCTV AI" berhasil dibuat di Desktop Anda.
        ) else (
            echo  [INFO] Pembuatan shortcut dilewati / tidak dapat dijalankan.
        )
    ) else (
        echo  [INFO] Script shortcut tidak ditemukan, dilewati.
    )
) else (
    echo  [INFO] Pembuatan shortcut dilewati oleh pengguna.
)

:: --- SELESAI SETUP ---
:SELESAI_SETUP
echo setup_done > "%~dp0.setup_done"
echo.
echo  ========================================================
echo  [STATUS] INSTALASI OTOMATIS BERHASIL!
echo  ========================================================
echo  Sistem CCTV AI Detection telah terkonfigurasi lengkap.
echo.
echo  Tekan tombol apa saja untuk langsung menjalankan CCTV AI...
pause >nul
goto JALANKAN_SISTEM

:: --- RUN PROGRAM ---
:JALANKAN_SISTEM
cls
echo.
echo  +========================================================+
echo  ^|       CCTV AI Detection --- Menjalankan Sistem         ^|
echo  +========================================================+
echo.
echo  [PEMBERITAHUAN SISTEM]
echo  - Live Dashboard Lokal : http://localhost:8000
echo  - Cloudflare Tunnel    : Dikelola otomatis ^(cek log/Telegram^)
echo  - Cara Menghentikan    : Tekan Ctrl+C pada jendela ini
echo.
echo  Memulai sistem CCTV AI...
echo.
python "%~dp0run.py"
echo.
echo  ========================================================
echo  [INFO] Sistem CCTV AI Detection telah dihentikan.
echo  ========================================================
goto KELUAR

:GAGAL
echo.
echo  ========================================================
echo  [ERROR] Terjadi kesalahan dalam proses instalasi!
echo  Jendela ini TIDAK akan tertutup otomatis.
echo  Silakan periksa pesan error di atas.
echo  ========================================================
goto KELUAR

:KELUAR
echo.
echo  Tekan tombol apa saja untuk menutup jendela ini...
pause >nul
exit /b 0
