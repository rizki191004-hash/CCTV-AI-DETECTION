# ADR-007: Vehicle Detection (Motorcycle & Car Rider Alert)

**Date:** 2026-11-17  
**Status:** Accepted  
**Deciders:** User + Antigravity  

---

## Context

The CCTV AI Detection system currently detects only humans (and animals). The user requested adding detection for vehicles — specifically motorcycles and cars that are **actively being ridden/driven** — with Telegram alerts and live dashboard visualization.

## Decisions

### Q1 — Vehicle Classes Detected
**Decision:** Detect **motorcycle (COCO class 2) and car (COCO class 3) only.**  
Truck, bus, bicycle excluded — not relevant for the deployment context (parking area / residential CCTV).

### Q2 — Alert Trigger
**Decision:** Send Telegram alert **only when a person bounding box overlaps a vehicle bounding box** (IoU ≥ 0.15), indicating the person is riding/driving.  
Parked vehicles without a rider produce no alert.

### Q3 — Model Strategy
**Decision:** Add a secondary `VehicleDetector` class using `yolov8n.pt` (full 80-class COCO).  
`PersonDetector` retains `yolov8n-pose.pt` (pose skeleton preserved). Both run when motion is detected.  
This avoids restructuring the existing pipeline and keeps pose estimation intact.

### Q4 — Dashboard Visualization
**Decision:**  
- Motorcycle → **orange** bounding box, Car → **blue** bounding box  
- When rider detected (IoU ≥ 0.15) → box turns **red** + label `"🏍️ Rider!"` / `"🚗 Driver!"`  
- HUD counter added: `🚗 Vehicles: N`

### Q5 — Telegram Alert Format
**Decision:** Vehicle info is **merged into the existing person alert** as an extra line.  
Format: `🏍️ Vehicle: Riding Motorcycle` or `🚗 Vehicle: Driving Car`  
No separate vehicle-only alert message.

### Q6 — Alert Cooldown
**Decision:** Reuse existing `AlarmGate` cooldown mechanism. No new cooldown logic needed.

### Q7 — IoU Threshold
**Decision:** **IoU ≥ 0.15** for person-on-vehicle detection.  
Sensitive enough for partially-occluded riders without excessive false positives from people standing near a parked vehicle.

### Q8 — Parked Vehicle Behavior
**Decision:** Parked vehicles (no rider) → draw bounding box on live feed, **no Telegram alert**.  
This keeps the operator informed without spamming notifications.

### Q9 — Detection Frequency
**Decision:** `VehicleDetector` runs **when motion is detected**, same gate as `PersonDetector`.  
`yolov8n.pt` is ~6 MB and ~15 ms/frame on CPU — negligible overhead.

### Q10 — Bounding Box Labels
**Decision:** Dynamic labels:  
- Rider detected → `"🏍️ Rider!"` / `"🚗 Driver!"`  
- No rider → `"Motorcycle"` / `"Car"`

---

## Implementation Plan Summary

1. Create `src/vehicle_detector.py` — `VehicleDetector` class with `yolov8n.pt`
2. Add `vehicle_count` to `DetectionResult` in `person_detector.py`
3. Update `src/main.py` — integrate `VehicleDetector` in pipeline, detect riders via IoU
4. Update `src/visualizer.py` — draw vehicle boxes + dynamic labels + HUD counter
5. Update `src/telegram_notifier.py` — add `vehicle_info` optional param to `send_alert` / `format_alert_caption`
6. Update `src/api/routes.py` MJPEG generator to pass vehicle detections to visualizer
7. Update `dashboard/src/App.tsx` — show vehicle count in HUD
8. TDD: write tests first for each component

## Consequences

- **Positive:** Operators can detect and be alerted when someone rides a motorcycle/car through monitored area
- **Positive:** No model restructuring required — additive only
- **Negative:** Slight CPU increase per frame (~15 ms) when motion detected
- **Mitigation:** `yolov8n.pt` is the lightest YOLO variant; impact is minimal

