# Fullscreen Live View & Human-Only Telegram Alert Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable fullscreen viewing for camera streams in the Live View Dashboard, and ensure Telegram alert captures focus specifically on the detected humans (cropped with padding) rather than the entire wide-angle room.

**Architecture:** 
1. **Backend (`src/snapshot_scheduler.py` & `src/main.py`)**: A new utility `crop_human_region` computes the union bounding box of all active/alerting human tracks, applies 25% protective padding, clamps coordinates to frame boundaries, and produces a cropped image. The full frame is preserved in local storage and the database for forensic evidence, while the human-focused crop is delivered to Telegram.
2. **Frontend (`dashboard/src/App.tsx`)**: In the `LiveView` component, camera cards gain a Maximize button, video hover control, and double-click handler. A responsive Fullscreen modal overlay (backed by the HTML5 Fullscreen API with ESC/Minimize controls) provides an immersive, full-screen live view experience on both desktop and mobile devices.

**Tech Stack:** Python 3.11+, OpenCV, NumPy, React 19, Vite, Tailwind CSS, Lucide React, Unittest.

**Spec:**
- Settled in Grilling Round 1:
  - Q1: Maximize button in camera header + hover overlay + double-click video.
  - Q2: HTML5 Fullscreen API with fallback full-window modal overlay and ESC listener.
  - Q3: 25% padding around human bounding box.
  - Q4: Multiple humans grouped into a single union crop with padding.
  - Q5: Full frame saved to disk/DB; cropped human frame dispatched to Telegram.

## Global Constraints

- Preserve backward compatibility with `ConfigLoader`, `DBLogger`, SQLite schema, and `TelegramNotifier`.
- Single command execution: `python src/main.py` or `python run.py`.
- No new external pip dependencies (uses OpenCV and standard NumPy).
- Clean fallback: If no human bounding box is available, gracefully send the full frame.

## Review Focus

1. **Bounding box out-of-bounds**: Padding causes `x1 < 0` or `x2 > width`. Reasonable behavior: Coordinates are clamped to `[0, frame_width]` and `[0, frame_height]`.
2. **Empty detection list during alert**: Alert event has no active track bboxes. Reasonable behavior: Fallback to full uncropped frame without raising exceptions.
3. **Escaping Fullscreen on Mobile**: Mobile browsers may not support ESC key. Reasonable behavior: Prominent visual Close/Minimize button on top control bar.
4. **Coordinate scaling mismatch**: Detection bboxes are in `input_resolution` (e.g. 640x360) while the frame buffer is in full resolution (1920x1080). Reasonable behavior: Bounding boxes are accurately scaled by `scale_x` and `scale_y`.
5. **Deduplication and disk storage**: Storing both full and cropped snapshots shouldn't corrupt database records. Reasonable behavior: Full snapshot path is stored in `snapshots` table; cropped snapshot is stored with `_crop` suffix and sent to Telegram.

---

### Task 1: Human Region Cropping Utility (`src/snapshot_scheduler.py`)

**Files:**
- Modify: `src/snapshot_scheduler.py`
- Create: `tests/test_human_crop.py`

**Interfaces:**
- Consumes: `frame: np.ndarray`, `bboxes: Sequence[Sequence[float]]`, `padding: float = 0.25`
- Produces: `crop_human_region(frame: np.ndarray, bboxes: Sequence[Sequence[float]], padding: float = 0.25) -> np.ndarray`
- Produces: `SnapshotScheduler.capture_human_crop(camera_id: str, event_id: str, bboxes: Sequence[Sequence[float]], frame_override: Optional[np.ndarray] = None, padding: float = 0.25) -> Optional[str]`

- [x] **Step 1: Write the failing test**
- [x] **Step 2: Run test to verify it fails**
- [x] **Step 3: Implement `crop_human_region` and `capture_human_crop` in `src/snapshot_scheduler.py`**
- [x] **Step 4: Run test to verify it passes**

---

### Task 2: Main Pipeline Telegram Crop Dispatch (`src/main.py`)

**Files:**
- Modify: `src/main.py:466-508`
- Create: `tests/test_main_human_crop_integration.py`

**Interfaces:**
- Consumes: `event.track_ids`, `self.tracker.get_active_tracks()`, `scale_x`, `scale_y`, `SnapshotScheduler.capture_human_crop`
- Produces: `telegram.send_alert` called with `snapshot_path=human_crop_path` if available, falling back to full `snapshot_path`.

- [x] **Step 1: Write test for `_handle_alert` with human crop**
- [x] **Step 2: Run test to verify it fails**
- [x] **Step 3: Implement human crop calculation and dispatch in `_handle_alert`**
- [x] **Step 4: Run test to verify it passes**

---

### Task 3: Fullscreen Live View in React Frontend (`dashboard/src/App.tsx`)

**Files:**
- Modify: `dashboard/src/App.tsx`
- Build: `dashboard/dist` via `npm run build`

**Interfaces:**
- UI components: Maximize button in camera header, hover overlay button, double-click handler, and Fullscreen Modal overlay with ESC listener.

- [x] **Step 1: Update `dashboard/src/App.tsx` with Fullscreen Live View**
- [x] **Step 2: Build frontend with `npm run build`**
- [x] **Step 3: Verify build artifacts in `dashboard/dist`**

---

### Task 4: Full Test Suite & Verification

- [x] **Step 1: Run complete test suite (`python -m unittest discover -s tests`) — 28/28 tests PASS**
- [x] **Step 2: Verify production build bundle in `dashboard/dist`**
