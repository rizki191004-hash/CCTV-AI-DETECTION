# ADR-006: Complete Process Termination & Guaranteed Web Shutdown

## Status
Accepted

## Context
When a user triggered shutdown via `POST /api/system/shutdown` (from the Web Dashboard's "Matikan CCTV" button) or attempted to stop the system:
1. `app.shutdown_event.set()` was triggered.
2. In `src/main.py`, `await asyncio.gather(*tasks)` was blocked waiting on:
   - `server.serve()` (Uvicorn HTTP server): did not exit because `server.should_exit` was never set.
   - `_maintenance_loop` & `_stats_loop`: sleeping inside `asyncio.sleep(3600)` without task cancellation.
   - `tunnel_manager`: child `cloudflared.exe` process trees were still alive.
3. Because `asyncio.gather` hung indefinitely, `finally: await self.shutdown()` was never reached. The Python process (`pythonw.exe`) kept listening on port 8000, `data/cctv.pid` was not deleted, and `cloudflared.exe` remained running in the background.
4. When forcibly terminating, child processes of `cloudflared.exe` were not reaped unless process tree termination (`taskkill /F /T`) was applied.

## Decision
1. **Shutdown Watcher in `src/main.py`**:
   - Spawn a dedicated `_shutdown_watcher` coroutine awaiting `self.shutdown_event.wait()`.
   - Upon trigger:
     - Explicitly set `server.should_exit = True` so Uvicorn stops gracefully.
     - Cancel all background tasks (`pipeline_tasks`, maintenance, stats).
     - Run `await self.shutdown()` to stop grabbers, close database, stop tunnel manager, and remove PID file.
     - Execute `os._exit(0)` to guarantee immediate termination of the process and release of port 8000.
2. **Process Tree Termination in `cctv.py`**:
   - In `stop_cctv()`, call `taskkill /F /T /PID <pid>` to kill the entire process tree including child subprocesses (`cloudflared`).
   - Query and kill any remaining processes running `src/main.py` or `cloudflared.exe`.
3. **Web Dashboard Build & Resilient Reconnection**:
   - Update `dashboard/src/App.tsx` with dynamic backend connection indicator and auto-reconnecting stream player.
   - Compile fresh production bundle to `dashboard/dist`.

## Consequences
- **Positive**: Port 8000 is 100% guaranteed to be released when shutdown is triggered.
- **Positive**: Zero orphan background processes (`pythonw`, `cloudflared`).
- **Positive**: The web dashboard offline overlay accurately reflects reality.

