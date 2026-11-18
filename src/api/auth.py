"""
auth.py — Lightweight PIN-based authentication gate for remote mobile access.

Protects FastAPI endpoints and dashboard streams when exposed over public Cloudflare Tunnels.
If DASHBOARD_PIN is configured in .env, users must enter a 4-6 digit PIN to gain access.
"""

import logging
import secrets
import time
from collections import defaultdict
from typing import Dict, Optional, Tuple
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class PinAuthManager:
    """Manages PIN verification, active session tokens, and brute-force protection."""

    def __init__(
        self,
        pin: Optional[str] = None,
        max_attempts: int = 5,
        lockout_sec: float = 300.0,
        session_ttl_sec: float = 30 * 86400.0,  # 30 days
    ):
        self.pin = str(pin).strip() if pin else None
        self.max_attempts = max_attempts
        self.lockout_sec = lockout_sec
        self.session_ttl_sec = session_ttl_sec

        # session_token -> expire_timestamp
        self._sessions: Dict[str, float] = {}

        # client_ip -> (fail_count, first_fail_time)
        self._failures: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, 0.0))

    @property
    def is_enabled(self) -> bool:
        """Return True if PIN protection is active."""
        return bool(self.pin)

    def is_rate_limited(self, client_ip: str) -> bool:
        """Check if client IP is temporarily locked out due to brute-force attempts."""
        count, first_time = self._failures.get(client_ip, (0, 0.0))
        if count >= self.max_attempts:
            if time.time() - first_time < self.lockout_sec:
                return True
            else:
                # Lockout expired, reset
                self._failures.pop(client_ip, None)
        return False

    def verify_pin(self, candidate: str, client_ip: str = "default") -> bool:
        """Verify candidate PIN against configured PIN with rate limiting."""
        if not self.is_enabled:
            return True

        if self.is_rate_limited(client_ip):
            logger.warning("Authentication attempt rejected: IP %s is rate-limited", client_ip)
            return False

        if not candidate:
            return False

        is_correct = secrets.compare_digest(str(candidate).strip(), self.pin)
        now = time.time()

        if is_correct:
            self._failures.pop(client_ip, None)
            return True
        else:
            count, first_time = self._failures.get(client_ip, (0, now))
            self._failures[client_ip] = (count + 1, first_time)
            logger.warning("Failed PIN attempt #%d from IP %s", count + 1, client_ip)
            return False

    def create_session(self) -> str:
        """Generate and record a secure session token."""
        token = secrets.token_urlsafe(32)
        self._sessions[token] = time.time() + self.session_ttl_sec
        return token

    def is_valid_session(self, token: Optional[str]) -> bool:
        """Check if session token is valid and unexpired."""
        if not self.is_enabled:
            return True
        if not token:
            return False

        expire_time = self._sessions.get(token)
        if expire_time is None:
            return False

        if time.time() > expire_time:
            self._sessions.pop(token, None)
            return False

        return True


# Responsive mobile-friendly PIN login HTML page
MOBILE_LOGIN_HTML = """<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <title>CCTV Security Gate</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body {
      background: #0f172a; color: #f8fafc;
      min-height: 100vh; display: flex; align-items: center; justify-content: center;
      padding: 20px;
    }
    .card {
      background: #1e293b; border: 1px solid #334155; border-radius: 16px;
      padding: 32px 24px; width: 100%; max-width: 360px; text-align: center;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    }
    .icon { font-size: 48px; margin-bottom: 12px; }
    h1 { font-size: 20px; font-weight: 700; margin-bottom: 8px; }
    p { font-size: 13px; color: #94a3b8; margin-bottom: 24px; line-height: 1.4; }
    input {
      width: 100%; padding: 14px; font-size: 22px; letter-spacing: 8px; text-align: center;
      background: #0f172a; border: 2px solid #475569; border-radius: 12px; color: #fff;
      margin-bottom: 16px; outline: none; transition: border-color 0.2s;
    }
    input:focus { border-color: #3b82f6; }
    button {
      width: 100%; padding: 14px; font-size: 16px; font-weight: 600;
      background: #2563eb; color: #fff; border: none; border-radius: 12px;
      cursor: pointer; transition: background 0.2s;
    }
    button:active { background: #1d4ed8; }
    .error { color: #ef4444; font-size: 13px; margin-top: 12px; display: none; }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">🔒</div>
    <h1>CCTV AI Security</h1>
    <p>Masukkan PIN keamanan untuk mengakses monitoring CCTV secara mobile.</p>
    <input type="password" id="pinInput" inputmode="numeric" pattern="[0-9]*" maxlength="8" placeholder="••••" autofocus>
    <button onclick="submitPin()">Buka Dashboard</button>
    <div id="errMsg" class="error">PIN salah atau terlalu banyak percobaan.</div>
  </div>
  <script>
    async function submitPin() {
      const pin = document.getElementById('pinInput').value;
      const err = document.getElementById('errMsg');
      err.style.display = 'none';
      if (!pin) return;
      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ pin: pin })
        });
        if (res.ok) {
          const data = await res.json();
          document.cookie = "cctv_session=" + data.token + "; path=/; max-age=2592000; SameSite=Lax";
          window.location.reload();
        } else {
          err.style.display = 'block';
        }
      } catch (e) {
        err.style.display = 'block';
      }
    }
    document.getElementById('pinInput').addEventListener('keypress', function(e) {
      if (e.key === 'Enter') submitPin();
    });
  </script>
</body>
</html>
"""


class PinAuthMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware verifying PIN authentication on protected endpoints."""

    def __init__(self, app, auth_manager: PinAuthManager):
        super().__init__(app)
        self.auth_manager = auth_manager

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.auth_manager.is_enabled:
            return await call_next(request)

        path = request.url.path

        # Whitelist public resources & auth API
        if (
            path.startswith("/api/auth/")
            or path.startswith("/assets/")
            or path in ("/favicon.ico", "/robots.txt")
        ):
            return await call_next(request)

        # Extract token from cookie, query param, or Authorization header
        token = request.cookies.get("cctv_session")
        if not token:
            token = request.query_params.get("token")
        if not token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1]

        # Check authentication
        if self.auth_manager.is_valid_session(token):
            return await call_next(request)

        # Unauthenticated: return 401 for API routes, or Mobile Login HTML for web requests
        if path.startswith("/api/"):
            return JSONResponse(
                {"error": "unauthorized", "message": "PIN authentication required"},
                status_code=401,
            )

        return HTMLResponse(MOBILE_LOGIN_HTML, status_code=200)

