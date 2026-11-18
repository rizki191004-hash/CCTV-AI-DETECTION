"""
tunnel_manager.py — Native asynchronous Cloudflare Tunnel orchestrator.

Manages cloudflared child process to expose the local CCTV FastAPI dashboard
securely to the internet without requiring start.bat or manual terminal windows.
"""

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Callable, Optional, Awaitable

logger = logging.getLogger(__name__)


class TunnelManager:
    """Manages cloudflared subprocess to expose local port to public HTTPS."""

    URL_PATTERN = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    def __init__(
        self,
        port: int = 8000,
        cloudflared_path: str = "cloudflared.exe",
        tunnel_token: Optional[str] = None,
        on_url_ready: Optional[Callable[[str], Awaitable[None]]] = None,
    ):
        """
        Args:
            port: Local port to expose (default 8000).
            cloudflared_path: Path to cloudflared executable.
            tunnel_token: Optional Cloudflare Tunnel Token for persistent named tunnels.
            on_url_ready: Optional async callback invoked when public URL is resolved.
        """
        self.port = port
        self.cloudflared_path = self._resolve_executable(cloudflared_path)
        self.tunnel_token = tunnel_token
        self.on_url_ready = on_url_ready

        self.current_url: Optional[str] = None
        self._process: Optional[asyncio.subprocess.Process] = None
        self._watchdog_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    @staticmethod
    def _resolve_executable(path_str: str) -> str:
        """Resolve full path to cloudflared executable."""
        p = Path(path_str)
        if p.is_file():
            return str(p.resolve())
        # Try finding in current directory or parent
        local_cf = Path.cwd() / "cloudflared.exe"
        if local_cf.is_file():
            return str(local_cf.resolve())
        return path_str

    async def start(self, timeout: float = 30.0) -> Optional[str]:
        """Start the tunnel subprocess and wait for the public HTTPS URL.

        Args:
            timeout: Maximum seconds to wait for URL resolution.

        Returns:
            Resolved HTTPS URL string, or None if timed out / failed.
        """
        self._stop_event.clear()

        # Build command
        if self.tunnel_token:
            cmd = [self.cloudflared_path, "tunnel", "run", "--token", self.tunnel_token]
        else:
            cmd = [self.cloudflared_path, "tunnel", "--url", f"http://127.0.0.1:{self.port}"]

        logger.info("Starting Cloudflare Tunnel on port %d...", self.port)
        try:
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except FileNotFoundError:
            logger.warning(
                "cloudflared executable not found at '%s'. Remote public tunnel disabled.",
                self.cloudflared_path,
            )
            return None
        except Exception as e:
            logger.error("Failed to spawn cloudflared: %s", e)
            return None

        # Read output stream until public URL is detected or timeout expires
        loop = asyncio.get_running_loop()
        start_time = loop.time()

        while not self._stop_event.is_set():
            if loop.time() - start_time > timeout:
                logger.warning("Timed out waiting for Cloudflare Tunnel URL")
                break

            if self._process.returncode is not None:
                logger.warning("cloudflared exited unexpectedly with code %s", self._process.returncode)
                break

            try:
                line_bytes = await asyncio.wait_for(
                    self._process.stdout.readline(), timeout=1.0
                )
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="replace").strip()
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

            # Check for URL match
            match = self.URL_PATTERN.search(line)
            if match:
                self.current_url = match.group(0)
                logger.info("Cloudflare Tunnel active: %s", self.current_url)
                if self.on_url_ready:
                    try:
                        res = self.on_url_ready(self.current_url)
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception as cb_err:
                        logger.warning("on_url_ready callback error: %s", cb_err)
                break

        # Start watchdog
        if self._process and self._process.returncode is None:
            self._watchdog_task = asyncio.create_task(self._watchdog_loop())

        return self.current_url

    async def _watchdog_loop(self) -> None:
        """Background loop ensuring tunnel stays alive."""
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(20.0)
            except asyncio.CancelledError:
                break
            if self._stop_event.is_set():
                break
            if self._process is None or self._process.returncode is not None:
                if not self._stop_event.is_set():
                    logger.warning("Tunnel dropped. Watchdog restarting cloudflared...")
                    await self.start()
                    break

    async def stop(self) -> None:
        """Gracefully terminate the tunnel process and cancel watchdog."""
        self._stop_event.set()
        if self._watchdog_task:
            if not self._watchdog_task.done():
                self._watchdog_task.cancel()
            self._watchdog_task = None

        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=3.0)
            except (asyncio.TimeoutError, ProcessLookupError):
                try:
                    self._process.kill()
                except ProcessLookupError:
                    pass
            except Exception as e:
                logger.debug("Error stopping cloudflared process: %s", e)
            finally:
                self._process = None

        self.current_url = None
        logger.info("Cloudflare Tunnel stopped.")

