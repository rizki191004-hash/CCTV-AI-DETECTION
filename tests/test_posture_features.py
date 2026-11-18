import unittest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.feature_extractor import FeatureExtractor, TrackFeatures

class TestPostureFeatures(unittest.TestCase):
    def test_horizontal_torso_classified_as_fallen(self):
        # 17 COCO keypoints: shoulders at 5,6 and hips at 11,12
        keypoints = np.zeros((17, 2), dtype=np.float32)
        conf = np.ones((17,), dtype=np.float32)
        # Shoulders (x=100, y=200), (x=120, y=200) -> midpoint (110, 200)
        keypoints[5] = [100, 200]
        keypoints[6] = [120, 200]
        # Hips (x=280, y=205), (x=300, y=205) -> midpoint (290, 205) [Horizontal orientation: dx=180, dy=5]
        keypoints[11] = [280, 205]
        keypoints[12] = [300, 205]
        
        posture, angle = FeatureExtractor.analyze_posture(keypoints, conf, bbox=(90, 180, 310, 220))
        self.assertEqual(posture, "FALLEN_HORIZONTAL")
        self.assertGreater(angle, 70.0)

    def test_upright_torso_classified_as_standing(self):
        keypoints = np.zeros((17, 2), dtype=np.float32)
        conf = np.ones((17,), dtype=np.float32)
        # Shoulders at y=100
        keypoints[5] = [95, 100]
        keypoints[6] = [105, 100]
        # Hips at y=250 (Vertical orientation: dx=0, dy=150)
        keypoints[11] = [95, 250]
        keypoints[12] = [105, 250]
        # Knees at y=350, ankles at y=450
        keypoints[13] = [95, 350]
        keypoints[14] = [105, 350]
        keypoints[15] = [95, 450]
        keypoints[16] = [105, 450]

        posture, angle = FeatureExtractor.analyze_posture(keypoints, conf, bbox=(90, 90, 110, 460))
        self.assertEqual(posture, "STANDING")
        self.assertLess(angle, 25.0)

    def test_crouching_classified_when_compressed(self):
        keypoints = np.zeros((17, 2), dtype=np.float32)
        conf = np.ones((17,), dtype=np.float32)
        # Shoulders
        keypoints[5] = [95, 120]
        keypoints[6] = [105, 120]
        # Hips
        keypoints[11] = [95, 180]
        keypoints[12] = [105, 180]
        # Knees bent close to hips
        keypoints[13] = [95, 195]
        keypoints[14] = [105, 195]

        posture, angle = FeatureExtractor.analyze_posture(keypoints, conf, bbox=(85, 110, 115, 210))
        self.assertEqual(posture, "CROUCHING_CRAWLING")

if __name__ == "__main__":
    unittest.main()

