@echo off
setlocal enabledelayedexpansion

:: ================================================================
:: setup.bat --- CCTV AI Detection: Setup & Lifecycle Manager
:: Pilihan:
::   [1] Install Semua Otomatis Sistem & Shortcut Desktop
::   [2] Hapus Semua Komponen Sistem & Shortcut (Uninstall)
::   [3] Keluar (Exit)
:: ================================================================

title CCTV AI Detection - Setup Menu
cd /d "%~dp0"

:MENU_UTAMA
cls
echo.
echo  +========================================================+
echo  ^|            CCTV AI Detection --- Setup Menu            ^|
echo  +========================================================+
echo.
if exist "%~dp0.setup_done" (
    echo  [STATUS] Sistem CCTV AI saat ini: TERINSTALL
) else (
    echo  [STATUS] Sistem CCTV AI saat ini: BELUM TERINSTALL
)
echo.
echo  Pilih tindakan:
echo    [1] Install Semua Otomatis Sistem ^& Shortcut Desktop
echo    [2] Hapus Semua Komponen Sistem ^& Shortcut (Uninstall)
echo    [3] Keluar (Exit)
echo.
set /p PILIHAN="  Masukkan pilihan (1/2/3) [Default 1]: "
if "!PILIHAN!"=="" set PILIHAN=1
if "!PILIHAN!"=="1" goto PROSES_INSTALL
if "!PILIHAN!"=="2" goto PROSES_UNINSTALL
if "!PILIHAN!"=="3" goto KELUAR
echo.
echo  [!] Pilihan tidak valid. Silakan ketik 1, 2, atau 3.
timeout /t 2 >nul
goto MENU_UTAMA

:: ================================================================
:: [1] PROSES INSTALL LENGKAP & SHORTCUT DESKTOP
:: ================================================================
:PROSES_INSTALL
cls
echo.
echo  ========================================================
echo  [PROSES] MEMULAI INSTALASI OTOMATIS SISTEM ^& SHORTCUT
echo  ========================================================
echo  Harap tunggu, proses ini menyiapkan seluruh kebutuhan AI...
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
echo        Mengunduh paket AI (OpenCV, YOLO, PyTorch, FastAPI)...
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
        echo  [OK] Shortcut tunggal "CCTV AI" berhasil dibuat di Desktop Anda!
    ) else (
        echo  [INFO] Pembuatan shortcut otomatis dilewati.
    )
) else (
    echo  [INFO] Script shortcut tidak ditemukan.
)
echo.

:: --- SELESAI SETUP & KELUAR OTOMATIS ---
echo setup_done > "%~dp0.setup_done"
echo  ========================================================
echo  [STATUS] INSTALASI BERHASIL!
echo  ========================================================
echo  Semua dependensi dan komponen telah siap digunakan.
echo.
echo  --- CARA MENGAKTIFKAN CCTV AI ---
echo  Buka shortcut "CCTV AI" di Desktop Anda!
echo.
echo  Jendela ini akan menutup otomatis dalam 3 detik...
timeout /t 3 >nul
exit /b 0

:: ================================================================
:: [2] PROSES HAPUS SEMUA KOMPONEN SISTEM & SHORTCUT (UNINSTALL)
:: ================================================================
:PROSES_UNINSTALL
cls
echo.
echo  ========================================================
echo  [PROSES] PEMBERSIHAN SISTEM ^& PENGHAPUSAN SHORTCUT
echo  ========================================================
echo.
echo  1. Menghentikan proses CCTV AI dan Cloudflare latar belakang...
taskkill /F /IM cloudflared.exe >nul 2>&1
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*src\main.py*' -or $_.CommandLine -like '*run.py*' -or $_.CommandLine -like '*cctv.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
echo     [OK] Proses latar belakang telah dihentikan.

echo.
echo  2. Menghapus shortcut "CCTV AI" dari Desktop...
powershell -Command "$dirs = @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('CommonDesktopDirectory'), (Join-Path [Environment]::GetFolderPath('UserProfile') 'Desktop'), (Join-Path [Environment]::GetFolderPath('UserProfile') 'OneDrive\Desktop')); foreach ($d in $dirs) { if ($d) { $lnk = Join-Path $d 'CCTV AI.lnk'; if (Test-Path $lnk) { Remove-Item $lnk -Force -ErrorAction SilentlyContinue } } }" >nul 2>&1
echo     [OK] Shortcut Desktop telah dibersihkan.

echo.
echo  3. Membersihkan status setup dan runtime temporary...
del /f /q "%~dp0.setup_done" >nul 2>&1
del /f /q "%~dp0data\cctv.pid" >nul 2>&1
del /f /q "%~dp0data\cctv_events.db" >nul 2>&1
for /d /r "%~dp0" %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" >nul 2>&1
echo     [OK] Status setup dan database event berhasil di-reset.

echo.
echo  ========================================================
echo  [STATUS] PEMBERSIHAN SELESAI!
echo  ========================================================
echo  Shortcut Desktop dan komponen sistem telah dihapus.
echo  Sistem CCTV AI telah kembali ke kondisi awal yang bersih.
echo.
echo  Jendela ini akan menutup otomatis dalam 3 detik...
timeout /t 3 >nul
exit /b 0

:: ================================================================
:: [3] KELUAR
:: ================================================================
:KELUAR
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
