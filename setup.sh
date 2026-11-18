#!/usr/bin/env bash
# ================================================================
# setup.sh --- CCTV AI Detection: Smart Setup + Launcher
# Linux / macOS launcher: setup otomatis jika belum, lalu run.
# Untuk Windows gunakan: setup.bat (double-click)
# ================================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SENTINEL="$SCRIPT_DIR/.setup_done"
ENV_FILE="$SCRIPT_DIR/.env"
REQ_FILE="$SCRIPT_DIR/requirements.txt"

clear
echo ""
echo "  +======================================================+"
echo "  |      CCTV AI Detection --- Smart Launcher           |"
echo "  |  Setup otomatis + jalankan sistem sekaligus         |"
echo "  +======================================================+"
echo ""

# ── Cek apakah setup sudah pernah dilakukan ──────────────────────
if [ -f "$SENTINEL" ]; then
    echo "  [OK] Setup sudah selesai sebelumnya. Langsung menjalankan sistem..."
    echo ""
    run_program
fi

# ── Belum pernah setup: pilih mode ───────────────────────────────
echo "  Ini adalah instalasi pertama. Pilih mode:"
echo ""
echo "    [1]  Install Lengkap  (deps + konfigurasi Telegram + shortcut)"
echo "    [2]  Install Minimal  (deps saja)"
echo ""
while true; do
    read -rp "  Masukkan pilihan (1/2) lalu tekan Enter: " INSTALL_MODE
    case "$INSTALL_MODE" in
        1|2) break ;;
        *) echo "  [!] Pilihan tidak valid. Ketik 1 atau 2." ;;
    esac
done

echo ""
[ "$INSTALL_MODE" = "1" ] && echo "  Mode: Install Lengkap." || echo "  Mode: Install Minimal."
echo ""
echo "  Tekan Enter di setiap langkah, Ctrl+C untuk batal."
echo ""
read -rp "  Tekan Enter untuk mulai..." _

# ================================================================
# LANGKAH 1 -- Cek Python
# ================================================================
clear
echo ""
echo "  +======================================================+"
echo "  |  Langkah 1 / 5 : Memeriksa instalasi Python         |"
echo "  +======================================================+"
echo ""
read -rp "  Tekan Enter untuk lanjut..." _
echo ""

if ! command -v python3 &>/dev/null; then
    echo "  [ERROR] Python 3 tidak ditemukan!"
    echo "  Install Python 3.11+ dari: https://www.python.org/downloads/"
    exit 1
fi
PYVER=$(python3 --version 2>&1)
echo "  [OK] $PYVER ditemukan."
echo ""
read -rp "  Tekan Enter untuk lanjut..." _

# ================================================================
# LANGKAH 2 -- Upgrade pip
# ================================================================
clear
echo ""
echo "  +======================================================+"
echo "  |  Langkah 2 / 5 : Memperbarui pip                    |"
echo "  +======================================================+"
echo ""
read -rp "  Tekan Enter untuk lanjut..." _
echo ""
python3 -m pip install --upgrade pip --quiet
echo "  [OK] pip diperbarui."
echo ""
read -rp "  Tekan Enter untuk lanjut..." _

# ================================================================
# LANGKAH 3 -- Install dependensi
# ================================================================
clear
echo ""
echo "  +======================================================+"
echo "  |  Langkah 3 / 5 : Menginstall dependensi             |"
echo "  +======================================================+"
echo ""
echo "  Waktu: 5-15 menit tergantung kecepatan internet."
echo ""
read -rp "  Tekan Enter untuk lanjut..." _
echo ""
python3 -m pip install -r "$REQ_FILE"
echo ""
echo "  [OK] Semua dependensi berhasil diinstall."
echo ""
read -rp "  Tekan Enter untuk lanjut..." _

# ================================================================
# LANGKAH 4 -- Konfigurasi .env  (hanya mode Lengkap)
# ================================================================
clear
echo ""
echo "  +======================================================+"
echo "  |  Langkah 4 / 5 : Konfigurasi aplikasi (.env)        |"
echo "  +======================================================+"
echo ""

if [ "$INSTALL_MODE" = "2" ]; then
    echo "  [--] Mode Minimal -- langkah ini dilewati."
    read -rp "  Tekan Enter untuk lanjut..." _
elif [ -f "$ENV_FILE" ]; then
    echo "  File .env sudah ada -- dilewati."
    read -rp "  Tekan Enter untuk lanjut..." _
else
    echo "  File .env belum ada. Isi konfigurasi:"
    echo "  (Kosongkan = isi nanti di file .env)"
    echo ""
    read -rp "  Masukkan Telegram Bot Token: " BOT_TOKEN
    read -rp "  Masukkan Telegram Chat ID  : " CHAT_ID
    {
        echo "# CCTV AI Detection --- Konfigurasi dibuat oleh setup.sh"
        echo "TELEGRAM_BOT_TOKEN=$BOT_TOKEN"
        echo "TELEGRAM_CHAT_ID=$CHAT_ID"
        echo ""
        echo "# Cloudflare Tunnel (kosongkan = pakai Quick Tunnel gratis)"
        echo "# CLOUDFLARE_TUNNEL_TOKEN="
        echo ""
        echo "# PIN Dashboard (kosongkan = tanpa PIN)"
        echo "# DASHBOARD_PIN="
    } > "$ENV_FILE"
    echo "  [OK] File .env berhasil dibuat."
    read -rp "  Tekan Enter untuk lanjut..." _
fi

# ================================================================
# LANGKAH 5 -- Shortcut (hanya mode Lengkap, Linux/Mac)
# ================================================================
clear
echo ""
echo "  +======================================================+"
echo "  |  Langkah 5 / 5 : Shortcut (opsional)                |"
echo "  +======================================================+"
echo ""

if [ "$INSTALL_MODE" = "2" ]; then
    echo "  [--] Mode Minimal -- langkah ini dilewati."
    read -rp "  Tekan Enter untuk lanjut..." _
else
    read -rp "  Buat shortcut/alias 'cctv-ai' di /usr/local/bin? (y/n): " BUAT_SC
    if [[ "$BUAT_SC" =~ ^[Yy]$ ]]; then
        LINK="/usr/local/bin/cctv-ai"
        LAUNCHER="$SCRIPT_DIR/launch.py"
        sudo ln -sf "$LAUNCHER" "$LINK" 2>/dev/null && \
            echo "  [OK] Shortcut dibuat: ketik 'cctv-ai' dari mana saja." || \
            echo "  [PERINGATAN] Gagal membuat shortcut (butuh sudo). Tidak masalah."
    else
        echo "  Dilewati."
    fi
    read -rp "  Tekan Enter untuk lanjut..." _
fi

# ── Tandai setup selesai ──────────────────────────────────────────
echo "setup_done" > "$SENTINEL"

clear
echo ""
echo "  +======================================================+"
echo "  |   Setup Selesai! Menjalankan sistem sekarang...     |"
echo "  +======================================================+"
echo ""
read -rp "  Tekan Enter untuk mulai..." _

# ================================================================
# RUN
# ================================================================
run_program() {
    clear
    echo ""
    echo "  +======================================================+"
    echo "  |      CCTV AI Detection --- Sistem Berjalan          |"
    echo "  |  Dashboard: http://localhost:8000                    |"
    echo "  |  Tekan Ctrl+C untuk menghentikan                    |"
    echo "  +======================================================+"
    echo ""
    python3 "$SCRIPT_DIR/run.py"
    echo ""
    echo "  [INFO] Sistem dihentikan."
}

run_program
