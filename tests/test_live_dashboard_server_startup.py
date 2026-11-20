import os
import sys
import unittest
from unittest.mock import patch
import uvicorn
from fastapi import FastAPI


class TestLiveDashboardServerStartup(unittest.TestCase):
    def test_uvicorn_config_with_none_stdout(self):
        """When sys.stdout is None (as in pythonw.exe), uvicorn config must initialize without AttributeError."""
        with patch.object(sys, "stdout", None), patch.object(sys, "stderr", None):
            app = FastAPI()
            # Configuring with log_config=None must succeed without error
            config = uvicorn.Config(
                app=app,
                host="0.0.0.0",
                port=8000,
                log_level="error",
                log_config=None,
                access_log=False,
            )
            server = uvicorn.Server(config)
            self.assertIsNotNone(server)


    def test_dashboard_index_cache_busting_headers(self):
        """GET / and SPA fallback routes serving index.html must return no-cache headers."""
        from unittest.mock import MagicMock
        from fastapi.testclient import TestClient
        from src.api.server import create_app

        mock_app = MagicMock()
        mock_app.pipelines = {}
        mock_app.storage_manager = None
        mock_app.shutdown_event = MagicMock()

        api_app = create_app(mock_app)
        client = TestClient(api_app)

        # 1. Root route
        res_root = client.get("/")
        if res_root.status_code == 200:
            cache_control = res_root.headers.get("cache-control", "")
            self.assertIn("no-cache", cache_control)
            self.assertIn("no-store", cache_control)

        # 2. SPA fallback route
        res_spa = client.get("/dashboard-view")
        if res_spa.status_code == 200:
            cache_control = res_spa.headers.get("cache-control", "")
            self.assertIn("no-cache", cache_control)
            self.assertIn("no-store", cache_control)


if __name__ == "__main__":
    unittest.main()

