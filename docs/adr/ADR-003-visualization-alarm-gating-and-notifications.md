# ADR-003: Visual Overlay, Alarm Gate Fall Adaptation, and Telegram Alerts

- **Status:** Accepted
- **Date:** 2026-11-13
- **Deciders:** Engineering Lead & AI Architect

## Context

When a fall or abnormal posture is triggered, security operators need clear, immediate visual evidence in both the web dashboard and Telegram snapshot notifications.

Furthermore, traditional alarm gates discard bounding boxes with low height-to-width ratios ($h/w < 1.0$) to reject non-human ground clutter. However, a person lying on the ground horizontally inherently has an inverted aspect ratio ($h/w \approx 0.3 - 0.6$). Without conditional bypass, the alarm gate would silently discard valid fall events.

## Decision

1. **Visualizer Skeletal & Posture Overlay:**
   - In `src/visualizer.py`, render keypoint bones (connections between nose, shoulders, elbows, wrists, hips, knees, ankles) using OpenCV `line` and `circle` primitives when `person_keypoints` are available.
   - Color-code bounding boxes and labels according to posture state:
     - `FALLEN_HORIZONTAL`: Bold Red (`#FF0000`).
     - `CROUCHING_CRAWLING`: Amber/Orange (`#FFA500`).
     - `STANDING`: Standard Green (`#00FF00`).
2. **Alarm Gate Adaptation:**
   - In `src/alarm_gate.py`, check `track_features.is_fall_detected` and `posture_state`.
   - If a candidate detection is identified as a fall or lying flat with high confidence ($> 0.6$ torso angle confirmation), bypass the standard minimum aspect ratio filter (`min_aspect_ratio`), preventing false rejection of ground-level persons.
3. **Telegram Notification Enrichment:**
   - In `src/telegram_notifier.py`, prefix critical alerts with `🚨 [FALL DETECTED / DARURAT]` and include posture metrics:
     - Posture: `FALLEN_HORIZONTAL`
     - Torso Angle: `~78°`
     - Downward Velocity: `~142 px/s`
     - Snapshot: JPEG image annotated with skeletal keypoints and red highlight box.

## Consequences

### Positive
- Guards against false negative rejections of fallen individuals.
- Provides immediate, unmistakable visual feedback to security personnel via Telegram.
- Clean separation of concern across `visualizer`, `alarm_gate`, and `telegram_notifier`.

### Negative / Trade-offs
- Rendering 17 keypoint lines on high-resolution snapshots adds negligible CPU overhead (~1ms per frame).

