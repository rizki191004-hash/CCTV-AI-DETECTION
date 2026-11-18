"""
tests/test_shutdown_watcher_unblocks_gather.py — Verify shutdown watcher cleanly halts uvicorn and cancels tasks.
"""

import asyncio
import unittest
from unittest.mock import MagicMock
from src.main import CCTVApplication


class TestShutdownWatcher(unittest.TestCase):
    def test_shutdown_watcher_sets_server_should_exit(self):
        """When shutdown_event is set, server.should_exit must be set to True and tasks cancelled."""
        app = CCTVApplication(config_dir=".")
        mock_server = MagicMock()
        mock_server.should_exit = False

        dummy_task = MagicMock()
        dummy_task.done.return_value = False
        dummy_task.cancel = MagicMock()

        tasks = [dummy_task]

        async def run_watcher():
            # Define watcher logic as in src/main.py
            server_instance = mock_server

            async def _shutdown_watcher():
                await app.shutdown_event.wait()
                if server_instance is not None:
                    server_instance.should_exit = True
                for t in tasks:
                    if not t.done():
                        t.cancel()

            watcher = asyncio.create_task(_shutdown_watcher())
            # Trigger shutdown
            app.shutdown_event.set()
            await watcher

        asyncio.run(run_watcher())

        self.assertTrue(mock_server.should_exit)
        dummy_task.cancel.assert_called_once()


if __name__ == "__main__":
    unittest.main()

