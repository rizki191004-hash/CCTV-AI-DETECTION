# ADR-017 — Seamless Auto-Close Installer & Shortcut-Driven Activation

**Date:** 2026-11-20  
**Status:** Accepted & Implemented  
**Author:** AI Agent (ADR-017)

---

## Context

Pada iterasi sebelumnya, `setup.bat` masih bertindak ganda sebagai installer dan launcher server AI. Hal ini menimbulkan beberapa friksi bagi pengguna:
1. Pengguna harus memilih lagi opsi pasca-instalasi di jendela CMD yang sama.
2. Jendela CMD tetap terbuka dan server AI langsung menyala tanpa kehendak pengguna, padahal pengguna ingin menyalakannya secara mandiri saat dibutuhkan.
3. Terjadi kebingungan pada menu saat `setup.bat` dibuka kembali (tampilan terpotong oleh buffer scroll CMD).

---

## Decision

### 1. Pemisahan Tanggung Jawab: Installer vs Activator
- **`setup.bat` (Installer Murni)**: Bertugas 100% menyiapkan dependensi, memeriksa dashboard build, membuat **1 shortcut tunggal** `CCTV AI` di Desktop, lalu **menutup CMD otomatis** dalam 3 detik (`timeout /t 3 >nul && exit /b 0`).
- **Shortcut `CCTV AI` di Desktop (Aktivasi Utama)**: Menjadi saklar utama untuk menyalakan/mematikan sistem dan meluncurkan web browser dashboard `http://localhost:8000`.

### 2. Tampilan Ringkas Saat Dibuka Ulang
Jika `setup.bat` dibuka kembali setelah instalasi selesai (`.setup_done` ada), sistem langsung menampilkan pesan ringkas bahwa sistem sudah terinstall dan mengarahkan pengguna untuk mengeklik shortcut di Desktop, dengan default pilihan `[4] Keluar`.

---

## Consequences

- Pengalaman instalasi menjadi instan dan mulus (sekali klik, tunggu selesai, jendela menutup sendiri).
- Pengguna memegang kendali penuh kapan harus mengaktifkan atau mematikan CCTV AI melalui shortcut di Desktop.

---

## Tests

- `tests/test_setup_script.py` — **12/12 PASS**
- Full test suite — **76/76 PASS**
