# ADR-012: Perbaikan Kesalahan Klasifikasi Animal & Fokus Penuh pada Manusia dan Kendaraan

**Tanggal:** 2026-11-17  
**Status:** Diterima (Accepted)  

---

## 1. Konteks

Pada pengujian Live View CCTV jalan raya / keamanan, terdeteksi bug visual di mana **sepeda motor yang melintas diberi label `Animal #ID (85%)` dengan kotak oranye**, dan counter HUD bertuliskan `Animals: 1`.

Setelah penelusuran kode, ditemukan akar masalah pada `src/tracker.py` baris 160:
```python
class_type = "human" if class_id == 0 else "animal"
```
Logika biner ini menganggap **setiap objek selain class 0 (person) secara membabi-buta sebagai "Animal"**. Karena sepeda motor adalah COCO class 3, sistem secara salah melabelinya sebagai hewan.

Selain itu, di lingkungan CCTV jalan raya dan pengawasan keamanan, pendeteksian burung, kucing liar, dan anjing tidak memberikan nilai keamanan, melainkan hanya membebani inferensi dan menimbulkan false alarm di layar.

---

## 2. Keputusan

1. **Perbaikan Logika Klasifikasi Tracker (`src/tracker.py`):**
   - Hapus asumsi `class_id != 0` adalah animal.
   - Hanya beri label `"animal"` jika `class_id in {14, 15, 16}` (burung, kucing, anjing).
   - Beri label `"human"` jika `class_id == 0`.
   - Beri label `"vehicle"` jika `class_id in {2, 3}` (mobil, motor).
   - Objek lain diberi label `"object"` dan tidak digambar sebagai orang atau hewan.

2. **Nonaktifkan Deteksi Hewan di PersonDetector (`src/person_detector.py`):**
   - Hapus ID hewan (14, 15, 16) dari `DETECTABLE_CLASSES`.
   - `PersonDetector` kini fokus mendeteksi manusia dan objek pendukung postur (kursi/bangku untuk deteksi duduk).
   - Deteksi kendaraan ditangani secara terpisah dan optimal oleh `VehicleDetector`.

3. **Penyederhanaan Tampilan HUD (`src/visualizer.py`):**
   - Format HUD diubah menjadi:
     `Persons: X | Vehicles: Y`
   - Label `Animals: Z` hanya ditampilkan jika memang terdeteksi hewan asli (`animal_count > 0`), sehingga secara default tidak lagi mengotori layar.

---

## 3. Konsekuensi

### Positif:
- Sepeda motor yang melintas **100% tidak akan pernah lagi** dilabeli sebagai `Animal`.
- Inferensi YOLO menjadi lebih cepat dan ringan karena tidak memproses kelas burung, kucing, dan anjing.
- HUD dan Live View jauh lebih bersih, rapi, dan profesional (hanya menampilkan Persons dan Vehicles).

### Negatif:
- Kucing liar atau burung yang lewat di depan kamera tidak lagi diberi kotak (sesuai persetujuan pengguna untuk CCTV keamanan/jalan raya).

