# Mobile Online Access & Native Tunnel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable seamless, secure mobile access to the CCTV AI Detection system without using `start.bat`, by embedding Cloudflare Tunnel management directly into the Python orchestrator, automatically dispatching 1-click access links to Telegram, and securing public mobile access with a PIN gate.

**Architecture:** A native asynchronous `TunnelManager` spawns and monitors `cloudflared.exe` inside the main event loop, capturing dynamic `trycloudflare.com` URLs (or supporting named tunnel tokens). The resolved public URL is immediately broadcasted to Telegram with a 1-click mobile button and stored in the application context. A lightweight FastAPI authentication middleware gates public access with a PIN/passcode to prevent unauthorized viewing of live CCTV streams.

**Tech Stack:** Python 3.11+, asyncio, FastAPI, Starlette, Cloudflare Tunnel (`cloudflared.exe`), python-telegram-bot, unittest.

**Spec:**
- [ADR-004: Native Tunnel Orchestration, Telegram Mobile Link Dispatch, and PIN Security Gate](file:///c:/Users/RizXenzs/Downloads/CCTV%20AI%20DETECTION/CCTV%20AI%20DETECTION/docs/adr/ADR-004-mobile-access-and-tunnel-orchestration.md)
- [ADR-005: Tunnel Watchdog Healthcheck & Mobile Viewport Optimization](file:///c:/Users/RizXenzs/Downloads/CCTV%20AI%20DETECTION/CCTV%20AI%20DETECTION/docs/adr/ADR-005-tunnel-watchdog-and-mobile-pwa-optimization.md)

## Global Constraints

- Never rely on `start.bat` or multi-window CMD batch scripts.
- Single command entry: `python src/main.py` handles the full application lifecycle.
- Backward compatibility: If no internet or `cloudflared.exe` is absent, the local server continues running on `http://localhost:8000` without crashing.
- Safe default: If `DASHBOARD_PIN` is not configured in `.env`, the system functions in open mode for local networks.

## Review Focus

1. **Zombie tunnel process:** Application is terminated (Ctrl+C or SIGTERM) while `cloudflared.exe` continues running in the background, locking port 8000. Reasonable behavior: `TunnelManager.stop()` sends SIGTERM/terminate and awaits clean child exit in `finally` block.
2. **Dynamic URL changes:** Cloudflare quick tunnel disconnects and reconnects with a newly assigned subdomain. Reasonable behavior: Watchdog detects the new URL and automatically dispatches an updated link to Telegram.
3. **Stream lag over mobile cellular connection:** Mobile 4G/5G experiences variable bandwidth. Reasonable behavior: MJPEG endpoint maintains frame-dropping so video latency never accumulates.
4. **Brute-force PIN attacks over public internet:** Automated scanners attempt to guess `DASHBOARD_PIN`. Reasonable behavior: Middleware enforces rate limiting (max 5 failed attempts per IP per 5 minutes).
5. **Missing executable:** `cloudflared.exe` is moved or missing. Reasonable behavior: System logs an actionable warning and keeps local web server operational without raising unhandled exceptions.

---

### Task 1: Native Async Tunnel Manager (`src/tunnel_manager.py`)

**Files:**
- Create: `src/tunnel_manager.py`
- Create: `tests/test_tunnel_manager.py`

**Interfaces:**
- Consumes: Path to `cloudflared.exe`, local target port (default 8000).
- Produces: `TunnelManager.start() -> Optional[str]`, `TunnelManager.stop()`, `TunnelManager.current_url: Optional[str]`.

- [x] **Step 1: Write the failing test**
...
- [x] **Step 2: Run test to verify it fails**
...
- [x] **Step 3: Implement `src/tunnel_manager.py`**
...
- [x] **Step 4: Run test to verify it passes**
...
- [x] **Step 5: Commit**

```bash
git add src/tunnel_manager.py tests/test_tunnel_manager.py
git commit -m "feat(tunnel): add native async Cloudflare tunnel manager"
```

---

### Task 2: Automatic Telegram Mobile URL Broadcast

**Files:**
- Modify: `src/telegram_notifier.py`
- Create: `tests/test_telegram_mobile_broadcast.py`

**Interfaces:**
- Consumes: `public_url: str`
- Produces: `TelegramNotifier.send_mobile_link(public_url: str) -> bool`.

- [x] **Step 1: Write the failing test**
...
- [x] **Step 2: Run test to verify it fails**
...
- [x] **Step 3: Implement `format_mobile_link_message` & `send_mobile_link` in `src/telegram_notifier.py`**
...
- [x] **Step 4: Run test to verify it passes**
...
- [x] **Step 5: Commit**

```bash
git add src/telegram_notifier.py tests/test_telegram_mobile_broadcast.py
git commit -m "feat(telegram): add mobile access link broadcast"
```

---

### Task 3: Lightweight PIN Security Gate (`src/api/auth.py`)

**Files:**
- Create: `src/api/auth.py`
- Modify: `src/api/server.py`
- Create: `tests/test_dashboard_pin_gate.py`

**Interfaces:**
- Consumes: `DASHBOARD_PIN` from `.env` or config.
- Produces: Starlette middleware validating session token cookie (`cctv_session`), `/api/auth/login` endpoint, and responsive PIN login modal.

- [x] **Step 1: Write the failing test**
...
- [x] **Step 2: Run test to verify it fails**
...
- [x] **Step 3: Implement `src/api/auth.py` and attach to FastAPI in `src/api/server.py`**
...
- [x] **Step 4: Run test to verify it passes**
...
- [x] **Step 5: Commit**

```bash
git add src/api/auth.py src/api/server.py tests/test_dashboard_pin_gate.py
git commit -m "feat(auth): add lightweight PIN security gate for remote mobile access"
```

---

### Task 4: Main Orchestrator Integration & Replacement of `start.bat` ✅

**Files:**
- Modified: `src/main.py` — TunnelManager integrated
- Deleted: `start.bat` — **DIHAPUS PERMANEN**
- Created: `run.py` — Python launcher pengganti start.bat (double-click friendly)
- Created: `tests/test_main_tunnel_integration.py`

**Interfaces:**
- Consumes: `TunnelManager`, `TelegramNotifier`, `CCTVApplication`
- Produces: Automatic tunnel startup in `src/main.py`, single-command execution `python src/main.py` atau `python run.py`.

- [x] **Step 1: Write the failing test** ✅
- [x] **Step 2: Run test to verify it fails** ✅
- [x] **Step 3: Integrate `TunnelManager` into `src/main.py`** ✅
- [x] **Step 4: Delete `start.bat`, create `run.py` launcher** ✅
- [x] **Step 5: Run full test suite — 15 tests PASS** ✅

```
Ran 15 tests in 0.016s
OK
```

**Cara menjalankan aplikasi:**
```bash
# Option 1 — langsung (recommended untuk CLI)
python src/main.py

# Option 2 — via launcher (double-click friendly, ada banner)
python run.py
```

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-11-13-mobile-online-access-and-native-tunnel.md`. Please review the plan. Which execution approach would you prefer?

- **Native** - I implement every task directly in this session with full TDD passes, then run the full test suite.
- **Subagent-driven** - A fresh subagent implements each task and a fresh reviewer checks it before the next one starts.

For this plan I recommend **Native**, because the tasks directly coordinate internal FastAPI and process interfaces in the existing repository. Does the plan capture what you want, and which approach should we use?
