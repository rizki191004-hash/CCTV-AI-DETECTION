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
├── setup.bat                   ← ⭐ INSTALLER UTAMA (double-click pertama kali)
├── install_shortcut.bat        ← Shortcut Desktop
├── run.py                      ← Launcher utama
├── cctv.pyw                    ← Launcher tanpa console
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
| `tests/` | Opsional, hanya untuk developer |
| `.git/` | Riwayat git tidak perlu untuk pengguna akhir |
| `data/cctv_events.db` | Database akan dibuat ulang otomatis |
| `docs/` | Opsional |

---

## 🖥️ Prasyarat di Perangkat Penerima

| Kebutuhan | Versi Minimum | Cara Install |
|-----------|--------------|-------------|
| **Windows** | 10 / 11 | — |
| **Python** | 3.11+ | [python.org/downloads](https://www.python.org/downloads/) ⚠️ centang "Add to PATH" |
| **Internet** | — | Untuk download package saat setup |
| GPU NVIDIA | Opsional | Untuk performa lebih cepat (CUDA) |

---

## 🚀 Langkah Setup di Perangkat Baru

1. **Install Python 3.11+** dari [python.org](https://www.python.org/downloads/)
   - ⚠️ Centang **"Add Python to PATH"** saat instalasi!

2. **Extract ZIP** ke folder mana saja (misal: `D:\CCTV AI DETECTION\`)

3. **Double-click `setup.bat`**
   - Otomatis install semua dependensi Python
   - Tanya Telegram Bot Token & Chat ID
   - Tawarkan buat shortcut Desktop

4. **Selesai!** Jalankan via shortcut Desktop atau double-click `run.py`

---

## ⚙️ Konfigurasi Tambahan (Opsional)

Edit file `config/config.yaml` untuk mengatur:
- **URL kamera RTSP** (`rtsp://...`)
- **Zona terlarang** (koordinat ROI)
- **Sensitivitas deteksi**

Edit file `.env` untuk mengatur:
- **Cloudflare Tunnel** (URL publik yang tetap)
- **PIN Dashboard** (keamanan akses remote)

---

## ❓ Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `python tidak dikenali` | Tambah Python ke PATH atau install ulang dengan centang "Add to PATH" |
| Error install `torchreid` | Jalankan `pip install torchreid --no-deps` lalu `pip install -r requirements.txt` |
| Dashboard tidak terbuka | Pastikan port 8000 tidak dipakai program lain |
| Telegram tidak kirim notif | Cek `.env` — pastikan Token dan Chat ID benar |
| Kamera tidak terdeteksi | Cek URL RTSP di `config/config.yaml` |

