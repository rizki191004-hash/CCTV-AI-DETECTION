#!/usr/bin/env python3
"""
launch.py --- CCTV AI Detection: Universal Cross-Platform Launcher
=================================================================
Jalankan file ini di platform mana saja:
  Windows : python launch.py
  Linux   : python3 launch.py
  macOS   : python3 launch.py

Perilaku:
  - Jika setup BELUM dilakukan (.setup_done tidak ada):
      Tampilkan status BELUM TERINSTALL, jalankan setup otomatis, lalu langsung run.
  - Jika setup SUDAH dilakukan:
      Tampilkan status SUDAH TERINSTALL, berikan opsi langsung jalankan atau setup ulang.
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


def step_config_env():
    print()
    print("  --------------------------------------------------------")
    print("  [Langkah 4/5] Konfigurasi Pengaturan (.env)...")
    print("  --------------------------------------------------------")
    if os.path.exists(ENV_FILE):
        print("  [OK] File .env sudah ada (konfigurasi dipertahankan).")
        return
    print("  File .env belum ada. Isi konfigurasi dasar Telegram Notifier:")
    print("  (Tekan Enter jika ingin melewati dan mengisi nanti di file .env)")
    print()
    bot_token = input("  1. Masukkan Telegram Bot Token (opsional): ").strip()
    chat_id   = input("  2. Masukkan Telegram Chat ID   (opsional): ").strip()
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("# CCTV AI Detection --- Konfigurasi otomatis\n")
        f.write(f"TELEGRAM_BOT_TOKEN={bot_token}\n")
        f.write(f"TELEGRAM_CHAT_ID={chat_id}\n")
        f.write("\n# Cloudflare Quick Tunnel (kosongkan = otomatis gratis)\n")
        f.write("# CLOUDFLARE_TUNNEL_TOKEN=\n")
        f.write("\n# PIN Dashboard Mobile (kosongkan = tanpa PIN)\n")
        f.write("# DASHBOARD_PIN=\n")
    print("\n  [OK] File konfigurasi .env berhasil dibuat!")


def step_shortcut():
    print()
    print("  --------------------------------------------------------")
    print("  [Langkah 5/5] Membuat Shortcut Desktop (Opsional)...")
    print("  --------------------------------------------------------")
    if IS_WINDOWS:
        ps1 = os.path.join(PROJECT_ROOT, "scripts", "create_desktop_shortcut.ps1")
        ans = input("  Buat shortcut 'CCTV AI' di Desktop? (y/n) [Default y]: ").strip().lower()
        if ans in ("", "y") and os.path.exists(ps1):
            r = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", ps1],
                capture_output=True
            )
            if r.returncode == 0:
                print("  [OK] Shortcut berhasil dibuat di Desktop Anda.")
            else:
                print("  [INFO] Gagal membuat shortcut otomatis. Dilewati.")
        else:
            print("  [INFO] Pembuatan shortcut dilewati.")
    else:
        link = "/usr/local/bin/cctv-ai"
        ans = input(f"  Buat alias 'cctv-ai' di {link}? (y/n): ").strip().lower()
        if ans == "y":
            try:
                subprocess.run(["sudo", "ln", "-sf", RUN_SCRIPT, link], check=True)
                print("  [OK] Shortcut dibuat: ketik 'cctv-ai' dari terminal.")
            except Exception:
                print("  [INFO] Gagal (butuh sudo), dilewati.")
        else:
            print("  [INFO] Pembuatan shortcut dilewati.")


def do_setup(mode: str):
    print("\n  ========================================================")
    print("  [INFO] MEMULAI PROSES INSTALASI OTOMATIS")
    print("  ========================================================")
    step_check_python()
    step_upgrade_pip()
    step_install_deps()
    if mode == "1":
        step_config_env()
        step_shortcut()
    # Tandai setup selesai
    with open(SENTINEL, "w") as f:
        f.write("setup_done\n")
    print("\n  ========================================================")
    print("  [STATUS] INSTALASI OTOMATIS BERHASIL!")
    print("  ========================================================")
    print("  Sistem CCTV AI Detection siap dijalankan.")
    pause("\n  Tekan Enter untuk langsung menjalankan sistem...")


def main():
    clear()
    banner("CCTV AI Detection --- Smart Setup & Launcher")

    # Jika sudah pernah setup
    if os.path.exists(SENTINEL):
        print("  [PEMBERITAHUAN STATUS]")
        print("  --------------------------------------------------------")
        print("  STATUS: SISTEM SUDAH TERINSTALL SEBELUMNYA.")
        print("  Semua dependensi dan konfigurasi sudah siap digunakan.")
        print("  --------------------------------------------------------")
        print()
        print("  Pilih opsi:")
        print("    [1] Langsung Jalankan CCTV AI (Rekomendasi)")
        print("    [2] Install Ulang / Perbarui Dependensi (Setup Ulang)")
        print("    [3] Keluar")
        print()
        ans = input("  Masukkan pilihan (1/2/3) [Default 1]: ").strip()
        if ans == "" or ans == "1":
            run_program()
            return
        elif ans == "2":
            if os.path.exists(SENTINEL):
                os.remove(SENTINEL)
            print("\n  [INFO] Penanda setup dibersihkan. Memulai setup ulang...")
        elif ans == "3":
            print("\n  [INFO] Keluar.")
            return

    # Setup pertama kali
    print("  [PEMBERITAHUAN STATUS]")
    print("  --------------------------------------------------------")
    print("  STATUS: SISTEM BELUM TERINSTALL DI PERANGKAT INI.")
    print("  Sistem akan memandu instalasi otomatis step-by-step.")
    print("  --------------------------------------------------------")
    print()
    print("  Pilih mode instalasi:")
    print("    [1]  Install Lengkap  (deps + Telegram config + shortcut)")
    print("    [2]  Install Cepat    (deps saja)")
    print("    [3]  Keluar / Batal")
    print()
    while True:
        mode = input("  Masukkan pilihan (1/2/3) [Default 1]: ").strip()
        if mode == "" or mode == "1":
            mode = "1"
            break
        elif mode == "2":
            break
        elif mode == "3":
            print("\n  [INFO] Dibatalkan oleh pengguna.")
            return
        print("  [!] Pilihan tidak valid.")

    do_setup(mode)
    run_program()


if __name__ == "__main__":
    main()
