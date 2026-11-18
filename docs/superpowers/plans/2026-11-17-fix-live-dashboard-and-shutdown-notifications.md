# Fix Live Dashboard Error & Suppress Telegram Notifications on Shutdown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the dashboard startup failure occurring under `pythonw.exe` windowless execution, eliminate log flooding and high CPU from missing Re-ID dependencies, and ensure zero Telegram notifications are dispatched when the user stops/shuts down the CCTV system.

**Architecture:**
1. **Windowless Server Compatibility (`src/main.py`)**: When executed with `pythonw.exe`, `sys.stdout` and `sys.stderr` are `None`. We redirect them to `os.devnull` and configure `uvicorn.Config` with `log_config=None` so `sys.stdout.isatty()` is never invoked, allowing FastAPI to successfully bind to port 8000 and serve the live dashboard.
2. **Re-ID Failure Caching (`src/reid_manager.py`)**: When `torchreid` is not installed, record `self._load_failed = True` so subsequent frames do not re-attempt import or flood `data/cctv_ai.log` with thousands of warnings, dropping CPU usage back to normal levels.
3. **Shutdown Notification Suppression (`src/telegram_notifier.py`, `src/tunnel_manager.py`, `src/main.py`, `cctv.py`)**: Introduce `TelegramNotifier.stop()`, cancel tunnel watchdog restarts upon shutdown, verify `shutdown_event.is_set()` before dispatching any tunnel URL, and use `taskkill /F /T /PID` plus process name matching in `cctv.py` to cleanly terminate Python and Cloudflare before watchdog restarts can fire.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, Windows `taskkill` API, Telegram Bot API, Pytest/Unittest.

**Spec:** User reported:
1. Live dashboard cannot be accessed when launched via double-click / background execution (`AttributeError: 'NoneType' object has no attribute 'isatty'` in uvicorn formatter).
2. Clicking "Yes" / [Ya] to terminate all processes triggers a Telegram mobile link notification from the tunnel watchdog.

## Global Constraints

- No visible terminal/CMD windows when launched via `cctv.pyw`.
- Zero Telegram messages may be sent during or after the user initiates shutdown.
- All 32 existing tests must continue to PASS.
- No new external pip packages required.

## Review Focus

1. **`pythonw.exe` stdout is None**: `sys.stdout.isatty()` raises `AttributeError` when uvicorn initializes formatters. Expected: server boots cleanly without errors.
2. **Watchdog race condition on kill**: Cloudflare process killed before Python process exits, triggering tunnel restart and Telegram alert. Expected: tunnel watchdog canceled and TelegramNotifier stopped before process termination.
3. **Repeated Re-ID import attempts**: Missing `torchreid` causes disk writes on every single frame. Expected: single log warning, cached failure flag, normal CPU usage.
4. **Residual Python background processes**: If port 8000 is occupied or stale Python process remains, shutdown must kill tree. Expected: `taskkill /T /F` kills parent and children.
5. **Dashboard reconnect resilience**: Frontend live view reconnects if server temporarily restarts. Expected: standard error handling without permanent hidden display.

---

### Task 1: Fix Uvicorn Windowless Server Startup (`src/main.py`)

**Files:**
- Modify: `src/main.py`
- Test: `tests/test_live_dashboard_server_startup.py`

**Interfaces:**
- Produces: Safe `uvicorn.Config(log_config=None, access_log=False)` and `sys.stdout` fallback to `os.devnull`.

- [x] **Step 1: Write test for windowless uvicorn startup**

```python
# tests/test_live_dashboard_server_startup.py
import os
import sys
import unittest
from unittest.mock import patch
import uvicorn
from fastapi import FastAPI

class TestLiveDashboardServerStartup(unittest.TestCase):
    def test_uvicorn_config_with_none_stdout(self):
        """When sys.stdout is None (as in pythonw.exe), uvicorn config must initialize without AttributeError."""
        with patch.object(sys, "stdout", None), patch.object(sys, "stderr", None):
            app = FastAPI()
            # Configuring with log_config=None must succeed without error
            config = uvicorn.Config(
                app=app,
                host="0.0.0.0",
                port=8000,
                log_level="error",
                log_config=None,
                access_log=False,
            )
            server = uvicorn.Server(config)
            self.assertIsNotNone(server)
```

- [x] **Step 2: Run test to verify it passes**

Run: `python -m unittest tests/test_live_dashboard_server_startup.py -v`
Expected: PASS

- [x] **Step 3: Update `src/main.py` to safeguard `sys.stdout`/`sys.stderr` and configure uvicorn with `log_config=None`**

In `src/main.py`:
1. At module start:
```python
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
```
2. In `CCTVApplication.run()` around line 823:
```python
config = uvicorn.Config(
    app=api_app, 
    host="0.0.0.0", 
    port=8000, 
    log_level="error",
    log_config=None,
    access_log=False,
)
```

- [x] **Step 4: Run test suite to verify no regressions**

Run: `python -m unittest discover -s tests -v`
Expected: 33 tests PASS

---

### Task 2: Re-ID Manager Failure Caching to Prevent Log Flooding and High CPU

**Files:**
- Modify: `src/reid_manager.py`
- Test: `tests/test_reid_manager_load_failure_caching.py`

**Interfaces:**
- Produces: `self._load_failed` boolean flag preventing repeated import attempts and repeated logger warnings.

- [x] **Step 1: Write test for ReIDManager failure caching**

```python
# tests/test_reid_manager_load_failure_caching.py
import unittest
from unittest.mock import patch
from src.reid_manager import ReIDManager

class TestReIDManagerLoadFailureCaching(unittest.TestCase):
    def test_load_failure_cached_after_first_attempt(self):
        manager = ReIDManager()
        # When torchreid is not present, first call returns False and sets _load_failed
        with patch.dict("sys.modules", {"torchreid": None, "torchreid.utils": None}):
            res1 = manager._load_model()
            self.assertFalse(res1)
            self.assertTrue(getattr(manager, "_load_failed", False))
            
            # Second call immediately returns False without entering load logic
            res2 = manager._load_model()
            self.assertFalse(res2)
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_reid_manager_load_failure_caching.py -v`
Expected: FAIL (missing `_load_failed` attribute)

- [x] **Step 3: Implement `_load_failed` flag in `src/reid_manager.py`**

In `src/reid_manager.py`:
1. Initialize `self._load_failed: bool = False` in `__init__`.
2. Check `if self._load_failed: return False` at the start of `_load_model()`.
3. In `except (ImportError, Exception)`: set `self._load_failed = True`.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_reid_manager_load_failure_caching.py -v`
Expected: PASS

---

### Task 3: Suppress Telegram Notifications on Shutdown & Clean Up Process Kill

**Files:**
- Modify: `src/telegram_notifier.py`
- Modify: `src/tunnel_manager.py`
- Modify: `src/main.py`
- Modify: `cctv.py`
- Test: `tests/test_shutdown_suppresses_telegram.py`

**Interfaces:**
- Produces: `TelegramNotifier.stop()` method setting `self._enabled = False`.
- Produces: `TunnelManager` respects `_stop_event` before watchdog restart.
- Produces: `cctv.py.stop_cctv()` uses `taskkill /F /T /PID` and process tree termination to prevent watchdog restarts.

- [x] **Step 1: Write tests for shutdown suppression**

```python
# tests/test_shutdown_suppresses_telegram.py
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock
from src.telegram_notifier import TelegramNotifier
from src.tunnel_manager import TunnelManager

class TestShutdownSuppressesTelegram(unittest.TestCase):
    def test_telegram_notifier_stop_disables_sending(self):
        notifier = TelegramNotifier(bot_token="fake_token", chat_id="fake_chat")
        notifier._enabled = True
        notifier._bot = MagicMock()
        
        notifier.stop()
        self.assertFalse(notifier._enabled)
        
        # Calling send_mobile_link returns False immediately
        res = asyncio.run(notifier.send_mobile_link("https://test.trycloudflare.com"))
        self.assertFalse(res)

    def test_tunnel_manager_stop_cancels_watchdog(self):
        tm = TunnelManager(port=8000)
        tm._watchdog_task = MagicMock()
        tm._process = MagicMock()
        tm._process.wait = AsyncMock()
        
        asyncio.run(tm.stop())
        self.assertTrue(tm._stop_event.is_set())
        tm._watchdog_task.cancel.assert_called_once()
```

- [x] **Step 2: Run test to verify it fails or passes**

Run: `python -m unittest tests/test_shutdown_suppresses_telegram.py -v`

- [x] **Step 3: Implement `stop()` in `src/telegram_notifier.py` and integrate in `src/main.py` and `src/tunnel_manager.py`**

1. In `src/telegram_notifier.py`:
```python
def stop(self) -> None:
    """Disable notifier to suppress any outgoing alerts or messages during/after shutdown."""
    self._enabled = False
```
2. In `src/main.py`:
In `shutdown()`:
```python
if self.telegram:
    self.telegram.stop()
```
In `_on_tunnel_url_ready()`:
```python
if self.shutdown_event.is_set():
    return
```
3. In `src/tunnel_manager.py`:
In `_watchdog_loop()`: check `self._stop_event.is_set()` before and after sleep, and abort if set.
In `stop()`: await `self._watchdog_task` cancellation cleanly.

4. In `cctv.py`:
Update `stop_cctv()`:
- Call `POST /api/system/shutdown`.
- If PID file exists, execute `taskkill /F /T /PID <pid>` (kills entire process tree).
- Run PowerShell command to stop any lingering Python processes running `src/main.py` or `run.py`.
- Run PowerShell command to kill `cloudflared`.
- Remove PID file.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_shutdown_suppresses_telegram.py -v`
Expected: PASS

---

### Task 4: Full System Verification

- [x] **Step 1: Run full unit test suite** — 36/36 tests PASS
- [x] **Step 2: Verify `pythonw cctv.pyw` starts and port 8000 responds with HTTP 200**
- [x] **Step 3: Verify stopping CCTV triggers zero Telegram notifications and leaves zero residual processes**

