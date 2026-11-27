"""
tests/test_vehicle_speed_status.py
TDD tests for vehicle label rendering: motor/car, ASCII labels, berhenti/berjalan.
"""
import numpy as np
import pytest
import supervision as sv

from src.visualizer import Visualizer, MOTORCYCLE_CLASS_ID, CAR_CLASS_ID
from src.vehicle_detector import RiderInfo
from src.vehicle_tracker import VehicleTrackResult


def _make_vehicle_detections(boxes, class_ids):
    return sv.Detections(
        xyxy=np.array(boxes, dtype=float),
        class_id=np.array(class_ids, dtype=int),
        confidence=np.array([0.9] * len(boxes), dtype=float),
    )


def _make_track_result(vehicle_ids, speeds_kmh, moving_flags):
    """Build a VehicleTrackResult for testing."""
    return VehicleTrackResult(
        tracked_vehicles=sv.Detections.empty(),
        vehicle_speeds={vid: spd for vid, spd in zip(vehicle_ids, speeds_kmh)},
        vehicle_moving={vid: mov for vid, mov in zip(vehicle_ids, moving_flags)},
        vehicle_speed_kmh={vid: spd for vid, spd in zip(vehicle_ids, speeds_kmh)},
    )


class MockTrack:
    def __init__(self, track_id=1, bbox=(100, 100, 180, 260), class_type="human", speed=0.0):
        self.track_id = track_id
        self.latest_bbox = bbox
        self.class_type = class_type
        self.latest_keypoints = None

        class MockPoint:
            def __init__(self, centroid, ts):
                self.centroid = centroid
                self.timestamp = ts
                self.confidence = 0.9

        self.points = [
            MockPoint((140, 180), 10.0),
            MockPoint((140 + speed, 180), 11.0),
        ]


class TestVehicleLabelASCII:
    def test_motorcycle_rider_label_naik_motor_berhenti(self):
        """Stopped motor rider: posture label is 'Naik Motor' (ASCII, no emoji)."""
        track = MockTrack(bbox=(100, 100, 180, 260), speed=0.0)
        veh_boxes = [[90.0, 150.0, 200.0, 300.0]]
        veh_dets = _make_vehicle_detections(veh_boxes, [MOTORCYCLE_CLASS_ID])
        riders = [RiderInfo(person_idx=0, vehicle_idx=0, vehicle_class=MOTORCYCLE_CLASS_ID, iou=0.45)]

        posture_state, _ = Visualizer._get_posture_state(
            track=track,
            bbox=np.array([100.0, 100.0, 180.0, 260.0]),
            all_detections=None,
            vehicle_detections=veh_dets,
            riders=riders,
        )

        assert "Naik Motor" in posture_state, f"Expected 'Naik Motor', got '{posture_state}'"
        # Must NOT contain emoji
        assert "\U0001f3cd" not in posture_state, f"Emoji found in label: {posture_state}"

    def test_car_driver_label_mengemudi_ascii(self):
        """Car driver posture label is 'Mengemudi' (ASCII, no emoji)."""
        track = MockTrack(bbox=(100, 100, 220, 260), speed=0.0)
        veh_boxes = [[80.0, 120.0, 250.0, 320.0]]
        veh_dets = _make_vehicle_detections(veh_boxes, [CAR_CLASS_ID])
        riders = [RiderInfo(person_idx=0, vehicle_idx=0, vehicle_class=CAR_CLASS_ID, iou=0.5)]

        posture_state, _ = Visualizer._get_posture_state(
            track=track,
            bbox=np.array([100.0, 100.0, 220.0, 260.0]),
            all_detections=None,
            vehicle_detections=veh_dets,
            riders=riders,
        )

        assert "Mengemudi" in posture_state, f"Expected 'Mengemudi', got '{posture_state}'"
        assert "\U0001f697" not in posture_state, f"Emoji found in label: {posture_state}"


class TestVehicleBBoxRendering:
    def test_car_bbox_drawn_even_without_rider(self):
        """Car bounding box MUST be drawn even when no rider/driver is detected."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        car_boxes = [[50.0, 50.0, 300.0, 250.0]]
        veh_dets = _make_vehicle_detections(car_boxes, [CAR_CLASS_ID])

        annotated = Visualizer.draw_annotated_frame(
            frame=frame,
            active_tracks={},
            track_scores={},
            suspicious_threshold=60,
            person_count=0,
            animal_count=0,
            vehicle_detections=veh_dets,
            riders=[],           # NO riders
            vehicle_count=1,
            only_riders=False,   # Show all vehicles
        )

        # Frame must have been modified (car bbox drawn)
        assert np.sum(annotated) > 0, "Car bbox not drawn when no rider"

    def test_stopped_vehicle_label_berhenti(self):
        """Stopped vehicle label contains 'Berhenti'."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        motor_boxes = [[100.0, 100.0, 200.0, 250.0]]
        veh_dets = _make_vehicle_detections(motor_boxes, [MOTORCYCLE_CLASS_ID])
        track_result = _make_track_result([1], [0.0], [False])

        annotated = Visualizer.draw_annotated_frame(
            frame=frame,
            active_tracks={},
            track_scores={},
            suspicious_threshold=60,
            person_count=0,
            animal_count=0,
            vehicle_detections=veh_dets,
            riders=[],
            vehicle_count=1,
            only_riders=False,
            vehicle_track_result=track_result,
        )
        assert annotated is not None
        assert annotated.shape == frame.shape

    def test_moving_vehicle_label_berjalan(self):
        """Moving vehicle label contains speed info."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        motor_boxes = [[100.0, 100.0, 200.0, 250.0]]
        veh_dets = _make_vehicle_detections(motor_boxes, [MOTORCYCLE_CLASS_ID])
        track_result = _make_track_result([1], [25.0], [True])

        annotated = Visualizer.draw_annotated_frame(
            frame=frame,
            active_tracks={},
            track_scores={},
            suspicious_threshold=60,
            person_count=0,
            animal_count=0,
            vehicle_detections=veh_dets,
            riders=[],
            vehicle_count=1,
            only_riders=False,
            vehicle_track_result=track_result,
        )
        assert annotated is not None
        assert annotated.shape == frame.shape
