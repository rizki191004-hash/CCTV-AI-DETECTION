import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.rule_engine import RuleEngine
from src.config_loader import Rule, RuleCondition
from src.feature_extractor import TrackFeatures, SceneFeatures

class TestPoseRules(unittest.TestCase):
    def test_fall_detected_rule_triggers_critical_alert(self):
        rule = Rule(
            id="fall_detected",
            enabled=True,
            condition=RuleCondition(type="fall_detected"),
            score_delta=85.0,
            cooldown_sec=120,
            critical=True,
            reason="Terdeteksi jatuh"
        )
        engine = RuleEngine(rules=[rule], suspicious_threshold=70.0, critical_threshold=80.0)
        
        # Test with is_fall_detected=True
        features = TrackFeatures(track_id=1, is_fall_detected=True, posture_state="FALLEN_HORIZONTAL")
        results = engine.evaluate(track_features={1: features}, scene_features=SceneFeatures())
        
        self.assertIn(1, results)
        score = results[1]
        self.assertTrue(score.has_critical)
        self.assertTrue(score.is_suspicious)
        self.assertIn("fall_detected", score.triggered_rules)
        self.assertEqual(score.total_score, 85.0)

    def test_suspicious_crouching_rule_triggers(self):
        rule = Rule(
            id="suspicious_crouching",
            enabled=True,
            condition=RuleCondition(type="posture_state", params={"state": "CROUCHING_CRAWLING"}),
            score_delta=45.0,
            cooldown_sec=45,
            critical=False,
            reason="Postur merayap / jongkok"
        )
        engine = RuleEngine(rules=[rule], suspicious_threshold=70.0, critical_threshold=80.0)
        
        features = TrackFeatures(track_id=2, posture_state="CROUCHING_CRAWLING")
        results = engine.evaluate(track_features={2: features}, scene_features=SceneFeatures())
        
        self.assertIn(2, results)
        score = results[2]
        self.assertFalse(score.has_critical)
        self.assertIn("suspicious_crouching", score.triggered_rules)
        self.assertEqual(score.total_score, 45.0)

if __name__ == "__main__":
    unittest.main()
