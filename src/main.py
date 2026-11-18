"""
main.py — Application entry point and async orchestrator.

Initializes all components, spawns per-camera processing pipelines,
and coordinates the detection → tracking → scoring → alerting flow.
"""

import asyncio
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Optional

import cv2
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure stdout and stderr are not None when running via pythonw.exe
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

from src.config_loader import ConfigLoader, AppConfig, CameraConfig
from src.db_logger import DBLogger
from src.frame_grabber import FrameGrabber
from src.preprocessor import Preprocessor, compute_black_ratio
from src.motion_detector import MotionDetector
from src.person_detector import PersonDetector
from src.vehicle_detector import VehicleDetector
from src.tracker import PersonTracker
from src.feature_extractor import FeatureExtractor
from src.rule_engine import RuleEngine
from src.event_manager import EventManager, EventState
from src.snapshot_scheduler import SnapshotScheduler
from src.telegram_notifier import TelegramNotifier
from src.event_recorder import EventRecorder
from src.alarm_gate import AlarmGate
from src.storage_manager import StorageManager
from src.reid_manager import ReIDManager

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(level: str = "INFO", log_file: str = "data/cctv_ai.log") -> None:
    """Configure logging for the application."""
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    fmt = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(log_path), encoding="utf-8"),
    ]

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt=date_fmt,
        handlers=handlers,
    )

    # Reduce noise from third-party libraries
    logging.getLogger("ultralytics").setLevel(logging.WARNING)
    logging.getLogger("supervision").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)


logger = logging.getLogger("cctv_ai")


# ---------------------------------------------------------------------------
# Camera Processing Pipeline
# ---------------------------------------------------------------------------

class CameraPipeline:
    """Processing pipeline for a single camera.

    Orchestrates: grab → preprocess → motion → detect → track → features → rules → events → alerts
    """
    latest_vehicle_detections = None
    latest_riders = []

    def __init__(
        self,
        camera_config: CameraConfig,
        app_config: AppConfig,
        detector: PersonDetector,
        event_manager: EventManager,
        rule_engine: RuleEngine,
        snapshot_scheduler: SnapshotScheduler,
        telegram: TelegramNotifier,
        db: DBLogger,
        reid_manager: Optional[ReIDManager] = None,
        vehicle_detector: Optional[VehicleDetector] = None,
    ):
        self.camera_config = camera_config
        self.app_config = app_config
        self.camera_id = camera_config.camera_id

        # Shared components
        self.detector = detector
        self.vehicle_detector = vehicle_detector
        self.event_manager = event_manager
        self.rule_engine = rule_engine
        self.snapshot_scheduler = snapshot_scheduler
        self.telegram = telegram
        self.db = db
        self.reid_manager = reid_manager

        # Per-camera components
        self.grabber = FrameGrabber(
            camera_id=camera_config.camera_id,
            rtsp_url=camera_config.rtsp_url,
            name=camera_config.name,
        )
        self.preprocessor = Preprocessor(
            target_resolution=app_config.input_resolution,
        )
        self.motion_detector = MotionDetector(
            sensitivity=app_config.motion_sensitivity,
            history=app_config.motion_history,
            var_threshold=app_config.motion_var_threshold,
        )
        self.tracker = PersonTracker(
            camera_id=camera_config.camera_id,
            frame_rate=app_config.detect_fps_target,
        )
        self.feature_extractor = FeatureExtractor(
            camera_config=camera_config,
            app_config=app_config,
            frame_shape=(app_config.input_resolution[1], app_config.input_resolution[0]),
        )
        self.event_recorder = EventRecorder(
            camera_id=camera_config.camera_id,
            fps=app_config.detect_fps_target,
            resolution=(app_config.input_resolution[1], app_config.input_resolution[0]), # or original frame size? Assuming we pass the display_frame down or original frame
            pre_sec=5,
            post_sec=15,
        )

        # Anti-False Alarm Gate (per-camera overrides)
        gate_conf = camera_config.alarm_gate_confidence or app_config.alarm_gate.confidence_gate
        gate_frames = camera_config.alarm_gate_min_frames or app_config.alarm_gate.min_frames

        self.alarm_gate = AlarmGate(
            confidence_gate=gate_conf,
            min_frames=gate_frames,
            min_bbox_area=app_config.alarm_gate.min_bbox_area,
            max_bbox_ratio=app_config.alarm_gate.max_bbox_ratio,
            max_aspect_ratio=app_config.alarm_gate.max_aspect_ratio,
        )

        # Performance tracking
        self._frame_times: list = []
        self._skip_counter: int = 0
        self._dynamic_skip: int = 0
        
        self._was_recording = False
        
        # Camera Health Monitoring
        self._health_status = "ONLINE"
        self._offline_since = 0.0
        self._health_notified = False
        self._low_fps_notified = False
        self._last_health_check = time.monotonic()
        
        # State sharing
        self.latest_track_scores = {}
        self.latest_vehicle_detections = None
        self.latest_riders = []

    async def run(self, shutdown_event: asyncio.Event) -> None:
        """Main processing loop for this camera."""
        cam_id = self.camera_id
        cam_name = self.camera_config.name
        logger.info("[%s] Starting pipeline: %s", cam_id, cam_name)

        # Register camera in database
        await self.db.upsert_camera(
            camera_id=cam_id,
            name=cam_name,
            rtsp_url=self.camera_config.rtsp_url,
            enabled=self.camera_config.enabled,
        )

        # Start frame grabber
        self.grabber.start()

        # Wait for first frame
        logger.info("[%s] Waiting for stream connection...", cam_id)
        for _ in range(100):  # 10 second timeout
            if shutdown_event.is_set():
                return
            frame, _ = self.grabber.get_latest_frame()
            if frame is not None:
                break
            await asyncio.sleep(0.1)
        else:
            logger.error("[%s] Timeout waiting for stream — pipeline not starting", cam_id)
            return

        logger.info("[%s] Stream connected — pipeline running", cam_id)

        # Calculate target frame interval
        target_interval = 1.0 / max(self.app_config.detect_fps_target, 1)
        track_flush_counter = 0

        try:
            while not shutdown_event.is_set():
                loop_start = time.monotonic()

                # --- Frame skip logic ---
                if self._dynamic_skip > 0:
                    self._skip_counter += 1
                    if self._skip_counter < self._dynamic_skip:
                        await asyncio.sleep(0.01)
                        continue
                    self._skip_counter = 0

                # --- 0. Health Monitoring ---
                current_time = time.monotonic()
                if current_time - self._last_health_check >= 1.0:
                    self._last_health_check = current_time
                    is_connected = self.grabber.is_connected
                    
                    if not is_connected:
                        if self._health_status == "ONLINE":
                            self._health_status = "OFFLINE"
                            self._offline_since = current_time
                        elif self._health_status == "OFFLINE":
                            offline_duration = current_time - self._offline_since
                            # Default 60 seconds offline duration before notifying
                            if offline_duration >= 60.0 and not self._health_notified:
                                mins = int(offline_duration / 60)
                                msg = f"Terputus selama {mins} menit" if mins > 0 else f"Terputus selama {int(offline_duration)} detik"
                                asyncio.create_task(self.telegram.send_health_alert(cam_name, "OFFLINE", msg))
                                self._health_notified = True
                    else:
                        if self._health_status == "OFFLINE":
                            self._health_status = "ONLINE"
                            if self._health_notified:
                                asyncio.create_task(self.telegram.send_health_alert(cam_name, "ONLINE", "Kembali online"))
                            self._health_notified = False
                            self._offline_since = 0.0
                            
                        # Low FPS check (if connected)
                        fps = self.grabber.fps
                        target_fps = self.app_config.detect_fps_target
                        if fps > 0 and fps < (target_fps * 0.3):
                            if not self._low_fps_notified:
                                asyncio.create_task(self.telegram.send_health_alert(
                                    cam_name, "WARNING", f"FPS terlalu rendah ({fps:.1f} fps / Target {target_fps} fps)"
                                ))
                                self._low_fps_notified = True
                        elif fps >= (target_fps * 0.5):
                            if self._low_fps_notified:
                                asyncio.create_task(self.telegram.send_health_alert(
                                    cam_name, "ONLINE", f"FPS kembali stabil ({fps:.1f} fps)"
                                ))
                                self._low_fps_notified = False

                # --- 1. Grab latest frame ---
                frame, frame_ts = self.grabber.get_latest_frame()
                if frame is None:
                    await asyncio.sleep(0.1)
                    continue
                    
                # Add frame to continuous recording buffer
                self.event_recorder.add_frame(frame)

                # --- 2. Preprocess ---
                processed = self.preprocessor.process(frame)

                # --- 3. Motion detection ---
                motion_level, motion_mask = self.motion_detector.detect(processed)
                has_motion = self.motion_detector.has_significant_motion(motion_level)

                # --- 4. Motion gate: skip YOLO if no motion ---
                detections = None
                tracked = None
                person_count = 0

                if has_motion or not self.app_config.motion_gate_enabled:
                    # --- 5. Person & Animal detection (YOLO) ---
                    # Yields to event loop so other cameras can process while YOLO runs
                    detection_result = await self.detector.detect_all_async(processed)
                    all_detections = detection_result.all_detections
                    self.latest_detections = all_detections
                    person_count = detection_result.person_count # Only humans trigger events

                    # --- 5.5 Vehicle detection & rider association ---
                    if self.vehicle_detector is not None:
                        vehicle_result = await self.vehicle_detector.detect_async(processed)
                        self.latest_vehicle_detections = vehicle_result.vehicles
                        self.latest_riders = VehicleDetector.find_riders(
                            detection_result.persons,
                            vehicle_result.vehicles,
                        )
                    else:
                        self.latest_vehicle_detections = None
                        self.latest_riders = []

                    # --- 6. Tracking ---
                    if len(all_detections) > 0:
                        tracked = self.tracker.update(
                            all_detections, 
                            keypoints=detection_result.person_keypoints
                        )
                        
                        # Recalculate person count from active human tracks
                        active_tracks = self.tracker.get_active_tracks()
                        person_count = sum(1 for t in active_tracks.values() if t.class_type == "human")
                    else:
                        # Update tracker with empty to handle lost tracks
                        import supervision as sv
                        tracked = self.tracker.update(sv.Detections.empty())
                else:
                    # No motion — update tracker with empty
                    import supervision as sv
                    tracked = self.tracker.update(sv.Detections.empty())
                    self.latest_vehicle_detections = None
                    self.latest_riders = []

                # --- 7. Anti-False Alarm Gate ---
                # Filter tracks through multi-stage validation pipeline
                # Only validated tracks proceed to feature extraction & rule engine
                validated_tracks = self.alarm_gate.get_validated_tracks(
                    self.tracker, processed.shape[:2]
                )

                # Recalculate person count based on validated human tracks only
                person_count = len(validated_tracks)

                # --- 8. Feature extraction (only validated tracks) ---
                black_ratio = compute_black_ratio(processed)
                track_features, scene_features = self.feature_extractor.extract(
                    tracker=self.tracker,
                    detections=tracked,
                    motion_level=motion_level,
                    black_frame_ratio=black_ratio,
                    validated_track_ids=set(validated_tracks.keys()),
                )

                # --- 8.5 Person Re-Identification (Cross-Camera Matching) ---
                if self.reid_manager:
                    # Get the internal track history for validated tracks
                    active_human_tracks = {
                        tid: th for tid, th in self.tracker.get_active_tracks().items()
                        if tid in validated_tracks
                    }
                    
                    # Process Re-ID in background thread
                    reid_matches = await self.reid_manager.process_tracks(
                        camera_id=cam_id,
                        camera_name=cam_name,
                        frame=frame,
                        active_tracks=active_human_tracks,
                    )
                    
                    # Handle new cross-camera matches
                    for match in reid_matches:
                        # Log to DB
                        await self.db.log_reid_match(
                            global_person_id=match.global_person_id,
                            camera_id=cam_id,
                            track_id=1,  # We don't have direct access to local track_id in the match result, but it's not strictly necessary for the global log
                            prev_camera_id=match.prev_camera_id,
                            similarity=match.similarity,
                        )
                        
                        # Send Telegram notification
                        asyncio.create_task(
                            self.telegram.send_reid_alert(
                                global_person_id=match.global_person_id,
                                prev_camera_name=match.prev_camera_name,
                                current_camera_name=cam_name,
                                similarity=match.similarity,
                                seconds_since_last=match.seconds_since_last,
                            )
                        )

                # --- 9. Rule engine ---
                track_scores = self.rule_engine.evaluate(
                    track_features, 
                    scene_features,
                    night_mode_multiplier=self.app_config.night_mode_multiplier
                )
                self.latest_track_scores = track_scores

                # --- 10. Event management ---
                event = self.event_manager.update(
                    camera_id=cam_id,
                    has_motion=has_motion,
                    person_count=person_count,
                    track_scores=track_scores,
                )

                # --- 11. Update best frame for snapshot ---
                if event and event.is_active:
                    max_conf = 0.0
                    if tracked and tracked.confidence is not None and len(tracked.confidence) > 0:
                        max_conf = float(np.max(tracked.confidence))
                    
                    # Annotate frame using the shared Visualizer
                    from src.visualizer import Visualizer
                    
                    orig_h, orig_w = frame.shape[:2]
                    proc_w, proc_h = self.app_config.input_resolution
                    scale_x = orig_w / proc_w
                    scale_y = orig_h / proc_h
                    
                    active_tracks = self.tracker.get_active_tracks()
                    veh_detections = getattr(self, "latest_vehicle_detections", None)
                    riders = getattr(self, "latest_riders", None)
                    vehicle_count = len(veh_detections) if veh_detections is not None else 0
                    
                    annotated_frame = Visualizer.draw_annotated_frame(
                        frame=frame,
                        active_tracks=active_tracks,
                        track_scores=self.latest_track_scores,
                        suspicious_threshold=getattr(self.app_config, "suspicious_score_threshold", 60),
                        person_count=person_count,
                        animal_count=sum(1 for t in active_tracks.values() if t.class_type == "animal"),
                        all_detections=self.latest_detections if hasattr(self, "latest_detections") else None,
                        scale_x=scale_x,
                        scale_y=scale_y,
                        vehicle_detections=veh_detections,
                        riders=riders,
                        vehicle_count=vehicle_count,
                        only_riders=True,
                    )

                    self.snapshot_scheduler.update_best_frame(
                        cam_id, event.event_id, annotated_frame, max_conf, None
                    )

                # --- 12. Handle pending alerts ---
                for alert_event in self.event_manager.pop_pending_alerts():
                    if alert_event.is_critical:
                        self.event_recorder.start_recording(alert_event.event_id)
                    await self._handle_alert(alert_event, processed)

                # --- 13. Handle periodic snapshots ---
                for snap_event in self.event_manager.pop_pending_snapshots():
                    await self._handle_periodic_snapshot(snap_event)

                # --- 14. Log tracks (batched) ---
                track_flush_counter += 1
                if track_flush_counter >= 30:  # Flush every ~30 frames
                    await self.db.flush_tracks()
                    track_flush_counter = 0

                # --- 15. Handle Video Recording Completion ---
                is_recording = self.event_recorder.is_recording
                if self._was_recording and not is_recording:
                    video_path = self.event_recorder.current_file_path
                    event_id = self.event_recorder.current_event_id
                    if video_path and event_id:
                        asyncio.create_task(
                            self.telegram.send_video(cam_name, event_id, video_path)
                        )
                self._was_recording = is_recording

                # --- Performance tracking ---
                elapsed = time.monotonic() - loop_start
                self._frame_times.append(elapsed)
                if len(self._frame_times) > 100:
                    self._frame_times.pop(0)

                # Dynamic frame skip: if processing is too slow
                if elapsed > target_interval * 1.5:
                    self._dynamic_skip = min(self._dynamic_skip + 1, 5)
                elif elapsed < target_interval * 0.8:
                    self._dynamic_skip = max(self._dynamic_skip - 1, 0)

                # --- Maintain target FPS ---
                sleep_time = max(0, target_interval - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

        except asyncio.CancelledError:
            logger.info("[%s] Pipeline cancelled", cam_id)
        except Exception as e:
            logger.error("[%s] Pipeline error: %s", cam_id, e, exc_info=True)
        finally:
            self.grabber.stop()
            await self.db.flush_tracks()
            logger.info("[%s] Pipeline stopped", cam_id)

    async def _handle_alert(self, event, frame: np.ndarray) -> None:
        """Process a new alert: snapshot + Telegram + DB."""
        cam_id = self.camera_id
        cam_name = self.camera_config.name

        # Collect bounding boxes for human-focused crop
        human_bboxes = []
        if frame is not None and len(frame.shape) >= 2:
            orig_h, orig_w = frame.shape[:2]
            proc_w, proc_h = self.app_config.input_resolution if hasattr(self.app_config, "input_resolution") else (640, 360)
            scale_x = orig_w / proc_w if proc_w > 0 else 1.0
            scale_y = orig_h / proc_h if proc_h > 0 else 1.0

            active_tracks = self.tracker.get_active_tracks() if hasattr(self.tracker, "get_active_tracks") else {}
            target_ids = event.track_ids if getattr(event, "track_ids", None) else active_tracks.keys()
            for tid in target_ids:
                th = active_tracks.get(tid)
                if th and getattr(th, "latest_bbox", None):
                    bx1, by1, bx2, by2 = th.latest_bbox
                    human_bboxes.append([
                        bx1 * scale_x,
                        by1 * scale_y,
                        bx2 * scale_x,
                        by2 * scale_y
                    ])

        # Capture cropped human snapshot specifically for Telegram (must be before capture_snapshot clears buffer)
        crop_snapshot_path = None
        if human_bboxes and hasattr(self.snapshot_scheduler, "capture_human_crop"):
            crop_snapshot_path = self.snapshot_scheduler.capture_human_crop(
                camera_id=cam_id,
                event_id=event.event_id,
                bboxes=human_bboxes,
                frame_override=None,
                padding=0.25,
            )

        # Capture full snapshot (clears buffer)
        snapshot_path = self.snapshot_scheduler.capture_snapshot(
            camera_id=cam_id,
            event_id=event.event_id,
            snapshot_type="alert",
            frame_override=None,
        )

        telegram_snapshot = crop_snapshot_path or snapshot_path

        vehicle_info = None
        riders = getattr(self, "latest_riders", None)
        if riders:
            vehicle_info = VehicleDetector.describe_riders(riders)

        # Send Telegram alert (using cropped human image when available)
        await self.telegram.send_alert(
            camera_name=cam_name,
            score=event.score,
            triggered_rules=event.triggered_rules,
            track_ids=list(event.track_ids),
            snapshot_path=telegram_snapshot,
            event_id=event.event_id,
            alert_level="CRITICAL" if event.is_critical else "SUSPICIOUS",
            vehicle_info=vehicle_info,
        )

        # Log to database
        await self.db.create_event(
            event_id=event.event_id,
            camera_id=cam_id,
            state=event.state.value,
            score=event.score,
            triggered_rules=event.triggered_rules,
            track_ids=list(event.track_ids),
        )

        if snapshot_path:
            await self.db.log_snapshot(
                event_id=event.event_id,
                camera_id=cam_id,
                file_path=snapshot_path,
                snapshot_type="alert",
                score=event.score,
                sent_telegram=True,
            )

        # Log rule triggers
        for rule_id in event.triggered_rules:
            await self.db.log_rule_trigger(
                event_id=event.event_id,
                rule_id=rule_id,
                score_delta=0,  # Will be refined
                reason=rule_id,
            )

        event.last_snapshot_time = time.time()
        event.alert_sent = True
        logger.info("[%s] Alert processed: event=%s", cam_id, event.event_id[:8])

    async def _handle_periodic_snapshot(self, event) -> None:
        """Capture and send a periodic snapshot."""
        cam_id = self.camera_id
        cam_name = self.camera_config.name

        snapshot_path = self.snapshot_scheduler.capture_snapshot(
            camera_id=cam_id,
            event_id=event.event_id,
            snapshot_type="periodic",
        )

        if snapshot_path:
            await self.telegram.send_periodic_snapshot(
                camera_name=cam_name,
                event_id=event.event_id,
                score=event.score,
                snapshot_path=snapshot_path,
                snapshot_number=event.snapshot_count,
            )

            await self.db.log_snapshot(
                event_id=event.event_id,
                camera_id=cam_id,
                file_path=snapshot_path,
                snapshot_type="periodic",
                score=event.score,
                sent_telegram=True,
            )

            logger.info(
                "[%s] Periodic snapshot #%d sent: event=%s",
                cam_id,
                event.snapshot_count,
                event.event_id[:8],
            )

    def get_stats(self) -> dict:
        """Get pipeline performance statistics."""
        avg_time = sum(self._frame_times) / len(self._frame_times) if self._frame_times else 0
        return {
            "camera_id": self.camera_id,
            "name": self.camera_config.name,
            "avg_process_time_ms": round(avg_time * 1000, 1),
            "actual_fps": round(1.0 / avg_time, 1) if avg_time > 0 else 0,
            "dynamic_skip": self._dynamic_skip,
            "grabber": self.grabber.get_health_info(),
            "active_tracks": self.tracker.active_count,
            "total_tracks": self.tracker.total_tracks,
            "active_vehicles": len(self.latest_vehicle_detections) if self.latest_vehicle_detections is not None else 0,
            "active_riders": len(self.latest_riders),
        }


# ---------------------------------------------------------------------------
# Browser Auto-Open Helper — delegasi ke src.browser_utils untuk testability
# ---------------------------------------------------------------------------

from src.browser_utils import open_browser_when_ready as _open_browser_when_ready  # noqa: E402


# ---------------------------------------------------------------------------
# Main Application
# ---------------------------------------------------------------------------

class CCTVApplication:
    """Main application orchestrator."""

    def __init__(self, config_dir: str = "."):
        self.config_dir = Path(config_dir)
        self.config: Optional[AppConfig] = None
        self.db: Optional[DBLogger] = None
        self.telegram: Optional[TelegramNotifier] = None
        self.detector: Optional[PersonDetector] = None
        self.vehicle_detector: Optional[VehicleDetector] = None
        self.event_manager: Optional[EventManager] = None
        self.rule_engine: Optional[RuleEngine] = None
        self.snapshot_scheduler: Optional[SnapshotScheduler] = None
        self.storage_manager: Optional[StorageManager] = None
        self.reid_manager: Optional[ReIDManager] = None
        self.tunnel_manager: Optional[Any] = None
        self.pipelines: Dict[str, CameraPipeline] = {}
        self.pipeline_tasks: Dict[str, asyncio.Task] = {}
        self.shutdown_event = asyncio.Event()
        # Flag: buka tab tunnel URL di browser hanya sekali (even on reconnect)
        self._tunnel_browser_opened: bool = False

    async def initialize(self) -> None:
        """Initialize all components."""
        logger.info("=" * 60)
        logger.info("  AI CCTV Detection System — Initializing")
        logger.info("=" * 60)

        # 1. Load configuration
        config_path = self.config_dir / "config" / "config.yaml"
        rules_path = self.config_dir / "config" / "rules.yaml"
        env_path = self.config_dir / ".env"

        # Record PID for process management
        try:
            pid_file = self.config_dir / "data" / "cctv.pid"
            pid_file.parent.mkdir(parents=True, exist_ok=True)
            pid_file.write_text(str(os.getpid()), encoding="utf-8")
        except Exception as e:
            logger.debug("Could not record PID: %s", e)

        loader = ConfigLoader(
            config_path=str(config_path),
            rules_path=str(rules_path),
            env_path=str(env_path),
        )
        self.config = loader.load()

        # 2. Initialize database
        self.db = DBLogger(self.config.database.path)
        await self.db.initialize()

        # 3. Initialize Telegram
        self.telegram = TelegramNotifier(
            bot_token=self.config.telegram.bot_token,
            chat_id=self.config.telegram.chat_id,
            retry_count=self.config.telegram.retry_count,
            retry_backoff_base=self.config.telegram.retry_backoff_base,
            rate_limit_interval=self.config.telegram.rate_limit_interval,
            send_timeout=self.config.telegram.send_timeout,
        )
        await self.telegram.initialize()

        # 4. Initialize YOLO detector (shared across cameras)
        self.detector = PersonDetector(
            model_name=self.config.model_name,
            device_mode=self.config.device_mode,
            confidence_threshold=self.config.confidence_threshold,
            img_size=self.config.input_resolution[0],
        )

        self.vehicle_detector = VehicleDetector(
            confidence_threshold=self.config.confidence_threshold,
            device="cuda" if self.config.device_mode == "cuda" else "cpu",
            img_size=self.config.input_resolution[0],
        )

        # 5. Initialize rule engine
        self.rule_engine = RuleEngine(
            rules=self.config.rules,
            suspicious_threshold=self.config.suspicious_score_threshold,
            critical_threshold=self.config.critical_score_threshold,
        )

        # 6. Initialize event manager
        self.event_manager = EventManager(
            suspicious_threshold=self.config.suspicious_score_threshold,
            critical_threshold=self.config.critical_score_threshold,
            stability_window_sec=self.config.stability_window_sec,
            alert_cooldown_sec=self.config.alert_cooldown_sec,
            snapshot_interval_sec=self.config.snapshot_interval_sec,
        )

        # 7. Initialize snapshot scheduler
        self.snapshot_scheduler = SnapshotScheduler(
            snapshot_dir=self.config.database.snapshot_dir,
            quality=self.config.snapshot_quality,
        )

        # 7.5 Initialize Re-ID Manager
        self.reid_manager = ReIDManager(
            device="cuda" if self.config.device_mode == "cuda" else "cpu"
        )

        # 8. Create camera pipelines
        enabled_cameras = [c for c in self.config.cameras if c.enabled]
        logger.info("Creating pipelines for %d cameras", len(enabled_cameras))

        for cam_config in enabled_cameras:
            pipeline = CameraPipeline(
                camera_config=cam_config,
                app_config=self.config,
                detector=self.detector,
                event_manager=self.event_manager,
                vehicle_detector=self.vehicle_detector,
                rule_engine=self.rule_engine,
                snapshot_scheduler=self.snapshot_scheduler,
                telegram=self.telegram,
                db=self.db,
                reid_manager=self.reid_manager,
            )
            self.pipelines[cam_config.camera_id] = pipeline

        # 9. Initialize storage manager
        self.storage_manager = StorageManager(
            config=self.config.storage,
            db=self.db,
            telegram=self.telegram,
            data_dir=str(self.config_dir / "data")
        )

        # 10. Initialize Cloudflare Tunnel Manager for seamless mobile access
        try:
            from src.tunnel_manager import TunnelManager
            tunnel_token = os.getenv("CLOUDFLARE_TUNNEL_TOKEN")
            self.tunnel_manager = TunnelManager(
                port=8000,
                cloudflared_path="cloudflared.exe",
                tunnel_token=tunnel_token,
                on_url_ready=self._on_tunnel_url_ready,
            )
        except Exception as e:
            logger.warning("Failed to initialize TunnelManager: %s", e)

        logger.info("Initialization complete — %d pipelines ready", len(self.pipelines))

    async def _on_tunnel_url_ready(self, url: str) -> None:
        """Invoked when Cloudflare Tunnel establishes a public HTTPS URL."""
        if self.shutdown_event.is_set():
            return
        if self.config:
            self.config.public_url = url
        if self.telegram:
            self.telegram.public_url = url
            await self.telegram.send_mobile_link(url)
        logger.info("=" * 60)
        logger.info("  📱 MOBILE ACCESS URL: %s", url)
        logger.info("=" * 60)

        # Buka tab browser untuk URL tunnel — hanya sekali meskipun tunnel reconnect
        if not self._tunnel_browser_opened:
            self._tunnel_browser_opened = True
            asyncio.create_task(
                _open_browser_when_ready(url, delay=0.5),
                name="open_browser_tunnel",
            )

    async def run(self) -> None:
        """Run all camera pipelines concurrently."""
        if not self.pipelines:
            logger.warning("No camera pipelines to run. Check config/config.yaml")
            return

        logger.info("=" * 60)
        logger.info("  AI CCTV Detection System — Starting")
        logger.info("  Cameras: %d | Device: %s | Threshold: %.0f",
                    len(self.pipelines),
                    self.config.device_mode if self.config else "unknown",
                    self.config.suspicious_score_threshold if self.config else 70)
        logger.info("=" * 60)

        # Create tasks for all pipelines
        tasks = []
        for cam_id, pipeline in self.pipelines.items():
            task = asyncio.create_task(
                pipeline.run(self.shutdown_event),
                name=f"pipeline-{cam_id}",
            )
            self.pipeline_tasks[cam_id] = task
            tasks.append(task)
            
        # Start storage manager
        if self.storage_manager:
            self.storage_manager.start()

        # Add periodic maintenance task
        tasks.append(asyncio.create_task(
            self._maintenance_loop(),
            name="maintenance",
        ))

        # Add stats logging task
        tasks.append(asyncio.create_task(
            self._stats_loop(),
            name="stats",
        ))

        # Add FastAPI Web Server task
        server = None
        try:
            import uvicorn
            from src.api.server import create_app
            api_app = create_app(self)
            
            # Configure uvicorn (log_config=None avoids crash when stdout is None in pythonw)
            config = uvicorn.Config(
                app=api_app, 
                host="0.0.0.0", 
                port=8000, 
                log_level="error",
                log_config=None,
                access_log=False,
            )
            server = uvicorn.Server(config)
            
            # Run server in the event loop
            tasks.append(asyncio.create_task(
                server.serve(),
                name="api_server"
            ))
            logger.info("FastAPI Web Server starting on http://0.0.0.0:8000")
            logger.info("  🖥️  LOCAL  : http://localhost:8000")
            logger.info("  📱 MOBILE : URL tunnel akan dikirim ke Telegram otomatis")

            # Otomatis buka dashboard di browser lokal setelah server bind (~2 detik)
            asyncio.create_task(
                _open_browser_when_ready("http://localhost:8000", delay=2.0),
                name="open_browser_local",
            )

        except ImportError as exc:
            logger.error("FastAPI/Uvicorn or dependency not installed (%s). Dashboard API disabled.", exc, exc_info=True)
        except Exception as exc:
            logger.error("Failed to start FastAPI Web Server: %s", exc, exc_info=True)

        # Add Cloudflare Tunnel task for seamless mobile access
        if self.tunnel_manager:
            tasks.append(asyncio.create_task(
                self.tunnel_manager.start(),
                name="cloudflare_tunnel"
            ))

        # Add shutdown watcher task to immediately unblock gather and exit components
        server_instance = server

        async def _shutdown_watcher():
            await self.shutdown_event.wait()
            logger.info("Shutdown event triggered — stopping web server and background tasks...")
            if server_instance is not None:
                server_instance.should_exit = True
            for t in tasks:
                if t is not asyncio.current_task() and not t.done():
                    t.cancel()

        watcher_task = asyncio.create_task(_shutdown_watcher(), name="shutdown_watcher")
        tasks.append(watcher_task)
            
        try:
            # Wait for all tasks (or until shutdown)
            await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            logger.info("Application cancelled")
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Gracefully shut down all components."""
        logger.info("Initiating shutdown sequence...")
        self.shutdown_event.set()

        if self.telegram:
            try:
                self.telegram.stop()
            except Exception as e:
                logger.debug("Error stopping telegram notifier: %s", e)

        if self.tunnel_manager:
            try:
                await self.tunnel_manager.stop()
            except Exception as e:
                logger.debug("Error stopping tunnel manager: %s", e)

        if self.storage_manager:
            self.storage_manager.stop()

        # Stop all grabbers
        for pipeline in self.pipelines.values():
            pipeline.grabber.stop()

        # Close database
        if self.db:
            await self.db.close()

        # Remove PID file
        try:
            pid_file = self.config_dir / "data" / "cctv.pid"
            if pid_file.exists():
                pid_file.unlink()
        except Exception as e:
            logger.debug("Could not remove PID file: %s", e)

        logger.info("Shutdown complete")

    # ----- Hot Reload: Dynamic Camera Management -----

    def _build_camera_config(self, cam_data: dict) -> CameraConfig:
        """Build a CameraConfig from a raw dict (as stored in config.yaml)."""
        from src.config_loader import ROIZone
        roi_zones = {}
        for zname, zdata in cam_data.get("roi_zones", {}).items():
            if isinstance(zdata, dict):
                roi_zones[zname] = ROIZone(
                    name=zname,
                    points=zdata.get("points", []),
                    zone_type=zdata.get("zone_type", "general"),
                )
        return CameraConfig(
            camera_id=cam_data["camera_id"],
            name=cam_data.get("name", cam_data["camera_id"]),
            rtsp_url=cam_data.get("rtsp_url", ""),
            enabled=cam_data.get("enabled", True),
            active_hours=cam_data.get("active_hours"),
            roi_zones=roi_zones,
            crossing_lines=cam_data.get("crossing_lines", {}),
            resolution=cam_data.get("resolution"),
            fps=cam_data.get("fps"),
            confidence_threshold=cam_data.get("confidence_threshold"),
            night_mode=cam_data.get("night_mode"),
            loitering_time_sec=cam_data.get("loitering_time_sec"),
            alert_threshold=cam_data.get("alert_threshold"),
            recording_duration_sec=cam_data.get("recording_duration_sec"),
            alarm_gate_confidence=cam_data.get("alarm_gate_confidence"),
            alarm_gate_min_frames=cam_data.get("alarm_gate_min_frames"),
        )

    async def add_camera_pipeline(self, cam_data: dict) -> str:
        """Dynamically add and start a new camera pipeline at runtime."""
        cam_config = self._build_camera_config(cam_data)
        cam_id = cam_config.camera_id

        if cam_id in self.pipelines:
            return f"Pipeline '{cam_id}' already running"

        if not cam_config.enabled:
            return f"Camera '{cam_id}' is disabled, not starting pipeline"

        pipeline = CameraPipeline(
            camera_config=cam_config,
            app_config=self.config,
            detector=self.detector,
            event_manager=self.event_manager,
            vehicle_detector=self.vehicle_detector,
            rule_engine=self.rule_engine,
            snapshot_scheduler=self.snapshot_scheduler,
            telegram=self.telegram,
            db=self.db,
        )
        self.pipelines[cam_id] = pipeline

        task = asyncio.create_task(
            pipeline.run(self.shutdown_event),
            name=f"pipeline-{cam_id}",
        )
        self.pipeline_tasks[cam_id] = task
        logger.info("[%s] Pipeline hot-started (no restart needed)", cam_id)
        return f"Camera '{cam_config.name}' ({cam_id}) started successfully"

    async def remove_camera_pipeline(self, cam_id: str) -> str:
        """Dynamically stop and remove a camera pipeline at runtime."""
        if cam_id not in self.pipelines:
            return f"Pipeline '{cam_id}' not found (may not be running)"

        pipeline = self.pipelines[cam_id]
        pipeline.grabber.stop()

        task = self.pipeline_tasks.get(cam_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

        del self.pipelines[cam_id]
        self.pipeline_tasks.pop(cam_id, None)
        logger.info("[%s] Pipeline hot-removed (no restart needed)", cam_id)
        return f"Camera '{cam_id}' stopped and removed"

    async def update_camera_pipeline(self, cam_id: str, cam_data: dict) -> str:
        """Dynamically update a camera pipeline (stop old → start new)."""
        await self.remove_camera_pipeline(cam_id)
        result = await self.add_camera_pipeline(cam_data)
        logger.info("[%s] Pipeline hot-reloaded (no restart needed)", cam_id)
        return result

    async def _maintenance_loop(self) -> None:
        """Periodic maintenance: DB cleanup, snapshot cleanup, etc."""
        while not self.shutdown_event.is_set():
            try:
                await asyncio.sleep(3600)  # Every hour

                if self.db and self.config:
                    deleted = await self.db.cleanup_old_records(
                        days=self.config.database.cleanup_days
                    )
                    if deleted > 0:
                        logger.info("Maintenance: cleaned %d old records", deleted)

                if self.snapshot_scheduler and self.config:
                    self.snapshot_scheduler.cleanup_old_snapshots(
                        max_age_days=self.config.database.cleanup_days
                    )

                if self.rule_engine:
                    self.rule_engine.cleanup_cooldowns()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Maintenance error: %s", e)

    async def _stats_loop(self) -> None:
        """Periodically log system statistics."""
        while not self.shutdown_event.is_set():
            try:
                await asyncio.sleep(60)  # Every minute

                for cam_id, pipeline in self.pipelines.items():
                    stats = pipeline.get_stats()
                    logger.info(
                        "[%s] Stats: fps=%.1f, process=%.0fms, tracks=%d, skip=%d",
                        cam_id,
                        stats["actual_fps"],
                        stats["avg_process_time_ms"],
                        stats["active_tracks"],
                        stats["dynamic_skip"],
                    )

                if self.telegram:
                    tg_stats = self.telegram.get_stats()
                    logger.info(
                        "Telegram: sent=%d, errors=%d",
                        tg_stats["sent_count"],
                        tg_stats["error_count"],
                    )

                if self.event_manager:
                    cam_states = self.event_manager.get_all_camera_states()
                    for cid, state in cam_states.items():
                        if state["state"] != "NORMAL":
                            logger.info(
                                "[%s] State=%s, event=%s",
                                cid,
                                state["state"],
                                state.get("event_id", "none"),
                            )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Stats loop error: %s", e)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main():
    """Application entry point."""
    # Determine project root
    project_root = Path(__file__).parent.parent

    # Setup logging
    setup_logging(level="INFO", log_file=str(project_root / "data" / "cctv_ai.log"))

    logger.info("AI CCTV Detection System starting...")
    logger.info("Project root: %s", project_root)

    # Create data directories
    (project_root / "data").mkdir(exist_ok=True)
    (project_root / "snapshots").mkdir(exist_ok=True)

    # Change to project root for relative paths in config
    os.chdir(str(project_root))

    # Create and run application
    app = CCTVApplication(config_dir=str(project_root))

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Received signal %s — initiating shutdown", sig)
        app.shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run async event loop
    try:
        asyncio.run(_run_app(app))
        logger.info("Application exited cleanly.")
        os._exit(0)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        os._exit(0)
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        os._exit(1)


async def _run_app(app: CCTVApplication) -> None:
    """Async wrapper for application lifecycle."""
    await app.initialize()
    await app.run()


if __name__ == "__main__":
    main()
