# ADR-001: Focus on Inference Stabilization & Advanced Pose/Behavior Analytics

- **Status:** Accepted
- **Date:** 2026-11-13
- **Deciders:** Engineering Lead & AI Architect

## Context

The CCTV AI Detection system currently supports YOLOv8 object detection, ByteTrack multi-camera tracking, motion gating, and a rule-based behavioral scoring engine. 

Inspection of the environment reveals:
1. `kernel.errors.txt` contains critical Intel GPU OpenVINO CISA JIT compiler errors (`Input V38 intersects with V37`, `Explicit input 2 must not follow an implicit input 0`).
2. `PersonDetector` loads `yolov8n-pose.pt` and parses 17 skeletal keypoints, but `feature_extractor.py` and `rule_engine.py` currently ignore keypoint data (relying only on bounding box aspect ratio).
3. The codebase needs a hardened, high-performance pipeline that protects against device compilation failures and fully leverages posture estimation.

## Decision

1. **Strategic Focus:** The current development initiative will focus on **Inference Stabilization** (mitigating OpenVINO kernel issues, safe hardware fallback, FPS optimization) and **Advanced Pose & Fall Analytics** (utilizing `yolov8n-pose` keypoints for posture classification, fall detection, and distressed state recognition).
2. **Architecture Documentation:** All architectural decisions will be formally recorded as ADRs in `docs/adr/` with an accompanying domain glossary.
3. **Strict Backward Compatibility:** All changes will preserve existing configuration files (`config/config.yaml`, `config/rules.yaml`), API interfaces, and SQLite schemas without breaking existing camera streams or database records.

## Consequences

### Positive
- Prevents system crashes and silent kernel failures on Intel integrated GPU / CPU environments.
- Elevates CCTV AI capabilities from simple bounding box tracking to deep behavioral analysis (falls, crouching, climbing).
- Clean audit trail of architecture decisions.

### Negative / Trade-offs
- Keypoint processing introduces slight computational overhead per tracked person, requiring strict motion gating and keypoint caching.

