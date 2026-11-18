"""
tests/test_stream_probe.py – Tests for camera stream pre-flight probe endpoint
"""

import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.api.server import create_app
from src.config_loader import AppConfig


class TestStreamProbe(unittest.TestCase):
    def setUp(self):
        mock_app_config = MagicMock(spec=AppConfig)
        mock_app_config.dashboard_pin = ""
        mock_cctv_app = MagicMock()
        mock_cctv_app.config = mock_app_config
        mock_cctv_app.pipelines = {}

        self.app = create_app(mock_cctv_app)
        self.client = TestClient(self.app)

    @patch("cv2.VideoCapture")
    def test_probe_active_stream_returns_online(self, mock_cv2_capture):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: 1920.0 if prop == 3 else (1080.0 if prop == 4 else 30.0)
        mock_cv2_capture.return_value = mock_cap

        res = self.client.post("/api/cameras/probe", json={"stream_url": "https://stream.palembang.go.id/cam8/index.m3u8"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["online"])
        self.assertIn("1920x1080", data["resolution"])

    def test_probe_dead_stream_returns_offline_and_reason(self):
        # A known 404 URL
        dead_url = "https://stream.palembang.go.id/cam999999/index.m3u8"
        res = self.client.post("/api/cameras/probe", json={"stream_url": dead_url})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["online"])
        self.assertTrue("404" in data["message"] or "offline" in data["message"].lower())


if __name__ == "__main__":
    unittest.main()

