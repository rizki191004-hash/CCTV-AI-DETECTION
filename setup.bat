@echo off
setlocal enabledelayedexpansion

:: ================================================================
:: setup.bat --- CCTV AI Detection: Installer Otomatis
:: Windows installer: install otomatis, buat shortcut, lalu tutup.
:: Untuk menjalankan CCTV AI: buka shortcut "CCTV AI" di Desktop!
:: ================================================================

title CCTV AI Detection - Setup
cd /d "%~dp0"

:CEK_STATUS
cls
echo.
echo  +========================================================+
echo  ^|            CCTV AI Detection --- Setup                 ^|
echo  +========================================================+
echo.

if exist "%~dp0.setup_done" (
    echo  [STATUS] Sistem CCTV AI sudah terinstall di perangkat ini.
    echo  Silakan buka shortcut "CCTV AI" di Desktop untuk mengaktifkan AI.
    echo.
    echo  Pilihan:
    echo    [1] Jalankan CCTV AI Sekarang
    echo    [2] Buat / Perbaiki Shortcut CCTV AI di Desktop
    echo    [3] Install Ulang / Perbarui Dependensi
    echo    [4] Keluar (Default)
    echo.
    set /p PILIHAN_SUDAH="  Masukkan pilihan (1/2/3/4) [Default 4]: "
    if "!PILIHAN_SUDAH!"=="" set PILIHAN_SUDAH=4
    if "!PILIHAN_SUDAH!"=="1" goto JALANKAN_SISTEM
    if "!PILIHAN_SUDAH!"=="2" goto BUAT_SHORTCUT_SAJA
    if "!PILIHAN_SUDAH!"=="3" goto KONFIRMASI_SETUP_ULANG
    if "!PILIHAN_SUDAH!"=="4" goto KELUAR_CEPAT
    goto KELUAR_CEPAT
)

:: --- Belum terinstall: mulai instalasi otomatis ---
echo  [STATUS] Memulai proses instalasi otomatis untuk perangkat ini...
echo.
echo  Pilih mode instalasi:
echo    [1] Install Lengkap (Otomatis: Dependensi + Shortcut Desktop)
echo    [2] Keluar / Batalkan
echo.
set /p INSTALL_MODE="  Masukkan pilihan (1/2) [Default 1]: "
if "!INSTALL_MODE!"=="" set INSTALL_MODE=1
if "!INSTALL_MODE!"=="1" goto MULAI_SETUP
if "!INSTALL_MODE!"=="2" goto KELUAR_CEPAT
goto MULAI_SETUP

:BUAT_SHORTCUT_SAJA
echo.
echo  --------------------------------------------------------
echo  Membuat shortcut tunggal 'CCTV AI' di Desktop...
echo  --------------------------------------------------------
if exist "%~dp0scripts\create_desktop_shortcut.ps1" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\create_desktop_shortcut.ps1"
    if %ERRORLEVEL% EQU 0 (
        echo  [OK] Shortcut "CCTV AI" berhasil dibuat di Desktop Anda!
    ) else (
        echo  [PERINGATAN] Gagal membuat shortcut via PowerShell.
    )
) else (
    echo  [ERROR] File scripts\create_desktop_shortcut.ps1 tidak ditemukan!
)
echo.
echo  Menutup jendela dalam 3 detik...
timeout /t 3 >nul
exit /b 0

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
echo  [PROSES] MEMULAI INSTALASI OTOMATIS
echo  ========================================================
echo  Harap tunggu, sistem sedang memasang seluruh kebutuhan AI...
echo.

:: --- LANGKAH 1: Cek Python ---
echo  [1/5] Memeriksa Instalasi Python...
python --version 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Python tidak ditemukan di PATH sistem Anda!
    echo.
    echo  Silakan download dan install Python 3.11+ dari:
    echo  https://www.python.org/downloads/
    echo  PENTING: Centang kotak "Add Python to PATH" saat instalasi.
    goto GAGAL
)
python -c "import sys; print(f'      Versi Python: {sys.version.split()[0]}')"
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [PERINGATAN] Versi Python di bawah 3.10. Disarankan Python 3.11+.
) else (
    echo  [OK] Python valid.
)
echo.

:: --- LANGKAH 2: Update pip ---
echo  [2/5] Memeriksa & Memperbarui pip...
python -m pip install --upgrade pip --quiet
echo  [OK] pip siap digunakan.
echo.

:: --- LANGKAH 3: Install Dependensi ---
echo  [3/5] Menginstall Dependensi AI (requirements.txt)...
echo        Mengunduh library (OpenCV, YOLO, PyTorch, FastAPI)...
python -m pip install -r "%~dp0requirements.txt"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Instalasi dependensi requirements.txt gagal!
    echo  Pastikan koneksi internet terhubung lalu coba kembali.
    goto GAGAL
)
echo  [OK] Semua dependensi Python berhasil diinstall.
echo.

:: --- Pengecekan Dashboard Web Frontend ---
if not exist "%~dp0dashboard\dist\index.html" (
    echo  [PERINGATAN] File dashboard web belum ter-build!
    where npm >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo  Membangun komponen dashboard via npm...
        pushd "%~dp0dashboard"
        call npm run build
        popd
    )
) else (
    echo  [OK] Komponen Dashboard Web siap.
)
echo.

:: --- LANGKAH 4: Konfigurasi .env ---
echo  [4/5] Menyiapkan Konfigurasi (.env)...
if not exist "%~dp0.env" (
    set ENVFILE=%~dp0.env
    echo # CCTV AI Detection --- Konfigurasi otomatis> "!ENVFILE!"
    echo TELEGRAM_BOT_TOKEN=>> "!ENVFILE!"
    echo TELEGRAM_CHAT_ID=>> "!ENVFILE!"
    echo.>> "!ENVFILE!"
    echo # Cloudflare Quick Tunnel (kosongkan = otomatis gratis)>> "!ENVFILE!"
    echo # CLOUDFLARE_TUNNEL_TOKEN=>> "!ENVFILE!"
    echo.>> "!ENVFILE!"
    echo # PIN Dashboard Mobile (kosongkan = tanpa PIN)>> "!ENVFILE!"
    echo # DASHBOARD_PIN=>> "!ENVFILE!"
    echo  [OK] File .env dasar berhasil dibuat.
) else (
    echo  [OK] File .env sudah ada (dipertahankan).
)
echo.

:: --- LANGKAH 5: Shortcut Desktop Otomatis ---
echo  [5/5] Membuat Shortcut "CCTV AI" di Desktop...
if exist "%~dp0scripts\create_desktop_shortcut.ps1" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\create_desktop_shortcut.ps1"
    if %ERRORLEVEL% EQU 0 (
        echo  [OK] Shortcut "CCTV AI" berhasil dibuat di Desktop Anda!
    ) else (
        echo  [INFO] Pembuatan shortcut otomatis dilewati.
    )
) else (
    echo  [INFO] Script shortcut tidak ditemukan.
)
echo.

:: --- SELESAI SETUP & KELUAR OTOMATIS ---
:SELESAI_SETUP
echo setup_done > "%~dp0.setup_done"
echo  ========================================================
echo  [STATUS] INSTALASI BERHASIL!
echo  ========================================================
echo  Semua dependensi dan komponen telah siap digunakan.
echo.
echo  >> UNTUK MENGAKTIFKAN CCTV AI:
echo     Buka shortcut "CCTV AI" di Desktop Anda!
echo.
echo  Jendela ini akan menutup otomatis dalam 3 detik...
timeout /t 3 >nul
exit /b 0

:: --- RUN PROGRAM JIKA DIMINTA VIA MENU ---
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
timeout /t 3 >nul
exit /b 0

:GAGAL
echo.
echo  ========================================================
echo  [ERROR] Terjadi kesalahan dalam proses instalasi!
echo  Silakan periksa pesan error di atas.
echo  ========================================================
echo.
echo  Tekan tombol apa saja untuk menutup jendela ini...
pause >nul
exit /b 1

:KELUAR_CEPAT
exit /b 0
