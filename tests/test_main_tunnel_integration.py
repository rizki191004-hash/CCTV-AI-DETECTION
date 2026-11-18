import asyncio
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock heavy dependencies if not present
if "ultralytics" not in sys.modules:
    sys.modules["ultralytics"] = MagicMock()

from src.main import CCTVApplication

class TestMainTunnelIntegration(unittest.TestCase):
    @patch("src.main.ConfigLoader")
    @patch("src.main.DBLogger")
    @patch("src.main.TelegramNotifier")
    @patch("src.main.PersonDetector")
    def test_cctv_app_initializes_tunnel(self, mock_det, mock_tg, mock_db, mock_cfg_loader):
        app = CCTVApplication()
        # Verify app defines tunnel_manager attribute
        self.assertTrue(hasattr(app, "tunnel_manager"))

    def test_cctv_app_has_tunnel_browser_opened_flag(self):
        """CCTVApplication must initialise _tunnel_browser_opened = False."""
        app = CCTVApplication()
        self.assertFalse(app._tunnel_browser_opened)

    def test_tunnel_browser_opened_flag_set_on_first_url(self):
        """_on_tunnel_url_ready must set _tunnel_browser_opened = True after first call."""
        app = CCTVApplication()
        app.telegram = MagicMock()
        app.telegram.send_mobile_link = AsyncMock()
        app.config = MagicMock()

        asyncio.run(app._on_tunnel_url_ready("https://first.trycloudflare.com"))
        self.assertTrue(app._tunnel_browser_opened)

    def test_tunnel_browser_not_opened_twice(self):
        """_tunnel_browser_opened stays True; second call must NOT reset it."""
        app = CCTVApplication()
        app.telegram = MagicMock()
        app.telegram.send_mobile_link = AsyncMock()
        app.config = MagicMock()

        asyncio.run(app._on_tunnel_url_ready("https://first.trycloudflare.com"))
        asyncio.run(app._on_tunnel_url_ready("https://second.trycloudflare.com"))
        # Flag stays True — not toggled or reset
        self.assertTrue(app._tunnel_browser_opened)

if __name__ == "__main__":
    unittest.main()

