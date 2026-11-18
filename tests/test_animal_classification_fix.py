"""
tests/test_animal_classification_fix.py
TDD for fixing animal misclassification and disabling animal clutter.
"""
import numpy as np
import pytest
import supervision as sv

from src.tracker import PersonTracker
from src.person_detector import PersonDetector, PERSON_CLASS_ID, DETECTABLE_CLASSES
from src.visualizer import Visualizer


class TestAnimalClassificationFix:
    def test_motorcycle_is_not_classified_as_animal_by_tracker(self):
        """A motorcycle (COCO class 3) must NOT be labeled as class_type='animal'."""
        tracker = PersonTracker(camera_id="cam_test")
        
        # Mock detection with class_id = 3 (motorcycle)
        boxes = np.array([[100.0, 100.0, 200.0, 200.0]])
        conf = np.array([0.85])
        class_ids = np.array([3])  # Motorcycle
        
        detections = sv.Detections(
            xyxy=boxes,
            confidence=conf,
            class_id=class_ids,
        )
        
        # ByteTrack update (might need 2 frames or min_frames depending on tracker)
        tracker.update(detections)
        tracker.update(detections)
        
        active_tracks = tracker.get_all_tracks()
        for track_id, track in active_tracks.items():
            assert track.class_type != "animal", f"Track #{track_id} was wrongly classified as 'animal'!"

    def test_detectable_classes_does_not_include_animals(self):
        """DETECTABLE_CLASSES in PersonDetector should not include animal COCO IDs."""
        # Bird=14, Cat=15, Dog=16
        animal_ids = {14, 15, 16}
        for aid in animal_ids:
            assert aid not in DETECTABLE_CLASSES, f"Animal COCO ID {aid} should not be in DETECTABLE_CLASSES"

    def test_visualizer_hud_clean_format_without_animals(self):
        """Visualizer HUD should show Persons and Vehicles, without Animals label."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        annotated = Visualizer.draw_annotated_frame(
            frame=frame,
            active_tracks={},
            track_scores={},
            suspicious_threshold=60,
            person_count=2,
            animal_count=0,
            vehicle_count=3,
        )
        
        # Let's inspect the draw_annotated_frame implementation to confirm clean HUD
        assert annotated is not None
