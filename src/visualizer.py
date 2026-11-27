"""
visualizer.py — Shared visualization logic for bounding boxes and UI overlays.

Provides unified drawing functions used by both the live MJPEG dashboard stream
and the Telegram snapshot generator. Handles detailed posture estimation
(including intersection checks for sitting on motorcycle vs chair),
suspicion-based color coding, and HUD overlays.
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Any

# COCO Class IDs for posture context and vehicle detection
CAR_CLASS_ID = 2
MOTORCYCLE_CLASS_ID = 3
BENCH_CLASS_ID = 13
CHAIR_CLASS_ID = 56
COUCH_CLASS_ID = 57
SEATING_CLASSES = {BENCH_CLASS_ID, CHAIR_CLASS_ID, COUCH_CLASS_ID}

# Vehicle display colors (BGR)
_VEHICLE_COLOR_DEFAULT = {
    MOTORCYCLE_CLASS_ID: (0, 165, 255),   # Orange for motorcycle
    CAR_CLASS_ID:        (255, 100, 0),   # Blue for car
}
_VEHICLE_COLOR_RIDER = (0, 0, 255)  # Red when rider detected


class Visualizer:
    SKELETON_BONES = [
        (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
        (5, 11), (6, 12), (11, 12),
        (11, 13), (13, 15), (12, 14), (14, 16),
        (0, 1), (0, 2), (1, 3), (2, 4)
    ]

    @staticmethod
    def draw_skeleton(
        frame: np.ndarray,
        keypoints: np.ndarray,
        color: Tuple[int, int, int] = (0, 255, 255),
        scale_x: float = 1.0,
        scale_y: float = 1.0,
    ) -> np.ndarray:
        """Draw 17-keypoint skeletal lines and joints onto frame."""
        if keypoints is None or len(keypoints) < 17:
            return frame

        # Draw bones
        for p1, p2 in Visualizer.SKELETON_BONES:
            x1, y1 = keypoints[p1][:2]
            x2, y2 = keypoints[p2][:2]
            if (x1 > 0 or y1 > 0) and (x2 > 0 or y2 > 0):
                pt1 = (int(x1 * scale_x), int(y1 * scale_y))
                pt2 = (int(x2 * scale_x), int(y2 * scale_y))
                cv2.line(frame, pt1, pt2, color, 2, cv2.LINE_AA)

        # Draw joints
        for i in range(len(keypoints)):
            x, y = keypoints[i][:2]
            if x > 0 or y > 0:
                pt = (int(x * scale_x), int(y * scale_y))
                cv2.circle(frame, pt, 3, (255, 255, 255), -1, cv2.LINE_AA)

        return frame

    @staticmethod
    def _compute_iou(boxA: np.ndarray, boxB: np.ndarray) -> float:
        """Compute Intersection over Union (IoU) of two bounding boxes [x1, y1, x2, y2]."""
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        interArea = max(0, xB - xA) * max(0, yB - yA)
        if interArea == 0:
            return 0.0

        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

        iou = interArea / float(boxAArea + boxBArea - interArea)
        return iou

    @staticmethod
    def _get_posture_state(
        track: Any,
        bbox: np.ndarray,
        all_detections: Any = None,
        vehicle_detections: Any = None,
        riders: Any = None,
    ) -> Tuple[str, Tuple[int, int, int]]:
        """Determine posture state (Jatuh, Merayap, Duduk, Berjalan, dll) and color.

        ADR-013: If the person is a confirmed motorcycle/car rider (via riders list
        and IoU overlap with vehicle bbox), return a vehicle-riding label immediately,
        bypassing all posture heuristics.
        """
        # --- ADR-013: Motorcycle / vehicle rider early-exit ---
        if riders and vehicle_detections is not None and len(vehicle_detections) > 0:
            track_bbox = np.array(bbox, dtype=float)
            for rider in riders:
                v_box = vehicle_detections.xyxy[rider.vehicle_idx]
                iou = Visualizer._compute_iou(track_bbox, v_box)
                if iou > 0.1:
                    if rider.vehicle_class == MOTORCYCLE_CLASS_ID:
                        return "Naik Motor", (0, 180, 120)   # green-teal
                    else:
                        return "Mengemudi", (255, 140, 0)     # orange

        # Check skeletal keypoints first
        if getattr(track, 'latest_keypoints', None) is not None:
            try:
                from src.feature_extractor import FeatureExtractor
                kposture, angle = FeatureExtractor.analyze_posture(track.latest_keypoints, bbox=bbox)
                if kposture == "FALLEN_HORIZONTAL" or angle >= 60.0:
                    return "Jatuh / Terkapar", (0, 0, 255)  # Bright Red
                elif kposture == "CROUCHING_CRAWLING":
                    return "Merayap / Jongkok", (0, 165, 255)  # Amber
            except Exception:
                pass

        bx1, by1, bx2, by2 = bbox
        bw = max(bx2 - bx1, 1)
        bh = max(by2 - by1, 1)
        aspect = bh / bw
        
        # Estimate speed from recent centroids
        speed = 0.0
        if hasattr(track, 'points') and len(track.points) >= 2:
            p1 = track.points[-2]
            p2 = track.points[-1]
            dt = p2.timestamp - p1.timestamp
            if dt > 0:
                dx = p2.centroid[0] - p1.centroid[0]
                dy = p2.centroid[1] - p1.centroid[1]
                speed = (dx*dx + dy*dy) ** 0.5 / dt

        if speed >= 25.0:
            return "Berjalan", (255, 200, 0)  # cyan-ish
        
        if aspect < 1.3 and bh < bw * 1.5:
            # Person seems to be sitting. Check for overlap with motorcycle or chairs.
            posture_state = "Duduk"
            posture_color = (0, 200, 255)  # orange/yellow

            if all_detections is not None and all_detections.xyxy is not None:
                max_iou_motor = 0.0
                max_iou_chair = 0.0
                
                for i in range(len(all_detections.xyxy)):
                    cls_id = all_detections.class_id[i]
                    if cls_id == MOTORCYCLE_CLASS_ID:
                        iou = Visualizer._compute_iou(bbox, all_detections.xyxy[i])
                        if iou > max_iou_motor:
                            max_iou_motor = iou
                    elif cls_id in SEATING_CLASSES:
                        iou = Visualizer._compute_iou(bbox, all_detections.xyxy[i])
                        if iou > max_iou_chair:
                            max_iou_chair = iou
                
                # If there's significant overlap, refine the posture
                if max_iou_motor > 0.1 and max_iou_motor > max_iou_chair:
                    posture_state = "Duduk di Motor"
                    posture_color = (200, 150, 255) # pinkish
                elif max_iou_chair > 0.1:
                    posture_state = "Duduk di Kursi"
                    posture_color = (0, 220, 255)
            
            return posture_state, posture_color
        
        return "Berdiri Diam", (0, 255, 0)  # green

    @staticmethod
    def draw_annotated_frame(
        frame: np.ndarray,
        active_tracks: Dict[int, Any],
        track_scores: Dict[int, Any],
        suspicious_threshold: float,
        person_count: int,
        animal_count: int,
        all_detections: Any = None,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        vehicle_detections: Any = None,
        riders: Any = None,
        vehicle_count: int = 0,
        only_riders: bool = False,
        vehicle_track_result: Any = None,
    ) -> np.ndarray:
        """Draw bounding boxes, labels, and HUD on the frame.
        
        Args:
            frame: Original BGR frame.
            active_tracks: Dictionary of tracked objects.
            track_scores: Dictionary of TrackScore objects.
            suspicious_threshold: Threshold for turning bounding box red.
            person_count: Total person count for HUD.
            animal_count: Total animal count for HUD.
            all_detections: sv.Detections of all objects (posture context).
            scale_x: Scale factor for x coordinates (default 1.0).
            scale_y: Scale factor for y coordinates (default 1.0).
            vehicle_detections: sv.Detections of vehicles (optional).
            riders: List[RiderInfo] from VehicleDetector.find_riders().
            vehicle_count: Number of vehicles detected for HUD.
            
        Returns:
            Annotated BGR frame.
        """
        display_frame = frame.copy()

        for track_id, track in active_tracks.items():
            bbox = track.latest_bbox
            if bbox is None:
                continue

            x1, y1, x2, y2 = bbox
            x1, x2 = int(x1 * scale_x), int(x2 * scale_x)
            y1, y2 = int(y1 * scale_y), int(y2 * scale_y)

            if track.class_type == "animal":
                conf = track.points[-1].confidence if track.points and hasattr(track.points[-1], 'confidence') else 0.0
                color = (255, 165, 0)  # Orange/Blueish in BGR for animals
                label = f"Animal #{track_id} ({conf:.0%})"
                box_thickness = 3
                
                # Draw box and label
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, box_thickness)
                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
                cv2.rectangle(display_frame, (x1, y1 - 26), (x1 + w + 6, y1), color, -1)
                cv2.putText(display_frame, label, (x1 + 3, y1 - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
            
            elif track.class_type == "human":
                # Human tracking
                track_score_obj = track_scores.get(track_id)
                track_score = track_score_obj.total_score if track_score_obj else 0.0
                triggered_rules = track_score_obj.rule_reasons if track_score_obj else []
                
                # Posture state — ADR-013: pass vehicle context for rider detection
                posture_state, posture_color = Visualizer._get_posture_state(
                    track, bbox, all_detections,
                    vehicle_detections=vehicle_detections,
                    riders=riders,
                )

                # Draw skeletal bones if keypoints available
                if getattr(track, 'latest_keypoints', None) is not None:
                    Visualizer.draw_skeleton(
                        display_frame,
                        track.latest_keypoints,
                        color=posture_color,
                        scale_x=scale_x,
                        scale_y=scale_y,
                    )
                
                # Color based on score level
                if track_score > suspicious_threshold:
                    color = (0, 0, 255)    # Red for suspicious
                    box_thickness = 4
                elif track_score > 30:
                    color = (0, 165, 255)  # Orange for moderate
                    box_thickness = 3
                elif track_score > 0:
                    color = (0, 255, 255)  # Yellow for low activity
                    box_thickness = 3
                else:
                    color = (0, 255, 0)    # Green for normal
                    box_thickness = 3
                
                # Main label
                label = f"#{track_id} {posture_state} | Skor: {track_score:.0f}/100"
                
                # Draw thick box
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, box_thickness)
                
                # Draw label with score (top of box)
                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
                cv2.rectangle(display_frame, (x1, y1 - 26), (x1 + w + 6, y1), color, -1)
                cv2.putText(display_frame, label, (x1 + 3, y1 - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
                
                # Draw triggered rules below the bounding box
                y_offset = y2 + 2
                
                # Posture badge
                posture_text = f"[{posture_state}]"
                (pw, ph), _ = cv2.getTextSize(posture_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                cv2.rectangle(display_frame, (x1, y_offset), (x1 + pw + 6, y_offset + 22), posture_color, -1)
                cv2.putText(display_frame, posture_text, (x1 + 3, y_offset + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
                y_offset += 24
                
                # Show triggered rule reasons (max 2 lines)
                if triggered_rules:
                    for reason in triggered_rules[:2]:
                        rule_text = f"! {reason}"
                        (rw, rh), _ = cv2.getTextSize(rule_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
                        cv2.rectangle(display_frame, (x1, y_offset), (x1 + rw + 4, y_offset + 18), (0, 0, 180), -1)
                        cv2.putText(display_frame, rule_text, (x1 + 2, y_offset + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                        y_offset += 20

        # Draw vehicle bounding boxes (before HUD so HUD renders on top)
        if vehicle_detections is not None and len(vehicle_detections) > 0:
            rider_vehicle_idxs = set()
            if riders:
                rider_vehicle_idxs = {r.vehicle_idx for r in riders}

            tracked_vehicles = getattr(vehicle_track_result, "tracked_vehicles", None)
            v_movings = getattr(vehicle_track_result, "vehicle_moving", {}) or {}
            v_speeds_kmh = getattr(vehicle_track_result, "vehicle_speed_kmh", {}) or {}

            for v_idx, v_box in enumerate(vehicle_detections.xyxy):
                is_rider = v_idx in rider_vehicle_idxs
                if only_riders and not is_rider:
                    continue
                v_cls = int(vehicle_detections.class_id[v_idx]) if vehicle_detections.class_id is not None else MOTORCYCLE_CLASS_ID
                
                vx1, vy1, vx2, vy2 = v_box
                vx1, vx2 = int(vx1 * scale_x), int(vx2 * scale_x)
                vy1, vy2 = int(vy1 * scale_y), int(vy2 * scale_y)

                # Find vehicle track ID
                v_tid = None
                if tracked_vehicles is not None and hasattr(tracked_vehicles, "tracker_id") and tracked_vehicles.tracker_id is not None and len(tracked_vehicles) > 0:
                    if v_idx < len(tracked_vehicles.tracker_id) and tracked_vehicles.tracker_id[v_idx] is not None:
                        v_tid = int(tracked_vehicles.tracker_id[v_idx])
                    else:
                        best_iou = 0.0
                        for t_idx, t_box in enumerate(tracked_vehicles.xyxy):
                            iou = Visualizer._compute_iou(v_box, t_box)
                            if iou > best_iou:
                                best_iou = iou
                                if tracked_vehicles.tracker_id[t_idx] is not None:
                                    v_tid = int(tracked_vehicles.tracker_id[t_idx])

                is_moving = False
                speed_kmh = 0.0
                if v_tid is not None:
                    is_moving = v_movings.get(v_tid, False)
                    speed_kmh = v_speeds_kmh.get(v_tid, 0.0)
                elif len(v_movings) == 1:
                    single_id = next(iter(v_movings.keys()))
                    is_moving = v_movings.get(single_id, False)
                    speed_kmh = v_speeds_kmh.get(single_id, 0.0)
                    v_tid = single_id

                id_str = f" #V{v_tid}" if v_tid is not None else ""
                status_str = f"Berjalan | {speed_kmh:.0f} km/j" if is_moving else "Berhenti"

                if v_cls == MOTORCYCLE_CLASS_ID:
                    if is_rider:
                        color = _VEHICLE_COLOR_RIDER
                        thickness = 4
                        label = f"Motor{id_str} | Naik Motor: {status_str}" if vehicle_track_result else f"Motor{id_str} | Naik Motor"
                    else:
                        color = _VEHICLE_COLOR_DEFAULT.get(v_cls, (0, 165, 255))
                        thickness = 2
                        label = f"Motor{id_str} | {status_str}" if vehicle_track_result else f"Motor{id_str}"
                else:
                    # Car -> displayed cleanly as "Kendaraan"
                    if is_moving:
                        color = (255, 140, 0)
                        thickness = 3
                        label = f"Kendaraan{id_str} | {status_str}"
                    else:
                        color = (180, 100, 50)
                        thickness = 2
                        label = f"Kendaraan{id_str} | Berhenti" if vehicle_track_result else f"Kendaraan{id_str}"

                cv2.rectangle(display_frame, (vx1, vy1), (vx2, vy2), color, thickness)
                lw, lh = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)[0]
                cv2.rectangle(display_frame, (vx1, vy1 - 26), (vx1 + lw + 6, vy1), color, -1)
                cv2.putText(display_frame, label, (vx1 + 3, vy1 - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

        # Draw HUD overlay (top-left)
        has_rider = bool(riders)
        hud_text = f"Persons: {person_count} | Vehicles: {vehicle_count}"
        if animal_count > 0:
            hud_text += f" | Animals: {animal_count}"
        hud_color = (0, 0, 255) if (person_count > 0 or has_rider) else (0, 255, 0)
        hud_w = max(320, len(hud_text) * 11)
        cv2.rectangle(display_frame, (5, 5), (hud_w, 35), (0, 0, 0), -1)
        cv2.putText(display_frame, hud_text, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, hud_color, 2)
        
        # Rider alert banner (top-right corner)
        if has_rider:
            alert_text = 'RIDER DETECTED!'
            aw, _ = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 0.75, 2)[0]
            fw = display_frame.shape[1]
            ax = fw - aw - 20
            cv2.rectangle(display_frame, (ax - 5, 5), (fw - 5, 40), (0, 0, 200), -1)
            cv2.putText(display_frame, alert_text, (ax, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

        # Live clock overlay (bottom-left) for real-time verification
        from datetime import datetime
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fh = display_frame.shape[0]
        (tw, th), _ = cv2.getTextSize(now_str, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(display_frame, (5, fh - 25), (tw + 15, fh - 5), (0, 0, 0), -1)
        cv2.putText(display_frame, now_str, (10, fh - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)

        return display_frame
