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

:: --- LANGKAH 1: Cek & Pasang Python Otomatis ---
echo  [1/5] Memeriksa Instalasi Python...

:: Cek path instalasi standar di LocalAppData atau Program Files terlebih dahulu
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;!PATH!"
)
if exist "%ProgramFiles%\Python311\python.exe" (
    set "PATH=%ProgramFiles%\Python311;%ProgramFiles%\Python311\Scripts;!PATH!"
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;!PATH!"
)

:: Periksa apakah Python sudah bisa dieksekusi dan memenuhi versi >= 3.10
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if %ERRORLEVEL% EQU 0 goto PYTHON_SIAP

echo.
echo  [INFO] Python belum terpasang atau tidak memenuhi syarat (dibutuhkan Python 3.11+).
echo  [PROSES] Memulai instalasi otomatis Python 3.11 untuk perangkat ini...
echo         Harap tunggu, proses unduh dan instalasi berjalan otomatis di latar belakang...
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
    "$installer = Join-Path $env:TEMP 'python-3.11.9-amd64.exe';" ^
    "if (-not (Test-Path $installer)) {" ^
    "    Write-Host '  --> Mengunduh installer resmi Python 3.11.9 dari python.org...';" ^
    "    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
    "    try {" ^
    "        Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile $installer -UseBasicParsing;" ^
    "    } catch {" ^
    "        Write-Host '  [ERROR] Gagal mengunduh installer Python: ' $_.Exception.Message;" ^
    "        exit 1;" ^
    "    }" ^
    "};" ^
    "Write-Host '  --> Memasang Python 3.11.9 secara otomatis...';" ^
    "$proc = Start-Process -FilePath $installer -ArgumentList '/quiet InstallAllUsers=0 Include_launcher=0 PrependPath=1' -Wait -PassThru;" ^
    "exit $proc.ExitCode"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [PERINGATAN] Instalasi via installer langsung gagal. Mencoba alternatif via winget...
    winget install --id Python.Python.3.11 --exact --source winget --accept-package-agreements --accept-source-agreements --silent >nul 2>&1
)

:: Refresh PATH lingkungan pengguna agar Python yang baru dipasang langsung terbaca
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;!PATH!"
)
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do (
    set "USER_PATH=%%b"
    if defined USER_PATH set "PATH=!USER_PATH!;!PATH!"
)

:: Cek ulang setelah proses instalasi otomatis
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Python gagal dipasang secara otomatis!
    echo.
    echo  Silakan download dan install Python 3.11+ secara manual dari:
    echo  https://www.python.org/downloads/
    echo  PENTING: Centang kotak "Add Python to PATH" saat instalasi.
    goto GAGAL
)
echo  [OK] Python 3.11 berhasil dipasang dan dikonfigurasi otomatis.

:PYTHON_SIAP
python -c "import sys; print(f'      Versi Python: {sys.version.split()[0]}')"
echo  [SUDAH ADA] Python valid dan siap digunakan.
echo.

:: --- LANGKAH 2: Update pip ---
echo  [2/5] Memeriksa ^& Memperbarui pip...
python -m pip install --upgrade pip
echo  [OK] pip siap digunakan.
echo.

:: --- LANGKAH 3: Cek & Pasang Dependensi AI ---
echo  [3/5] Memeriksa Dependensi AI (requirements.txt)...
python -c "import importlib.util, sys; pkgs = ['ultralytics', 'supervision', 'cv2', 'torch', 'fastapi', 'uvicorn', 'aiosqlite', 'yaml', 'dotenv', 'PIL', 'telegram', 'GPUtil', 'torchreid']; missing = [p for p in pkgs if importlib.util.find_spec(p) is None]; sys.exit(0 if not missing else 1)" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo  [SUDAH LENGKAP] Semua dependensi AI utama sudah terpasang.
    echo                  Melewati pengunduhan ulang dependensi.
) else (
    echo  [PROSES] Mengunduh ^& memasang dependensi yang belum ada...
    python -m pip install -r "%~dp0requirements.txt"
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo  [ERROR] Instalasi dependensi requirements.txt gagal!
        echo  Pastikan koneksi internet terhubung lalu coba kembali.
        goto GAGAL
    )
    echo  [OK] Semua dependensi Python berhasil diinstall.
)
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
    echo  [SUDAH ADA] Komponen Dashboard Web sudah siap - tidak perlu build ulang.
)
echo.

:: --- LANGKAH 4: Konfigurasi .env ---
echo  [4/5] Menyiapkan Konfigurasi (.env)...
if exist "%~dp0.env" goto ENV_SUDAH_ADA

if exist "%~dp0.env.example" (
    copy /y "%~dp0.env.example" "%~dp0.env" >nul
) else (
    echo # CCTV AI Detection --- Konfigurasi otomatis> "%~dp0.env"
    echo TELEGRAM_BOT_TOKEN=>> "%~dp0.env"
    echo TELEGRAM_CHAT_ID=>> "%~dp0.env"
)
echo  [BARU] File .env dasar berhasil dibuat dari template.
goto ENV_SELESAI

:ENV_SUDAH_ADA
echo  [DIPERTAHANKAN] File .env sudah ada - token dan konfigurasi Anda aman, tidak ditimpa.

:ENV_SELESAI
echo.

:: --- LANGKAH 5: Shortcut Desktop Otomatis ---
echo  [5/5] Memeriksa Shortcut "CCTV AI" di Desktop...
if exist "%~dp0scripts\create_desktop_shortcut.ps1" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\create_desktop_shortcut.ps1"
    if %ERRORLEVEL% EQU 0 (
        echo  [OK] Shortcut "CCTV AI" siap di Desktop Anda.
    ) else (
        echo  [INFO] Pembuatan shortcut otomatis dilewati.
    )
) else (
    echo  [INFO] Script shortcut tidak ditemukan.
)
echo.

:: --- SELESAI SETUP & KONFIRMASI KELUAR ---
echo setup_done > "%~dp0.setup_done"
echo  ========================================================
echo  [STATUS] INSTALASI BERHASIL!
echo  ========================================================
echo  Semua dependensi dan komponen telah siap digunakan.
echo.
echo  --- CARA MENGAKTIFKAN CCTV AI ---
echo  1. Buka shortcut "CCTV AI" di Desktop Anda (Start/Stop 1-click), ATAU
echo  2. Jalankan perintah: python run.py
echo.
echo  Dashboard Lokal: http://localhost:8000
echo  ========================================================
echo.
echo  Tekan tombol apa saja untuk menutup jendela ini...
pause >nul
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
