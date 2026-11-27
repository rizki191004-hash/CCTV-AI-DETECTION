"""
tests/test_vehicle_no_spam.py
TDD tests for anti-spam gate: stationary vehicles must NOT trigger Telegram alert.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np
import pytest

from src.vehicle_tracker import VehicleTracker, VehicleTrackResult


class TestAntiSpamGate:
    def test_stationary_vehicle_does_not_set_vehicle_event_pending(self):
        """When all vehicles are stopped, any_moving=False => no Telegram alert."""
        result = VehicleTrackResult(
            tracked_vehicles=MagicMock(),
            vehicle_speeds={1: 0.0, 2: 0.0},
            vehicle_moving={1: False, 2: False},
            vehicle_speed_kmh={1: 0.0, 2: 0.0},
        )
        assert result.any_moving is False, \
            "All stopped vehicles should have any_moving=False"

    def test_moving_vehicle_sets_vehicle_event_pending(self):
        """When at least one vehicle is moving, any_moving=True => Telegram alert allowed."""
        result = VehicleTrackResult(
            tracked_vehicles=MagicMock(),
            vehicle_speeds={1: 0.0, 2: 45.0},
            vehicle_moving={1: False, 2: True},
            vehicle_speed_kmh={1: 0.0, 2: 45.0},
        )
        assert result.any_moving is True, \
            "Moving vehicle should set any_moving=True"

    def test_all_moving_vehicles_sets_any_moving(self):
        """All vehicles moving => any_moving=True."""
        result = VehicleTrackResult(
            tracked_vehicles=MagicMock(),
            vehicle_speeds={1: 30.0},
            vehicle_moving={1: True},
            vehicle_speed_kmh={1: 30.0},
        )
        assert result.any_moving is True

    def test_empty_vehicle_result_any_moving_false(self):
        """No vehicles => any_moving=False (no alert)."""
        result = VehicleTrackResult(
            tracked_vehicles=MagicMock(),
            vehicle_speeds={},
            vehicle_moving={},
            vehicle_speed_kmh={},
        )
        assert result.any_moving is False


class TestVehicleAlertGateIntegration:
    def test_vehicle_alert_requires_moving_flag(self):
        """The pipeline should only trigger vehicle alert when any_moving=True."""
        # Simulate pipeline logic: vehicle_event_pending set only if any_moving
        def should_trigger_vehicle_alert(track_result: VehicleTrackResult) -> bool:
            return track_result.any_moving

        stopped_result = VehicleTrackResult(
            tracked_vehicles=MagicMock(),
            vehicle_speeds={1: 0.0},
            vehicle_moving={1: False},
            vehicle_speed_kmh={1: 0.0},
        )
        moving_result = VehicleTrackResult(
            tracked_vehicles=MagicMock(),
            vehicle_speeds={1: 32.0},
            vehicle_moving={1: True},
            vehicle_speed_kmh={1: 32.0},
        )

        assert should_trigger_vehicle_alert(stopped_result) is False
        assert should_trigger_vehicle_alert(moving_result) is True
