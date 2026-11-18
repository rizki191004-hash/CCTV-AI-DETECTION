# Inference Stabilization & Advanced Pose/Behavior Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize OpenVINO device inference against Intel GPU kernel compilation crashes and operationalize YOLOv8-Pose 17-keypoint skeletal tracking for instantaneous fall detection, crouching surveillance, and visual emergency alerts.

**Architecture:** A probe-and-fallback mechanism in `PersonDetector` transparently detects OpenVINO CISA/JIT errors during warmup and falls back to CPU. In `FeatureExtractor`, geometric vector analysis on 17 skeletal landmarks computes torso angle, downward drop velocity, and discrete posture states (`STANDING`, `CROUCHING_CRAWLING`, `FALLEN_HORIZONTAL`). `RuleEngine` evaluates new configurable rules (`fall_detected` as critical, `suspicious_crouching` as cumulative score), while `AlarmGate`, `Visualizer`, and `TelegramNotifier` adapt to deliver color-coded skeletal snapshot alerts.

**Tech Stack:** Python 3.11+, Ultralytics YOLOv8-Pose, OpenVINO, OpenCV, Supervision, NumPy, Pytest / unittest.

**Spec:**
- [ADR-001: Focus on Inference Stabilization & Advanced Pose/Behavior Analytics](file:///c:/Users/RizXenzs/Downloads/CCTV%20AI%20DETECTION/CCTV%20AI%20DETECTION/docs/adr/ADR-001-inference-stabilization-and-pose-analytics.md)
- [ADR-002: OpenVINO GPU Probe-and-Fallback & Keypoint Posture Rules](file:///c:/Users/RizXenzs/Downloads/CCTV%20AI%20DETECTION/CCTV%20AI%20DETECTION/docs/adr/ADR-002-openvino-fallback-and-pose-rules.md)
- [ADR-003: Visual Overlay, Alarm Gate Fall Adaptation, and Telegram Alerts](file:///c:/Users/RizXenzs/Downloads/CCTV%20AI%20DETECTION/CCTV%20AI%20DETECTION/docs/adr/ADR-003-visualization-alarm-gating-and-notifications.md)

## Global Constraints

- Full backward compatibility with existing YAML schema in `config/config.yaml` and `config/rules.yaml`.
- No destructive alterations to SQLite database schema in `data/cctv_events.db`.
- Clean error handling with zero unhandled exceptions on unsupported hardware.
- Real-time performance guarantee: $O(1)$ posture feature extraction per tracked person without invoking secondary heavy ML models.

## Review Focus

1. **JIT compilation failure:** Intel GPU drivers raise CISA routine kernel errors or segfaults during dynamic model execution. Reasonable behavior: System catches the failure during probe warmup and smoothly degrades to OpenVINO CPU with logged instructions.
2. **Keypoint occlusion:** Person is partially occluded behind furniture or fences where leg keypoints have confidence < 0.3. Reasonable behavior: Posture calculator falls back gracefully to shoulder-hip angle or bounding box aspect ratio rather than misclassifying as fallen.
3. **Inverted aspect ratio rejection:** A person lying flat on the floor has aspect ratio ($h/w < 0.6$). Reasonable behavior: Alarm gate detects active fall state and bypasses minimum aspect ratio gatekeeper.
4. **Sudden drop vs camera glitch:** Camera frame jumps or momentary tracker re-association creates an artificial velocity spike. Reasonable behavior: Velocity calculation requires minimum track age ($\ge 3$ frames) and temporal confirmation before firing critical fall alert.
5. **Multi-person skeletal clutter:** Multiple overlapping people in frame produce visual clutter. Reasonable behavior: Skeletal lines are drawn only for high-scoring/suspicious tracks, and colored distinctively by posture.

---

### Task 1: OpenVINO GPU Probe and Safe CPU Fallback in `PersonDetector`

**Files:**
- Create: `tests/test_person_detector_fallback.py`
- Modify: `src/person_detector.py:125-185`

**Interfaces:**
- Consumes: `openvino.Core`, `ultralytics.YOLO`, `PersonDetector.device`
- Produces: `PersonDetector._probe_device() -> str`, robust `PersonDetector._warmup()` with automatic CPU fallback.

- [x] **Step 1: Write the failing test**
...
- [x] **Step 2: Run test to verify it fails**
...
- [x] **Step 3: Implement device probe and fallback in `src/person_detector.py`**
...
- [x] **Step 4: Run test to verify it passes**
...
- [x] **Step 5: Commit**

```bash
git add src/person_detector.py tests/test_person_detector_fallback.py
git commit -m "fix(inference): add probe and automatic CPU fallback for OpenVINO GPU kernel errors"
```

---

### Task 2: Geometric Posture & Fall Feature Extraction in `FeatureExtractor`

**Files:**
- Create: `tests/test_posture_features.py`
- Modify: `src/feature_extractor.py:30-120`

**Interfaces:**
- Consumes: Keypoints array `xy` of shape $(17, 2)$ and confidence of shape $(17,)$ from `DetectionResult.person_keypoints`.
- Produces: Fields in `TrackFeatures`:
  - `posture_state: str` (`"STANDING"`, `"CROUCHING_CRAWLING"`, `"FALLEN_HORIZONTAL"`)
  - `torso_angle: float` (degrees from vertical)
  - `is_fall_detected: bool`
  - `vertical_velocity_px_s: float`

- [x] **Step 1: Write the failing test**
...
- [x] **Step 2: Run test to verify it fails**
...
- [x] **Step 3: Implement `analyze_posture` and update `TrackFeatures` in `src/feature_extractor.py`**
...
- [x] **Step 4: Run test to verify it passes**
...
- [x] **Step 5: Commit**

```bash
git add src/feature_extractor.py tests/test_posture_features.py
git commit -m "feat(analytics): add geometric posture and fall detection in FeatureExtractor"
```

---

### Task 3: Configurable Posture & Fall Rules in `RuleEngine` and `rules.yaml`

**Files:**
- Create: `tests/test_pose_rules.py`
- Modify: `config/rules.yaml`
- Modify: `src/rule_engine.py:100-220`

**Interfaces:**
- Consumes: `TrackFeatures.is_fall_detected`, `TrackFeatures.posture_state`, `config/rules.yaml`
- Produces: `RuleResult` with `rule_id="fall_detected"`, `critical=True`, `score_delta=85.0`; and `rule_id="suspicious_crouching"`, `score_delta=45.0`.

- [x] **Step 1: Write the failing test**
...
- [x] **Step 2: Run test to verify it fails**
...
- [x] **Step 3: Update `config/rules.yaml` and `src/rule_engine.py`**
...
- [x] **Step 4: Run test to verify it passes**
...
- [x] **Step 5: Commit**

```bash
git add config/rules.yaml src/rule_engine.py tests/test_pose_rules.py
git commit -m "feat(rules): integrate fall_detected and suspicious_crouching into rule engine"
```

---

### Task 4: Alarm Gate Aspect Ratio Adaptation for Falls

**Files:**
- Create: `tests/test_alarm_gate_fall.py`
- Modify: `src/alarm_gate.py:40-95`

**Interfaces:**
- Consumes: `TrackFeatures.is_fall_detected`, `TrackFeatures.posture_state`, bounding box aspect ratio
- Produces: `AlarmGate.is_valid_detection(...) -> bool` allowing horizontal aspect ratio ($< 0.6$) when `is_fall_detected=True`.

- [x] **Step 1: Write the failing test**
...
- [x] **Step 2: Run test to verify it fails**
...
- [x] **Step 3: Modify `src/alarm_gate.py`**
...
- [x] **Step 4: Run test to verify it passes**
...
- [x] **Step 5: Commit**

```bash
git add src/alarm_gate.py tests/test_alarm_gate_fall.py
git commit -m "fix(gate): allow horizontal aspect ratios for verified fall events"
```

---

### Task 5: Skeletal Drawing & Enriched Telegram Notification

**Files:**
- Create: `tests/test_visualizer_and_notifier.py`
- Modify: `src/visualizer.py:80-160`
- Modify: `src/telegram_notifier.py:120-170`

**Interfaces:**
- Consumes: `person_keypoints`, `TrackFeatures.posture_state`, `TrackScore`
- Produces: Skeletal lines overlay on OpenCV frame, `TelegramNotifier.format_alert(...)` containing posture details and emergency prefix.

- [x] **Step 1: Write the failing test**
...
- [x] **Step 2: Run test to verify it fails**
...
- [x] **Step 3: Implement skeletal drawing and Telegram formatting**
...
- [x] **Step 4: Run test to verify it passes**
...
- [x] **Step 5: Commit**

```bash
git add src/visualizer.py src/telegram_notifier.py tests/test_visualizer_and_notifier.py
git commit -m "feat(vis): add skeletal keypoints overlay and Telegram emergency posture formatting"
```

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-11-13-inference-stabilization-and-pose-analytics.md`. Please review the plan. Which execution approach would you prefer?

- **Subagent-driven** - A fresh subagent implements each task and a fresh reviewer checks it before the next one starts, then a whole-branch review at the end. Most thorough; costs a fresh context per task and per review.
- **Native** - I implement every task myself in this session, the way this harness runs work, then one fresh reviewer on the most capable model checks the whole branch. Cheapest and fastest; no independent review until the end. Runs well with a mid-tier session model, since the plan carries the design.

For this plan I recommend **Native**, because the tasks build directly on clean internal interfaces in the existing pipeline with minimal external entanglement, making fast single-session execution highly reliable. Does the plan capture what you want, and which approach should we use?

