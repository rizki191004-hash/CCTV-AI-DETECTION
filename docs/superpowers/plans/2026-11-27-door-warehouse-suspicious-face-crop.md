# Door/Warehouse Suspicious Person Detection & Face Crop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Optimize CCTV AI detection for suspicious persons at gates/doors and warehouse goods-taking, capturing a tightly focused person crop, and extracting a high-resolution face crop sent as a single anti-spam Telegram media group (album).

**Architecture:** 
1. Pose-and-geometric face extractor in `src/snapshot_scheduler.py` that validates facial visibility (nose/eyes confidence) and produces a clean facial crop without heavy extra neural network models.
2. Contextual behavioral rules in `src/rule_engine.py` and `config/rules.yaml` for warehouse taking-goods (crouching/merunduk in storage zone, rapid departure) and gate loitering/crossing.
3. Telegram anti-spam media group integration in `src/telegram_notifier.py` bundling person and face crops in 1 notification bubble.
4. Pipeline orchestration in `src/main.py` isolating the primary suspect for facial zoom-in.

**Tech Stack:** Python 3.11, OpenCV (cv2), Supervision, Ultralytics YOLOv8, python-telegram-bot, pytest.

**Spec:** `docs/superpowers/specs/2026-11-27-door-warehouse-suspicious-face-crop-design.md`

## Global Constraints

- Must keep all existing 111 tests passing without regression.
- Zero spamming: Body crop + face crop must be sent in a single Telegram message bubble (media group) with 1 notification sound.
- If person is facing away (back to camera), `capture_face_crop` must return `None` and Telegram must send only the single body photo.
- In multi-person alerts, face crop must isolate the primary suspect with highest suspicion score, not a random bystander.
- No heavy neural network model downloads (>100MB) for face extraction; must run seamlessly on standard CPU.

## Review Focus

1. **Back-turned suspect:** Suspect crouching facing away from camera; `crop_face_region` returns `None` and Telegram sends only body photo without blank attachments.
2. **Multi-person event:** Innocent person standing near door, suspect crouching in warehouse; face crop isolates the crouching suspect.
3. **Media group network fallback:** Telegram API fails media group sending (e.g. rate limit / network error); falls back gracefully to sending single photo.
4. **Missing keypoints (standard YOLO detection without pose):** `crop_face_region` uses upper-body ROI + Haar cascade fallback without crashing.
5. **Boundary clamp on edge of frame:** Suspect's face at very top edge of frame ($y=0$); crop padding is clamped within $[0, H] \times [0, W]$.

---

### Task 1: Face Crop Extraction Module

**Files:**
- Modify: `src/snapshot_scheduler.py`
- Test: `tests/test_face_crop.py`

**Interfaces:**
- Produces:
  - `crop_face_region(frame: np.ndarray, bbox: Sequence[float], keypoints: Optional[np.ndarray] = None, padding: float = 0.3) -> Optional[np.ndarray]`
  - `SnapshotScheduler.capture_face_crop(camera_id: str, event_id: str, bbox: Sequence[float], keypoints: Optional[np.ndarray] = None, frame_override: Optional[np.ndarray] = None, padding: float = 0.3) -> Optional[str]`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_face_crop.py`:
- `test_crop_face_with_frontal_keypoints_returns_face_slice`: Frontal pose keypoints (points 0, 1, 2 confidence > 0.5) returns a non-None valid BGR image slice smaller than frame.
- `test_crop_face_with_back_turned_returns_none`: Keypoints with face confidence < 0.25 (facing away) returns `None`.
- `test_crop_face_boundary_clamped`: Bbox near edge of frame ($y=0$) returns valid image slice clamped to frame boundaries.
- `test_capture_face_crop_saves_file`: `scheduler.capture_face_crop(...)` saves file ending with `_face.jpg` and returns valid path.
- `test_capture_face_crop_returns_none_when_face_not_visible`: Returns `None` when face is not visible.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_face_crop.py -v`  
Expected: FAIL with `AttributeError` or `cannot import name 'crop_face_region'`

- [ ] **Step 3: Implement `crop_face_region` and `capture_face_crop` in `src/snapshot_scheduler.py`**

- If `keypoints` provided and keypoints shape $\ge (3, 2)$:
  - Check facial keypoints: index 0 (nose), 1 (left eye), 2 (right eye).
  - If confidences exist and $\max(conf_0, conf_1, conf_2) < 0.25$, return `None`.
  - Calculate min/max across face keypoints with 30% padding.
- Fallback (no keypoints):
  - Extract upper 30% height of bbox, centered horizontally.
  - Attempt `cv2.CascadeClassifier` on grayscale upper ROI.
  - If frontal face confirmed or reasonable upper head ROI, return cropped slice; if face clearly facing away, return `None`.
- In `capture_face_crop`:
  - Fetch frame from `self._best_frames` or `frame_override`.
  - Call `crop_face_region`. If `None`, return `None`.
  - Save as `{camera_id}_{short_event}_{timestamp}_face.jpg` and return path.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_face_crop.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/snapshot_scheduler.py tests/test_face_crop.py
git commit -m "feat: add face crop extraction and visibility validation"
```

---

### Task 2: Warehouse Goods-Taking & Door Behavior Rules

**Files:**
- Modify: `src/feature_extractor.py`
- Modify: `src/rule_engine.py`
- Modify: `config/rules.yaml`
- Test: `tests/test_warehouse_door_rules.py`

**Interfaces:**
- Consumes: `TrackHistory`, `TrackFeatures`, `RuleEngine`
- Produces:
  - Rules: `warehouse_taking_goods`, `warehouse_rapid_departure`, `gate_door_loitering`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_warehouse_door_rules.py`:
- `test_warehouse_taking_goods_rule_triggers`: Person in `warehouse_zone` with posture `CROUCHING_CRAWLING` triggers `warehouse_taking_goods` (+60 score).
- `test_warehouse_rapid_departure_rule_triggers`: Person with rapid departure ($\ge 120\text{ px/s}$) within 5s after crouching triggers `warehouse_rapid_departure`.
- `test_gate_door_loitering_triggers`: Person with dwell time $\ge 15\text{s}$ in `door_zone` triggers `gate_door_loitering`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_warehouse_door_rules.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement warehouse & door rules**

- In `src/feature_extractor.py`:
  - Add `recent_crouch_timestamp: float = 0.0` to `TrackHistory` and update it whenever posture is `CROUCHING_CRAWLING` or aspect ratio $< 0.8$.
  - In `TrackFeatures`, add `time_since_crouch_sec: float = 999.0`.
- In `src/rule_engine.py`:
  - Handle `warehouse_taking_goods`: checks if person is in specified zone (e.g. `warehouse_zone` or `storage_zone`) and posture is `CROUCHING_CRAWLING` or `crouch_like`.
  - Handle `warehouse_rapid_departure`: checks if `speed_px_per_sec >= min_speed` (default 120) and `time_since_crouch_sec <= max_sec` (default 5.0).
- In `config/rules.yaml`:
  - Add `gate_door_loitering`, `warehouse_taking_goods`, `warehouse_rapid_departure`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_warehouse_door_rules.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/feature_extractor.py src/rule_engine.py config/rules.yaml tests/test_warehouse_door_rules.py
git commit -m "feat: add warehouse goods taking and door loitering rules"
```

---

### Task 3: Telegram Album (Media Group) Anti-Spam Notifier

**Files:**
- Modify: `src/telegram_notifier.py`
- Test: `tests/test_telegram_album_alert.py`

**Interfaces:**
- Consumes: `telegram.InputMediaPhoto`
- Produces:
  - `TelegramNotifier.send_alert(..., snapshot_path: Optional[str] = None, face_snapshot_path: Optional[str] = None) -> bool`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_telegram_album_alert.py`:
- `test_send_alert_with_face_snapshot_sends_media_group`: When both `snapshot_path` and `face_snapshot_path` are provided, calls `bot.send_media_group` with 2 `InputMediaPhoto` objects.
- `test_send_alert_without_face_snapshot_sends_single_photo`: When only `snapshot_path` is provided, calls `_send_message_with_photo`.
- `test_send_alert_media_group_fallback_on_error`: If `send_media_group` raises an exception, falls back safely to sending the primary snapshot without failing.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_telegram_album_alert.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement media group album in `TelegramNotifier.send_alert`**

- In `src/telegram_notifier.py`:
  - Add `face_snapshot_path: Optional[str] = None` to `send_alert`.
  - If `snapshot_path` and `face_snapshot_path` and both files exist:
    - Build `media = [InputMediaPhoto(open(snapshot_path, 'rb'), caption=caption, parse_mode='MarkdownV2'), InputMediaPhoto(open(face_snapshot_path, 'rb'))]`.
    - Call `await self._bot.send_media_group(chat_id=self.chat_id, media=media)`.
    - Try/except fallback to `_send_message_with_photo` if media group fails.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_telegram_album_alert.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/telegram_notifier.py tests/test_telegram_album_alert.py
git commit -m "feat: send person and face crops as single telegram media group album"
```

---

### Task 4: Pipeline Target Suspect Isolation & Alert Flow

**Files:**
- Modify: `src/main.py`
- Test: `tests/test_main_face_crop_integration.py`

**Interfaces:**
- Consumes: `CameraPipeline._handle_alert`, `SnapshotScheduler.capture_face_crop`, `TelegramNotifier.send_alert`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_main_face_crop_integration.py`:
- `test_handle_alert_isolates_primary_suspect_face`: In multi-person alert, calls `capture_face_crop` with the bounding box and keypoints of the suspect with highest score.
- `test_handle_alert_passes_face_snapshot_to_telegram`: When `capture_face_crop` succeeds, passes `face_snapshot_path` to `telegram.send_alert`.
- `test_handle_alert_handles_none_face_snapshot_gracefully`: When `capture_face_crop` returns `None` (back turned), passes `face_snapshot_path=None` to `telegram.send_alert`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_main_face_crop_integration.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement suspect isolation in `CameraPipeline._handle_alert` in `src/main.py`**

- In `_handle_alert`:
  - Identify `primary_track_id`:
    ```python
    target_ids = list(event.track_ids) if getattr(event, "track_ids", None) else list(active_tracks.keys())
    scores = self.latest_track_scores or {}
    primary_track_id = max(target_ids, key=lambda tid: getattr(scores.get(tid), "total_score", 0.0)) if target_ids else None
    ```
  - Retrieve primary suspect's bbox and `latest_keypoints`.
  - If event is suspicious / critical ($\text{score} \ge 60$ with warehouse/gate/crouch triggers or $\ge 80$):
    - Call `capture_face_crop(camera_id, event_id, bbox=primary_bbox, keypoints=primary_kp)`.
  - Pass `face_snapshot_path=face_crop_path` to `self.telegram.send_alert`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_main_face_crop_integration.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_main_face_crop_integration.py
git commit -m "feat: isolate primary suspect face and integrate with alert pipeline"
```

---

### Task 5: Full Regression Testing & Verification

**Files:**
- Entire repository

- [ ] **Step 1: Run full pytest suite**

Run: `python -m pytest tests/ -v`  
Expected: All 111+ tests PASS.

- [ ] **Step 2: Verify git status and commit any cleanups**

```bash
git status
```
Expected: Clean working tree on branch `main`.

- [ ] **Step 3: Push to GitHub remote**

```bash
git push origin main
```
