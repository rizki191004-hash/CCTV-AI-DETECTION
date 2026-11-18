"""
tests/test_main_human_crop_integration.py — Test human crop integration in CameraPipeline._handle_alert.
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Only mock heavy GPU/inference dependencies if needed
if "ultralytics" not in sys.modules:
    sys.modules["ultralytics"] = MagicMock()

from src.main import CameraPipeline


class TestMainHumanCropIntegration(unittest.TestCase):
    def test_handle_alert_uses_human_crop_for_telegram(self):
        """_handle_alert must dispatch the cropped human snapshot to Telegram."""
        # Mock dependencies
        mock_cam_cfg = MagicMock()
        mock_cam_cfg.camera_id = "cam_test"
        mock_cam_cfg.name = "Test Camera"

        mock_app_cfg = MagicMock()
        mock_app_cfg.input_resolution = (640, 360)

        mock_tracker = MagicMock()
        mock_track = MagicMock()
        mock_track.latest_bbox = (100, 100, 200, 300)
        mock_tracker.get_active_tracks.return_value = {1: mock_track}

        mock_scheduler = MagicMock()
        mock_scheduler.capture_snapshot.return_value = "snapshots/full_snapshot.jpg"
        mock_scheduler.capture_human_crop.return_value = "snapshots/crop_snapshot_crop.jpg"

        mock_telegram = MagicMock()
        mock_telegram.send_alert = AsyncMock()

        mock_db = MagicMock()
        mock_db.create_event = AsyncMock()
        mock_db.log_snapshot = AsyncMock()
        mock_db.log_rule_trigger = AsyncMock()

        # Instantiate pipeline using __new__ to bypass full constructor
        pipeline = CameraPipeline.__new__(CameraPipeline)
        pipeline.camera_id = "cam_test"
        pipeline.camera_config = mock_cam_cfg
        pipeline.app_config = mock_app_cfg
        pipeline.tracker = mock_tracker
        pipeline.snapshot_scheduler = mock_scheduler
        pipeline.telegram = mock_telegram
        pipeline.db = mock_db

        event = MagicMock()
        event.event_id = "evt_001"
        event.score = 85.0
        event.triggered_rules = ["fall_detected"]
        event.track_ids = {1}
        event.is_critical = True
        event.state = MagicMock()
        event.state.value = "ALERTING"

        frame = np.zeros((720, 1280, 3), dtype=np.uint8)

        asyncio.run(pipeline._handle_alert(event, frame))

        # Full snapshot must be saved and logged to database
        mock_scheduler.capture_snapshot.assert_called_once()
        mock_db.log_snapshot.assert_called_once_with(
            event_id="evt_001",
            camera_id="cam_test",
            file_path="snapshots/full_snapshot.jpg",
            snapshot_type="alert",
            score=85.0,
            sent_telegram=True,
        )

        # Telegram must be sent the cropped human snapshot!
        mock_telegram.send_alert.assert_called_once()
        call_kwargs = mock_telegram.send_alert.call_args.kwargs
        self.assertEqual(call_kwargs["snapshot_path"], "snapshots/crop_snapshot_crop.jpg")


if __name__ == "__main__":
    unittest.main()
