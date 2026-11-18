"""
tests/test_vehicle_bbox_optimization.py
TDD for Vehicle BBox Optimization and Snapshot Synchronization.
"""
import numpy as np
import pytest
import supervision as sv

from src.vehicle_detector import (
    CAR_CLASS_ID,
    MOTORCYCLE_CLASS_ID,
    RiderInfo,
    VehicleDetector,
)
from src.visualizer import Visualizer


class TestVehicleBboxOptimization:
    def test_filter_small_distant_vehicles(self):
        """VehicleDetector should filter out tiny distant boxes (e.g. area < min_area)."""
        detector = VehicleDetector(min_area=1200, min_dimension=35)
        
        # Create mock detections with 1 large vehicle and 1 tiny distant vehicle
        boxes = np.array([
            [100.0, 100.0, 250.0, 220.0],  # w=150, h=120, area=18000 -> KEEP
            [500.0, 50.0, 520.0, 65.0],    # w=20, h=15, area=300 -> DISCARD (too small)
            [300.0, 300.0, 310.0, 450.0],  # w=10, h=150, area=1500, but w < 35 -> DISCARD (too narrow)
        ])
        class_ids = np.array([CAR_CLASS_ID, MOTORCYCLE_CLASS_ID, CAR_CLASS_ID])
        confidences = np.array([0.85, 0.70, 0.80])
        
        raw_detections = sv.Detections(
            xyxy=boxes,
            confidence=confidences,
            class_id=class_ids,
        )
        
        filtered = detector.filter_vehicles(raw_detections)
        assert len(filtered) == 1
        assert np.allclose(filtered.xyxy[0], [100.0, 100.0, 250.0, 220.0])

    def test_visualizer_only_draws_riders_when_only_riders_enabled(self):
        """Visualizer should only draw vehicle bounding boxes for vehicles that have riders."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 2 vehicles: motorcycle (with rider) and car (empty parked)
        veh_boxes = np.array([
            [50.0, 50.0, 150.0, 150.0],   # idx 0: motorcycle
            [300.0, 300.0, 500.0, 450.0], # idx 1: car (empty)
        ])
        veh_detections = sv.Detections(
            xyxy=veh_boxes,
            class_id=np.array([MOTORCYCLE_CLASS_ID, CAR_CLASS_ID]),
            confidence=np.array([0.9, 0.85]),
        )
        
        # Rider on vehicle 0
        riders = [
            RiderInfo(
                person_idx=0,
                vehicle_idx=0,
                vehicle_class=MOTORCYCLE_CLASS_ID,
                iou=0.45,
            )
        ]
        
        # Draw with only_riders=True (default clean mode)
        annotated = Visualizer.draw_annotated_frame(
            frame=frame,
            active_tracks={},
            track_scores={},
            suspicious_threshold=60,
            person_count=1,
            animal_count=0,
            vehicle_detections=veh_detections,
            riders=riders,
            vehicle_count=2,
            only_riders=True,
        )
        
        # Frame should be modified (drawn)
        assert annotated is not None
        assert not np.array_equal(annotated, frame)
        
        # In the region of the empty car (x: 310..490, y: 310..440), it should be black (no box drawn)
        inner_empty_car = annotated[320:430, 320:480]
        assert np.sum(inner_empty_car) == 0, "Empty vehicle should not be drawn when only_riders=True"

    def test_snapshot_scheduler_crop_before_pop(self):
        """SnapshotScheduler can produce human crop and full snapshot without losing buffer."""
        from src.snapshot_scheduler import SnapshotScheduler
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = SnapshotScheduler(snapshot_dir=tmpdir)
            test_frame = np.full((480, 640, 3), 128, dtype=np.uint8)
            
            # Put test pattern in center for person
            test_frame[100:300, 200:400] = 255
            
            scheduler.update_best_frame("cam1", "evt1", test_frame, 0.95)
            
            # Both capture_human_crop and capture_snapshot should succeed
            crop_path = scheduler.capture_human_crop(
                camera_id="cam1",
                event_id="evt1",
                bboxes=[[200, 100, 400, 300]],
            )
            assert crop_path is not None
            
            full_path = scheduler.capture_snapshot(
                camera_id="cam1",
                event_id="evt1",
            )
            assert full_path is not None

