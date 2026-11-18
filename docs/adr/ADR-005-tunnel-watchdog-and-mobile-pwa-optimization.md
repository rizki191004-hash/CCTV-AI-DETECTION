# ADR-005: Tunnel Watchdog Healthcheck & Mobile Viewport Optimization

- **Status:** Accepted
- **Date:** 2026-11-13
- **Deciders:** Engineering Lead & AI Architect

## Context

When running Cloudflare tunnels over residential or mobile ISP connections, transient network drops or socket timeouts can silently terminate the `cloudflared` process. If not monitored, the mobile dashboard becomes unreachable until the application is restarted.

Furthermore, viewing multiple high-definition RTSP camera feeds on narrow smartphone viewports requires touch-responsive layouts and tap-to-fullscreen capabilities.

## Decision

1. **Tunnel Watchdog & Auto-Reconnect:**
   - In `src/tunnel_manager.py`, maintain an async watchdog loop running every 20 seconds.
   - If the tunnel process terminates unexpectedly, the watchdog automatically restarts `cloudflared.exe`, extracts the newly assigned URL, updates `public_url`, and dispatches an updated access link to Telegram.
2. **Mobile Viewport & Touch Stream Controls:**
   - In `dashboard/index.html` and `dashboard/src/App.tsx`, guarantee `<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">`.
   - Provide touch-friendly single-camera full-screen toggle for responsive viewing on iOS Safari and Android Chrome.

## Consequences

### Positive
- Resilient mobile uptime: recovers automatically from Wi-Fi or ISP disconnects.
- Superior smartphone usability with dedicated full-screen camera inspection.

### Negative / Trade-offs
- If dynamic quick tunnels are forced to obtain a new URL upon severe network reconnection, Telegram receives a notification of the updated URL.

