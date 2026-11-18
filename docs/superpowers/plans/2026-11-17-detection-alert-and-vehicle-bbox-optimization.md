# Plan: Optimasi Deteksi, Alert Notifikasi, dan Bounding Box Kendaraan

**Tanggal:** 2026-11-17  
**Status:** 🔄 In Progress  

## Masalah yang Ditemukan
1. **Layar Penuh Kotak Kendaraan (Visual Clutter):**
   - Puluhan mobil dan motor parkir/lewat di kejauhan semuanya diberi bounding box.
   - Kendaraan kecil sebesar semut di ujung jalan raya ikut terdeteksi dan memicu noise.
2. **Pemberitahuan Mencurigakan Tidak Sesuai Live View (False Alarm & Visual Desync):**
   - `restricted_zone` aktif di tengah jalan raya CCTV `SP CINDE`, memicu status `CRITICAL - Masuk area terlarang (Skor 90)` setiap kendaraan lewat.
   - `suspicious_score_threshold: 10` terlalu rendah (pejalan kaki normal langsung memicu alert).
   - Snapshot Telegram tidak memuat kotak motor/rider yang ada di Live View karena parameter kendaraan tidak dioper ke visualizer saat update snapshot.
   - Bug buffer frame pada `capture_human_crop` terhapus sebelum fungsi crop dijalankan.

## Keputusan Arsitektur & Solusi (ADR-011)
1. **Optimasi Bounding Box Kendaraan:**
   - Di `src/visualizer.py`: Default hanya gambar kotak pada kendaraan yang **sedang dikendarai** (`🏍️ Rider!` atau `🚗 Driver!`). Kendaraan pasif/parkir tidak digambar kotaknya agar layar bersih dan fokus pada manusia/pengendara.
   - Di `src/vehicle_detector.py`: Tambahkan filter ukuran minimum (`min_area=1200`, `min_dimension=35`) dan naikkan default confidence kendaraan ke `0.45` untuk mengabaikan kendaraan semut di kejauhan.
2. **Sinkronisasi Visual Snapshot dengan Live View:**
   - Di `src/main.py`: Pastikan pemanggilan `Visualizer.draw_annotated_frame` saat `update_best_frame` menyertakan `vehicle_detections`, `riders`, dan `vehicle_count`.
   - Perbaiki urutan `capture_human_crop` dan `capture_snapshot` di `src/main.py` dan `src/snapshot_scheduler.py` agar snapshot yang dikirim ke Telegram memiliki visual yang 100% konsisten.
3. **Kalibrasi Threshold & CCTV Jalan Raya:**
   - Di `config/config.yaml`:
     - Kosongkan `restricted_zone` pada kamera jalan raya `SP CINDE`.
     - Naikkan `suspicious_score_threshold` dari `10` ke `60`.
     - Naikkan `confidence_threshold` dari `0.15` ke `0.35`.
     - Naikkan `alarm_gate.min_frames` dari `1` ke `3` untuk menyaring noise 1 frame.

## Langkah Eksekusi (TDD)
- [x] 1. TDD: Tulis unit test untuk filter kendaraan dan sinkronisasi snapshot (`tests/test_vehicle_bbox_optimization.py`)
- [x] 2. Update `src/vehicle_detector.py` (filter min_area & distant objects)
- [x] 3. Update `src/visualizer.py` (hanya gambar rider/driver saat `only_riders=True`)
- [x] 4. Update `src/main.py` & `src/snapshot_scheduler.py` (sinkronisasi snapshot visual)
- [x] 5. Kalibrasi `config/config.yaml`
- [x] 6. Jalankan full test suite (`pytest tests/`) — 70/70 PASS ✅
- [x] 7. Buat `docs/adr/ADR-011-detection-alert-and-vehicle-bbox-optimization.md`
