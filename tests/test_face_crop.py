"""
tests/test_face_crop.py — TDD tests for face crop extraction and visibility validation.
"""
import os
import tempfile
import numpy as np
import pytest

from src.snapshot_scheduler import SnapshotScheduler, crop_face_region


class TestCropFaceRegion:
    def test_crop_face_with_frontal_keypoints_returns_face_slice(self):
        """When frontal keypoints (nose, eyes) have high confidence, returns cropped face."""
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 200
        bbox = [100.0, 50.0, 200.0, 350.0]

        # 17 keypoints with nose (0), left_eye (1), right_eye (2) in head region
        keypoints = np.zeros((17, 3), dtype=float)
        keypoints[0] = [150.0, 80.0, 0.9]   # nose
        keypoints[1] = [140.0, 75.0, 0.85]  # left eye
        keypoints[2] = [160.0, 75.0, 0.85]  # right eye

        face_slice = crop_face_region(frame, bbox, keypoints=keypoints, padding=0.3)
        assert face_slice is not None, "Expected face slice, got None"
        assert face_slice.ndim == 3
        # Face slice must be smaller than the whole human bbox
        assert face_slice.shape[0] < (bbox[3] - bbox[1])
        assert face_slice.shape[1] < (bbox[2] - bbox[0])

    def test_crop_face_with_back_turned_returns_none(self):
        """When suspect is facing away (face keypoints low/zero confidence), returns None."""
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 200
        bbox = [100.0, 50.0, 200.0, 350.0]

        # Keypoints where facial features are not visible (conf < 0.25)
        keypoints = np.zeros((17, 3), dtype=float)
        keypoints[0] = [150.0, 80.0, 0.05]  # nose confidence very low
        keypoints[1] = [140.0, 75.0, 0.1]
        keypoints[2] = [160.0, 75.0, 0.1]
        keypoints[5] = [130.0, 120.0, 0.8]  # shoulders visible from behind
        keypoints[6] = [170.0, 120.0, 0.8]

        face_slice = crop_face_region(frame, bbox, keypoints=keypoints, padding=0.3)
        assert face_slice is None, "Expected None when back is turned, but got image"

    def test_crop_face_boundary_clamped(self):
        """When bbox is at the top/edge of frame, coordinates are safely clamped."""
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 150
        bbox = [0.0, 0.0, 100.0, 200.0]  # At top-left corner
        keypoints = np.zeros((17, 3), dtype=float)
        keypoints[0] = [30.0, 20.0, 0.9]
        keypoints[1] = [20.0, 15.0, 0.9]
        keypoints[2] = [40.0, 15.0, 0.9]

        face_slice = crop_face_region(frame, bbox, keypoints=keypoints, padding=0.5)
        assert face_slice is not None
        assert face_slice.shape[0] > 0
        assert face_slice.shape[1] > 0

    def test_crop_face_empty_or_invalid_returns_none(self):
        """Empty frame or invalid bbox returns None."""
        assert crop_face_region(None, [0, 0, 10, 10]) is None
        frame = np.ones((100, 100, 3), dtype=np.uint8)
        assert crop_face_region(frame, []) is None
        assert crop_face_region(frame, [50, 50, 50, 50]) is None


class TestCaptureFaceCrop:
    def test_capture_face_crop_saves_file(self):
        """capture_face_crop saves file ending with _face.jpg."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = SnapshotScheduler(snapshot_dir=tmpdir, quality=85)
            frame = np.ones((480, 640, 3), dtype=np.uint8) * 180

            scheduler.update_best_frame("cam1", "evt123", frame, confidence=0.9)

            bbox = [100.0, 50.0, 200.0, 350.0]
            keypoints = np.zeros((17, 3), dtype=float)
            keypoints[0] = [150.0, 80.0, 0.9]
            keypoints[1] = [140.0, 75.0, 0.9]
            keypoints[2] = [160.0, 75.0, 0.9]

            path = scheduler.capture_face_crop(
                camera_id="cam1",
                event_id="evt123",
                bbox=bbox,
                keypoints=keypoints,
            )

            assert path is not None
            assert os.path.exists(path)
            assert path.endswith("_face.jpg")

    def test_capture_face_crop_returns_none_when_face_not_visible(self):
        """Returns None if face is not visible."""
        with tempfile.TemporaryDirectory() as tmpdir:
            scheduler = SnapshotScheduler(snapshot_dir=tmpdir, quality=85)
            frame = np.ones((480, 640, 3), dtype=np.uint8) * 180
            scheduler.update_best_frame("cam1", "evt123", frame, confidence=0.9)

            bbox = [100.0, 50.0, 200.0, 350.0]
            keypoints = np.zeros((17, 3), dtype=float)
            # Confidence < 0.25
            keypoints[0] = [150.0, 80.0, 0.1]

            path = scheduler.capture_face_crop(
                camera_id="cam1",
                event_id="evt123",
                bbox=bbox,
                keypoints=keypoints,
            )

            assert path is None
