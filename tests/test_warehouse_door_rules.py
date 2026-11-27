"""
tests/test_warehouse_door_rules.py — TDD tests for warehouse goods-taking and door rules.
"""
import pytest
from src.config_loader import Rule, RuleCondition
from src.feature_extractor import TrackFeatures, SceneFeatures
from src.rule_engine import RuleEngine


class TestWarehouseDoorRules:
    def test_warehouse_taking_goods_rule_triggers(self):
        """Person crouching in warehouse/storage zone triggers warehouse_taking_goods rule."""
        rule = Rule(
            id="warehouse_taking_goods",
            enabled=True,
            condition=RuleCondition(
                type="warehouse_taking_goods",
                params={"zone": "warehouse_zone"},
            ),
            score_delta=60,
            cooldown_sec=0,
            critical=False,
            reason="Terindikasi mengambil barang di gudang (merunduk)",
        )
        engine = RuleEngine([rule], suspicious_threshold=60)

        # 1. Matching case: crouching in warehouse
        tf_match = TrackFeatures(
            track_id=1,
            current_zones={"warehouse_zone"},
            posture_state="CROUCHING_CRAWLING",
        )
        scene = SceneFeatures()
        res_match = engine.evaluate({1: tf_match}, scene)
        assert res_match[1].total_score >= 60
        assert "warehouse_taking_goods" in res_match[1].triggered_rules

        # 2. Non-matching case: standing in warehouse
        tf_standing = TrackFeatures(
            track_id=2,
            current_zones={"warehouse_zone"},
            posture_state="STANDING",
        )
        res_standing = engine.evaluate({2: tf_standing}, scene)
        assert res_standing[2].total_score == 0
        assert "warehouse_taking_goods" not in res_standing[2].triggered_rules

    def test_warehouse_rapid_departure_rule_triggers(self):
        """Fast departure (speed >= 120 px/s) within 5s of crouching triggers rapid departure."""
        rule = Rule(
            id="warehouse_rapid_departure",
            enabled=True,
            condition=RuleCondition(
                type="warehouse_rapid_departure",
                params={"min_speed": 120.0, "max_sec": 5.0},
            ),
            score_delta=30,
            cooldown_sec=0,
            critical=False,
            reason="Kabur cepat setelah merunduk di gudang",
        )
        engine = RuleEngine([rule], suspicious_threshold=60)

        # 1. Matching case: speed=150 px/s and time_since_crouch_sec=2.0
        tf_fast = TrackFeatures(
            track_id=1,
            speed_px_per_sec=150.0,
            time_since_crouch_sec=2.0,
        )
        scene = SceneFeatures()
        res_fast = engine.evaluate({1: tf_fast}, scene)
        assert "warehouse_rapid_departure" in res_fast[1].triggered_rules

        # 2. Non-matching case: fast speed but no recent crouch (time_since_crouch_sec = 999)
        tf_normal_fast = TrackFeatures(
            track_id=2,
            speed_px_per_sec=150.0,
            time_since_crouch_sec=999.0,
        )
        res_normal = engine.evaluate({2: tf_normal_fast}, scene)
        assert "warehouse_rapid_departure" not in res_normal[2].triggered_rules

    def test_gate_door_loitering_triggers(self):
        """Loitering at gate/door zone triggers loitering rule."""
        rule = Rule(
            id="gate_door_loitering",
            enabled=True,
            condition=RuleCondition(
                type="dwell_time",
                params={"zone": "door_zone", "min_sec": 15},
            ),
            score_delta=35,
            cooldown_sec=0,
            critical=False,
            reason="Berdiam lama di area pintu/gerbang",
        )
        engine = RuleEngine([rule], suspicious_threshold=35)

        tf = TrackFeatures(
            track_id=1,
            current_zones={"door_zone"},
            dwell_time_sec=20.0,
        )
        scene = SceneFeatures()
        res = engine.evaluate({1: tf}, scene)
        assert "gate_door_loitering" in res[1].triggered_rules
