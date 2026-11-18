import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.telegram_notifier import TelegramNotifier

class TestTelegramMobileBroadcast(unittest.TestCase):
    def test_format_mobile_access_message(self):
        notifier = TelegramNotifier(bot_token="dummy_token", chat_id="123456")
        msg = notifier.format_mobile_link_message("https://sample-cctv.trycloudflare.com")
        self.assertIn("CCTV Mobile Dashboard", msg)
        self.assertIn("https://sample\\-cctv\\.trycloudflare\\.com", msg)

    def test_format_mobile_message_escapes_reserved_characters(self):
        """Verify that period at the end of guidance sentence is escaped for Telegram MarkdownV2."""
        notifier = TelegramNotifier(bot_token="dummy_token", chat_id="123456")
        msg = notifier.format_mobile_link_message("https://sample-cctv.trycloudflare.com")
        self.assertIn("ponsel Anda\\.", msg)
        self.assertNotIn("ponsel Anda.\n", msg)
        self.assertFalse(msg.endswith("ponsel Anda."))

if __name__ == "__main__":
    unittest.main()

