# ADR-014 — Interactive Setup Status Notifications & Anti-Close CMD Window

**Date:** 2026-11-20  
**Status:** Accepted & Implemented  
**Author:** AI Agent (ADR-014)

---

## Context

Pada versi sebelumnya, saat pengguna menjalankan `setup.bat` melalui double-click dari File Explorer:
1. Terjadi kesalahan parsing batch (`& was unexpected at this time`) saat memeriksa versi Python dengan konstruksi `for /f ... ('python --version 2^>^&1')`. Hal ini menyebabkan CMD langsung menutup tiba-tiba (*crash on exit*) tanpa jejak error.
2. Penggunaan perintah `cls` (clear screen) yang terlalu agresif di tiap tahap instalasi menghapus progres download pip, sehingga pengguna tidak mengetahui proses apa yang sedang berjalan ("proses tidak diketahui").
3. Pengguna tidak mendapatkan status yang jelas apakah perangkat ini **Sudah Terinstall** atau **Belum Terinstall**.

---

## Decision

### 1. Banner Status Deteksi Awal yang Jelas
Saat `setup.bat` atau `launch.py` dijalankan, sistem segera memeriksa file sentinel `.setup_done`:
- **Jika SUDAH terinstall**: Menampilkan notifikasi `[STATUS: SISTEM SUDAH TERINSTALL SEBELUMNYA]` dan menawarkan menu:
  - `[1] Langsung Jalankan CCTV AI (Rekomendasi)`
  - `[2] Install Ulang / Perbarui Dependensi (Setup Ulang)`
  - `[3] Keluar`
- **Jika BELUM terinstall**: Menampilkan notifikasi `[STATUS: SISTEM BELUM TERINSTALL DI PERANGKAT INI]` dan memandu proses instalasi otomatis.

### 2. Transparansi Progres (Hapus `cls` di tengah proses pip)
Proses `python -m pip install -r requirements.txt` kini ditampilkan secara langsung ke terminal tanpa dibersihkan oleh `cls`. Pengguna dapat melihat nama paket, persentase download, dan konfirmasi `[OK]` di akhir setiap langkah.

### 3. Anti-Close Trap (Jendela CMD Dijamin Tidak Menutup Tiba-Tiba)
Seluruh titik keluar (exit), baik karena kesalahan instalasi (`:GAGAL`), pembatalan pengguna (`:KELUAR`), maupun setelah program CCTV AI dihentikan, dilengkapi dengan perintah `pause >nul` dan pesan penjelas:
`Tekan tombol apa saja untuk menutup jendela ini...`
Dengan demikian, CMD tidak akan pernah tertutup secara instan di Windows.

---

## Consequences

- Pengguna mendapatkan kejelasan penuh setiap kali menekan keyboard atau memilih menu.
- Terminal log tetap tersaji transparan saat proses download dependensi AI yang berat.
- Kompatibilitas cross-platform terjaga dengan sinkronisasi antara `setup.bat` (Windows) dan `launch.py` (Universal).

---

## Tests

- `tests/test_setup_script.py` — **12/12 PASS**
- Full test suite — **76/76 PASS**
