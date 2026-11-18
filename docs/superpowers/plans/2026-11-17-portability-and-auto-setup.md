# Plan: Portabilitas & Auto-Setup untuk Perangkat Lain
**Tanggal:** 2026-11-17  
**Status:** 🔄 In Progress

## Tujuan
Memastikan aplikasi CCTV AI Detection dapat dibuka di perangkat Windows lain tanpa error,
dengan proses setup semudah mungkin (double-click `setup.bat`).

## Keputusan (dari Grill Session)
| Keputusan | Pilihan |
|-----------|---------|
| Target OS | Windows (semua versi modern) |
| Metode distribusi | Zip manual oleh user |
| Level pengguna | Semi-teknis (double-click friendly) |
| Python | Harus pre-install manual (3.11+) |
| Konfigurasi .env | setup.bat tanya interaktif |

## Deliverables
- [ ] `setup.bat` — installer otomatis sekali double-click
- [ ] `docs/adr/ADR-010-portability-and-auto-setup.md`
- [ ] Update `README.md` — panduan setup perangkat baru
- [ ] `tests/test_setup_script.py` — verifikasi file setup ada & valid
- [ ] `DISTRIBUSI.md` — checklist apa saja yang perlu masuk zip

## Apa yang di-install oleh setup.bat
1. Cek Python 3.11+ terinstall
2. Upgrade pip
3. `pip install -r requirements.txt` (semua 13 package)
4. Jika `.env` belum ada → tanya TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID
5. Tawarkan buat Desktop Shortcut
6. Tampilkan instruksi cara menjalankan

## Checklist File untuk Zip
Wajib ikut:
- Semua file source (`src/`, `config/`, `dashboard/dist/`, `data/`)
- `yolov8n.pt`, `yolov8n-pose.pt` (model AI, ~13 MB total)
- `requirements.txt`
- `setup.bat` ← BARU
- `install_shortcut.bat`
- `run.py`, `cctv.pyw`
- `.env.example`
- `README.md`, `DISTRIBUSI.md` ← BARU

Tidak perlu ikut:
- `node_modules/`, `dashboard/node_modules/`
- `venv/`, `.venv/`
- `__pycache__/`
- `.env` (rahasia, isi sendiri via setup.bat)
- `tests/` (opsional)

## Status
- [x] Test (Red) — 7 fail
- [x] Implementasi (Green) — 11/11 pass
- [x] Docs — ADR-010, DISTRIBUSI.md, README updated
- [x] Full suite — 67/67 PASS ✅

