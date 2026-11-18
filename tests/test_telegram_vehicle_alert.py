"""
tests/test_telegram_vehicle_alert.py – Tests for vehicle information in Telegram alerts
"""

import unittest
from unittest.mock import AsyncMock, MagicMock
from src.telegram_notifier import TelegramNotifier


class TestTelegramVehicleAlert(unittest.TestCase):
    def setUp(self):
        self.notifier = TelegramNotifier(
            bot_token="test_token",
            chat_id="12345678",
        )

    def test_format_alert_caption_includes_vehicle_info(self):
        caption = self.notifier.format_alert_caption(
            camera_name="CAM_01",
            score=75.0,
            triggered_rules=["person_detected"],
            track_ids=[1],
            event_id="evt12345",
            alert_level="SUSPICIOUS",
            vehicle_info="Riding Motorcycle",
        )
        self.assertIn("Vehicle", caption)
        self.assertIn("Riding Motorcycle", caption)

    def test_format_alert_caption_without_vehicle_info(self):
        caption = self.notifier.format_alert_caption(
            camera_name="CAM_01",
            score=75.0,
            triggered_rules=["person_detected"],
            track_ids=[1],
            event_id="evt12345",
            alert_level="SUSPICIOUS",
            vehicle_info=None,
        )
        self.assertNotIn("Vehicle", caption)


if __name__ == "__main__":
    unittest.main()

