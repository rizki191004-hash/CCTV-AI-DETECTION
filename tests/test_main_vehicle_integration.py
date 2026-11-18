"""
tests/test_main_vehicle_integration.py – Integration tests for vehicle detection pipeline in CameraPipeline
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np
import supervision as sv

from src.config_loader import AppConfig, CameraConfig
from src.vehicle_detector import VehicleDetector, VehicleDetectionResult, RiderInfo
from src.person_detector import DetectionResult
from src.main import CameraPipeline


class TestMainVehicleIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_pipeline_invokes_vehicle_detector_and_detects_rider(self):
        # Setup mocks
        cam_cfg = CameraConfig(camera_id="cam_test", name="Test Cam", rtsp_url="rtsp://dummy")
        app_cfg = MagicMock(spec=AppConfig)
        app_cfg.input_resolution = (640, 480)
        app_cfg.motion_gate_enabled = False
        app_cfg.detect_fps_target = 10
        app_cfg.motion_sensitivity = 0.1
        app_cfg.motion_history = 10
        app_cfg.motion_var_threshold = 16
        app_cfg.alarm_gate = MagicMock()
        app_cfg.alarm_gate.confidence_gate = 0.4
        app_cfg.alarm_gate.min_frames = 1
        app_cfg.alarm_gate.min_bbox_area = 100
        app_cfg.alarm_gate.max_bbox_ratio = 0.9
        app_cfg.alarm_gate.max_aspect_ratio = 4.0

        mock_detector = MagicMock()
        mock_vehicle_detector = MagicMock()
        mock_event_mgr = MagicMock()
        mock_rule_engine = MagicMock()
        mock_snapshot_sched = MagicMock()
        mock_snapshot_sched.capture_snapshot = MagicMock(return_value="/tmp/test.jpg")
        mock_snapshot_sched.capture_human_crop = MagicMock(return_value=None)
        mock_telegram = MagicMock()
        mock_telegram.send_alert = AsyncMock(return_value=True)
        mock_db = MagicMock()
        mock_db.create_event = AsyncMock()
        mock_db.log_snapshot = AsyncMock()
        mock_db.log_rule_trigger = AsyncMock()

        pipeline = CameraPipeline(
            camera_config=cam_cfg,
            app_config=app_cfg,
            detector=mock_detector,
            event_manager=mock_event_mgr,
            rule_engine=mock_rule_engine,
            snapshot_scheduler=mock_snapshot_sched,
            telegram=mock_telegram,
            db=mock_db,
            vehicle_detector=mock_vehicle_detector,
        )

        # Verify initial attributes
        self.assertIs(pipeline.vehicle_detector, mock_vehicle_detector)
        self.assertIsNone(pipeline.latest_vehicle_detections)
        self.assertEqual(pipeline.latest_riders, [])

        # Simulate vehicle detection result with rider
        person_boxes = np.array([[100, 100, 200, 250]], dtype=np.float32)
        persons = sv.Detections(
            xyxy=person_boxes,
            class_id=np.array([0], dtype=int),
            confidence=np.array([0.9], dtype=np.float32),
        )
        moto_boxes = np.array([[90, 150, 210, 300]], dtype=np.float32)
        vehicles = sv.Detections(
            xyxy=moto_boxes,
            class_id=np.array([3], dtype=int),
            confidence=np.array([0.85], dtype=np.float32),
        )

        mock_vehicle_detector.detect_async = AsyncMock(
            return_value=VehicleDetectionResult(
                vehicles=vehicles,
                vehicle_count=1,
                riders=[],
            )
        )

        # Trigger vehicle detection step directly
        veh_result = await pipeline.vehicle_detector.detect_async(np.zeros((480, 640, 3), dtype=np.uint8))
        pipeline.latest_vehicle_detections = veh_result.vehicles
        pipeline.latest_riders = VehicleDetector.find_riders(persons, veh_result.vehicles)

        self.assertEqual(len(pipeline.latest_riders), 1)
        self.assertEqual(pipeline.latest_riders[0].vehicle_class, 3)

        # Test _handle_alert passes vehicle_info to send_alert
        mock_event = MagicMock()
        mock_event.event_id = "ev_test_123"
        mock_event.score = 80.0
        mock_event.triggered_rules = ["person_detected"]
        mock_event.track_ids = [1]
        mock_event.is_critical = False
        mock_event.state.value = "alert"

        # Mock tracker
        pipeline.tracker.get_active_tracks = MagicMock(return_value={})

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        await pipeline._handle_alert(mock_event, frame=frame)

        mock_telegram.send_alert.assert_called_once()
        call_kwargs = mock_telegram.send_alert.call_args.kwargs
        self.assertEqual(call_kwargs["vehicle_info"], "Riding Motorcycle")


if __name__ == "__main__":
    unittest.main()
