"""
tests/test_browser_auto_open.py — TDD for auto-open browser after server starts.

Imports only src.browser_utils (lightweight) for the helper tests,
to avoid pulling in ultralytics/opencv via src.main at module-load time.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class TestOpenBrowserWhenReady(unittest.TestCase):
    """src.browser_utils.open_browser_when_ready must call webbrowser.open after delay."""

    def test_open_local_url_called(self):
        """webbrowser.open is called with the given URL."""
        with patch("webbrowser.open") as mock_open:
            from src.browser_utils import open_browser_when_ready
            asyncio.run(open_browser_when_ready("http://localhost:8000", delay=0))
            mock_open.assert_called_once_with("http://localhost:8000")

    def test_exception_does_not_propagate(self):
        """If webbrowser.open raises, the coroutine must NOT raise."""
        with patch("webbrowser.open", side_effect=OSError("no display")):
            from src.browser_utils import open_browser_when_ready
            # Must complete without exception
            asyncio.run(open_browser_when_ready("http://localhost:8000", delay=0))

    def test_tunnel_url_opened(self):
        """open_browser_when_ready works with any URL, including tunnel URLs."""
        with patch("webbrowser.open") as mock_open:
            from src.browser_utils import open_browser_when_ready
            tunnel_url = "https://abc123.trycloudflare.com"
            asyncio.run(open_browser_when_ready(tunnel_url, delay=0))
            mock_open.assert_called_once_with(tunnel_url)
