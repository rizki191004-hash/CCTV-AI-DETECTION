# ADR-011: Optimasi Deteksi, Alert Notifikasi, dan Bounding Box Kendaraan

**Tanggal:** 2026-11-17  
**Status:** Diterima (Accepted)  

---

## 1. Konteks

Pada implementasi sebelumnya di kamera publik/jalanan (contoh: CCTV Dishub Palembang `SP CINDE`):
1. **False Alarm Beruntun:**
   - Konfigurasi default kamera memiliki `restricted_zone` yang terletak di tengah jalan (`[100, 200]` hingga `[400, 500]`), sehingga setiap pejalan kaki atau pengendara yang melintas langsung memicu status `CRITICAL - Masuk area terlarang (Skor 90)`.
   - Nilai `suspicious_score_threshold: 10` terlalu sensitif.
   - Nilai `confidence_threshold: 0.15` dan `alarm_gate.min_frames: 1` menyebabkan false positive dari bayangan atau noise 1-frame.
2. **Visual Clutter pada Kendaraan:**
   - Puluhan mobil dan motor yang sedang parkir, berhenti, atau berada jauh di kejauhan semuanya digambar kotak bounding box-nya. Ini membuat layar semrawut dan tidak fokus.
3. **Desinkronisasi Snapshot Notifikasi vs Live View:**
   - Di Live View, bounding box pengendara (`🏍️ Rider!` / `🚗 Driver!`) dan banner `RIDER DETECTED!` ditampilkan dengan jelas. Namun saat snapshot Telegram di-generate, parameter kendaraan tidak disertakan ke `Visualizer.draw_annotated_frame`.
   - Fungsi `capture_snapshot` menghapus buffer frame sebelum fungsi pemotongan `capture_human_crop` dijalankan.

---

## 2. Keputusan

1. **Optimasi Bounding Box Kendaraan (`only_riders=True`):**
   - Di `src/visualizer.py`: Default hanya menggambar kotak pada kendaraan yang **sedang dikendarai manusia** (`🏍️ Rider!` atau `🚗 Driver!`). Kendaraan kosong / parkir tidak lagi digambar kotaknya.
   - Di `src/vehicle_detector.py`: Ditambahkan filter dimensi minimum (`min_area=1200`, `min_dimension=35`) dan `confidence_threshold=0.45` untuk membuang deteksi kendaraan kecil sebesar semut di ujung cakrawala.
2. **Sinkronisasi Visual 1-ke-1 Snapshot Telegram:**
   - Pemanggilan `Visualizer.draw_annotated_frame` saat merekam snapshot kini menyertakan `vehicle_detections`, `riders`, `vehicle_count`, dan `only_riders=True`.
   - Mengubah urutan capture pada `_handle_alert` agar `capture_human_crop` dijalankan sebelum `capture_snapshot` membersihkan buffer.
3. **Kalibrasi Threshold & CCTV Jalan Raya:**
   - Mengosongkan `restricted_zone` default pada kamera jalan raya `SP CINDE` (`roi_zones: {}`).
   - Menaikkan `suspicious_score_threshold` dari `10` ke `60`.
   - Menaikkan `confidence_threshold` dari `0.15` ke `0.35`.
   - Menaikkan `alarm_gate.min_frames` dari `1` ke `3` frame stabil.

---

## 3. Konsekuensi

### Positif:
- Layar Live View dan foto Telegram kini bersih dan hanya menyorot orang serta pengendara aktif.
- Foto notifikasi Telegram 100% konsisten dengan visual Live View (memuat kotak motor/rider, banner HUD, dan waktu real-time).
- Menghentikan banjir false alarm "Masuk area terlarang" setiap ada kendaraan lewat di jalan raya.

### Negatif:
- Kendaraan yang parkir tanpa ada orang di sekitarnya tidak lagi diberi kotak (sesuai kebutuhan user). Jika ingin melihat semua kendaraan, parameter `only_riders=False` dapat diaktifkan.

