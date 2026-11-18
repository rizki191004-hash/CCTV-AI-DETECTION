# Smart Toggle Launcher & Web Dashboard Shutdown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide a seamless, zero-terminal experience where double-clicking a single launcher icon (`cctv.pyw` / Desktop Shortcut) starts everything silently in the background, or stops all processes if already running, while also providing a "Shutdown CCTV" button directly in the web dashboard.

**Architecture:**
1. **Backend (`src/api/routes.py` & `src/main.py`)**: A `POST /api/system/shutdown` endpoint safely signals `app.shutdown_event` and terminates child processes (`cloudflared`). `src/main.py` writes PID to `data/cctv.pid` on initialization and clears it on shutdown.
2. **Controller Launcher (`cctv.pyw`)**: Windowless Python launcher using standard library (`ctypes`, `subprocess`, `urllib`). Checks if CCTV is running:
   - If OFF: Spawns `pythonw src/main.py` detached with zero CMD windows, browser opens automatically.
   - If ON: Native Windows dialog prompts: *"CCTV AI sedang aktif. Hentikan aplikasi sekarang? [Ya] / [Buka Web]"*. Clicking [Ya] executes full clean termination and notifies the user.
3. **Desktop Shortcut (`scripts/create_desktop_shortcut.ps1`)**: Creates a ready-to-click shortcut on `C:\Users\RizXenzs\Desktop\CCTV AI.lnk`.
4. **Frontend Dashboard (`dashboard/src/App.tsx`)**: Adds a "Matikan CCTV" (`Power` icon) button in the header with a confirmation modal, sending the shutdown command and showing an offline screen.

**Tech Stack:** Python 3.11+, FastAPI, Windows API (`ctypes.windll.user32.MessageBoxW`), React 19, Lucide React, Unittest.

**Spec:**
- Settled in Grilling Round 2:
  - Q1: Single smart toggle launcher (`cctv.pyw`) with state detection & native dialog.
  - Q2: Web dashboard shutdown button with confirmation.
  - Q3: Zero residual processes guarantee (`cloudflared`, `pythonw`, port 8000 release).

## Global Constraints

- Never show a black CMD/console window on launch.
- No new external pip packages required (stdlib `ctypes`, `urllib`, `subprocess`).
- All 28 existing tests must continue to PASS.
- Clean process shutdown: verify port 8000 and background tasks stop completely.

## Review Focus

1. **Zombie processes after shutdown**: `cloudflared.exe` continues running after Python exits. Reasonable behavior: Both `src/main.py` shutdown hook and `cctv.pyw` stop routine forcefully terminate any remaining `cloudflared` instances.
2. **PID file stale after ungraceful crash**: Computer power loss leaves `data/cctv.pid`. Reasonable behavior: `is_running()` validates via HTTP ping to `http://127.0.0.1:8000/api/status` rather than blindly trusting the PID file alone.
3. **Web browser shutdown feedback**: User clicks Shutdown in browser. Reasonable behavior: UI immediately displays a friendly "Sistem Dimatikan" overlay so user knows the server stopped.
4. **Desktop shortcut path resolution**: Shortcut runs from any working directory. Reasonable behavior: `cctv.pyw` resolves `PROJECT_ROOT` based on `__file__` and changes CWD before executing.
5. **Double launch prevention**: User double-clicks launcher multiple times in quick succession. Reasonable behavior: Launcher detects process or socket within 1.5s and avoids duplicate instances.

---

### Task 1: Backend System Shutdown API & PID Management

**Files:**
- Modify: `src/api/routes.py`
- Modify: `src/main.py`
- Create: `tests/test_system_shutdown.py`

**Interfaces:**
- Produces: `POST /api/system/shutdown` returns `{"status": "ok", "message": "..."}` and triggers `app.shutdown_event.set()`
- Produces: `data/cctv.pid` written on `app.initialize()`, deleted on `app.shutdown()`

- [x] **Step 1: Write test for `/api/system/shutdown`**
- [x] **Step 2: Run test to verify it fails**
- [x] **Step 3: Implement shutdown route and PID file tracking**
- [x] **Step 4: Run test to verify it passes**

---

### Task 2: Smart Toggle Controller Launcher (`cctv.pyw`)

**Files:**
- Create: `cctv.pyw`
- Create: `tests/test_cctv_launcher.py`
- Create: `scripts/create_desktop_shortcut.ps1`

**Interfaces:**
- Produces: `cctv.pyw` executable via `pythonw` with `is_cctv_running()`, `start_cctv()`, `stop_cctv()`, and `main()`

- [x] **Step 1: Write unit tests for launcher detection and commands**
- [x] **Step 2: Run test to verify it fails**
- [x] **Step 3: Implement `cctv.pyw` and shortcut generator script**
- [x] **Step 4: Run test to verify it passes**
- [x] **Step 5: Execute shortcut generator to place `CCTV AI.lnk` on Desktop**

---

### Task 3: Web Dashboard Shutdown Button (`dashboard/src/App.tsx`)

**Files:**
- Modify: `dashboard/src/App.tsx`
- Build: `dashboard/dist` via `npm run build`

**Interfaces:**
- UI components: "Matikan CCTV" button in Header with `Power` icon, confirmation modal, and shutdown state overlay.

- [x] **Step 1: Add Shutdown button & confirmation modal to `App.tsx`**
- [x] **Step 2: Rebuild frontend (`npm run build`)**
- [x] **Step 3: Verify build in `dashboard/dist`**

---

### Task 4: Complete Verification & Test Suite

- [x] **Step 1: Run full test suite (`python -m unittest discover -s tests`)** — 32/32 tests PASS
- [x] **Step 2: Verify Desktop shortcut creation** — `C:\Users\RizXenzs\Desktop\CCTV AI.lnk` verified

