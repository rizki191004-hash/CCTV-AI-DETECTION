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
      Jalankan setup interaktif, lalu langsung run.
  - Jika setup SUDAH dilakukan:
      Langsung jalankan sistem (python run.py).
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
    input(msg)


def run_program():
    banner("CCTV AI Detection --- Sistem Berjalan")
    print("  Dashboard : http://localhost:8000")
    print("  Tekan Ctrl+C untuk menghentikan")
    print()
    try:
        result = subprocess.run([PYTHON, RUN_SCRIPT], cwd=PROJECT_ROOT)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n  [INFO] Sistem dihentikan oleh pengguna.")
        sys.exit(0)


def step_check_python():
    banner("Langkah 1 / 5 : Memeriksa instalasi Python")
    print("  Memastikan Python 3.11+ tersedia.")
    print()
    pause()
    major, minor = sys.version_info.major, sys.version_info.minor
    if major < 3 or (major == 3 and minor < 11):
        print(f"\n  [ERROR] Python {major}.{minor} terlalu lama. Butuh 3.11+.")
        print("  Download: https://www.python.org/downloads/")
        sys.exit(1)
    print(f"\n  [OK] Python {sys.version.split()[0]} ditemukan.")
    print()
    pause()


def step_upgrade_pip():
    banner("Langkah 2 / 5 : Memperbarui pip")
    print("  Memperbarui pip ke versi terbaru.")
    print()
    pause()
    print()
    subprocess.run([PYTHON, "-m", "pip", "install", "--upgrade", "pip", "--quiet"],
                   check=True)
    print("  [OK] pip diperbarui.")
    print()
    pause()


def step_install_deps():
    banner("Langkah 3 / 5 : Menginstall dependensi")
    print("  Menginstall semua library dari requirements.txt.")
    print("  Waktu: 5-15 menit tergantung kecepatan internet.")
    print()
    pause()
    print()
    result = subprocess.run([PYTHON, "-m", "pip", "install", "-r", REQ_FILE])
    if result.returncode != 0:
        print("\n  [ERROR] Gagal menginstall dependensi!")
        print("  Pastikan koneksi internet aktif, lalu coba lagi.")
        sys.exit(1)
    print("\n  [OK] Semua dependensi berhasil diinstall.")
    print()
    pause()


def step_config_env():
    banner("Langkah 4 / 5 : Konfigurasi aplikasi (.env)")
    if os.path.exists(ENV_FILE):
        print("  File .env sudah ada -- dilewati.")
        print()
        pause()
        return
    print("  File .env belum ada. Isi konfigurasi dasar.")
    print("  (Kosongkan = isi nanti di file .env)")
    print()
    pause()
    print()
    bot_token = input("  Masukkan Telegram Bot Token : ").strip()
    chat_id   = input("  Masukkan Telegram Chat ID   : ").strip()
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("# CCTV AI Detection --- Konfigurasi dibuat oleh launch.py\n")
        f.write(f"TELEGRAM_BOT_TOKEN={bot_token}\n")
        f.write(f"TELEGRAM_CHAT_ID={chat_id}\n")
        f.write("\n# Cloudflare Tunnel (kosongkan = Quick Tunnel gratis)\n")
        f.write("# CLOUDFLARE_TUNNEL_TOKEN=\n")
        f.write("\n# PIN Dashboard (kosongkan = tanpa PIN)\n")
        f.write("# DASHBOARD_PIN=\n")
    print("\n  [OK] File .env berhasil dibuat.")
    print()
    pause()


def step_shortcut():
    banner("Langkah 5 / 5 : Shortcut Desktop (opsional)")
    if IS_WINDOWS:
        ps1 = os.path.join(PROJECT_ROOT, "scripts", "create_desktop_shortcut.ps1")
        ans = input("  Buat shortcut 'CCTV AI' di Desktop? (y/n): ").strip().lower()
        if ans == "y" and os.path.exists(ps1):
            r = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", ps1],
                capture_output=True
            )
            if r.returncode == 0:
                print("  [OK] Shortcut berhasil dibuat di Desktop.")
            else:
                print("  [PERINGATAN] Gagal membuat shortcut. Tidak masalah.")
        else:
            print("  Dilewati.")
    else:
        link = "/usr/local/bin/cctv-ai"
        ans = input(f"  Buat alias 'cctv-ai' di {link}? (y/n): ").strip().lower()
        if ans == "y":
            try:
                subprocess.run(["sudo", "ln", "-sf", RUN_SCRIPT, link], check=True)
                print("  [OK] Ketik 'cctv-ai' dari mana saja untuk menjalankan.")
            except Exception:
                print("  [PERINGATAN] Gagal (butuh sudo). Tidak masalah.")
        else:
            print("  Dilewati.")
    print()
    pause()


def do_setup(mode: str):
    step_check_python()
    step_upgrade_pip()
    step_install_deps()
    if mode == "1":
        step_config_env()
        step_shortcut()
    # Tandai setup selesai
    with open(SENTINEL, "w") as f:
        f.write("setup_done\n")
    banner("Setup Selesai! Menjalankan sistem sekarang...")
    pause("  Tekan Enter untuk mulai...")


def main():
    # Jika sudah pernah setup, langsung run
    if os.path.exists(SENTINEL):
        banner("CCTV AI Detection --- Smart Launcher")
        print("  [OK] Setup sudah selesai sebelumnya.")
        print("       Langsung menjalankan sistem...")
        print()
        pause("  Tekan Enter untuk mulai...")
        run_program()
        return

    # Setup pertama kali
    banner("CCTV AI Detection --- Setup Pertama Kali")
    print("  Pilih mode instalasi:")
    print()
    print("    [1]  Install Lengkap  (deps + Telegram config + shortcut)")
    print("    [2]  Install Minimal  (deps saja)")
    print()
    while True:
        mode = input("  Masukkan pilihan (1/2) lalu tekan Enter: ").strip()
        if mode in ("1", "2"):
            break
        print("  [!] Pilihan tidak valid.")

    print()
    label = "Install Lengkap" if mode == "1" else "Install Minimal"
    print(f"  Mode: {label} dipilih.")
    print()
    print("  Tekan Enter di setiap langkah, Ctrl+C untuk batal.")
    print()
    pause("  Tekan Enter untuk mulai...")

    do_setup(mode)
    run_program()


if __name__ == "__main__":
    main()
