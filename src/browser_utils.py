"""
src/browser_utils.py — Utility untuk membuka browser secara async.

Dipisahkan dari main.py agar bisa di-test tanpa mengimport
dependensi berat (ultralytics, opencv, dll).
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def open_browser_when_ready(url: str, delay: float = 2.0) -> None:
    """Tunggu `delay` detik lalu buka `url` di browser default sistem.

    Delay memastikan HTTP server sudah bind sebelum browser dibuka.
    Jika tidak ada display (headless server), exception ditangkap dan
    di-log sebagai warning — aplikasi tetap berjalan normal.

    Args:
        url: URL yang akan dibuka, e.g. "http://localhost:8000"
        delay: Waktu tunggu dalam detik sebelum membuka browser.
    """
    await asyncio.sleep(delay)
    try:
        import webbrowser
        webbrowser.open(url)
        logger.info("🌐 Dashboard dibuka di browser: %s", url)
    except Exception as exc:
        logger.warning("Tidak dapat membuka browser secara otomatis: %s", exc)

