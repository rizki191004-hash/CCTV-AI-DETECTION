"""
tests/test_main_face_crop_integration.py — Integration tests for suspect isolation & face crop in CameraPipeline.
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np
import pytest

from src.config_loader import AppConfig, CameraConfig
from src.main import CameraPipeline


def _make_pipeline(cam_cfg, app_cfg, mock_snapshot_sched, mock_telegram, mock_db,
                   mock_event_mgr=None, mock_rule_engine=None):
    """Build a CameraPipeline via __new__ to bypass constructor side-effects (MotionDetector, etc.)."""
    pipeline = CameraPipeline.__new__(CameraPipeline)
    pipeline.camera_config = cam_cfg
    pipeline.app_config = app_cfg
    pipeline.camera_id = cam_cfg.camera_id

    pipeline.detector = MagicMock()
    pipeline.vehicle_detector = None
    pipeline.event_manager = mock_event_mgr or MagicMock()
    pipeline.rule_engine = mock_rule_engine or MagicMock()
    pipeline.snapshot_scheduler = mock_snapshot_sched
    pipeline.telegram = mock_telegram
    pipeline.db = mock_db
    pipeline.reid_manager = None

    pipeline.grabber = MagicMock()
    pipeline.preprocessor = MagicMock()
    pipeline.motion_detector = MagicMock()
    pipeline.tracker = MagicMock()
    pipeline.feature_extractor = MagicMock()
    pipeline.event_recorder = MagicMock()
    pipeline.alarm_gate = MagicMock()
    pipeline.vehicle_tracker = MagicMock()

    pipeline._frame_times = []
    pipeline._skip_counter = 0
    pipeline._dynamic_skip = 0
    pipeline._was_recording = False
    pipeline._health_status = "ONLINE"
    pipeline._offline_since = 0.0
    pipeline._health_notified = False
    pipeline._low_fps_notified = False

    pipeline.latest_track_scores = {}
    pipeline.latest_vehicle_detections = None
    pipeline.latest_riders = []
    pipeline.latest_vehicle_tracks = None
    return pipeline


class TestMainFaceCropIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_handle_alert_isolates_primary_suspect_and_sends_face_crop(self):
        """Pipeline should extract primary suspect face crop and pass face_snapshot_path to telegram."""
        import time
        cam_cfg = CameraConfig(camera_id="cam_test", name="Gate Cam", rtsp_url="rtsp://dummy")
        app_cfg = MagicMock(spec=AppConfig)
        app_cfg.input_resolution = (640, 480)
        app_cfg.alarm_gate = MagicMock()
        app_cfg.alarm_gate.confidence_gate = 0.4
        app_cfg.alarm_gate.min_frames = 1
        app_cfg.alarm_gate.min_bbox_area = 100
        app_cfg.alarm_gate.max_bbox_ratio = 0.9
        app_cfg.alarm_gate.max_aspect_ratio = 4.0

        mock_snapshot_sched = MagicMock()
        mock_snapshot_sched.capture_snapshot = MagicMock(return_value="/tmp/body.jpg")
        mock_snapshot_sched.capture_human_crop = MagicMock(return_value="/tmp/human_crop.jpg")
        mock_snapshot_sched.capture_face_crop = MagicMock(return_value="/tmp/face_crop.jpg")
        mock_telegram = MagicMock()
        mock_telegram.send_alert = AsyncMock(return_value=True)
        mock_db = MagicMock()
        mock_db.create_event = AsyncMock()
        mock_db.log_snapshot = AsyncMock()
        mock_db.log_rule_trigger = AsyncMock()

        pipeline = _make_pipeline(cam_cfg, app_cfg, mock_snapshot_sched, mock_telegram, mock_db)

        # Mock 2 active tracks: track 1 (innocent bystander, score 10), track 2 (crouching suspect, score 85)
        class MockTrack:
            def __init__(self, tid, bbox):
                self.track_id = tid
                self.latest_bbox = bbox
                self.latest_keypoints = np.zeros((17, 3), dtype=float)

        pipeline.tracker.get_active_tracks = MagicMock(return_value={
            1: MockTrack(1, [50, 50, 100, 200]),
            2: MockTrack(2, [300, 100, 400, 300]),
        })

        mock_score1 = MagicMock()
        mock_score1.total_score = 10.0
        mock_score2 = MagicMock()
        mock_score2.total_score = 85.0
        pipeline.latest_track_scores = {1: mock_score1, 2: mock_score2}

        mock_event = MagicMock()
        mock_event.event_id = "evt_goods_theft_123456"
        mock_event.score = 85.0
        mock_event.triggered_rules = ["warehouse_taking_goods"]
        mock_event.track_ids = [1, 2]
        mock_event.is_critical = False
        mock_event.state.value = "alert"
        mock_event.last_snapshot_time = 0.0
        mock_event.alert_sent = False
        mock_event.snapshot_count = 0

        frame = np.ones((480, 640, 3), dtype=np.uint8) * 100
        await pipeline._handle_alert(mock_event, frame=frame)

        # Verify capture_face_crop was called for suspect 2 (higher score)
        mock_snapshot_sched.capture_face_crop.assert_called_once()
        call_kwargs = mock_snapshot_sched.capture_face_crop.call_args.kwargs
        # Suspect 2 bbox starts around 300
        assert call_kwargs["bbox"][0] >= 290

        # Verify telegram.send_alert was called with face_snapshot_path
        mock_telegram.send_alert.assert_called_once()
        tg_kwargs = mock_telegram.send_alert.call_args.kwargs
        assert tg_kwargs["face_snapshot_path"] == "/tmp/face_crop.jpg"

    async def test_handle_alert_when_face_crop_returns_none(self):
        """When face_crop returns None (back turned), face_snapshot_path passed as None."""
        import time
        cam_cfg = CameraConfig(camera_id="cam_test2", name="Gate Cam 2", rtsp_url="rtsp://dummy")
        app_cfg = MagicMock(spec=AppConfig)
        app_cfg.input_resolution = (640, 480)
        app_cfg.alarm_gate = MagicMock()
        app_cfg.alarm_gate.confidence_gate = 0.4
        app_cfg.alarm_gate.min_frames = 1
        app_cfg.alarm_gate.min_bbox_area = 100
        app_cfg.alarm_gate.max_bbox_ratio = 0.9
        app_cfg.alarm_gate.max_aspect_ratio = 4.0

        mock_snapshot_sched = MagicMock()
        mock_snapshot_sched.capture_snapshot = MagicMock(return_value="/tmp/body.jpg")
        mock_snapshot_sched.capture_human_crop = MagicMock(return_value="/tmp/human_crop.jpg")
        mock_snapshot_sched.capture_face_crop = MagicMock(return_value=None)  # Face not visible
        mock_telegram = MagicMock()
        mock_telegram.send_alert = AsyncMock(return_value=True)
        mock_db = MagicMock()
        mock_db.create_event = AsyncMock()
        mock_db.log_snapshot = AsyncMock()
        mock_db.log_rule_trigger = AsyncMock()

        pipeline = _make_pipeline(cam_cfg, app_cfg, mock_snapshot_sched, mock_telegram, mock_db)

        class MockTrack:
            def __init__(self, tid, bbox):
                self.track_id = tid
                self.latest_bbox = bbox
                self.latest_keypoints = None

        pipeline.tracker.get_active_tracks = MagicMock(return_value={
            1: MockTrack(1, [100, 100, 200, 300]),
        })
        pipeline.latest_track_scores = {}

        mock_event = MagicMock()
        mock_event.event_id = "evt_back_turned_12345"
        mock_event.score = 75.0
        mock_event.triggered_rules = ["loitering"]
        mock_event.track_ids = [1]
        mock_event.is_critical = False
        mock_event.state.value = "alert"
        mock_event.last_snapshot_time = 0.0
        mock_event.alert_sent = False
        mock_event.snapshot_count = 0

        frame = np.ones((480, 640, 3), dtype=np.uint8) * 100
        await pipeline._handle_alert(mock_event, frame=frame)

        mock_telegram.send_alert.assert_called_once()
        tg_kwargs = mock_telegram.send_alert.call_args.kwargs
        assert tg_kwargs["face_snapshot_path"] is None
