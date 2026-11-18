"""
tests/test_vehicle_detector.py – TDD tests for VehicleDetector

Tests:
  1. VehicleDetector can be imported and instantiated (lazy model load)
  2. find_riders returns match when IoU >= 0.15
  3. find_riders returns empty when IoU < 0.15
  4. find_riders returns empty when no vehicles
  5. VehicleDetectionResult has correct fields
"""

import unittest
import numpy as np


class TestFindRiders(unittest.TestCase):
    """Unit tests for VehicleDetector.find_riders() — pure logic, no model needed."""

    def setUp(self):
        from src.vehicle_detector import VehicleDetector, VehicleDetectionResult
        self.VehicleDetector = VehicleDetector
        self.VehicleDetectionResult = VehicleDetectionResult

    def _make_detections(self, boxes, class_ids):
        """Helper: build sv.Detections from raw boxes and class ids."""
        import supervision as sv
        if not boxes:
            return sv.Detections.empty()
        return sv.Detections(
            xyxy=np.array(boxes, dtype=np.float32),
            class_id=np.array(class_ids, dtype=int),
            confidence=np.ones(len(boxes), dtype=np.float32),
        )

    def test_find_riders_overlap_above_threshold(self):
        """When person bbox significantly overlaps motorcycle bbox, rider is detected."""
        # Person sitting on motorcycle — large overlap
        person_box = [100, 100, 200, 250]  # person bbox
        moto_box   = [90, 150, 210, 300]   # motorcycle bbox overlapping lower half

        persons  = self._make_detections([person_box], [0])    # class 0 = person
        vehicles = self._make_detections([moto_box],  [3])    # class 3 = motorcycle

        riders = self.VehicleDetector.find_riders(persons, vehicles, iou_threshold=0.15)
        self.assertGreater(len(riders), 0, "Should detect a rider when IoU >= 0.15")
        self.assertEqual(riders[0].vehicle_class, 3)

    def test_find_riders_no_overlap(self):
        """When person and vehicle bboxes don't overlap, no rider detected."""
        person_box  = [0,   0,  50,  50]   # top-left
        moto_box    = [300, 300, 400, 400]  # far bottom-right

        persons  = self._make_detections([person_box], [0])
        vehicles = self._make_detections([moto_box],  [3])

        riders = self.VehicleDetector.find_riders(persons, vehicles, iou_threshold=0.15)
        self.assertEqual(len(riders), 0, "Should not detect rider when no overlap")

    def test_find_riders_low_iou_below_threshold(self):
        """When overlap is present but below threshold (< 0.15), no rider detected."""
        # Minimal corner overlap — IoU will be ~0.01
        person_box = [0,   0,  100, 100]
        moto_box   = [95, 95,  200, 200]

        persons  = self._make_detections([person_box], [0])
        vehicles = self._make_detections([moto_box],  [3])

        riders = self.VehicleDetector.find_riders(persons, vehicles, iou_threshold=0.15)
        self.assertEqual(len(riders), 0, "Should not detect rider when IoU < threshold")

    def test_find_riders_no_vehicles(self):
        """When no vehicles in frame, find_riders returns empty list."""
        import supervision as sv
        person_box = [100, 100, 200, 250]
        persons  = self._make_detections([person_box], [0])
        vehicles = sv.Detections.empty()

        riders = self.VehicleDetector.find_riders(persons, vehicles, iou_threshold=0.15)
        self.assertEqual(len(riders), 0)

    def test_find_riders_no_persons(self):
        """When no persons in frame, find_riders returns empty list."""
        import supervision as sv
        moto_box = [100, 100, 200, 250]
        persons  = sv.Detections.empty()
        vehicles = self._make_detections([moto_box], [3])

        riders = self.VehicleDetector.find_riders(persons, vehicles, iou_threshold=0.15)
        self.assertEqual(len(riders), 0)

    def test_car_class_detected_as_vehicle(self):
        """Car (COCO class 2) is included in vehicle detection."""
        person_box = [100, 100, 200, 250]
        car_box    = [90,  120, 210, 300]

        persons  = self._make_detections([person_box], [0])
        vehicles = self._make_detections([car_box],   [2])  # class 2 = car

        riders = self.VehicleDetector.find_riders(persons, vehicles, iou_threshold=0.15)
        self.assertGreater(len(riders), 0)
        self.assertEqual(riders[0].vehicle_class, 2)

    def test_vehicle_detection_result_fields(self):
        """VehicleDetectionResult has expected fields."""
        import supervision as sv
        result = self.VehicleDetectionResult(
            vehicles=sv.Detections.empty(),
            vehicle_count=0,
            riders=[],
        )
        self.assertEqual(result.vehicle_count, 0)
        self.assertEqual(result.riders, [])


class TestVehicleDetectorImport(unittest.TestCase):
    """Smoke test: module imports without error."""

    def test_import(self):
        """VehicleDetector can be imported."""
        from src.vehicle_detector import VehicleDetector, VehicleDetectionResult  # noqa: F401


if __name__ == "__main__":
    unittest.main()
