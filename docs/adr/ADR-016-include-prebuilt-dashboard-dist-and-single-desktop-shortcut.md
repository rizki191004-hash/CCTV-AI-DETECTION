# ADR-016 — Include Prebuilt Dashboard Dist in Repository & Single Desktop Shortcut

**Date:** 2026-11-20  
**Status:** Accepted & Implemented  
**Author:** AI Agent (ADR-016)

---

## Context

1. **Dashboard Blank / JSON Error**:
   Saat CCTV AI dijalankan di browser (`http://localhost:8000`), muncul respon:
   `{"status":"ok", "message":"Dashboard not built yet. Run 'cd dashboard && npm run build' first."}`.
   Penyebabnya adalah folder `dashboard/dist/` dan `dist` dikecualikan oleh `.gitignore` dan `dashboard/.gitignore`. Akibatnya, file static frontend web yang sudah di-build tidak pernah terkirim ke GitHub saat push, sehingga ketika diekstrak di perangkat penerima, foldernya kosong.
2. **Shortcut Terpisah / Gandanya Icon di Layar**:
   Script `create_desktop_shortcut.ps1` sebelumnya menulis ke Public Desktop (`C:\Users\Public\Desktop`) dan User Desktop sekaligus, menyebabkan duplikasi icon atau pemisahan icon di layar monitor.
3. **Konfirmasi Pasca-Instalasi**:
   Pengguna memerlukan pilihan konfirmasi apakah ingin langsung menjalankan sistem atau keluar setelah proses instalasi selesai.

---

## Decision

### 1. Sertakan `dashboard/dist/` ke Git Tracking
- Hapus `dist` dari `dashboard/.gitignore`.
- Tambahkan exception `!dashboard/dist/` dan `!dashboard/dist/**` di root `.gitignore`.
- Lakukan fresh build React dashboard via `npm run build` dan track seluruh aset dist (HTML, JS chunk, CSS) ke dalam Git repo.

### 2. Tepat 1 Shortcut Tunggal di Desktop
- `scripts/create_desktop_shortcut.ps1` dibatasi hanya menulis ke **satu Desktop aktif pengguna** (`[Environment]::GetFolderPath('Desktop')`).
- File duplikat lama di `Public\Desktop` otomatis dibersihkan agar tidak muncul ganda.

### 3. Pilihan Pasca-Instalasi (Jalankan vs Keluar)
Di akhir instalasi otomatis `setup.bat` dan `launch.py`:
- `[1] Langsung Jalankan CCTV AI Sekarang (Buka Dashboard)`
- `[2] Selesai & Keluar (Jalankan nanti via Shortcut Desktop)`

---

## Consequences

- Dashboard web dijamin langsung tampil utuh (tidak blank/JSON error) di perangkat baru tanpa perlu install Node.js/npm.
- Hanya ada tepat 1 icon shortcut `CCTV AI` di desktop.
- Pengguna memiliki kontrol penuh untuk langsung menjalankan atau keluar setelah setup selesai.

---

## Tests

- `tests/test_setup_script.py` — **12/12 PASS**
- Full test suite — **76/76 PASS**
