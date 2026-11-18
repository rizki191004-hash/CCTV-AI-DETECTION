"""
tests/test_human_crop.py — TDD tests for crop_human_region and capture_human_crop.
"""

import os
import shutil
import tempfile
import unittest
import numpy as np

from src.snapshot_scheduler import crop_human_region, SnapshotScheduler


class TestHumanCrop(unittest.TestCase):
    def test_single_bbox_crop_with_padding(self):
        frame = np.zeros((1000, 1000, 3), dtype=np.uint8)
        # Person at [200, 200, 400, 600] (w=200, h=400)
        # 25% padding: pad_w=50, pad_h=100 -> [150, 100, 450, 700]
        # height = 700 - 100 = 600, width = 450 - 150 = 300
        cropped = crop_human_region(frame, [[200, 200, 400, 600]], padding=0.25)
        self.assertEqual(cropped.shape, (600, 300, 3))

    def test_multiple_bboxes_union(self):
        frame = np.zeros((1000, 1000, 3), dtype=np.uint8)
        # Two people: [100, 100, 200, 300] and [400, 200, 500, 400]
        # Union: [100, 100, 500, 400] (w=400, h=300)
        # 25% padding: pad_w=100, pad_h=75 -> [0, 25, 600, 475]
        # height = 475 - 25 = 450, width = 600 - 0 = 600
        cropped = crop_human_region(
            frame,
            [[100, 100, 200, 300], [400, 200, 500, 400]],
            padding=0.25,
        )
        self.assertEqual(cropped.shape, (450, 600, 3))

    def test_empty_bboxes_returns_original(self):
        frame = np.zeros((500, 500, 3), dtype=np.uint8)
        cropped = crop_human_region(frame, [], padding=0.25)
        self.assertEqual(cropped.shape, (500, 500, 3))

    def test_padding_clamps_to_boundaries(self):
        frame = np.zeros((500, 500, 3), dtype=np.uint8)
        # Person near top-left: [10, 10, 100, 100] -> padded coordinates would be negative
        cropped = crop_human_region(frame, [[10, 10, 100, 100]], padding=0.5)
        self.assertGreater(cropped.shape[0], 0)
        self.assertGreater(cropped.shape[1], 0)
        self.assertLessEqual(cropped.shape[0], 500)
        self.assertLessEqual(cropped.shape[1], 500)

    def test_capture_human_crop_saves_file(self):
        temp_dir = tempfile.mkdtemp()
        try:
            scheduler = SnapshotScheduler(snapshot_dir=temp_dir, quality=80)
            frame = np.ones((800, 800, 3), dtype=np.uint8) * 128
            crop_path = scheduler.capture_human_crop(
                camera_id="cam_01",
                event_id="evt_12345678",
                bboxes=[[100, 100, 300, 500]],
                frame_override=frame,
                padding=0.2,
            )
            self.assertIsNotNone(crop_path)
            self.assertTrue(os.path.exists(crop_path))
            self.assertIn("_crop", crop_path)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

