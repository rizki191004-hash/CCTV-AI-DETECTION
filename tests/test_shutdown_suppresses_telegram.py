import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock
from src.telegram_notifier import TelegramNotifier
from src.tunnel_manager import TunnelManager


class TestShutdownSuppressesTelegram(unittest.TestCase):
    def test_telegram_notifier_stop_disables_sending(self):
        notifier = TelegramNotifier(bot_token="fake_token", chat_id="fake_chat")
        notifier._enabled = True
        notifier._bot = MagicMock()

        notifier.stop()
        self.assertFalse(notifier._enabled)

        # Calling send_mobile_link returns False immediately
        res = asyncio.run(notifier.send_mobile_link("https://test.trycloudflare.com"))
        self.assertFalse(res)

    def test_tunnel_manager_stop_cancels_watchdog(self):
        tm = TunnelManager(port=8000)
        mock_task = MagicMock()
        mock_task.done.return_value = False
        tm._watchdog_task = mock_task
        tm._process = MagicMock()
        tm._process.wait = AsyncMock()

        asyncio.run(tm.stop())
        self.assertTrue(tm._stop_event.is_set())
        mock_task.cancel.assert_called_once()
        self.assertIsNone(tm._watchdog_task)


if __name__ == "__main__":
    unittest.main()
