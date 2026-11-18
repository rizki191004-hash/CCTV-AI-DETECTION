# Plan: Perbaikan Postur Pengendara Motor (Naik Motor) & Imunitas Rule Berdiri Diam

**Tanggal:** 2026-11-17  
**Status:** 🔄 In Progress  

## Masalah yang Ditemukan
1. Di `src/visualizer.py`:
   - `_get_posture_state()` memeriksa `aspect < 1.3` untuk deteksi duduk. Pengendara motor bertubuh tegak memiliki rasio tinggi `aspect >= 1.3`, sehingga gagal terdeteksi duduk.
   - Jika motor berhenti di lampu merah atau melaju perlahan (`speed < 25`), pengendara jatuh ke fallback dan dicap sebagai **`Berdiri Diam`**.
   - Jika motor melaju cepat, pengendara dicap sebagai **`Berjalan`**.
   - `_get_posture_state()` tidak menerima informasi `vehicle_detections` atau `riders` dari `VehicleDetector`.
2. Di `src/feature_extractor.py` & `src/rule_engine.py`:
   - Rule 11 (`person_berdiri_diam`) menaikkan skor kecurigaan jika seseorang "berdiri diam" lebih dari 10 detik. Hal ini memicu false alarm saat pengendara motor berhenti di lampu merah.

## Keputusan Arsitektur & Solusi (ADR-013)
1. **Label Postur Khusus `Naik Motor` (`src/visualizer.py`):**
   - Berikan akses data `riders` dan `vehicle_detections` ke `_get_posture_state()`.
   - Jika person terasosiasi dengan motor (`is_motorcycle_rider`), posturnya langsung menjadi **`🏍️ Naik Motor`** dengan warna khusus (oranye keemasan).
   - Jika terasosiasi dengan mobil, posturnya menjadi **`🚗 Mengemudi`**.
   - Mencegah pengendara jatuh ke label `Berdiri Diam` atau `Berjalan`.
2. **Kekebalan dari Rule Berdiri Diam (`src/feature_extractor.py`):**
   - Update `_classify_posture()` dan `analyze_posture()` agar mendeteksi status berkendara (`naik_motor` / `RIDING_VEHICLE`).
   - Pengendara motor kebal dari Rule 11 (`person_berdiri_diam`).

## Langkah Eksekusi (TDD)
- [ ] 1. Tulis unit test di `tests/test_motorcycle_rider_posture.py` (Red)
- [ ] 2. Update `src/visualizer.py` (`_get_posture_state` mendukung rider motor/mobil)
- [ ] 3. Update `src/feature_extractor.py` (posture `naik_motor`)
- [ ] 4. Jalankan full test suite (`pytest tests/`)
- [ ] 5. Rebuild dashboard jika diperlukan
- [ ] 6. Buat `docs/adr/ADR-013-motorcycle-rider-posture-and-loitering-immunity.md`

