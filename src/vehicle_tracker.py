"""
vehicle_tracker.py — ByteTrack-based vehicle tracker with speed estimation and hysteresis.

Assigns persistent IDs to vehicles (cars & motorcycles), tracks position history,
computes smoothed speed (px/s and km/h), and determines whether a vehicle is moving
or stationary with hysteresis to avoid bounding box jitter.
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple

import numpy as np
import supervision as sv

logger = logging.getLogger(__name__)


@dataclass
class VehicleTrackPoint:
    centroid: Tuple[float, float]
    bbox: Tuple[float, float, float, float]
    timestamp: float


@dataclass
class VehicleTrackHistory:
    track_id: int
    class_id: int = 3  # default MOTORCYCLE_CLASS_ID
    points: Deque[VehicleTrackPoint] = field(default_factory=lambda: deque(maxlen=60))
    moving_confirm_count: int = 0
    stopped_confirm_count: int = 0
    is_moving: bool = False
    speed_px_s: float = 0.0
    speed_kmh: float = 0.0


@dataclass
class VehicleTrackResult:
    """Result of vehicle tracking for a single frame."""
    tracked_vehicles: sv.Detections
    vehicle_speeds: Dict[int, float] = field(default_factory=dict)
    vehicle_moving: Dict[int, bool] = field(default_factory=dict)
    vehicle_speed_kmh: Dict[int, float] = field(default_factory=dict)

    @property
    def any_moving(self) -> bool:
        """Returns True if at least one tracked vehicle is currently moving."""
        return any(self.vehicle_moving.values())


class VehicleTracker:
    """
    ByteTrack wrapper dedicated to vehicles.
    Maintains persistent IDs, tracks movement trajectory, calculates smoothed speed,
    and classifies movement with hysteresis.
    """

    def __init__(
        self,
        camera_id: str = "default",
        speed_threshold_px_s: float = 15.0,
        moving_confirm_frames: int = 2,
        stopped_confirm_frames: int = 4,
        history_window_sec: float = 0.5,
        frame_rate: int = 10,
        track_activation_threshold: float = 0.25,
        lost_track_buffer: int = 30,
        minimum_matching_threshold: float = 0.95,
    ):
        self.camera_id = camera_id
        self.speed_threshold_px_s = speed_threshold_px_s
        self.moving_confirm_frames = moving_confirm_frames
        self.stopped_confirm_frames = stopped_confirm_frames
        self.history_window_sec = history_window_sec

        self._tracker = sv.ByteTrack(
            track_activation_threshold=track_activation_threshold,
            lost_track_buffer=lost_track_buffer,
            minimum_matching_threshold=minimum_matching_threshold,
            frame_rate=frame_rate,
        )
        self._tracks: Dict[int, VehicleTrackHistory] = {}

    def update(
        self,
        vehicle_detections: sv.Detections,
        timestamp: Optional[float] = None,
    ) -> VehicleTrackResult:
        """Update vehicle tracks and calculate speed/movement status."""
        if timestamp is None:
            timestamp = time.time()

        if vehicle_detections is None or len(vehicle_detections) == 0:
            tracked = self._tracker.update_with_detections(sv.Detections.empty())
            return VehicleTrackResult(
                tracked_vehicles=tracked,
                vehicle_speeds={},
                vehicle_moving={},
                vehicle_speed_kmh={},
            )

        # Update ByteTrack
        tracked = self._tracker.update_with_detections(vehicle_detections)

        vehicle_speeds: Dict[int, float] = {}
        vehicle_moving: Dict[int, bool] = {}
        vehicle_speed_kmh: Dict[int, float] = {}

        if tracked is None or len(tracked) == 0 or tracked.tracker_id is None:
            return VehicleTrackResult(
                tracked_vehicles=tracked if tracked is not None else sv.Detections.empty(),
                vehicle_speeds=vehicle_speeds,
                vehicle_moving=vehicle_moving,
                vehicle_speed_kmh=vehicle_speed_kmh,
            )

        active_ids = set()
        for idx, track_id in enumerate(tracked.tracker_id):
            if track_id is None:
                continue
            track_id = int(track_id)
            active_ids.add(track_id)

            box = tracked.xyxy[idx]
            cx = float((box[0] + box[2]) / 2.0)
            cy = float((box[1] + box[3]) / 2.0)
            cls_id = int(tracked.class_id[idx]) if tracked.class_id is not None else 3

            if track_id not in self._tracks:
                self._tracks[track_id] = VehicleTrackHistory(track_id=track_id, class_id=cls_id)

            th = self._tracks[track_id]
            th.class_id = cls_id
            th.points.append(
                VehicleTrackPoint(
                    centroid=(cx, cy),
                    bbox=(float(box[0]), float(box[1]), float(box[2]), float(box[3])),
                    timestamp=timestamp,
                )
            )

            # Compute smoothed speed over history window
            speed_px_s, speed_kmh = self._compute_speed(th, box)

            # Hysteresis update
            if speed_px_s >= self.speed_threshold_px_s:
                th.moving_confirm_count += 1
                th.stopped_confirm_count = 0
                if th.moving_confirm_count >= self.moving_confirm_frames:
                    th.is_moving = True
            else:
                th.stopped_confirm_count += 1
                th.moving_confirm_count = 0
                if th.stopped_confirm_count >= self.stopped_confirm_frames:
                    th.is_moving = False
                    speed_px_s = 0.0
                    speed_kmh = 0.0

            th.speed_px_s = speed_px_s
            th.speed_kmh = speed_kmh if th.is_moving else 0.0

            vehicle_speeds[track_id] = speed_px_s
            vehicle_moving[track_id] = th.is_moving
            vehicle_speed_kmh[track_id] = th.speed_kmh

        return VehicleTrackResult(
            tracked_vehicles=tracked,
            vehicle_speeds=vehicle_speeds,
            vehicle_moving=vehicle_moving,
            vehicle_speed_kmh=vehicle_speed_kmh,
        )

    def _compute_speed(
        self, th: VehicleTrackHistory, current_bbox: np.ndarray
    ) -> Tuple[float, float]:
        """Compute smoothed speed (px/s) and estimated km/h."""
        if len(th.points) < 2:
            return 0.0, 0.0

        latest = th.points[-1]
        target_time = latest.timestamp - self.history_window_sec
        ref_point = th.points[0]
        for p in reversed(th.points):
            if p.timestamp <= target_time:
                ref_point = p
                break

        dt = latest.timestamp - ref_point.timestamp
        if dt <= 0.001:
            return 0.0, 0.0

        dx = latest.centroid[0] - ref_point.centroid[0]
        dy = latest.centroid[1] - ref_point.centroid[1]
        dist_px = float(np.hypot(dx, dy))

        speed_px_s = dist_px / dt

        # Estimate scale: length/diagonal of vehicle box vs real-world size
        # Motorcycle ~ 1.8m, Car ~ 4.2m
        bw = max(1.0, float(current_bbox[2] - current_bbox[0]))
        bh = max(1.0, float(current_bbox[3] - current_bbox[1]))
        dim = max(bw, bh)
        ref_meters = 1.8 if th.class_id == 3 else 4.2
        m_per_px = ref_meters / dim
        speed_mps = speed_px_s * m_per_px
        speed_kmh = round(speed_mps * 3.6, 1)

        return speed_px_s, speed_kmh
