import unittest
import numpy as np
import sys
import os
from collections import deque

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.alarm_gate import AlarmGate
from src.tracker import TrackHistory, TrackPoint

class TestAlarmGateFall(unittest.TestCase):
    def test_horizontal_fallen_person_passes_aspect_gate(self):
        gate = AlarmGate(confidence_gate=0.5, min_frames=1, min_bbox_area=400)
        
        # 17 keypoints horizontally oriented
        keypoints = np.zeros((17, 2), dtype=np.float32)
        keypoints[5] = [100, 200]
        keypoints[6] = [120, 200]
        keypoints[11] = [280, 205]
        keypoints[12] = [300, 205]

        # Horizontal bbox: w=250, h=60 -> aspect_ratio = 60/250 = 0.24 (< MIN_HUMAN_ASPECT 0.4)
        bbox = (50.0, 180.0, 300.0, 240.0)
        point = TrackPoint(timestamp=100.0, centroid=(175.0, 210.0), bbox=bbox, confidence=0.85, keypoints=keypoints)
        
        track = TrackHistory(track_id=1, first_seen=100.0, last_seen=100.0)
        track.points.append(point)

        validation = gate.validate_track(track, frame_shape=(720, 1280))
        self.assertTrue(validation.passed, f"Fallen person was rejected: {validation.rejection_reason}")
        self.assertTrue(validation.aspect_ratio_ok)

if __name__ == "__main__":
    unittest.main()
