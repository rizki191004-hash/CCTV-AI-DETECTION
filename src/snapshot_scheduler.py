"""
snapshot_scheduler.py — Captures and manages snapshots during active events.

Handles:
- Initial alert snapshot (highest confidence frame)
- Periodic snapshots every 120s during active events
- File naming convention: cameraId_eventId_YYYYmmdd_HHMMSS.jpg
- Deduplication via image hash comparison
"""

import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, Sequence

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def crop_human_region(
    frame: np.ndarray,
    bboxes: Sequence[Sequence[float]],
    padding: float = 0.25,
) -> np.ndarray:
    """Crop the region containing detected humans with padding.

    Calculates the union bounding box of all provided human bounding boxes,
    expands it symmetrically by `padding` (e.g. 0.25 = 25%), clamps to frame
    boundaries, and returns the cropped image slice.

    Args:
        frame: BGR frame (H, W, C).
        bboxes: List of bounding boxes [[x1, y1, x2, y2], ...].
        padding: Fractional margin to add on all sides (0.25 = 25%).

    Returns:
        Cropped BGR image focusing on the detected human(s).
        Returns copy of frame if bboxes is empty or invalid.
    """
    if frame is None or len(bboxes) == 0:
        return frame.copy() if frame is not None else np.zeros((10, 10, 3), dtype=np.uint8)

    h, w = frame.shape[:2]

    # Calculate union bounding box of all detected persons
    min_x = min(b[0] for b in bboxes)
    min_y = min(b[1] for b in bboxes)
    max_x = max(b[2] for b in bboxes)
    max_y = max(b[3] for b in bboxes)

    box_w = max_x - min_x
    box_h = max_y - min_y

    if box_w <= 0 or box_h <= 0:
        return frame.copy()

    # Add protective padding
    pad_w = box_w * padding
    pad_h = box_h * padding

    x1 = int(max(0, np.floor(min_x - pad_w)))
    y1 = int(max(0, np.floor(min_y - pad_h)))
    x2 = int(min(w, np.ceil(max_x + pad_w)))
    y2 = int(min(h, np.ceil(max_y + pad_h)))

    if x2 <= x1 or y2 <= y1:
        return frame.copy()

    return frame[y1:y2, x1:x2].copy()


def crop_face_region(
    frame: np.ndarray,
    bbox: Sequence[float],
    keypoints: Optional[np.ndarray] = None,
    padding: float = 0.3,
) -> Optional[np.ndarray]:
    """Crop the facial/head region of a person with visibility confirmation.

    If keypoints are provided, validates that facial keypoints (nose, eyes)
    have sufficient confidence (>= 0.25). If the person is facing away
    (confidences < 0.25), returns None to prevent sending back-of-head crops.

    Args:
        frame: BGR frame (H, W, C).
        bbox: Bounding box [x1, y1, x2, y2] of the target person.
        keypoints: Optional 17-point pose keypoints array (N, 2) or (N, 3).
        padding: Padding factor around face bounds (default 0.3 = 30%).

    Returns:
        Cropped BGR image slice containing face, or None if face not visible/invalid.
    """
    if frame is None or len(bbox) < 4:
        return None

    bx1, by1, bx2, by2 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    bw = bx2 - bx1
    bh = by2 - by1

    if bw <= 0 or bh <= 0:
        return None

    h, w = frame.shape[:2]

    # Case 1: Pose keypoints provided
    if keypoints is not None and len(keypoints) >= 3:
        # Check facial points: 0 (nose), 1 (left eye), 2 (right eye)
        facial_pts = [keypoints[0], keypoints[1], keypoints[2]]
        confs = [pt[2] if len(pt) > 2 else 1.0 for pt in facial_pts]
        max_conf = max(confs)

        # If highest face confidence is below 0.25, person is facing away
        if max_conf < 0.25:
            return None

        # Collect valid facial coordinates
        valid_coords = [pt[:2] for pt, c in zip(facial_pts, confs) if c >= 0.25]
        if not valid_coords:
            return None

        min_fx = min(pt[0] for pt in valid_coords)
        max_fx = max(pt[0] for pt in valid_coords)
        min_fy = min(pt[1] for pt in valid_coords)
        max_fy = max(pt[1] for pt in valid_coords)

        # Factor in ears if available and visible
        if len(keypoints) >= 5:
            for ear_idx in (3, 4):
                ear_pt = keypoints[ear_idx]
                ear_conf = ear_pt[2] if len(ear_pt) > 2 else 1.0
                if ear_conf >= 0.3:
                    min_fx = min(min_fx, ear_pt[0])
                    max_fx = max(max_fx, ear_pt[0])
                    min_fy = min(min_fy, ear_pt[1])
                    max_fy = max(max_fy, ear_pt[1])

        cx = (min_fx + max_fx) / 2.0
        cy = (min_fy + max_fy) / 2.0

        raw_fw = max(20.0, max_fx - min_fx)
        raw_fh = max(20.0, max_fy - min_fy)
        face_w = max(raw_fw * (1.0 + padding * 2.0), bw * 0.4)
        face_h = max(raw_fh * (1.0 + padding * 2.0), bh * 0.25)

    else:
        # Case 2: Geometric upper-body estimate
        cx = (bx1 + bx2) / 2.0
        cy = by1 + bh * 0.15
        face_w = max(20.0, bw * 0.5 * (1.0 + padding))
        face_h = max(20.0, bh * 0.3 * (1.0 + padding))

    # Clamp coordinates to frame boundaries
    x1 = int(max(0, np.floor(cx - face_w / 2.0)))
    y1 = int(max(0, np.floor(cy - face_h / 2.0)))
    x2 = int(min(w, np.ceil(cx + face_w / 2.0)))
    y2 = int(min(h, np.ceil(cy + face_h / 2.0)))

    if x2 <= x1 or y2 <= y1:
        return None

    return frame[y1:y2, x1:x2].copy()


def crop_vehicle_region(
    frame: np.ndarray,
    bboxes: Sequence[Sequence[float]],
    padding: float = 0.18,
) -> np.ndarray:
    """Crop the region containing detected vehicles with tight padding.

    Calculates the union bounding box of all provided vehicle bounding boxes,
    expands it symmetrically by `padding` (default 0.18 = 18%), clamps to frame
    boundaries, and returns the cropped image slice.

    Args:
        frame: BGR frame (H, W, C).
        bboxes: List of bounding boxes [[x1, y1, x2, y2], ...].
        padding: Fractional margin to add on all sides (0.18 = 18%).

    Returns:
        Cropped BGR image focusing on the detected vehicle(s).
        Returns copy of frame if bboxes is empty or invalid.
    """
    if frame is None or len(bboxes) == 0:
        return frame.copy() if frame is not None else np.zeros((10, 10, 3), dtype=np.uint8)

    h, w = frame.shape[:2]

    min_x = min(b[0] for b in bboxes)
    min_y = min(b[1] for b in bboxes)
    max_x = max(b[2] for b in bboxes)
    max_y = max(b[3] for b in bboxes)

    box_w = max_x - min_x
    box_h = max_y - min_y

    if box_w <= 0 or box_h <= 0:
        return frame.copy()

    pad_w = box_w * padding
    pad_h = box_h * padding

    x1 = int(max(0, np.floor(min_x - pad_w)))
    y1 = int(max(0, np.floor(min_y - pad_h)))
    x2 = int(min(w, np.ceil(max_x + pad_w)))
    y2 = int(min(h, np.ceil(max_y + pad_h)))

    if x2 <= x1 or y2 <= y1:
        return frame.copy()

    return frame[y1:y2, x1:x2].copy()


class SnapshotScheduler:
    """Manages snapshot capture during active events.

    Selects the best frame (highest detection confidence) within each
    snapshot interval and saves it with a standardized filename.
    """

    def __init__(
        self,
        snapshot_dir: str = "snapshots",
        quality: int = 85,
    ):
        """
        Args:
            snapshot_dir: Directory to save snapshot images.
            quality: JPEG quality (0-100).
        """
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.quality = quality

        # Best frame buffer: (camera_id, event_id) -> (frame, confidence, timestamp)
        self._best_frames: Dict[str, Tuple[np.ndarray, float, float]] = {}

        # Last snapshot hash for deduplication: (camera_id, event_id) -> hash
        self._last_hashes: Dict[str, str] = {}

        logger.info("SnapshotScheduler initialized: dir=%s, quality=%d", snapshot_dir, quality)

    def update_best_frame(
        self,
        camera_id: str,
        event_id: str,
        frame: np.ndarray,
        confidence: float,
        bbox: Optional[np.ndarray] = None,
    ) -> None:
        """Track the best (highest confidence) frame for the current interval.

        Call this on every frame during an active event. The scheduler keeps
        the frame with the highest detection confidence.

        Args:
            camera_id: Camera identifier.
            event_id: Current event identifier.
            frame: BGR frame from camera.
            confidence: Detection confidence (higher = better frame).
            bbox: Bounding box [x1, y1, x2, y2] to crop the person (optional).
        """
        key = f"{camera_id}:{event_id}"
        current = self._best_frames.get(key)

        if current is None or confidence > current[1]:
            save_frame = frame.copy()
            self._best_frames[key] = (save_frame, confidence, 0.0)

    def capture_snapshot(
        self,
        camera_id: str,
        event_id: str,
        snapshot_type: str = "alert",
        frame_override: Optional[np.ndarray] = None,
    ) -> Optional[str]:
        """Capture and save a snapshot for an event.

        Uses the best buffered frame, or frame_override if provided.

        Args:
            camera_id: Camera identifier.
            event_id: Event identifier.
            snapshot_type: "alert" for initial, "periodic" for interval snapshots.
            frame_override: If provided, use this frame instead of the buffer.

        Returns:
            File path of saved snapshot, or None if no frame available or duplicate.
        """
        key = f"{camera_id}:{event_id}"

        # Get the frame to save
        if frame_override is not None:
            frame = frame_override
        elif key in self._best_frames:
            frame = self._best_frames[key][0]
        else:
            logger.warning("[%s] No frame available for snapshot", camera_id)
            return None

        # Deduplication: compute hash and compare with last snapshot
        frame_hash = self._compute_hash(frame)
        if key in self._last_hashes and self._last_hashes[key] == frame_hash:
            logger.debug("[%s] Duplicate snapshot skipped", camera_id)
            return None

        # Generate filename
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_event = event_id[:8]  # Use first 8 chars of UUID
        filename = f"{camera_id}_{short_event}_{timestamp_str}.jpg"

        # Save to disk
        filepath = self.snapshot_dir / filename
        try:
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.quality]
            success = cv2.imwrite(str(filepath), frame, encode_params)

            if not success:
                logger.error("[%s] Failed to write snapshot: %s", camera_id, filepath)
                return None

            # Update dedup hash
            self._last_hashes[key] = frame_hash

            # Reset best frame buffer for next interval
            self._best_frames.pop(key, None)

            file_size_kb = filepath.stat().st_size / 1024
            logger.info(
                "[%s] Snapshot saved: %s (%.1f KB, type=%s)",
                camera_id,
                filename,
                file_size_kb,
                snapshot_type,
            )
            return str(filepath)

        except Exception as e:
            logger.error("[%s] Error saving snapshot: %s", camera_id, e)
            return None

    def capture_human_crop(
        self,
        camera_id: str,
        event_id: str,
        bboxes: Sequence[Sequence[float]],
        frame_override: Optional[np.ndarray] = None,
        padding: float = 0.25,
    ) -> Optional[str]:
        """Capture and save a cropped snapshot focusing specifically on detected humans.

        Args:
            camera_id: Camera identifier.
            event_id: Event identifier.
            bboxes: Bounding boxes of active human tracks.
            frame_override: Optional frame to use instead of buffered best frame.
            padding: Padding ratio around bounding boxes (default 25%).

        Returns:
            File path of saved cropped snapshot, or None on failure.
        """
        key = f"{camera_id}:{event_id}"
        if frame_override is not None:
            source_frame = frame_override
        elif key in self._best_frames:
            source_frame = self._best_frames[key][0]
        else:
            logger.warning("[%s] No frame available for human crop snapshot", camera_id)
            return None

        cropped = crop_human_region(source_frame, bboxes, padding=padding)

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_event = event_id[:8]
        filename = f"{camera_id}_{short_event}_{timestamp_str}_crop.jpg"
        filepath = self.snapshot_dir / filename

        try:
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.quality]
            success = cv2.imwrite(str(filepath), cropped, encode_params)
            if not success:
                logger.error("[%s] Failed to write cropped snapshot: %s", camera_id, filepath)
                return None

            file_size_kb = filepath.stat().st_size / 1024
            logger.info(
                "[%s] Human crop snapshot saved: %s (%.1f KB, bboxes=%d)",
                camera_id,
                filename,
                file_size_kb,
                len(bboxes),
            )
            return str(filepath)
        except Exception as e:
            logger.error("[%s] Error saving cropped snapshot: %s", camera_id, e)
            return None

    def capture_vehicle_crop(
        self,
        camera_id: str,
        event_id: str,
        vehicle_bboxes: Sequence[Sequence[float]],
        frame_override: Optional[np.ndarray] = None,
        padding: float = 0.18,
    ) -> Optional[str]:
        """Capture and save a cropped snapshot focusing specifically on detected vehicles.

        Args:
            camera_id: Camera identifier.
            event_id: Event identifier.
            vehicle_bboxes: Bounding boxes of target vehicles.
            frame_override: Optional frame to use instead of buffered best frame.
            padding: Padding ratio around bounding boxes (default 18%).

        Returns:
            File path of saved cropped snapshot, or None on failure.
        """
        key = f"{camera_id}:{event_id}"
        if frame_override is not None:
            source_frame = frame_override
        elif key in self._best_frames:
            source_frame = self._best_frames[key][0]
        else:
            logger.warning("[%s] No frame available for vehicle crop snapshot", camera_id)
            return None

        cropped = crop_vehicle_region(source_frame, vehicle_bboxes, padding=padding)

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_event = event_id[:8]
        filename = f"{camera_id}_{short_event}_{timestamp_str}_vcrop.jpg"
        filepath = self.snapshot_dir / filename

        try:
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.quality]
            success = cv2.imwrite(str(filepath), cropped, encode_params)
            if not success:
                logger.error("[%s] Failed to write vehicle cropped snapshot: %s", camera_id, filepath)
                return None

            file_size_kb = filepath.stat().st_size / 1024
            logger.info(
                "[%s] Vehicle crop snapshot saved: %s (%.1f KB, bboxes=%d)",
                camera_id,
                filename,
                file_size_kb,
                len(vehicle_bboxes),
            )
            return str(filepath)
        except Exception as e:
            logger.error("[%s] Error saving vehicle cropped snapshot: %s", camera_id, e)
            return None

    def capture_face_crop(
        self,
        camera_id: str,
        event_id: str,
        bbox: Sequence[float],
        keypoints: Optional[np.ndarray] = None,
        frame_override: Optional[np.ndarray] = None,
        padding: float = 0.3,
    ) -> Optional[str]:
        """Capture and save a cropped snapshot focusing specifically on the primary suspect's face.

        Args:
            camera_id: Camera identifier.
            event_id: Event identifier.
            bbox: Bounding box [x1, y1, x2, y2] of the primary suspect.
            keypoints: Optional 17-point pose keypoints array.
            frame_override: Optional frame to use instead of buffered best frame.
            padding: Padding ratio around facial area (default 30%).

        Returns:
            File path of saved face crop, or None if face not visible/available.
        """
        key = f"{camera_id}:{event_id}"
        if frame_override is not None:
            source_frame = frame_override
        elif key in self._best_frames:
            source_frame = self._best_frames[key][0]
        else:
            logger.warning("[%s] No frame available for face crop snapshot", camera_id)
            return None

        cropped = crop_face_region(source_frame, bbox, keypoints=keypoints, padding=padding)
        if cropped is None:
            logger.debug("[%s] Face crop returned None (face not confirmed visible)", camera_id)
            return None

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_event = event_id[:8]
        filename = f"{camera_id}_{short_event}_{timestamp_str}_face.jpg"
        filepath = self.snapshot_dir / filename

        try:
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.quality]
            success = cv2.imwrite(str(filepath), cropped, encode_params)
            if not success:
                logger.error("[%s] Failed to write face crop snapshot: %s", camera_id, filepath)
                return None

            file_size_kb = filepath.stat().st_size / 1024
            logger.info(
                "[%s] Face crop snapshot saved: %s (%.1f KB)",
                camera_id,
                filename,
                file_size_kb,
            )
            return str(filepath)
        except Exception as e:
            logger.error("[%s] Error saving face crop snapshot: %s", camera_id, e)
            return None

    def get_snapshot_as_bytes(self, filepath: str) -> Optional[bytes]:
        """Read a snapshot file and return as bytes (for Telegram sending).

        Args:
            filepath: Path to the snapshot file.

        Returns:
            JPEG bytes, or None if file doesn't exist.
        """
        try:
            with open(filepath, "rb") as f:
                return f.read()
        except FileNotFoundError:
            logger.error("Snapshot file not found: %s", filepath)
            return None
        except Exception as e:
            logger.error("Error reading snapshot: %s", e)
            return None

    @staticmethod
    def _compute_hash(frame: np.ndarray) -> str:
        """Compute a perceptual hash of a frame for deduplication.

        Uses a downscaled grayscale version to detect similar (not identical) frames.
        """
        # Resize to small thumbnail for hash comparison
        small = cv2.resize(frame, (32, 32), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY) if len(small.shape) == 3 else small
        return hashlib.md5(gray.tobytes()).hexdigest()

    def cleanup_event(self, camera_id: str, event_id: str) -> None:
        """Clean up buffers for a resolved event."""
        key = f"{camera_id}:{event_id}"
        self._best_frames.pop(key, None)
        self._last_hashes.pop(key, None)

    def get_snapshot_count(self, camera_id: str) -> int:
        """Count snapshot files for a camera."""
        pattern = f"{camera_id}_*"
        return len(list(self.snapshot_dir.glob(pattern)))

    def cleanup_old_snapshots(self, max_age_days: int = 30) -> int:
        """Delete snapshot files older than N days."""
        import time as _time

        now = _time.time()
        cutoff = now - (max_age_days * 86400)
        deleted = 0

        for filepath in self.snapshot_dir.glob("*.jpg"):
            try:
                if filepath.stat().st_mtime < cutoff:
                    filepath.unlink()
                    deleted += 1
            except Exception as e:
                logger.debug("Error deleting old snapshot %s: %s", filepath, e)

        if deleted > 0:
            logger.info("Cleaned up %d old snapshots (>%d days)", deleted, max_age_days)
        return deleted
