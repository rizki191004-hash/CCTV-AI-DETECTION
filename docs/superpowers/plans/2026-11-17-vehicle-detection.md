# Plan: Vehicle Detection Feature (COMPLETED)
**Date:** 2026-11-17  
**ADR:** ADR-007  
**Status:** Completed & Verified (49/49 Tests Passing)

---

## Completed Steps

### STEP 1 — `src/vehicle_detector.py`
- Implemented `VehicleDetector` with `yolov8n.pt` lazy loading
- Implemented `RiderInfo` and `VehicleDetectionResult`
- Implemented `find_riders()` with IoU overlap threshold calculation (default 0.15)
- Implemented `describe_riders()` for human-readable alert summaries

### STEP 2 — `tests/test_vehicle_detector.py` (TDD)
- 8 tests verifying rider detection, IoU thresholding, car/motorcycle classes, and empty cases
- All tests passing.

### STEP 3 — `src/main.py`
- Added `VehicleDetector` import and instantiation
- Integrated vehicle detection step into `CameraPipeline.run`
- Stored `latest_vehicle_detections` and `latest_riders` on `CameraPipeline`
- Passed `vehicle_info` in `_handle_alert` to `send_alert`
- Updated `get_stats()` to include `active_vehicles` and `active_riders`

### STEP 4 — `src/visualizer.py`
- Added `CAR_CLASS_ID = 2` and vehicle colors
- Updated `draw_annotated_frame` to draw vehicle bounding boxes with dynamic labels (`🏍️ Rider!` / `🚗 Driver!` / `Motorcycle` / `Car`)
- Added HUD overlay for vehicle counts (`🚗 Vehicles: N`) and top-right `RIDER DETECTED!` emergency banner

### STEP 5 — `src/telegram_notifier.py`
- Added `vehicle_info` parameter to `send_alert` and `format_alert_caption`
- Added formatted line `🚗 Vehicle: {vehicle_info}` to alert captions

### STEP 6 — `src/api/routes.py`
- Updated `mjpeg_generator` to draw vehicle bounding boxes and riders
- Added `active_vehicles` and `active_riders` to `CameraStatus` model and `/status` endpoint

### STEP 7 — `dashboard/src/App.tsx`
- Added vehicle & rider indicators to camera cards in Live View and Fullscreen Modal View

### STEP 8 — `npm run build`
- Successfully rebuilt dashboard bundle in `dashboard/dist`

### STEP 9 — Testing & Verification
- Unit & integration tests created:
  - `tests/test_vehicle_detector.py` (8 tests)
  - `tests/test_telegram_vehicle_alert.py` (2 tests)
  - `tests/test_visualizer_vehicle.py` (1 test)
  - `tests/test_main_vehicle_integration.py` (1 test)
- Total test suite: **49/49 tests PASSED** in both `pytest` and `python -m unittest discover`
