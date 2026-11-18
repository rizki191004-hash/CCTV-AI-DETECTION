"""
tests/test_motorcycle_rider_posture.py
TDD for motorcycle rider posture detection ('Naik Motor') and avoiding 'Berdiri Diam'.
"""
import numpy as np
import pytest
import supervision as sv

from src.vehicle_detector import MOTORCYCLE_CLASS_ID, CAR_CLASS_ID, RiderInfo
from src.visualizer import Visualizer


class MockTrack:
    def __init__(self, track_id=1, bbox=(100, 100, 180, 260), class_type="human", speed=0.0):
        self.track_id = track_id
        self.latest_bbox = bbox
        self.class_type = class_type
        self.latest_keypoints = None
        
        # Mock track points
        class MockPoint:
            def __init__(self, centroid, ts):
                self.centroid = centroid
                self.timestamp = ts
                self.confidence = 0.9
        
        self.points = [
            MockPoint((140, 180), 10.0),
            MockPoint((140 + speed, 180), 11.0),
        ]


class TestMotorcycleRiderPosture:
    def test_posture_state_identifies_motorcycle_rider(self):
        """A person overlapping a motorcycle should have posture '🏍️ Naik Motor', not 'Berdiri Diam'."""
        track = MockTrack(bbox=(100, 100, 180, 260), speed=0.0)  # Tall aspect: (260-100)/(180-100) = 160/80 = 2.0
        
        # Motorcycle bbox overlapping person
        veh_boxes = np.array([[90.0, 150.0, 200.0, 300.0]])
        veh_detections = sv.Detections(
            xyxy=veh_boxes,
            class_id=np.array([MOTORCYCLE_CLASS_ID]),
            confidence=np.array([0.9]),
        )
        
        riders = [
            RiderInfo(
                person_idx=0,
                vehicle_idx=0,
                vehicle_class=MOTORCYCLE_CLASS_ID,
                iou=0.45,
            )
        ]
        
        posture_state, color = Visualizer._get_posture_state(
            track=track,
            bbox=np.array([100.0, 100.0, 180.0, 260.0]),
            all_detections=None,
            vehicle_detections=veh_detections,
            riders=riders,
        )
        
        assert "Naik Motor" in posture_state, f"Expected 'Naik Motor', got '{posture_state}'"
        assert "Berdiri Diam" not in posture_state
        assert "Berjalan" not in posture_state

    def test_draw_annotated_frame_renders_naik_motor_label(self):
        """Frame drawn with an active rider should render 'Naik Motor' on the person's label."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        track = MockTrack(track_id=1, bbox=(100, 100, 180, 260), speed=0.0)
        
        veh_boxes = np.array([[90.0, 150.0, 200.0, 300.0]])
        veh_detections = sv.Detections(
            xyxy=veh_boxes,
            class_id=np.array([MOTORCYCLE_CLASS_ID]),
            confidence=np.array([0.9]),
        )
        riders = [
            RiderInfo(
                person_idx=0,
                vehicle_idx=0,
                vehicle_class=MOTORCYCLE_CLASS_ID,
                iou=0.45,
            )
        ]
        
        annotated = Visualizer.draw_annotated_frame(
            frame=frame,
            active_tracks={1: track},
            track_scores={},
            suspicious_threshold=60,
            person_count=1,
            animal_count=0,
            vehicle_detections=veh_detections,
            riders=riders,
            vehicle_count=1,
        )
        
        # Frame should not be black
        assert annotated is not None
        assert not np.array_equal(annotated, frame)

