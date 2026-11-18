"""
vehicle_detector.py – Vehicle detection (motorcycle & car) with rider association.

Detects motorcycles (COCO class 3) and cars (COCO class 2) using yolov8n.pt.
Identifies riders/drivers by computing IoU overlap between person and vehicle
bounding boxes. A person with IoU >= iou_threshold against a vehicle is
classified as a rider/driver and triggers a Telegram alert.

Design decisions: ADR-007
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import supervision as sv
from ultralytics import YOLO

logger = logging.getLogger(__name__)

# COCO class IDs for vehicles
CAR_CLASS_ID = 2
MOTORCYCLE_CLASS_ID = 3
VEHICLE_CLASS_IDS = [CAR_CLASS_ID, MOTORCYCLE_CLASS_ID]

# Human-readable names
VEHICLE_CLASS_NAMES = {
    CAR_CLASS_ID: "Car",
    MOTORCYCLE_CLASS_ID: "Motorcycle",
}

# Display colors (BGR)
VEHICLE_COLORS = {
    CAR_CLASS_ID: (255, 100, 0),        # Blue for car
    MOTORCYCLE_CLASS_ID: (0, 165, 255),  # Orange for motorcycle
}
RIDER_COLOR = (0, 0, 255)  # Red when rider detected


@dataclass
class RiderInfo:
    """Describes a detected person-on-vehicle pair."""
    person_idx: int        # Index in persons sv.Detections
    vehicle_idx: int       # Index in vehicles sv.Detections
    vehicle_class: int     # CAR_CLASS_ID or MOTORCYCLE_CLASS_ID
    iou: float             # Computed IoU

    @property
    def vehicle_name(self) -> str:
        return VEHICLE_CLASS_NAMES.get(self.vehicle_class, "Vehicle")

    @property
    def alert_label(self) -> str:
        if self.vehicle_class == MOTORCYCLE_CLASS_ID:
            return "Riding Motorcycle"
        return "Driving Car"

    @property
    def emoji_label(self) -> str:
        if self.vehicle_class == MOTORCYCLE_CLASS_ID:
            return "\U0001f3cd\ufe0f Rider!"   # 🏍️ Rider!
        return "\U0001f697 Driver!"             # 🚗 Driver!


@dataclass
class VehicleDetectionResult:
    """Result of one vehicle-detection pass on a single frame."""
    vehicles: sv.Detections
    vehicle_count: int = 0
    riders: List[RiderInfo] = field(default_factory=list)


class VehicleDetector:
    """
    Lightweight vehicle detector using YOLOv8n (full COCO 80-class model).

    Runs alongside PersonDetector; each detects its own class subset.
    Model is loaded lazily on first call to detect() to keep startup fast
    and to avoid downloading the model at import time.
    """

    MODEL_NAME = "yolov8n.pt"

    def __init__(
        self,
        confidence_threshold: float = 0.45,
        iou_threshold: float = 0.5,
        img_size: int = 640,
        device: str = "cpu",
        rider_iou_threshold: float = 0.15,
        min_area: int = 1200,
        min_dimension: int = 35,
    ):
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.img_size = img_size
        self.device = device
        self.rider_iou_threshold = rider_iou_threshold
        self.min_area = min_area
        self.min_dimension = min_dimension

        self._model: Optional[YOLO] = None
        self._lock = asyncio.Lock()

    def filter_vehicles(self, detections: sv.Detections) -> sv.Detections:
        """Filter out small or distant vehicles below area and dimension thresholds."""
        if len(detections) == 0:
            return detections
        
        widths = detections.xyxy[:, 2] - detections.xyxy[:, 0]
        heights = detections.xyxy[:, 3] - detections.xyxy[:, 1]
        areas = widths * heights
        
        mask = (areas >= self.min_area) & (widths >= self.min_dimension) & (heights >= self.min_dimension)
        return detections[mask]

    # ------------------------------------------------------------------
    # Model loading (lazy)
    # ------------------------------------------------------------------

    def _ensure_model(self) -> None:
        """Load model on first use."""
        if self._model is not None:
            return
        logger.info("Loading VehicleDetector model: %s on %s", self.MODEL_NAME, self.device)
        self._model = YOLO(self.MODEL_NAME)
        # Warmup
        try:
            dummy = np.zeros((self.img_size, self.img_size, 3), dtype=np.uint8)
            self._model.predict(
                dummy,
                device=self.device,
                conf=self.confidence_threshold,
                classes=VEHICLE_CLASS_IDS,
                verbose=False,
            )
            logger.info("VehicleDetector warmup complete")
        except Exception as e:
            logger.warning("VehicleDetector warmup failed: %s", e)

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(self, frame: np.ndarray) -> VehicleDetectionResult:
        """Run vehicle detection on a single frame synchronously."""
        self._ensure_model()

        results = self._model.predict(
            frame,
            device=self.device,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            imgsz=self.img_size,
            classes=VEHICLE_CLASS_IDS,
            verbose=False,
        )

        detections = sv.Detections.empty()
        if results and len(results[0].boxes) > 0:
            detections = sv.Detections.from_ultralytics(results[0])
            # Keep only vehicle classes (safety filter)
            mask = np.isin(detections.class_id, VEHICLE_CLASS_IDS)
            detections = detections[mask]
            # Filter out tiny or distant vehicles
            detections = self.filter_vehicles(detections)

        return VehicleDetectionResult(
            vehicles=detections,
            vehicle_count=len(detections),
            riders=[],  # Rider association done separately via find_riders()
        )

    async def detect_async(self, frame: np.ndarray) -> VehicleDetectionResult:
        """Run vehicle detection asynchronously (yields to event loop)."""
        async with self._lock:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.detect, frame)

    # ------------------------------------------------------------------
    # Rider association (pure logic — no model needed)
    # ------------------------------------------------------------------

    @staticmethod
    def find_riders(
        persons: sv.Detections,
        vehicles: sv.Detections,
        iou_threshold: float = 0.15,
    ) -> List[RiderInfo]:
        """
        Find person↔vehicle pairs where the person is riding the vehicle.

        A person is considered a rider if their bounding box overlaps the
        vehicle bounding box with IoU >= iou_threshold.

        Args:
            persons:  sv.Detections of persons from PersonDetector.
            vehicles: sv.Detections of vehicles from VehicleDetector.
            iou_threshold: Minimum IoU to classify a person as a rider.

        Returns:
            List of RiderInfo for each confirmed person-on-vehicle pair.
        """
        riders: List[RiderInfo] = []

        if persons is None or vehicles is None:
            return riders
        if len(persons) == 0 or len(vehicles) == 0:
            return riders

        p_boxes = persons.xyxy   # shape (N, 4)
        v_boxes = vehicles.xyxy  # shape (M, 4)
        v_classes = vehicles.class_id if vehicles.class_id is not None else np.zeros(len(v_boxes), dtype=int)

        for p_idx, p_box in enumerate(p_boxes):
            for v_idx, v_box in enumerate(v_boxes):
                iou = VehicleDetector._compute_iou(p_box, v_box)
                if iou >= iou_threshold:
                    riders.append(RiderInfo(
                        person_idx=p_idx,
                        vehicle_idx=v_idx,
                        vehicle_class=int(v_classes[v_idx]),
                        iou=float(iou),
                    ))

        return riders

    @staticmethod
    def _compute_iou(box_a: np.ndarray, box_b: np.ndarray) -> float:
        """Compute Intersection over Union of two [x1, y1, x2, y2] boxes."""
        x_a = max(box_a[0], box_b[0])
        y_a = max(box_a[1], box_b[1])
        x_b = min(box_a[2], box_b[2])
        y_b = min(box_a[3], box_b[3])

        inter_w = max(0.0, x_b - x_a)
        inter_h = max(0.0, y_b - y_a)
        inter_area = inter_w * inter_h

        if inter_area == 0.0:
            return 0.0

        area_a = max(0.0, (box_a[2] - box_a[0]) * (box_a[3] - box_a[1]))
        area_b = max(0.0, (box_b[2] - box_b[0]) * (box_b[3] - box_b[1]))
        union_area = area_a + area_b - inter_area

        if union_area <= 0.0:
            return 0.0

        return inter_area / union_area

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @staticmethod
    def describe_riders(riders: List[RiderInfo]) -> Optional[str]:
        """
        Return a human-readable summary of detected riders for Telegram alerts.

        Returns None if no riders detected.
        Examples:
          "Riding Motorcycle"
          "Driving Car"
          "Riding Motorcycle, Driving Car"
        """
        if not riders:
            return None
        seen = {}
        for r in riders:
            seen[r.vehicle_class] = r.alert_label
        return ", ".join(seen.values())

