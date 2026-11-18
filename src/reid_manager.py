"""
reid_manager.py — Person Re-Identification for cross-camera matching.

Extracts appearance embeddings from detected persons using a lightweight
deep learning model (OSNet) and matches them across cameras via cosine
similarity. Assigns a global person ID that persists across camera views.
"""

import asyncio
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PersonGalleryEntry:
    """A single entry in the Re-ID gallery representing a known person."""
    global_person_id: str
    embeddings: List[np.ndarray] = field(default_factory=list)  # rolling buffer
    last_camera_id: str = ""
    last_camera_name: str = ""
    last_seen: float = 0.0
    first_seen: float = 0.0
    total_sightings: int = 0

    @property
    def mean_embedding(self) -> np.ndarray:
        """Average embedding across recent observations."""
        if not self.embeddings:
            return np.zeros(512)
        return np.mean(self.embeddings, axis=0)


@dataclass
class ReIDMatch:
    """Result of a Re-ID matching attempt."""
    global_person_id: str
    similarity: float
    prev_camera_id: str
    prev_camera_name: str
    seconds_since_last: float
    is_cross_camera: bool  # True if matched across different cameras


# ---------------------------------------------------------------------------
# Re-ID Manager
# ---------------------------------------------------------------------------

class ReIDManager:
    """Cross-camera Person Re-Identification manager.

    Uses a lightweight appearance model (OSNet) to extract visual embeddings
    from person crops, then matches them across cameras using cosine similarity.

    Thread-safe: embedding extraction runs in a background thread to avoid
    blocking the async event loop.
    """

    def __init__(
        self,
        model_name: str = "osnet_x0_25",
        similarity_threshold: float = 0.70,
        gallery_max_age_sec: float = 1800.0,  # 30 minutes
        max_embeddings_per_person: int = 10,
        min_crop_size: int = 40,  # minimum crop width/height in pixels
        update_interval_sec: float = 2.0,  # how often to re-extract per track
        device: str = "cpu",
    ):
        """
        Args:
            model_name: torchreid model name (e.g., 'osnet_x0_25', 'osnet_x1_0').
            similarity_threshold: Cosine similarity threshold for a match (0-1).
            gallery_max_age_sec: Remove gallery entries older than this (seconds).
            max_embeddings_per_person: Max embeddings to keep per person (rolling).
            min_crop_size: Minimum crop dimension to attempt Re-ID extraction.
            update_interval_sec: Min seconds between Re-ID updates for same track.
            device: 'cpu' or 'cuda'.
        """
        self._model_name = model_name
        self._similarity_threshold = similarity_threshold
        self._gallery_max_age_sec = gallery_max_age_sec
        self._max_embeddings = max_embeddings_per_person
        self._min_crop_size = min_crop_size
        self._update_interval_sec = update_interval_sec
        self._device = device

        # Gallery: global_person_id -> PersonGalleryEntry
        self._gallery: Dict[str, PersonGalleryEntry] = {}
        self._gallery_lock = threading.Lock()

        # Track -> global person mapping: (camera_id, local_track_id) -> global_person_id
        self._track_to_global: Dict[Tuple[str, int], str] = {}

        # Last extraction time per track to throttle: (camera_id, track_id) -> timestamp
        self._last_extract_time: Dict[Tuple[str, int], float] = {}

        # Global person ID counter
        self._next_person_id: int = 1

        # Model (lazy-loaded)
        self._extractor = None
        self._model_loaded = False
        self._load_failed = False
        self._load_lock = threading.Lock()

        # Stats
        self._total_extractions: int = 0
        self._total_matches: int = 0
        self._total_new_persons: int = 0

        logger.info(
            "ReIDManager initialized (model=%s, threshold=%.2f, gallery_ttl=%ds)",
            model_name, similarity_threshold, int(gallery_max_age_sec)
        )

    def _load_model(self) -> bool:
        """Lazy-load the Re-ID feature extractor model."""
        if self._model_loaded:
            return True
        if self._load_failed:
            return False

        with self._load_lock:
            if self._model_loaded:
                return True
            if self._load_failed:
                return False

            try:
                from torchreid.utils import FeatureExtractor

                self._extractor = FeatureExtractor(
                    model_name=self._model_name,
                    model_path='',  # auto-download
                    device=self._device,
                )
                self._model_loaded = True
                logger.info(
                    "Re-ID model loaded: %s on %s", self._model_name, self._device
                )
                return True

            except ImportError:
                self._load_failed = True
                logger.warning(
                    "torchreid not installed. Re-ID feature disabled. "
                    "Install with: pip install torchreid"
                )
                return False
            except Exception as e:
                self._load_failed = True
                logger.error("Failed to load Re-ID model: %s", e)
                return False

    def _generate_global_id(self) -> str:
        """Generate the next global person ID."""
        pid = f"P-{self._next_person_id:04d}"
        self._next_person_id += 1
        return pid

    # ----- Core API (called from async pipeline) -----

    async def process_tracks(
        self,
        camera_id: str,
        camera_name: str,
        frame: np.ndarray,
        active_tracks: dict,
    ) -> List[ReIDMatch]:
        """Process active tracks and attempt Re-ID matching.

        This is the main entry point called from CameraPipeline.run().
        Runs the heavy embedding extraction in a thread pool.

        Args:
            camera_id: Current camera ID.
            camera_name: Human-readable camera name.
            frame: Current BGR frame (original resolution).
            active_tracks: Dict of track_id -> TrackHistory for active human tracks.

        Returns:
            List of ReIDMatch results for cross-camera matches found this cycle.
        """
        if not self._load_model():
            return []

        now = time.time()
        cross_camera_matches: List[ReIDMatch] = []

        for track_id, track_history in active_tracks.items():
            # Only process human tracks
            if track_history.class_type != "human":
                continue

            # Throttle: don't re-extract too frequently for the same track
            key = (camera_id, track_id)
            last_time = self._last_extract_time.get(key, 0.0)
            if now - last_time < self._update_interval_sec:
                continue

            # Get bounding box
            bbox = track_history.latest_bbox
            if bbox is None:
                continue

            # Crop person from frame
            crop = self._crop_person(frame, bbox)
            if crop is None:
                continue

            # Extract embedding in thread pool (non-blocking)
            embedding = await asyncio.to_thread(self._extract_embedding, crop)
            if embedding is None:
                continue

            self._last_extract_time[key] = now
            self._total_extractions += 1

            # Try to match against gallery
            match = self._match_and_update(
                camera_id, camera_name, track_id, embedding, now
            )

            if match and match.is_cross_camera:
                cross_camera_matches.append(match)

        # Periodic gallery cleanup
        self._cleanup_gallery(now)

        return cross_camera_matches

    def _crop_person(
        self, frame: np.ndarray, bbox: Tuple[float, float, float, float]
    ) -> Optional[np.ndarray]:
        """Crop a person from the frame using their bounding box.

        Args:
            frame: Full BGR frame.
            bbox: (x1, y1, x2, y2) in frame coordinates.

        Returns:
            Cropped and resized BGR image, or None if too small.
        """
        h, w = frame.shape[:2]
        x1 = max(0, int(bbox[0]))
        y1 = max(0, int(bbox[1]))
        x2 = min(w, int(bbox[2]))
        y2 = min(h, int(bbox[3]))

        crop_w = x2 - x1
        crop_h = y2 - y1

        if crop_w < self._min_crop_size or crop_h < self._min_crop_size:
            return None

        crop = frame[y1:y2, x1:x2]

        # Resize to standard Re-ID input size (256x128)
        crop_resized = cv2.resize(crop, (128, 256), interpolation=cv2.INTER_LINEAR)

        return crop_resized

    def _extract_embedding(self, crop: np.ndarray) -> Optional[np.ndarray]:
        """Extract appearance embedding from a person crop.

        This runs synchronously and should be called via asyncio.to_thread().

        Args:
            crop: BGR image of a person (resized to 128x256).

        Returns:
            Normalized embedding vector, or None on failure.
        """
        if self._extractor is None:
            return None

        try:
            # torchreid FeatureExtractor expects a list of images (numpy or paths)
            # Convert BGR -> RGB for the model
            crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            features = self._extractor(crop_rgb)

            # Result is a torch.Tensor of shape (1, feature_dim)
            embedding = features.cpu().numpy().flatten()

            # L2 normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

            return embedding

        except Exception as e:
            logger.debug("Re-ID extraction error: %s", e)
            return None

    def _match_and_update(
        self,
        camera_id: str,
        camera_name: str,
        track_id: int,
        embedding: np.ndarray,
        now: float,
    ) -> Optional[ReIDMatch]:
        """Match an embedding against the gallery, update or create entry.

        Args:
            camera_id: Current camera.
            camera_name: Camera display name.
            track_id: Local track ID on this camera.
            embedding: Normalized appearance embedding.
            now: Current timestamp.

        Returns:
            ReIDMatch if a match was found, None otherwise.
        """
        key = (camera_id, track_id)

        with self._gallery_lock:
            # If this track already has a global ID, just update the gallery
            existing_global_id = self._track_to_global.get(key)
            if existing_global_id and existing_global_id in self._gallery:
                entry = self._gallery[existing_global_id]
                self._update_gallery_entry(entry, embedding, camera_id, camera_name, now)
                return None  # Not a new match, just an update

            # Search gallery for best match
            best_match_id: Optional[str] = None
            best_similarity: float = 0.0

            for gid, entry in self._gallery.items():
                sim = self._cosine_similarity(embedding, entry.mean_embedding)
                if sim > best_similarity:
                    best_similarity = sim
                    best_match_id = gid

            if best_match_id and best_similarity >= self._similarity_threshold:
                # Found a match!
                entry = self._gallery[best_match_id]
                prev_camera_id = entry.last_camera_id
                prev_camera_name = entry.last_camera_name
                seconds_since = now - entry.last_seen
                is_cross_camera = (prev_camera_id != camera_id)

                # Update gallery
                self._update_gallery_entry(entry, embedding, camera_id, camera_name, now)
                self._track_to_global[key] = best_match_id

                self._total_matches += 1

                logger.info(
                    "Re-ID match: %s (sim=%.3f) cam=%s->%s (%.0fs ago)",
                    best_match_id, best_similarity, prev_camera_id, camera_id, seconds_since
                )

                return ReIDMatch(
                    global_person_id=best_match_id,
                    similarity=best_similarity,
                    prev_camera_id=prev_camera_id,
                    prev_camera_name=prev_camera_name,
                    seconds_since_last=seconds_since,
                    is_cross_camera=is_cross_camera,
                )
            else:
                # New person — create gallery entry
                new_id = self._generate_global_id()
                new_entry = PersonGalleryEntry(
                    global_person_id=new_id,
                    embeddings=[embedding.copy()],
                    last_camera_id=camera_id,
                    last_camera_name=camera_name,
                    last_seen=now,
                    first_seen=now,
                    total_sightings=1,
                )
                self._gallery[new_id] = new_entry
                self._track_to_global[key] = new_id

                self._total_new_persons += 1

                logger.debug(
                    "New person registered: %s on cam=%s", new_id, camera_id
                )
                return None

    def _update_gallery_entry(
        self,
        entry: PersonGalleryEntry,
        embedding: np.ndarray,
        camera_id: str,
        camera_name: str,
        now: float,
    ) -> None:
        """Update an existing gallery entry with a new observation."""
        entry.embeddings.append(embedding.copy())
        # Keep rolling buffer
        if len(entry.embeddings) > self._max_embeddings:
            entry.embeddings.pop(0)
        entry.last_camera_id = camera_id
        entry.last_camera_name = camera_name
        entry.last_seen = now
        entry.total_sightings += 1

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    def _cleanup_gallery(self, now: float) -> None:
        """Remove stale gallery entries."""
        with self._gallery_lock:
            stale_ids = [
                gid for gid, entry in self._gallery.items()
                if (now - entry.last_seen) > self._gallery_max_age_sec
            ]
            for gid in stale_ids:
                del self._gallery[gid]

            # Clean up track mappings for stale gallery entries
            stale_keys = [
                k for k, v in self._track_to_global.items()
                if v in stale_ids
            ]
            for k in stale_keys:
                del self._track_to_global[k]

            if stale_ids:
                logger.debug("Gallery cleanup: removed %d stale entries", len(stale_ids))

        # Also clean up old extraction timestamps
        cutoff = now - 300  # 5 minutes
        stale_extract_keys = [
            k for k, t in self._last_extract_time.items()
            if t < cutoff
        ]
        for k in stale_extract_keys:
            del self._last_extract_time[k]

    def get_global_id(self, camera_id: str, track_id: int) -> Optional[str]:
        """Get the global person ID for a local track, if assigned."""
        return self._track_to_global.get((camera_id, track_id))

    def get_gallery_size(self) -> int:
        """Get current number of known persons in gallery."""
        return len(self._gallery)

    def get_stats(self) -> dict:
        """Get Re-ID statistics."""
        return {
            "model_loaded": self._model_loaded,
            "gallery_size": len(self._gallery),
            "total_extractions": self._total_extractions,
            "total_matches": self._total_matches,
            "total_new_persons": self._total_new_persons,
            "active_track_mappings": len(self._track_to_global),
        }
