# Plan: Nonaktifkan Deteksi Hewan & Fokus Penuh pada Manusia dan Kendaraan

**Tanggal:** 2026-11-17  
**Status:** 🔄 In Progress  

## Masalah yang Ditemukan
1. Di `src/tracker.py` baris 160:
   `class_type = "human" if class_id == 0 else "animal"`
   Menyebabkan **semua objek selain manusia (seperti sepeda motor class 3, kursi, bangku) otomatis dilabeli sebagai "Animal #ID"**.
2. Di CCTV jalan raya dan keamanan, deteksi burung/kucing/anjing menimbulkan clutter visual dan false alarm yang tidak relevan.
3. HUD menampilkan `Animals: X` yang membingungkan saat motor lewat.

## Keputusan Arsitektur & Solusi (ADR-012)
1. **Perbaikan Tracker (`src/tracker.py`):**
   - Hapus klasifikasi biner `if class_id == 0 else "animal"`.
   - Hanya beri label `"animal"` jika `class_id in {14, 15, 16}` (burung, kucing, anjing).
   - Beri label `"human"` untuk `class_id == 0`.
   - Objek lain diberi label sesuai kelasnya atau diabaikan dari tracker manusia.
2. **Nonaktifkan Deteksi Hewan (`src/person_detector.py`):**
   - Hapus kelas hewan (`BIRD_CLASS_ID`, `CAT_CLASS_ID`, `DOG_CLASS_ID`) dari `DETECTABLE_CLASSES`.
   - `PersonDetector` kini fokus mendeteksi manusia (`PERSON_CLASS_ID = 0`), sementara kendaraan dideteksi khusus oleh `VehicleDetector`.
   - `animal_count` diset default `0` dan `animals` kosong untuk backward compatibility.
3. **Penyederhanaan HUD Live View (`src/visualizer.py`):**
   - Sederhanakan format HUD menjadi:
     `👤 Persons: X | 🚗 Vehicles: Y`
   - Hilangkan `Animals: Z` dari tampilan utama.

## Langkah Eksekusi (TDD)
- [x] 1. Tulis unit test di `tests/test_animal_classification_fix.py` (Red)
- [x] 2. Update `src/tracker.py` (pemetaan class_type yang benar)
- [x] 3. Update `src/person_detector.py` (fokus person, nonaktifkan animal)
- [x] 4. Update `src/visualizer.py` (HUD `Persons: X | Vehicles: Y`)
- [x] 5. Jalankan full test suite (`pytest tests/`) — 73/73 PASS ✅
- [x] 6. Rebuild dashboard (`npm run build`)
- [x] 7. Buat `docs/adr/ADR-012-disable-animal-detection-and-focus-human-vehicle.md`

