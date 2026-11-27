"""
routes.py — FastAPI routes for the CCTV Dashboard.
Serves MJPEG live streams, events, snapshots, camera management, and Telegram config.
"""

import asyncio
import io
import json
import logging
import os
import re
import psutil
try:
    import GPUtil
except ImportError:
    GPUtil = None
from pathlib import Path
from typing import List, Dict, Any, Optional

import cv2
import numpy as np
import yaml
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from src.main import CCTVApplication
from src.visualizer import Visualizer

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Dependency to get app instance ---
def get_app(request: Request) -> CCTVApplication:
    return request.app.state.cctv_app

# --- Models ---
class CameraStatus(BaseModel):
    camera_id: str
    name: str
    state: str
    fps: float
    active_tracks: int
    is_connected: bool
    active_vehicles: int = 0
    active_riders: int = 0

class CameraAddRequest(BaseModel):
    camera_id: str
    name: str
    rtsp_url: str
    enabled: bool = True
    active_hours: Optional[str] = None
    # Per-camera overrides
    resolution: Optional[List[int]] = None
    fps: Optional[int] = None
    confidence_threshold: Optional[float] = None
    night_mode: Optional[bool] = None
    loitering_time_sec: Optional[float] = None
    alert_threshold: Optional[float] = None
    recording_duration_sec: Optional[int] = None
    alarm_gate_confidence: Optional[float] = None
    alarm_gate_min_frames: Optional[int] = None
    roi_zones: Optional[dict] = None
    crossing_lines: Optional[dict] = None

class StreamProbeRequest(BaseModel):
    stream_url: str

class StreamProbeResponse(BaseModel):
    online: bool
    source_type: str
    resolution: str
    fps: float
    message: str

class TelegramConfigRequest(BaseModel):
    bot_token: str
    chat_id: str
    public_url: Optional[str] = None

class TelegramTestRequest(BaseModel):
    bot_token: str
    chat_id: str
    public_url: Optional[str] = None
    message: str = "🔔 Test notification from CCTV AI Dashboard"

async def mjpeg_generator(app: CCTVApplication, camera_id: str):
    """Generator for MJPEG stream from the latest camera frame."""
    pipeline = app.pipelines.get(camera_id)
    if not pipeline:
        yield b""
        return

    # Frame interval for ~20 FPS low-latency stream to the browser
    frame_time = 1.0 / 20.0

    while not app.shutdown_event.is_set():
        start_time = asyncio.get_event_loop().time()

        # Fetch pipeline dynamically in case it was hot-reloaded
        pipeline = app.pipelines.get(camera_id)
        if not pipeline:
            await asyncio.sleep(0.1)
            continue

        # Get latest frame from the grabber
        frame, _ = pipeline.grabber.get_latest_frame()

        try:
            if frame is not None:
                # Process copy to avoid mutating the original
                display_frame = frame.copy()
                
                # Get scale factors (processed coords to original frame)
                orig_h, orig_w = display_frame.shape[:2]
                proc_w, proc_h = app.config.input_resolution
                scale_x = orig_w / proc_w
                scale_y = orig_h / proc_h

                # Draw AI Detections (Bounding Boxes)
                import time as _time
                active_tracks = pipeline.tracker.get_active_tracks()
                all_tracks = pipeline.tracker.get_all_tracks()
                now = _time.time()
                
                person_count = sum(1 for t in active_tracks.values() if t.class_type == "human")
                animal_count = sum(1 for t in active_tracks.values() if t.class_type == "animal")
                
                # Draw recently-lost tracks (faded yellow, last 3 seconds)
                for tid, track in all_tracks.items():
                    if track.is_active or tid in active_tracks:
                        continue
                    if (now - track.last_seen) > 3.0:
                        continue
                    bbox = track.latest_bbox
                    if not bbox:
                        continue
                    x1, y1, x2, y2 = bbox
                    x1, x2 = int(x1 * scale_x), int(x2 * scale_x)
                    y1, y2 = int(y1 * scale_y), int(y2 * scale_y)
                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 200, 255), 1)
                    cv2.putText(display_frame, f"Lost #{tid}", (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)
                

                veh_detections = getattr(pipeline, "latest_vehicle_detections", None)
                riders = getattr(pipeline, "latest_riders", None)
                vehicle_count = len(veh_detections) if veh_detections is not None else 0

                display_frame = Visualizer.draw_annotated_frame(
                    frame=display_frame,
                    active_tracks=active_tracks,
                    track_scores=pipeline.latest_track_scores,
                    suspicious_threshold=pipeline.event_manager.suspicious_threshold,
                    person_count=person_count,
                    animal_count=animal_count,
                    all_detections=pipeline.latest_detections if hasattr(pipeline, "latest_detections") else None,
                    scale_x=scale_x,
                    scale_y=scale_y,
                    vehicle_detections=veh_detections,
                    riders=riders,
                    vehicle_count=vehicle_count,
                    only_riders=False,
                    vehicle_track_result=getattr(pipeline, "latest_vehicle_tracks", None),
                )

                # Encode frame to JPEG (75% quality for ultra-low latency & bandwidth savings)
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 75]
                _, buffer = cv2.imencode('.jpg', display_frame, encode_param)
                frame_bytes = buffer.tobytes()

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                await asyncio.sleep(0.1)
        except Exception as e:
            logger.error("Error in mjpeg_generator: %s", e)
            await asyncio.sleep(0.1)

        # Control streaming FPS
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed < frame_time:
            await asyncio.sleep(frame_time - elapsed)


@router.get("/stream/{camera_id}")
async def video_stream(camera_id: str, app: CCTVApplication = Depends(get_app)):
    """Live MJPEG video stream for a specific camera."""
    if camera_id not in app.pipelines:
        raise HTTPException(status_code=404, detail="Camera not found")

    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }

    return StreamingResponse(
        mjpeg_generator(app, camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers=headers
    )

# --- Status & Config ---
@router.get("/status", response_model=List[CameraStatus])
async def get_status(app: CCTVApplication = Depends(get_app)):
    """Get the current status of all cameras."""
    status_list = []

    if not app.event_manager:
        return []

    cam_states = app.event_manager.get_all_camera_states()

    for cam_id, pipeline in app.pipelines.items():
        stats = pipeline.get_stats()
        state_info = cam_states.get(cam_id, {"state": "UNKNOWN"})

        status_list.append(CameraStatus(
            camera_id=cam_id,
            name=pipeline.camera_config.name,
            state=state_info["state"],
            fps=stats["actual_fps"],
            active_tracks=stats["active_tracks"],
            is_connected=stats["grabber"]["connected"],
            active_vehicles=stats.get("active_vehicles", 0),
            active_riders=stats.get("active_riders", 0),
        ))

    return status_list

@router.get("/config")
async def get_config(app: CCTVApplication = Depends(get_app)):
    """Get the current system configuration."""
    if not app.config:
        return {}

    import dataclasses
    return dataclasses.asdict(app.config)

# --- Events & Snapshots ---
@router.get("/events")
async def get_recent_events(limit: int = 50, app: CCTVApplication = Depends(get_app)):
    """Get recent suspicious events from the database."""
    if not app.db:
        return []

    cursor = await app.db.db.execute(
        """
        SELECT e.*, c.name as camera_name 
        FROM events e
        JOIN cameras c ON e.camera_id = c.camera_id
        ORDER BY e.started_at DESC LIMIT ?
        """,
        (limit,)
    )
    rows = await cursor.fetchall()

    events = []
    for row in rows:
        event = dict(row)
        event['triggered_rules'] = json.loads(event['triggered_rules']) if event['triggered_rules'] else []

        snap_cursor = await app.db.db.execute(
            "SELECT snapshot_id FROM snapshots WHERE event_id = ? AND snapshot_type = 'alert' LIMIT 1",
            (event['event_id'],)
        )
        snap_row = await snap_cursor.fetchone()
        event['has_snapshot'] = snap_row is not None
        if snap_row:
            event['snapshot_id'] = snap_row[0]

        # Check for video recording
        recording_dir = Path("data/recordings")
        event['has_video'] = False
        if recording_dir.exists():
            for _ in recording_dir.glob(f"*{event['event_id']}*.mp4"):
                event['has_video'] = True
                break

        events.append(event)

    return events

@router.get("/snapshots/{snapshot_id}")
async def get_snapshot(snapshot_id: int, app: CCTVApplication = Depends(get_app)):
    """Get a snapshot image by ID."""
    if not app.db:
        raise HTTPException(status_code=500, detail="Database not initialized")

    cursor = await app.db.db.execute(
        "SELECT file_path FROM snapshots WHERE snapshot_id = ?",
        (snapshot_id,)
    )
    row = await cursor.fetchone()

    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    file_path = row[0]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Snapshot file missing on disk")

    return FileResponse(file_path, media_type="image/jpeg")

# =============================================
# Camera Management API
# =============================================

@router.get("/cameras")
async def get_cameras(app: CCTVApplication = Depends(get_app)):
    """Get the list of all configured cameras from config.yaml."""
    config_path = Path(app.config_dir) / "config" / "config.yaml"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        cameras = config_data.get("cameras", [])
        return {"cameras": cameras}
    except Exception as e:
        logger.error("Failed to read config: %s", e)
        return {"cameras": [], "error": str(e)}


@router.post("/cameras/probe", response_model=StreamProbeResponse)
async def probe_camera_stream(req: StreamProbeRequest):
    """Probe a stream URL to check if it's reachable and active before adding."""
    source_str = req.stream_url.strip()
    if not source_str:
        return StreamProbeResponse(
            online=False,
            source_type="UNKNOWN",
            resolution="N/A",
            fps=0.0,
            message="URL stream tidak boleh kosong.",
        )

    # 1. Check if it's a USB webcam index
    if source_str.isdigit():
        idx = int(source_str)
        try:
            cap = cv2.VideoCapture(idx)
            is_open = cap.isOpened()
            cap.release()
            if is_open:
                return StreamProbeResponse(
                    online=True,
                    source_type="WEBCAM",
                    resolution="Device OK",
                    fps=30.0,
                    message=f"Webcam USB ID {idx} terdeteksi dan siap digunakan.",
                )
            else:
                return StreamProbeResponse(
                    online=False,
                    source_type="WEBCAM",
                    resolution="N/A",
                    fps=0.0,
                    message=f"Webcam USB ID {idx} tidak dapat dibuka (device sibuk atau tidak terpasang).",
                )
        except Exception as e:
            return StreamProbeResponse(
                online=False,
                source_type="WEBCAM",
                resolution="N/A",
                fps=0.0,
                message=f"Error mendeteksi webcam: {e}",
            )

    # 2. Pre-check HTTP / HTTPS streams (e.g. HLS .m3u8) for 404 / connection errors
    if source_str.startswith("http://") or source_str.startswith("https://"):
        import urllib.request
        import urllib.error
        import ssl
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            http_req = urllib.request.Request(
                source_str,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(http_req, context=ctx, timeout=3.0) as resp:
                if resp.status != 200:
                    return StreamProbeResponse(
                        online=False,
                        source_type="HLS",
                        resolution="N/A",
                        fps=0.0,
                        message=f"Server penyedia merespons HTTP {resp.status} (Stream offline).",
                    )
        except urllib.error.HTTPError as e:
            return StreamProbeResponse(
                online=False,
                source_type="HLS",
                resolution="N/A",
                fps=0.0,
                message=f"Server penyedia merespons HTTP {e.code}: {e.reason} (Kamera offline di server asal / URL salah).",
            )
        except Exception as e:
            return StreamProbeResponse(
                online=False,
                source_type="HLS",
                resolution="N/A",
                fps=0.0,
                message=f"Gagal menghubungkan ke server stream: {e}",
            )

    # 3. Test OpenCV opening
    try:
        def _test_cap():
            cap = cv2.VideoCapture(source_str, cv2.CAP_FFMPEG)
            if not cap.isOpened():
                return False, 0, 0, 0
            w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            f = cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            return True, int(w), int(h), float(f)

        loop = asyncio.get_event_loop()
        opened, w, h, fps = await loop.run_in_executor(None, _test_cap)

        if opened:
            stype = "RTSP" if source_str.startswith("rtsp://") else ("HLS" if ".m3u8" in source_str else "STREAM")
            res_str = f"{w}x{h}" if w > 0 and h > 0 else "Online"
            return StreamProbeResponse(
                online=True,
                source_type=stype,
                resolution=res_str,
                fps=fps if fps > 0 else 25.0,
                message=f"Stream aktif dan terhubung ({res_str} @ {fps:.1f} FPS)",
            )
        else:
            return StreamProbeResponse(
                online=False,
                source_type="STREAM",
                resolution="N/A",
                fps=0.0,
                message="Kamera tidak dapat dihubungkan (Periksa IP/URL dan jaringan).",
            )
    except Exception as e:
        return StreamProbeResponse(
            online=False,
            source_type="STREAM",
            resolution="N/A",
            fps=0.0,
            message=f"Error pengujian stream: {e}",
        )


@router.post("/cameras")
@router.post("/cameras/")
async def add_camera(req: CameraAddRequest, app: CCTVApplication = Depends(get_app)):
    """Add a new camera to config.yaml (requires restart to take effect)."""
    config_path = Path(app.config_dir) / "config" / "config.yaml"

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        cameras = config_data.get("cameras", [])

        # Check for duplicate camera_id
        for cam in cameras:
            if cam["camera_id"] == req.camera_id:
                raise HTTPException(status_code=400, detail=f"Camera ID '{req.camera_id}' already exists")

        # Add new camera
        new_cam = {
            "camera_id": req.camera_id,
            "name": req.name,
            "rtsp_url": req.rtsp_url,
            "enabled": req.enabled,
            "active_hours": req.active_hours,
        }
        # Add per-camera overrides (only if provided)
        if req.resolution is not None:
            new_cam["resolution"] = req.resolution
        if req.fps is not None:
            new_cam["fps"] = req.fps
        if req.confidence_threshold is not None:
            new_cam["confidence_threshold"] = req.confidence_threshold
        if req.night_mode is not None:
            new_cam["night_mode"] = req.night_mode
        if req.loitering_time_sec is not None:
            new_cam["loitering_time_sec"] = req.loitering_time_sec
        if req.alert_threshold is not None:
            new_cam["alert_threshold"] = req.alert_threshold
        if req.recording_duration_sec is not None:
            new_cam["recording_duration_sec"] = req.recording_duration_sec
        if req.alarm_gate_confidence is not None:
            new_cam["alarm_gate_confidence"] = req.alarm_gate_confidence
        if req.alarm_gate_min_frames is not None:
            new_cam["alarm_gate_min_frames"] = req.alarm_gate_min_frames
        if req.roi_zones is not None:
            new_cam["roi_zones"] = req.roi_zones
        else:
            new_cam["roi_zones"] = {
                "restricted_zone": {
                    "points": [[100, 200], [400, 200], [400, 500], [100, 500]]
                }
            }
        if req.crossing_lines is not None:
            new_cam["crossing_lines"] = req.crossing_lines
        cameras.append(new_cam)
        config_data["cameras"] = cameras

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

        # Hot-reload: start the new camera pipeline immediately
        result = await app.add_camera_pipeline(new_cam)

        return {"status": "ok", "message": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to add camera: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

def _set_or_remove(d: dict, k: str, v: Any):
    if v is not None:
        d[k] = v
    elif k in d:
        del d[k]

@router.put("/cameras/{camera_id}")
@router.put("/cameras/{camera_id}/")
async def update_camera(camera_id: str, req: CameraAddRequest, app: CCTVApplication = Depends(get_app)):
    """Update an existing camera's RTSP URL or name in config.yaml."""
    config_path = Path(app.config_dir) / "config" / "config.yaml"

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        cameras = config_data.get("cameras", [])
        found = False
        for cam in cameras:
            if cam["camera_id"] == camera_id:
                cam["name"] = req.name
                cam["rtsp_url"] = req.rtsp_url
                cam["enabled"] = req.enabled
                cam["active_hours"] = req.active_hours
                # Update per-camera overrides
                _set_or_remove(cam, "resolution", req.resolution)
                _set_or_remove(cam, "fps", req.fps)
                _set_or_remove(cam, "confidence_threshold", req.confidence_threshold)
                _set_or_remove(cam, "night_mode", req.night_mode)
                _set_or_remove(cam, "loitering_time_sec", req.loitering_time_sec)
                _set_or_remove(cam, "alert_threshold", req.alert_threshold)
                _set_or_remove(cam, "recording_duration_sec", req.recording_duration_sec)
                _set_or_remove(cam, "alarm_gate_confidence", req.alarm_gate_confidence)
                _set_or_remove(cam, "alarm_gate_min_frames", req.alarm_gate_min_frames)
                if req.roi_zones is not None:
                    cam["roi_zones"] = req.roi_zones
                if req.crossing_lines is not None:
                    cam["crossing_lines"] = req.crossing_lines
                found = True
                break

        if not found:
            raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")

        config_data["cameras"] = cameras
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

        # Hot-reload: find the updated cam data and restart its pipeline
        updated_cam = None
        for cam in cameras:
            if cam["camera_id"] == camera_id:
                updated_cam = cam
                break
        if updated_cam:
            result = await app.update_camera_pipeline(camera_id, updated_cam)
        else:
            result = f"Camera '{camera_id}' updated in config."

        return {"status": "ok", "message": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cameras/{camera_id}")
@router.delete("/cameras/{camera_id}/")
async def delete_camera(camera_id: str, app: CCTVApplication = Depends(get_app)):
    """Remove a camera from config.yaml."""
    config_path = Path(app.config_dir) / "config" / "config.yaml"

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        cameras = config_data.get("cameras", [])
        new_cameras = [c for c in cameras if c["camera_id"] != camera_id]

        if len(new_cameras) == len(cameras):
            raise HTTPException(status_code=404, detail="Camera not found")

        config_data["cameras"] = new_cameras
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

        # Hot-reload: stop the pipeline immediately
        result = await app.remove_camera_pipeline(camera_id)

        return {"status": "ok", "message": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================
# Telegram Configuration API
# =============================================

@router.get("/telegram")
async def get_telegram_config(app: CCTVApplication = Depends(get_app)):
    """Get the current Telegram configuration (token masked)."""
    env_path = Path(app.config_dir) / ".env"
    bot_token = ""
    chat_id = ""
    public_url = ""

    try:
        if env_path.exists():
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("TELEGRAM_BOT_TOKEN="):
                        bot_token = line.split("=", 1)[1]
                    elif line.startswith("TELEGRAM_CHAT_ID="):
                        chat_id = line.split("=", 1)[1]
                    elif line.startswith("PUBLIC_URL="):
                        public_url = line.split("=", 1)[1]
    except Exception as e:
        logger.error("Failed to read .env: %s", e)

    # Mask token for display
    masked_token = ""
    if bot_token and len(bot_token) > 10:
        masked_token = bot_token[:6] + "..." + bot_token[-4:]

    is_active = bool(app.telegram and app.telegram._enabled)
    stats = app.telegram.get_stats() if app.telegram else {}

    return {
        "bot_token_masked": masked_token,
        "bot_token_full": bot_token,
        "chat_id": chat_id,
        "public_url": public_url,
        "is_active": is_active,
        "stats": stats,
    }


@router.post("/telegram")
async def save_telegram_config(req: TelegramConfigRequest, app: CCTVApplication = Depends(get_app)):
    """Save Telegram configuration to .env file."""
    env_path = Path(app.config_dir) / ".env"

    try:
        lines = []
        if env_path.exists():
            with open(env_path, "r") as f:
                lines = f.readlines()

        # Update or add token, chat_id, and public_url
        token_found = False
        chat_found = False
        url_found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith("TELEGRAM_BOT_TOKEN="):
                new_lines.append(f"TELEGRAM_BOT_TOKEN={req.bot_token}\n")
                token_found = True
            elif line.strip().startswith("TELEGRAM_CHAT_ID="):
                new_lines.append(f"TELEGRAM_CHAT_ID={req.chat_id}\n")
                chat_found = True
            elif line.strip().startswith("PUBLIC_URL="):
                if req.public_url is not None:
                    new_lines.append(f"PUBLIC_URL={req.public_url}\n")
                else:
                    new_lines.append("PUBLIC_URL=\n")
                url_found = True
            else:
                new_lines.append(line)

        if not token_found:
            new_lines.append(f"TELEGRAM_BOT_TOKEN={req.bot_token}\n")
        if not chat_found:
            new_lines.append(f"TELEGRAM_CHAT_ID={req.chat_id}\n")
        if not url_found and req.public_url is not None:
            new_lines.append(f"PUBLIC_URL={req.public_url}\n")

        with open(env_path, "w") as f:
            f.writelines(new_lines)

        return {"status": "ok", "message": "Telegram configuration saved. Restart the application to apply."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/telegram/test")
async def test_telegram(req: TelegramTestRequest, app: CCTVApplication = Depends(get_app)):
    """Send a test message to verify Telegram config works."""
    try:
        from telegram import Bot

        bot = Bot(token=req.bot_token)
        me = await bot.get_me()

        msg_text = f"✅ *CCTV AI \\- Test Notification*\n\n{req.message}\n\nBot: @{me.username}"
        if req.public_url:
            msg_text += f"\n🔗 *Dashboard:* [Buka Link]({req.public_url})"

        await bot.send_message(
            chat_id=req.chat_id,
            text=msg_text,
            parse_mode="MarkdownV2",
        )

        return {"status": "ok", "bot_username": me.username, "message": "Test message sent successfully!"}
    except ImportError:
        raise HTTPException(status_code=500, detail="python-telegram-bot not installed")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Telegram error: {str(e)}")

# =============================================
# Dashboard Stats & Recordings API
# =============================================

@router.get("/health")
async def get_system_health(app: CCTVApplication = Depends(get_app)):
    """Get system health, resource usage, and connectivity status."""
    health = {
        "cameras": [],
        "ai_engine": "RUNNING" if app.detector else "OFFLINE",
        "telegram": "CONNECTED" if (app.telegram and app.telegram._enabled) else "OFFLINE",
        "database": "CONNECTED" if app.db else "OFFLINE",
        "storage": {"usage_percent": 0, "status": "UNKNOWN"},
        "cpu": {"percent": psutil.cpu_percent(interval=None)},
        "ram": {"percent": psutil.virtual_memory().percent},
        "gpu": {"percent": 0, "name": "None"},
        "fps_total": 0
    }

    # GPU Stats
    if GPUtil is not None:
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                health["gpu"]["percent"] = round(gpus[0].load * 100, 1)
                health["gpu"]["name"] = gpus[0].name
        except Exception as e:
            logger.debug("Failed to get GPU stats: %s", e)

    # Storage Stats
    if app.storage_manager:
        storage_stats = app.storage_manager.get_storage_stats()
        health["storage"]["usage_percent"] = storage_stats["usage_percent"]
        if storage_stats["usage_percent"] >= app.config.storage.critical_percent:
            health["storage"]["status"] = "CRITICAL"
        elif storage_stats["usage_percent"] >= app.config.storage.warning_percent:
            health["storage"]["status"] = "WARNING"
        else:
            health["storage"]["status"] = "OK"

    # Camera Stats
    total_fps = 0
    for cam_id, pipeline in app.pipelines.items():
        grabber = pipeline.grabber
        cam_health = grabber.get_health_info() if grabber else {}
        is_online = cam_health.get("connected", False)
        fps = cam_health.get("fps", 0)
        total_fps += fps
        
        health["cameras"].append({
            "camera_id": cam_id,
            "name": pipeline.camera_config.name,
            "status": "ONLINE" if is_online else "OFFLINE",
            "fps": fps
        })
        
    health["fps_total"] = total_fps

    return health

@router.get("/stats/today")
async def get_stats_today(app: CCTVApplication = Depends(get_app)):
    """Get today's statistics."""
    try:
        stats = await app.db.get_today_stats()
        return stats
    except Exception as e:
        logger.error("Failed to get today stats: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recordings/{event_id}")
async def get_recording(event_id: str, app: CCTVApplication = Depends(get_app)):
    """Serve the MP4 video recording for an event."""
    recording_dir = Path("data/recordings")
    
    if not recording_dir.exists():
        raise HTTPException(status_code=404, detail="Recording directory not found")
        
    # Search for a file with the event_id
    for file in recording_dir.glob(f"*{event_id}*.mp4"):
        return FileResponse(
            path=file,
            media_type="video/mp4",
            filename=file.name
        )
        
    raise HTTPException(status_code=404, detail=f"Recording for event {event_id} not found")


@router.post("/system/shutdown")
async def system_shutdown(app: CCTVApplication = Depends(get_app)):
    """Gracefully trigger system shutdown from the API."""
    logger.info("Received system shutdown request via API")

    async def _do_shutdown():
        await asyncio.sleep(0.5)
        if hasattr(app, "shutdown_event") and app.shutdown_event is not None:
            app.shutdown_event.set()

    asyncio.create_task(_do_shutdown())
    return {
        "status": "ok",
        "message": "CCTV AI system is shutting down gracefully."
    }

