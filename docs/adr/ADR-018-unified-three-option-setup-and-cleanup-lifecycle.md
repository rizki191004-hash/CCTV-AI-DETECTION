# ADR-018 — Unified Three-Option Setup and Cleanup Lifecycle

**Date:** 2026-11-20  
**Status:** Accepted & Implemented  
**Author:** AI Agent (ADR-018)

---

## Context

Untuk menyederhanakan alur pengguna dan menghindari kebingungan menu yang bercabang-cabang, pengguna menginginkan antarmuka `setup.bat` yang ringkas dan konsisten dengan 3 opsi utama:
1. **[1] Install Semua Otomatis Sistem & Shortcut Desktop**
2. **[2] Hapus Semua Komponen Sistem & Shortcut (Uninstall)**
3. **[3] Keluar (Exit)**

---

## Decision

### 1. Struktur 3 Pilihan Menu Utama
`setup.bat` dan `launch.py` kini selalu menampilkan 3 opsi yang sama di layar awal:
- `[1]` Menjalankan instalasi dependensi Python, verifikasi build dashboard web, konfigurasi `.env`, dan pembuatan 1 shortcut `CCTV AI` di Desktop. Selesai instalasi, CMD menutup otomatis dalam 3 detik.
- `[2]` Mematikan proses background CCTV AI dan Cloudflared, menghapus shortcut Desktop `CCTV AI.lnk`, menghapus file sentinel `.setup_done`, menghapus database event sementara, dan menutup CMD otomatis dalam 3 detik.
- `[3]` Menutup jendela installer seketika (`exit /b 0`).

### 2. Peluncuran Sistem Mandiri
Aktivasi CCTV AI sepenuhnya dialihkan ke shortcut `CCTV AI` di Desktop, sehingga peran `setup.bat` murni sebagai pengelola siklus hidup (install, uninstall, exit).

---

## Consequences

- Tampilan menu sangat bersih, mudah dipahami oleh pengguna pemula.
- Tersedia fitur Uninstall/Cleanup bawaan yang bersih untuk mereset sistem tanpa perlu menghapus folder secara manual.

---

## Tests

- `tests/test_setup_script.py` — **12/12 PASS**
- Full test suite — **76/76 PASS**
