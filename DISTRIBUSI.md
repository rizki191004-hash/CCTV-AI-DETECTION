# 📦 Panduan Distribusi — CCTV AI Detection

Dokumen ini menjelaskan **apa saja yang harus masuk ke dalam ZIP** saat membagikan
aplikasi ke perangkat lain, dan apa yang harus disiapkan penerima.

---

## ✅ File WAJIB masuk ZIP

```
CCTV AI DETECTION/
├── src/                        ← Source code utama
├── config/                     ← Konfigurasi kamera & rules
│   ├── config.yaml
│   └── rules.yaml
├── dashboard/
│   └── dist/                   ← Dashboard web (sudah di-build, siap pakai)
├── scripts/
│   └── create_desktop_shortcut.ps1
├── yolov8n.pt                  ← Model AI deteksi orang (~6.5 MB)
├── yolov8n-pose.pt             ← Model AI pose/kendaraan (~6.8 MB)
├── requirements.txt            ← Daftar package Python
├── setup.bat                   ← ⭐ INSTALLER & LAUNCHER (Windows)
├── setup.sh                    ← ⭐ INSTALLER & LAUNCHER (Linux/macOS)
├── launch.py                   ← ⭐ LAUNCHER UNIVERSAL (Cross-Platform)
├── run.py                      ← Launcher internal
├── cctv.pyw                    ← Launcher tanpa console
├── CARA_INSTALL.txt            ← ⭐ Panduan praktis penerima
├── .env.example                ← Template konfigurasi
├── README.md
└── DISTRIBUSI.md               ← File ini
```

> **Model `.pt` wajib ikut!** File `yolov8n.pt` dan `yolov8n-pose.pt` adalah
> model AI yang akan di-download ulang oleh ultralytics jika tidak ada —
> lebih baik ikutkan agar tidak perlu download lagi (~13 MB total).

---

## ❌ File yang TIDAK perlu masuk ZIP

| File/Folder | Alasan |
|-------------|--------|
| `venv/` atau `.venv/` | Tiap PC punya Python sendiri |
| `node_modules/` | Tidak dibutuhkan (dashboard sudah di-build) |
| `dashboard/node_modules/` | Sama, sudah ada `dist/` |
| `__pycache__/` | Di-generate otomatis oleh Python |
| `.env` | Berisi token pribadi — **JANGAN ikutkan!** |
| `.setup_done` | Penanda lokal perangkat Anda — **JANGAN ikutkan!** |
| `tests/` | Opsional, hanya untuk developer |
| `.git/` | Riwayat git tidak perlu untuk pengguna akhir |
| `data/cctv_events.db` | Database akan dibuat ulang otomatis |
| `docs/` | Opsional |

---

## 🖥️ Prasyarat di Perangkat Penerima

| Kebutuhan | Versi Minimum | Cara Install |
|-----------|--------------|-------------|
| **Sistem Operasi** | Windows 10/11, Linux, macOS | — |
| **Python** | 3.11+ | [python.org/downloads](https://www.python.org/downloads/) ⚠️ centang "Add to PATH" |
| **Internet** | — | Untuk download package saat pertama kali setup |
| GPU NVIDIA | Opsional | Untuk performa lebih cepat (CUDA) |

---

## 🚀 Langkah Setup di Perangkat Baru

1. **Install Python 3.11+** dari [python.org](https://www.python.org/downloads/)
   - ⚠️ Centang **"Add Python to PATH"** saat instalasi!

2. **Extract ZIP** ke folder mana saja (misal: `D:\CCTV AI DETECTION\`)

3. **Jalankan Installer:**
   - **Windows**: Double-click `setup.bat`
   - **Linux/macOS**: Buka terminal, ketik `bash setup.sh`
   - **Universal**: Buka terminal/cmd, ketik `python launch.py`

4. **Sistem otomatis mendeteksi status:**
   - Jika baru pertama kali: Panduan instalasi otomatis berjalan, mendownload library AI, mengisi token Telegram (opsional), dan membuat shortcut Desktop.
   - Jika sudah pernah diinstall: Langsung memilih `[1]` untuk menjalankan CCTV AI.
   - Selesai setup, aplikasi otomatis langsung berjalan dan membuka dashboard di browser (`http://localhost:8000`).

---

## ⚙️ Konfigurasi Tambahan (Opsional)

Edit file `config/config.yaml` untuk mengatur:
- **URL kamera RTSP** (`rtsp://...` atau URL stream lokal)
- **Zona terlarang** (koordinat ROI)
- **Sensitivitas deteksi**

Edit file `.env` untuk mengatur:
- **Telegram Bot Token & Chat ID**
- **Cloudflare Tunnel** (URL publik yang tetap)
- **PIN Dashboard** (keamanan akses remote)
