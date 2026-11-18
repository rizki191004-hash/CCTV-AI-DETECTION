# Dashboard Auto-Open & Server Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dashboard dapat dibuka otomatis di browser saat `python run.py` atau `python src/main.py` dijalankan — baik untuk akses lokal maupun mobile (tunnel).

**Architecture:** Uvicorn dipasang dan diverifikasi. `main.py` memanggil `webbrowser.open("http://localhost:8000")` setelah server bind. Tunnel URL dibuka sebagai tab kedua saat `_on_tunnel_url_ready()` dipanggil (satu kali saja).

**Tech Stack:** Python stdlib `webbrowser`, uvicorn 0.54.0, FastAPI, asyncio.

**Root Causes Fixed:**
- Root cause #1: `uvicorn` tidak terinstall → **FIXED** (0.54.0 installed)  
- Root cause #2: Browser tidak dibuka otomatis → diperbaiki di Task 1

## Global Constraints

- Entry point tunggal: `python src/main.py` atau `python run.py`
- Tidak menggunakan `start.bat`
- Browser dibuka SETELAH server bind (tidak ada race condition)
- Jika browser gagal dibuka (headless server), log warning dan lanjut
- Backward compat dengan `config/config.yaml`, `config/rules.yaml`, SQLite

## Review Focus

1. Race condition buka browser sebelum bind: tunggu `delay=2.0` detik.
2. Headless server: wrap `webbrowser.open()` dalam try/except.
3. Tunnel URL berubah (reconnect): hanya buka tab sekali (`_tunnel_browser_opened` flag).
4. Port 8000 sudah terpakai: log error yang jelas, pipeline tetap jalan.
5. `dashboard/dist/` tidak ada: server.py sudah handle dengan JSON fallback.

---

### Task 1: Auto-Open Browser (`src/main.py`) ✅

- [x] Write test, implement, verify PASS
- [x] `_open_browser_when_ready(url, delay)` helper ditambahkan
- [x] Browser lokal dibuka 2 detik setelah server bind
- [x] Tunnel URL dibuka sekali saat ready (flag `_tunnel_browser_opened`)

### Task 2: `run.py` Print URL ✅

- [x] Banner berisi `http://localhost:8000` dan instruksi akses mobile

### Task 3: Full Test Suite ✅

- [x] 16+ tests PASS

