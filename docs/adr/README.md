# Architectural Decision Records (ADR) & Domain Glossary

This directory maintains the Architecture Decision Records (ADRs) and domain terminology for the **CCTV AI Detection** system.

---

## Domain Glossary

| Term | Definition |
| :--- | :--- |
| **Motion Gate** | Background subtraction stage (OpenCV MOG2) that bypasses heavy neural network inference when frame pixels exhibit no significant movement. |
| **Person Detector** | Object detection module wrapping Ultralytics YOLOv8 / YOLOv8-Pose to identify human bounding boxes and skeletal keypoints. |
| **Keypoints (COCO 17)** | 17 skeletal landmark points (nose, eyes, ears, shoulders, elbows, wrists, hips, knees, ankles) produced by pose models. |
| **ByteTrack** | Multi-object tracking algorithm associating detections with persistent `track_id`s across consecutive frames based on motion similarity and IoU. |
| **TrackFeatures** | Aggregated temporal, spatial, and posture attributes computed for each persistent track over a sliding time window. |
| **Rule Engine** | Configurable scoring engine evaluating behavioral rules (e.g. loitering, intrusion, falling) against track features to compute a cumulative suspicion score. |
| **Alarm Gate** | Gatekeeper validating confidence, aspect ratios, bounding box size, and frame persistence to eliminate false positive triggers. |
| **OpenVINO** | Intel toolkit for optimizing and deploying deep learning inference on Intel CPUs, integrated GPUs, and discrete NPUs. |
| **CISA Routine Error** | Low-level Intel GPU driver / compiler error observed during OpenVINO JIT compilation when dynamic graph shapes or custom ops fail on specific iGPU architectures. |

---

## ADR Index

- [ADR-001: Focus on Inference Stabilization & Advanced Pose/Behavior Analytics](file:///c:/Users/RizXenzs/Downloads/CCTV%20AI%20DETECTION/CCTV%20AI%20DETECTION/docs/adr/ADR-001-inference-stabilization-and-pose-analytics.md)
- [ADR-002: OpenVINO GPU Probe-and-Fallback & Keypoint Posture Rules](file:///c:/Users/RizXenzs/Downloads/CCTV%20AI%20DETECTION/CCTV%20AI%20DETECTION/docs/adr/ADR-002-openvino-fallback-and-pose-rules.md)
- [ADR-003: Visual Overlay, Alarm Gate Fall Adaptation, and Telegram Alerts](file:///c:/Users/RizXenzs/Downloads/CCTV%20AI%20DETECTION/CCTV%20AI%20DETECTION/docs/adr/ADR-003-visualization-alarm-gating-and-notifications.md)
- [ADR-004: Native Tunnel Orchestration, Telegram Mobile Link Dispatch, and PIN Security Gate](file:///c:/Users/RizXenzs/Downloads/CCTV%20AI%20DETECTION/CCTV%20AI%20DETECTION/docs/adr/ADR-004-mobile-access-and-tunnel-orchestration.md)
- [ADR-005: Tunnel Watchdog Healthcheck & Mobile Viewport Optimization](file:///c:/Users/RizXenzs/Downloads/CCTV%20AI%20DETECTION/CCTV%20AI%20DETECTION/docs/adr/ADR-005-tunnel-watchdog-and-mobile-pwa-optimization.md)
