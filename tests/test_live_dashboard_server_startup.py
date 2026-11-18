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


if __name__ == "__main__":
    unittest.main()

