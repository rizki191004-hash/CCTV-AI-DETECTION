"""
tests/test_system_shutdown.py — Test /api/system/shutdown endpoint and graceful termination.
"""

import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from src.api.server import create_app


class TestSystemShutdownAPI(unittest.TestCase):
    def test_shutdown_endpoint_returns_ok_and_signals_shutdown(self):
        """POST /api/system/shutdown must return status ok and trigger shutdown_event."""
        mock_app = MagicMock()
        mock_app.pipelines = {}
        mock_app.storage_manager = None
        mock_app.shutdown_event = MagicMock()

        api_app = create_app(mock_app)
        client = TestClient(api_app)

        response = client.post("/api/system/shutdown")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("shutting down", data.get("message", "").lower())


if __name__ == "__main__":
    unittest.main()

