# ADR-015 — Automatic Desktop Shortcut & Multi-Desktop (OneDrive) Support

**Date:** 2026-11-20  
**Status:** Accepted & Implemented  
**Author:** AI Agent (ADR-015)

---

## Context

Pada pengujian pengguna, saat memilih mode instalasi otomatis, shortcut Desktop `CCTV AI.lnk` tidak muncul di monitor. Setelah diinvestigasi:
1. **Prompt Berulang**: `setup.bat` masih meminta konfirmasi pengguna `(y/n)` di Langkah 5, sehingga rentan terlewat.
2. **Hardcoded User Path**: `scripts/create_desktop_shortcut.ps1` menargetkan path `C:\Users\RizXenzs\...`, menyebabkan kegagalan di komputer atau profil pengguna lain.
3. **OneDrive Desktop Folder Redirection**: Pada Windows 10/11, Desktop sering kali dipindahkan ke folder sinkronisasi OneDrive (`C:\Users\<User>\OneDrive\Desktop`). Shortcut yang hanya dibuat di folder desktop lokal tidak terlihat di layar pengguna.

---

## Decision

### 1. 100% Otomatisasi Tanpa Prompt `(y/n)`
Pada mode instalasi `[1] Install Lengkap / Otomatis`, pembuatan shortcut langsung dieksekusi secara otomatis tanpa meminta konfirmasi lagi.

### 2. Multi-Desktop Target (Lokal, OneDrive, & Public)
`create_desktop_shortcut.ps1` kini mencari dan membuat shortcut di seluruh lokasi Desktop yang valid:
- Desktop Lingkungan Pengguna (`[Environment]::GetFolderPath('Desktop')`)
- Desktop Profil OneDrive (`~\OneDrive\Desktop`)
- Desktop Registry Shell (`HKCU:\...\User Shell Folders`)
- Desktop Bersama / Publik (`CommonDesktopDirectory`)

### 3. Penemuan Pythonw Dinamis
Path `pythonw.exe` tidak lagi di-hardcode, melainkan dideteksi secara dinamis melalui Python interpreter aktif yang menjalankan sistem.

### 4. Menu Perbaikan Cepat (Quick Recreate Shortcut)
Jika sistem sudah terinstall sebelumnya, menu utama menyediakan opsi cepat:
`[2] Buat / Perbaiki Shortcut CCTV AI di Desktop`
sehingga pengguna dapat membuat ulang shortcut kapan saja hanya dengan 1 klik.

---

## Consequences

- Shortcut `CCTV AI` dijamin 100% muncul di layar monitor Windows pengguna.
- Mode instalasi otomatis benar-benar berjalan tanpa jeda pertanyaan yang tidak perlu.
- Pengguna dapat memulihkan shortcut yang terhapus secara instan via `setup.bat`.

---

## Tests

- `tests/test_setup_script.py` — **12/12 PASS**
- Full test suite — **76/76 PASS**
