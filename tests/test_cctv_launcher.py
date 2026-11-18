"""
tests/test_cctv_launcher.py — Test smart toggle controller launcher logic.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestCCTVLauncherLogic(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_is_running_detects_http_service(self, mock_urlopen):
        """is_cctv_running must return True when port 8000 responds."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        from cctv import is_cctv_running
        self.assertTrue(is_cctv_running())

    @patch("urllib.request.urlopen", side_effect=OSError("connection refused"))
    @patch("os.path.exists", return_value=False)
    def test_is_running_returns_false_when_offline(self, mock_exists, mock_urlopen):
        """is_cctv_running must return False when service is down and no PID file."""
        from cctv import is_cctv_running
        self.assertFalse(is_cctv_running())

    def test_get_pythonw_path_returns_executable(self):
        """get_pythonw_path must return an existing python executable."""
        from cctv import get_pythonw_path
        path = get_pythonw_path()
        self.assertTrue(os.path.exists(path))
        self.assertTrue("python" in path.lower())


if __name__ == "__main__":
    unittest.main()

