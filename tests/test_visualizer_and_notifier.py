import unittest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.telegram_notifier import TelegramNotifier
from src.visualizer import Visualizer

class TestVisualizerAndNotifier(unittest.TestCase):
    def test_telegram_message_contains_fall_emergency_header(self):
        notifier = TelegramNotifier(bot_token="dummy_token", chat_id="123456")
        caption = notifier.format_alert_caption(
            camera_name="CAM-01 DEPAN",
            score=85.0,
            triggered_rules=["fall_detected"],
            track_ids=[1],
            event_id="abcdef123456",
            alert_level="CRITICAL",
            posture="FALLEN_HORIZONTAL"
        )
        self.assertIn("FALL DETECTED / DARURAT", caption)
        self.assertIn("Postur:", caption)
        self.assertIn("FALLEN\\_HORIZONTAL", caption)

    def test_visualizer_draw_skeleton_executes_without_error(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        keypoints = np.zeros((17, 2), dtype=np.float32)
        # Shoulders and hips
        keypoints[5] = [200, 200]
        keypoints[6] = [240, 200]
        keypoints[11] = [200, 300]
        keypoints[12] = [240, 300]
        
        annotated = Visualizer.draw_skeleton(frame, keypoints, color=(0, 0, 255))
        self.assertEqual(annotated.shape, (480, 640, 3))
        # Verify pixels were drawn (not all zeros)
        self.assertGreater(np.sum(annotated), 0)

if __name__ == "__main__":
    unittest.main()
