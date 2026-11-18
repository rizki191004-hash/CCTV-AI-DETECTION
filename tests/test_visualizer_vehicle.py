"""
tests/test_visualizer_vehicle.py – Tests for vehicle visualization and HUD overlay
"""

import unittest
import numpy as np
import supervision as sv
from src.visualizer import Visualizer, MOTORCYCLE_CLASS_ID, CAR_CLASS_ID
from src.vehicle_detector import RiderInfo


class TestVisualizerVehicle(unittest.TestCase):
    def test_draw_annotated_frame_with_vehicles_and_rider(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 1 motorcycle detection
        boxes = np.array([[100, 100, 200, 200]], dtype=np.float32)
        classes = np.array([MOTORCYCLE_CLASS_ID], dtype=int)
        confidences = np.array([0.9], dtype=np.float32)
        vehicle_detections = sv.Detections(
            xyxy=boxes,
            confidence=confidences,
            class_id=classes,
        )

        riders = [
            RiderInfo(
                person_idx=0,
                vehicle_idx=0,
                vehicle_class=MOTORCYCLE_CLASS_ID,
                iou=0.35,
            )
        ]

        annotated = Visualizer.draw_annotated_frame(
            frame=frame,
            active_tracks={},
            track_scores={},
            suspicious_threshold=70.0,
            person_count=1,
            animal_count=0,
            all_detections=None,
            vehicle_detections=vehicle_detections,
            riders=riders,
            vehicle_count=1,
        )

        self.assertEqual(annotated.shape, frame.shape)
        # Verify that frame has been modified (not pure black)
        self.assertGreater(np.sum(annotated), 0)


if __name__ == "__main__":
    unittest.main()

