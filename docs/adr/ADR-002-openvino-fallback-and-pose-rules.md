# ADR-002: OpenVINO GPU Probe-and-Fallback & Keypoint Posture Rules

- **Status:** Accepted
- **Date:** 2026-11-13
- **Deciders:** Engineering Lead & AI Architect

## Context

Running `yolov8n-pose` inference on Intel integrated graphics via OpenVINO can trigger driver-level CISA JIT compiler failures (`kernel.errors.txt`). If unhandled, this crashes the background processing thread or causes silent frame drops.

Additionally, while `PersonDetector` extracts 17 COCO keypoints, the tracking pipeline did not compute posture state or fall events. The rule engine lacked dedicated definitions for falls and abnormal crouching/crawling.

## Decision

1. **Hardware Probe & Automatic Fallback:**
   - In `PersonDetector._warmup()`, execute an isolated test inference on the requested device (`intel:gpu`).
   - If JIT compilation or inference raises an exception or emits known kernel compilation failures, automatically catch the error, log an actionable diagnostic warning, and gracefully switch `self.device` and OpenVINO context to `cpu` (or `openvino:cpu`).
2. **Geometric Keypoint Posture Extraction:**
   - In `TrackFeatures` and `FeatureExtractor`, implement an $O(1)$ geometric posture analyzer:
     - **Torso Angle:** Angle between the midpoint of the shoulders (keypoints 5, 6) and the midpoint of the hips (keypoints 11, 12) relative to the vertical axis.
     - **Vertical Drop Velocity:** Rate of downward movement of keypoint centroid $\Delta y / \Delta t$ over a rolling window ($< 0.5$s).
     - **Discrete Posture States:** Categorize state as `STANDING`, `CROUCHING_CRAWLING`, or `FALLEN_HORIZONTAL`.
3. **Rule Engine Integration:**
   - Update `config/rules.yaml` to include:
     - `fall_detected`: `score_delta: 85`, `critical: true`, `cooldown_sec: 120`. This instantly bypasses stability delay and dispatches a critical alert + snapshot to Telegram.
     - `suspicious_crouching`: `score_delta: 45`, `critical: false`, `dwell_threshold_sec: 3.0`.
   - Update `RuleEngine` to evaluate these rules against `TrackFeatures.posture_state` and `TrackFeatures.is_fall_detected`.

## Consequences

### Positive
- Zero risk of crash on heterogeneous Intel GPUs. Seamless degradation to optimized OpenVINO CPU.
- Immediate critical alerts for slips, trips, falls, and medical emergencies.
- Detection of stealth behavior (crawling/crouching under fences or near doors).
- Full auditability via YAML configuration.

### Negative / Trade-offs
- Occluded keypoints (e.g. person partially hidden behind a desk or car) could report low-confidence keypoints. To mitigate this, keypoint confidence scores ($< 0.35$) must be filtered before computing angles.

