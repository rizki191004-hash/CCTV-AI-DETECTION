#!/usr/bin/env python3
"""
launch.py --- CCTV AI Detection: Setup & Lifecycle Manager
=========================================================
Pilihan:
  [1] Install Semua Otomatis Sistem & Shortcut Desktop
  [2] Hapus Semua Komponen Sistem & Shortcut (Uninstall)
  [3] Keluar (Exit)
"""

import os
import sys
import subprocess
import platform

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SENTINEL     = os.path.join(PROJECT_ROOT, ".setup_done")
ENV_FILE     = os.path.join(PROJECT_ROOT, ".env")
REQ_FILE     = os.path.join(PROJECT_ROOT, "requirements.txt")
RUN_SCRIPT   = os.path.join(PROJECT_ROOT, "run.py")

IS_WINDOWS = platform.system() == "Windows"
PYTHON     = sys.executable


def clear():
    os.system("cls" if IS_WINDOWS else "clear")


def banner(title: str):
    clear()
    print()
    print("  +========================================================+")
    print(f"  |  {title:<54}|")
    print("  +========================================================+")
    print()


def pause(msg="  Tekan Enter untuk lanjut..."):
    try:
        input(msg)
    except (EOFError, KeyboardInterrupt):
        pass


def run_program():
    banner("CCTV AI Detection --- Menjalankan Sistem")
    print("  [PEMBERITAHUAN SISTEM]")
    print("  - Live Dashboard Lokal : http://localhost:8000")
    print("  - Cloudflare Tunnel    : Dikelola otomatis (cek log/Telegram)")
    print("  - Cara Menghentikan    : Tekan Ctrl+C pada jendela ini")
    print()
    print("  Memulai sistem CCTV AI...")
    print()
    try:
        result = subprocess.run([PYTHON, RUN_SCRIPT], cwd=PROJECT_ROOT)
        print("\n  ========================================================")
        print("  [INFO] Sistem CCTV AI Detection telah dihentikan.")
        print("  ========================================================")
        pause("\n  Tekan Enter untuk menutup...")
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n  [INFO] Sistem dihentikan oleh pengguna.")
        pause("\n  Tekan Enter untuk menutup...")
        sys.exit(0)


def step_check_python():
    print()
    print("  --------------------------------------------------------")
    print("  [Langkah 1/5] Memeriksa Instalasi Python...")
    print("  --------------------------------------------------------")
    major, minor = sys.version_info.major, sys.version_info.minor
    print(f"  Versi Python terdeteksi: {sys.version.split()[0]}")
    if major < 3 or (major == 3 and minor < 10):
        print(f"\n  [ERROR] Python {major}.{minor} tidak didukung. Butuh Python 3.10+ (disarankan 3.11+).")
        print("  Download: https://www.python.org/downloads/")
        pause("\n  Tekan Enter untuk menutup...")
        sys.exit(1)
    print("  [OK] Versi Python memenuhi syarat.")


def step_upgrade_pip():
    print()
    print("  --------------------------------------------------------")
    print("  [Langkah 2/5] Memeriksa & Memperbarui pip...")
    print("  --------------------------------------------------------")
    try:
        subprocess.run([PYTHON, "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
        print("  [OK] pip siap digunakan.")
    except Exception as e:
        print(f"  [PERINGATAN] Gagal update pip ({e}), melanjutkan...")


def step_install_deps():
    print()
    print("  --------------------------------------------------------")
    print("  [Langkah 3/5] Menginstall Dependensi (requirements.txt)...")
    print("  --------------------------------------------------------")
    print("  Mengunduh dan memasang paket AI (OpenCV, YOLO, PyTorch, FastAPI, dll).")
    print("  Harap tunggu hingga proses selesai...")
    print()
    result = subprocess.run([PYTHON, "-m", "pip", "install", "-r", REQ_FILE])
    if result.returncode != 0:
        print("\n  [ERROR] Gagal menginstall dependensi!")
        print("  Pastikan koneksi internet aktif, lalu coba lagi.")
        pause("\n  Tekan Enter untuk menutup...")
        sys.exit(1)
    print("\n  [OK] Semua dependensi berhasil diinstall!")

    # Check dashboard dist
    dist_index = os.path.join(PROJECT_ROOT, "dashboard", "dist", "index.html")
    if os.path.exists(dist_index):
        print("  [OK] Komponen tampilan Dashboard Web siap.")
    else:
        print("  [PERINGATAN] Folder dashboard/dist belum ditemukan!")


def step_config_env():
    print()
    print("  --------------------------------------------------------")
    print("  [Langkah 4/5] Menyiapkan Konfigurasi (.env)...")
    print("  --------------------------------------------------------")
    if os.path.exists(ENV_FILE):
        print("  [OK] File .env sudah ada (konfigurasi dipertahankan).")
        return
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("# CCTV AI Detection --- Konfigurasi otomatis\n")
        f.write("TELEGRAM_BOT_TOKEN=\n")
        f.write("TELEGRAM_CHAT_ID=\n")
        f.write("\n# Cloudflare Quick Tunnel (kosongkan = otomatis gratis)\n")
        f.write("# CLOUDFLARE_TUNNEL_TOKEN=\n")
        f.write("\n# PIN Dashboard Mobile (kosongkan = tanpa PIN)\n")
        f.write("# DASHBOARD_PIN=\n")
    print("  [OK] File konfigurasi .env dasar berhasil dibuat!")


def create_shortcut():
    print()
    print("  --------------------------------------------------------")
    print("  [Langkah 5/5] Membuat Shortcut Desktop Otomatis...")
    print("  --------------------------------------------------------")
    if IS_WINDOWS:
        ps1 = os.path.join(PROJECT_ROOT, "scripts", "create_desktop_shortcut.ps1")
        if os.path.exists(ps1):
            r = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", ps1],
                capture_output=True,
                text=True
            )
            if r.returncode == 0:
                print("  [OK] Shortcut tunggal CCTV AI berhasil dibuat di Desktop Anda!")
            else:
                print("  [INFO] Pembuatan shortcut otomatis dilewati / tidak didukung.")
        else:
            print("  [INFO] Script shortcut tidak ditemukan.")
    else:
        link = "/usr/local/bin/cctv-ai"
        try:
            subprocess.run(["sudo", "ln", "-sf", RUN_SCRIPT, link], check=True)
            print("  [OK] Shortcut dibuat: ketik 'cctv-ai' dari terminal.")
        except Exception:
            print("  [INFO] Shortcut terminal dilewati.")


def do_setup():
    clear()
    banner("Memulai Instalasi Otomatis Sistem & Shortcut")
    step_check_python()
    step_upgrade_pip()
    step_install_deps()
    step_config_env()
    create_shortcut()

    with open(SENTINEL, "w") as f:
        f.write("setup_done\n")

    print("\n  ========================================================")
    print("  [STATUS] INSTALASI BERHASIL!")
    print("  ========================================================")
    print("  Semua dependensi dan komponen telah siap digunakan.")
    print()
    print("  >> UNTUK MENGAKTIFKAN CCTV AI:")
    print("     Buka shortcut 'CCTV AI' di Desktop Anda!")
    print()
    print("  Jendela ini akan menutup otomatis dalam 3 detik...")
    import time
    time.sleep(3)
    sys.exit(0)


def do_uninstall():
    clear()
    banner("Pembersihan Sistem & Penghapusan Shortcut")
    print("  1. Menghentikan proses CCTV AI latar belakang...")
    if IS_WINDOWS:
        subprocess.run(["taskkill", "/F", "/IM", "cloudflared.exe"], capture_output=True)
        subprocess.run([
            "powershell", "-Command",
            "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*src\\main.py*' -or $_.CommandLine -like '*run.py*' -or $_.CommandLine -like '*cctv.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        ], capture_output=True)
    print("     [OK] Proses latar belakang telah dihentikan.")

    print("\n  2. Menghapus shortcut CCTV AI dari Desktop...")
    if IS_WINDOWS:
        subprocess.run([
            "powershell", "-Command",
            "$dirs = @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('CommonDesktopDirectory'), (Join-Path [Environment]::GetFolderPath('UserProfile') 'Desktop'), (Join-Path [Environment]::GetFolderPath('UserProfile') 'OneDrive\\Desktop')); foreach ($d in $dirs) { if ($d) { $lnk = Join-Path $d 'CCTV AI.lnk'; if (Test-Path $lnk) { Remove-Item $lnk -Force -ErrorAction SilentlyContinue } } }"
        ], capture_output=True)
    else:
        link = "/usr/local/bin/cctv-ai"
        if os.path.exists(link):
            try:
                os.remove(link)
            except Exception:
                pass
    print("     [OK] Shortcut Desktop telah dibersihkan.")

    print("\n  3. Membersihkan status setup dan runtime temporary...")
    for f in [SENTINEL, os.path.join(PROJECT_ROOT, "data", "cctv.pid"), os.path.join(PROJECT_ROOT, "data", "cctv_events.db")]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass
    print("     [OK] Status setup berhasil di-reset.")

    print("\n  ========================================================")
    print("  [STATUS] PEMBERSIHAN SELESAI!")
    print("  ========================================================")
    print("  Shortcut Desktop dan komponen sistem telah dihapus.")
    print("  Sistem CCTV AI telah kembali ke kondisi awal yang bersih.")
    print("\n  Jendela ini akan menutup otomatis dalam 3 detik...")
    import time
    time.sleep(3)
    sys.exit(0)


def main():
    clear()
    banner("CCTV AI Detection --- Setup Menu")

    if os.path.exists(SENTINEL):
        print("  [STATUS] Sistem CCTV AI saat ini: TERINSTALL")
    else:
        print("  [STATUS] Sistem CCTV AI saat ini: BELUM TERINSTALL")
    print()
    print("  Pilih tindakan:")
    print("    [1] Install Semua Otomatis Sistem & Shortcut Desktop")
    print("    [2] Hapus Semua Komponen Sistem & Shortcut (Uninstall)")
    print("    [3] Keluar (Exit)")
    print()
    ans = input("  Masukkan pilihan (1/2/3) [Default 1]: ").strip()
    if ans == "" or ans == "1":
        do_setup()
    elif ans == "2":
        do_uninstall()
    elif ans == "3":
        sys.exit(0)


if __name__ == "__main__":
    main()
