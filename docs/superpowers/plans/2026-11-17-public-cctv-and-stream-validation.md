# Plan: Camera Stream Pre-Flight Validation & Public CCTV Presets (COMPLETED)
**Date:** 2026-11-17  
**ADR:** ADR-009  
**Status:** Completed & Verified (56/56 Tests Passing)  

---

## Technical Objectives Achieved

1. **Pre-Flight Stream Probe Endpoint (`POST /api/cameras/probe`)**:
   - Implemented in `src/api/routes.py` with `StreamProbeRequest` and `StreamProbeResponse`.
   - Checks HTTP/HLS status code (diagnosing 404/500/timeout from provider).
   - Probes OpenCV FFmpeg capture and reads resolution & FPS.
   - Detects USB webcams (`0`, `1`).
2. **TDD Coverage**:
   - Implemented `tests/test_stream_probe.py` covering active streams and dead 404 streams (like `cam47`).
   - All tests passing.
3. **Frontend Diagnostics & Palembang Presets**:
   - Added **"⚡ Tes Koneksi"** button in `CameraManager` (`dashboard/src/App.tsx`).
   - Added diagnostic banner (green for online with resolution/FPS, amber/red for 404 with exact provider error explanation).
   - Added 1-click Palembang city public CCTV presets:
     - 🏙️ SP Charitas (`cam8` - 1080p @ 30 FPS)
     - 🏙️ Simpang Polda (`cam3` - 1080p @ 30 FPS)
     - 🏙️ Benteng Kuto Besak (`cam2` - 1080p @ 30 FPS)
4. **Bundle Rebuilt**:
   - `dashboard/dist` refreshed via `npm run build`.
5. **Full Regression Verification**:
   - **56 / 56 tests PASSED** in 3.37 seconds.
