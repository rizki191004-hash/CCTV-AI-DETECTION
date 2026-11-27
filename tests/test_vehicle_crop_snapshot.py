"""
tests/test_vehicle_crop_snapshot.py
TDD tests for vehicle-focused crop snapshots.
"""
import os
import tempfile
import numpy as np
import pytest

from src.snapshot_scheduler import SnapshotScheduler, crop_vehicle_region


class TestCropVehicleRegion:
    def test_crop_returns_correct_region(self):
        """crop_vehicle_region should return a subregion of the frame."""
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        bboxes = [[100.0, 50.0, 300.0, 250.0]]
        cropped = crop_vehicle_region(frame, bboxes, padding=0.1)
        assert cropped is not None
        assert cropped.ndim == 3
        # Cropped must be smaller than original frame
        assert cropped.shape[0] <= frame.shape[0]
        assert cropped.shape[1] <= frame.shape[1]

    def test_crop_with_multiple_vehicles(self):
        """Should union all vehicle bboxes and crop the combined region."""
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        bboxes = [[50.0, 50.0, 150.0, 150.0], [300.0, 200.0, 450.0, 350.0]]
        cropped = crop_vehicle_region(frame, bboxes, padding=0.1)
        assert cropped is not None
        assert cropped.ndim == 3

    def test_crop_empty_bboxes_returns_copy(self):
        """Empty bboxes should return full frame copy."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cropped = crop_vehicle_region(frame, [], padding=0.1)
        assert cropped.shape == frame.shape

    def test_crop_clamped_to_frame_boundaries(self):
        """Padded crop should not exceed frame dimensions."""
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        bboxes = [[80.0, 80.0, 99.0, 99.0]]  # Near edge
        cropped = crop_vehicle_region(frame, bboxes, padding=0.5)
        assert cropped.shape[0] <= 100
        assert cropped.shape[1] <= 100


class TestCaptureVehicleCrop:
    def test_capture_vehicle_crop_saves_file(self):
        """capture_vehicle_crop() should save a file and return its path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = SnapshotScheduler(snapshot_dir=tmpdir, quality=85)
            frame = np.random.randint(100, 200, (480, 640, 3), dtype=np.uint8)

            # Update best frame buffer
            scheduler.update_best_frame("cam1", "evt001", frame, confidence=0.9)

            vehicle_bboxes = [[100.0, 100.0, 300.0, 300.0]]
            path = scheduler.capture_vehicle_crop(
                camera_id="cam1",
                event_id="evt001",
                vehicle_bboxes=vehicle_bboxes,
                padding=0.1,
            )

            assert path is not None, "capture_vehicle_crop returned None"
            assert os.path.exists(path), f"File not found: {path}"
            assert path.endswith(".jpg")

    def test_capture_vehicle_crop_with_frame_override(self):
        """Should use frame_override when provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = SnapshotScheduler(snapshot_dir=tmpdir, quality=85)
            frame = np.random.randint(50, 150, (480, 640, 3), dtype=np.uint8)

            vehicle_bboxes = [[50.0, 50.0, 200.0, 200.0]]
            path = scheduler.capture_vehicle_crop(
                camera_id="cam2",
                event_id="evt002",
                vehicle_bboxes=vehicle_bboxes,
                frame_override=frame,
                padding=0.15,
            )
            assert path is not None
            assert os.path.exists(path)

    def test_capture_vehicle_crop_no_frame_returns_none(self):
        """Returns None if no frame buffered and no override given."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = SnapshotScheduler(snapshot_dir=tmpdir)
            path = scheduler.capture_vehicle_crop(
                camera_id="cam3",
                event_id="evt003",
                vehicle_bboxes=[[100.0, 100.0, 200.0, 200.0]],
            )
            assert path is None

    def test_vehicle_crop_filename_contains_vcrop(self):
        """Vehicle crop filename should include '_vcrop' marker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = SnapshotScheduler(snapshot_dir=tmpdir)
            frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
            scheduler.update_best_frame("cam1", "evtabc", frame, confidence=0.8)
            path = scheduler.capture_vehicle_crop(
                camera_id="cam1",
                event_id="evtabc",
                vehicle_bboxes=[[10.0, 10.0, 200.0, 200.0]],
            )
            assert path is not None
            assert "vcrop" in os.path.basename(path), f"'vcrop' not in filename: {path}"
