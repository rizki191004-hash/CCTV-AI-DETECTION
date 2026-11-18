#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║           CCTV AI DETECTION — Launcher                      ║
║   Double-click atau jalankan: python run.py                  ║
╚══════════════════════════════════════════════════════════════╝

Launcher ini:
  1. Memastikan working directory benar
  2. Menjalankan: python src/main.py
  3. Cloudflare Tunnel otomatis dibuka di dalam Python
  4. URL mobile dikirim ke Telegram secara otomatis
  5. Browser lokal otomatis terbuka di http://localhost:8000
"""
import subprocess
import sys
import os

# Pastikan CWD = direktori tempat run.py berada (root project)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)

BANNER = r"""
  ██████╗ ██████╗████████╗██╗   ██╗     █████╗ ██╗
 ██╔════╝██╔════╝╚══██╔══╝██║   ██║    ██╔══██╗██║
 ██║     ██║        ██║   ██║   ██║    ███████║██║
 ██║     ██║        ██║   ╚██╗ ██╔╝    ██╔══██║██║
 ╚██████╗╚██████╗   ██║    ╚████╔╝     ██║  ██║██║
  ╚═════╝ ╚═════╝   ╚═╝     ╚═══╝      ╚═╝  ╚═╝╚═╝

      CCTV AI Detection — Mobile-Ready Edition
------------------------------------------------------
  🖥️  LOKAL   : http://localhost:8000
                (browser akan terbuka otomatis)

  📱 MOBILE  : URL Cloudflare Tunnel akan muncul
                di log dan dikirim ke Telegram

  🔒 PIN GATE: Aktifkan dengan set DASHBOARD_PIN=
                di file .env (kosong = tanpa PIN)

  💡 SILENT  : Gunakan shortcut Desktop "CCTV AI" atau
                cctv.pyw untuk mode hening (tanpa terminal)
------------------------------------------------------
  Tekan Ctrl+C untuk menghentikan
------------------------------------------------------
"""

print(BANNER)

try:
    result = subprocess.run(
        [sys.executable, "src/main.py"],
        cwd=PROJECT_ROOT,
    )
    sys.exit(result.returncode)
except KeyboardInterrupt:
    print("\n[run.py] Dihentikan oleh pengguna.")
    sys.exit(0)
except FileNotFoundError:
    print("[ERROR] src/main.py tidak ditemukan. Pastikan Anda berada di root project.")
    sys.exit(1)

