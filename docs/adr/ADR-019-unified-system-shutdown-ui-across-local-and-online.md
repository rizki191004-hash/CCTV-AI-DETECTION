# ADR-019 — Unified System Shutdown UI Across Local & Online Dashboards

**Date:** 2026-11-20  
**Status:** Accepted & Implemented  
**Author:** AI Agent (ADR-019)

---

## Context

Sebelumnya, tombol untuk mematikan sistem CCTV AI hanya berupa tombol kecil di header yang tersembunyi pada tampilan layar tertentu dan tidak seragam antara dashboard lokal (`localhost:8000`) dan online (mobile/tunnel). Pengguna menginginkan kontrol daya **"Matikan Seluruh Sistem"** yang seragam, jelas, dan dapat diakses dengan mudah di seluruh tampilan menu.

---

## Decision

### 1. Penempatan Menu Seragam di 3 Lokasi
1. **Sidebar Navigation Footer**: Menambahkan tombol berdesain mencolok `Matikan Seluruh Sistem` di bagian bawah sidebar navigasi utama.
2. **Top Header Bar**: Tombol merah di baris atas samping indikator status backend dengan teks tegas `Matikan Seluruh Sistem`.
3. **Settings Page (Kontrol Daya Sistem)**: Kartu zona bahaya di tab Pengaturan dengan penjelasan detail dan tombol aksi langsung.

### 2. Dialog Konfirmasi Keamanan
Setiap pemicu shutdown menampilkan modal konfirmasi:
- *"Matikan Seluruh Sistem CCTV AI?"*
- Mencegah penekanan tombol yang tidak disengaja.
- Opsi `[Batal]` dan `[Ya, Matikan Sekarang]`.

### 3. Eksekusi Shutdown Bersih (`POST /api/system/shutdown`)
Saat dikonfirmasi:
- Menghentikan Uvicorn server, seluruh pipeline AI, dan child process Cloudflare Tunnel.
- Melepaskan port 8000 dan menghapus file PID.
- Menampilkan layar penutup *"Seluruh Sistem CCTV AI Telah Dimatikan — Buka shortcut CCTV AI di Desktop untuk menyalakan kembali"*.

---

## Consequences

- Kontrol shutdown mudah dijangkau dari mana saja, baik di monitor PC desktop maupun layar handphone/tablet online.
- Label dan alur konfirmasi sepenuhnya konsisten.

---

## Tests

- React Vite Build — **100% SUCCESS**
- Python Test Suite — **76/76 PASS**
