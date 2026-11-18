import unittest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.tunnel_manager import TunnelManager

class TestTunnelManager(unittest.TestCase):
    def test_parse_public_url_from_tunnel_output(self):
        async def run_test():
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_proc = MagicMock()
                mock_proc.returncode = None
                mock_proc.poll = MagicMock(return_value=None)
                
                # Mock stdout readline sequence
                mock_proc.stdout.readline = AsyncMock(side_effect=[
                    b"2026-11-13T10:00:00Z INF Requesting new quick Tunnel...\n",
                    b"2026-11-13T10:00:05Z INF |  https://my-cctv-preview.trycloudflare.com  |\n",
                    b""
                ])
                mock_proc.stderr.readline = AsyncMock(return_value=b"")
                mock_exec.return_value = mock_proc
                
                manager = TunnelManager(port=8000, cloudflared_path="cloudflared.exe")
                url = await manager.start()
                self.assertEqual(url, "https://my-cctv-preview.trycloudflare.com")
                self.assertEqual(manager.current_url, "https://my-cctv-preview.trycloudflare.com")
                
                # Test stop
                await manager.stop()
                self.assertTrue(mock_proc.terminate.called or mock_proc.kill.called)

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()

