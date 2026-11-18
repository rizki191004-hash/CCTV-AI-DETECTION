# ADR-004: Native Tunnel Orchestration, Telegram Mobile Link Dispatch, and PIN Security Gate

- **Status:** Accepted
- **Date:** 2026-11-13
- **Deciders:** Engineering Lead & AI Architect

## Context

The previous method for running the application and exposing it to mobile devices relied on `start.bat`. This required opening two CMD prompt windows simultaneously (`python src/main.py` and `cloudflared.exe tunnel`), manually locating the generated `trycloudflare.com` random URL in console logs, and manually copying that URL into the Telegram configuration.

Additionally, exposing the CCTV application over a public Cloudflare tunnel without authentication created a critical vulnerability, allowing anyone with the URL to view live camera streams and edit surveillance configurations.

The user explicitly requested eliminating `start.bat` and enabling a seamless, secure mobile access experience.

## Decision

1. **Native Async Tunnel Manager (`src/tunnel_manager.py`):**
   - Eliminate `start.bat`.
   - Embed `cloudflared.exe` process management directly into the Python orchestrator (`src/main.py`) using `asyncio.create_subprocess_exec`.
   - The Python backend manages the tunnel lifecycle: automatically starting the tunnel on startup, capturing stdout via regex to extract the live HTTPS URL, updating runtime configs, and cleanly terminating the child process on application shutdown.
   - Provide an optional Windows Background Service / Startup task installer (`scripts/install_service.py`) for headless background startup on boot.
2. **Automatic Telegram Link Broadcast:**
   - Once the tunnel establishes an active connection and resolves its public HTTPS URL (e.g. `https://xxxx.trycloudflare.com`), the backend automatically:
     - Updates `cctv_app.config.public_url`.
     - Injects the URL into `telegram_notifier.public_url`.
     - Sends a direct Telegram message with a 1-click button: `📱 CCTV Dashboard Mobile: [Buka Dashboard]({url})` and logs a clean ASCII QR code in the terminal.
3. **Lightweight PIN Security Gate:**
   - Implement a lightweight authentication middleware in FastAPI (`src/api/auth.py`).
   - If `DASHBOARD_PIN` is configured in `.env` (or config), requests to the dashboard and API (except public assets and healthcheck) require entering a 4-6 digit PIN.
   - Upon successful PIN entry, a short-lived secure session token / cookie is granted, keeping the mobile experience fast and secure.

## Consequences

### Positive
- Single command execution (`python src/main.py`) or zero-click Windows boot startup—no multiple CMD windows or batch scripts.
- Instant 1-click mobile access directly from the Telegram alert chat.
- Strong protection against unauthorized public access to live CCTV feeds.

### Negative / Trade-offs
- Entering a PIN on first mobile browser open adds a minor initial interaction step (which can be remembered via cookies for 30 days).

