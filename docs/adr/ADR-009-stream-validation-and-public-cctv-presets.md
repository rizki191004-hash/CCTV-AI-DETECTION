# ADR-009: Camera Stream Pre-Flight Validation and Public CCTV Catalog Presets

**Date:** 2026-11-17  
**Status:** Accepted  
**Deciders:** User + Antigravity  

---

## Context

When users attempted to connect external public CCTV streams (such as `https://stream.palembang.go.id/cam47/index.m3u8`), the stream failed to open because the camera at that specific intersection was offline/returning HTTP 404 from the provider's server. Because there was no pre-flight validation, operators were left uncertain whether the failure was caused by local system misconfiguration or by the external streaming provider.

Furthermore, out of 30 official Palembang City CCTV streams, 16 are actively broadcasting Full HD (1080p @ 30 FPS). Having ready-to-use presets saves operators from having to manually discover and copy-paste stream URLs.

---

## Decisions

### 1. Pre-Flight Stream Probe Endpoint (`POST /api/cameras/probe`)
A dedicated lightweight endpoint tests incoming stream sources before saving:
- Supports RTSP, HTTP/HTTPS HLS (`.m3u8`), and USB Webcam indices.
- Performs a 3-second non-blocking probe using OpenCV/urllib.
- Returns detailed diagnostics:
  ```json
  {
    "online": true,
    "source_type": "HLS",
    "resolution": "1920x1080",
    "fps": 30.0,
    "message": "Stream aktif dan terhubung (1920x1080 @ 30.0 FPS)"
  }
  ```
- If the provider server returns HTTP 404 or connection timeout, reports the exact root cause:
  `"Server penyedia merespons HTTP 404 (Kamera offline/tidak ditemukan di server asal)."`

### 2. Dashboard Stream Testing & Warning Banner
In `dashboard/src/App.tsx`:
- Operators can click **"⚡ Tes Koneksi Stream"** to verify a camera URL before saving.
- If a stream is verified as offline (404), a clear warning is displayed to prevent confusion.

### 3. Palembang City Public CCTV Catalog Presets
In `CameraManager`:
- Add instant 1-click presets for active Palembang traffic cameras:
  - `CCTV SP Charitas` (`cam8` - 1080p)
  - `CCTV Simpang Polda` (`cam3` - 1080p)
  - `CCTV Benteng Kuto Besak` (`cam2` - 1080p)
  - `CCTV Simpang Angkatan 45` (`cam5` - 1080p)

---

## Consequences

- Operators immediately know whether a stream is working before adding it.
- Prevents silent pipeline failures caused by dead external feeds.
- Full compatibility with existing cameras and config files.

