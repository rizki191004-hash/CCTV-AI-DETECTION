# ADR-013 — Motorcycle Rider Posture Fix & Loitering Rule Immunity

**Date:** 2026-11-17  
**Status:** Accepted & Implemented  
**Author:** AI Agent (ADR-013)

---

## Context

Seseorang yang mengendarai motor (berdiri/duduk di atas motor berhenti) memiliki aspect
ratio tinggi (> 1.3) sehingga `_get_posture_state()` sebelumnya mengembalikan
`"Berdiri Diam"`. Jika motor berhenti di lampu merah ≥ 10 detik, Rule 11
(`person_berdiri_diam`) memicu **false alert** ke Telegram.

---

## Decision

### 1. `src/visualizer.py` — `_get_posture_state()` ADR-013 early-exit

Tambah dua parameter opsional `vehicle_detections` dan `riders`.  
**Sebelum** semua logika aspect-ratio/speed, cek apakah track ini adalah rider:

```python
if riders and vehicle_detections is not None and len(vehicle_detections) > 0:
    track_bbox = np.array(bbox, dtype=float)
    for rider in riders:
        v_box = vehicle_detections.xyxy[rider.vehicle_idx]
        iou = Visualizer._compute_iou(track_bbox, v_box)
        if iou > 0.1:
            if rider.vehicle_class == MOTORCYCLE_CLASS_ID:
                return "🏍️ Naik Motor", (0, 180, 120)
            else:
                return "🚗 Mengemudi", (255, 140, 0)
```

### 2. `draw_annotated_frame()` meneruskan context

```python
posture_state, posture_color = Visualizer._get_posture_state(
    track, bbox, all_detections,
    vehicle_detections=vehicle_detections,
    riders=riders,
)
```

### 3. Rule 11 immunity (implicit)

Karena `posture_state` sekarang `"🏍️ Naik Motor"` (bukan `"Berdiri Diam"`),
Rule 11 tidak akan pernah ter-trigger untuk pengendara motor — tanpa perlu
mengubah `rule_engine.py`.

---

## Consequences

| Before | After |
|--------|-------|
| Pengendara motor → `"Berdiri Diam"` | Pengendara motor → `"🏍️ Naik Motor"` |
| False alert Rule 11 tiap lampu merah | Rule 11 tidak ter-trigger untuk rider |
| `_get_posture_state()` tidak tahu kendaraan | Terintegrasi dengan `VehicleDetector.riders` |

---

## Tests

- `tests/test_motorcycle_rider_posture.py` — 2/2 PASS  
- Full suite — **75/75 PASS**

