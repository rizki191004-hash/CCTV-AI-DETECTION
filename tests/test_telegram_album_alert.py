"""
tests/test_telegram_album_alert.py — TDD tests for Telegram album (media group) alerts.
"""
import asyncio
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.telegram_notifier import TelegramNotifier


class TestTelegramAlbumAlert(unittest.IsolatedAsyncioTestCase):
    async def test_send_alert_with_face_snapshot_sends_media_group(self):
        """When face_snapshot_path is provided, calls send_media_group with 2 InputMediaPhoto items."""
        with tempfile.TemporaryDirectory() as tmpdir:
            body_photo = Path(tmpdir) / "body.jpg"
            face_photo = Path(tmpdir) / "face.jpg"
            body_photo.write_bytes(b"body_image_data")
            face_photo.write_bytes(b"face_image_data")

            notifier = TelegramNotifier(bot_token="test_token", chat_id="12345", rate_limit_interval=0.0)
            mock_bot = MagicMock()
            mock_bot.send_media_group = AsyncMock(return_value=[MagicMock(), MagicMock()])
            notifier._bot = mock_bot
            notifier._enabled = True

            success = await notifier.send_alert(
                camera_name="Cam 01",
                score=85.0,
                triggered_rules=["warehouse_taking_goods"],
                track_ids=[1],
                snapshot_path=str(body_photo),
                face_snapshot_path=str(face_photo),
                event_id="evt_test",
            )

            assert success is True
            mock_bot.send_media_group.assert_called_once()
            call_kwargs = mock_bot.send_media_group.call_args.kwargs
            media_items = call_kwargs["media"]
            assert len(media_items) == 2
            # First item has caption
            assert media_items[0].caption is not None
            # Second item has no caption (or secondary)
            assert media_items[1].caption is None or media_items[1].caption == ""

    async def test_send_alert_without_face_snapshot_sends_single_photo(self):
        """When only snapshot_path is provided, calls send_photo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            body_photo = Path(tmpdir) / "body.jpg"
            body_photo.write_bytes(b"body_image_data")

            notifier = TelegramNotifier(bot_token="test_token", chat_id="12345", rate_limit_interval=0.0)
            mock_bot = MagicMock()
            mock_bot.send_photo = AsyncMock(return_value=MagicMock())
            notifier._bot = mock_bot
            notifier._enabled = True

            success = await notifier.send_alert(
                camera_name="Cam 01",
                score=70.0,
                triggered_rules=["loitering"],
                track_ids=[1],
                snapshot_path=str(body_photo),
                face_snapshot_path=None,
                event_id="evt_test_single",
            )

            assert success is True
            mock_bot.send_photo.assert_called_once()

    async def test_send_alert_media_group_fallback_on_error(self):
        """If send_media_group fails, falls back gracefully to single send_photo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            body_photo = Path(tmpdir) / "body.jpg"
            face_photo = Path(tmpdir) / "face.jpg"
            body_photo.write_bytes(b"body_image_data")
            face_photo.write_bytes(b"face_image_data")

            notifier = TelegramNotifier(bot_token="test_token", chat_id="12345", rate_limit_interval=0.0)
            mock_bot = MagicMock()
            mock_bot.send_media_group = AsyncMock(side_effect=Exception("Media group error"))
            mock_bot.send_photo = AsyncMock(return_value=MagicMock())
            notifier._bot = mock_bot
            notifier._enabled = True
            notifier.retry_count = 1  # 1 attempt then fallback

            success = await notifier.send_alert(
                camera_name="Cam 01",
                score=85.0,
                triggered_rules=["warehouse_taking_goods"],
                track_ids=[1],
                snapshot_path=str(body_photo),
                face_snapshot_path=str(face_photo),
                event_id="evt_fallback",
            )

            assert success is True
            mock_bot.send_photo.assert_called_once()
