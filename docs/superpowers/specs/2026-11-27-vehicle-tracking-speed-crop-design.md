# Design Doc: Akurasi Bounding Box Pengendara Motor, Pelacakan & Kecepatan Kendaraan, dan Crop Objek Kendaraan

**Tanggal:** 2026-11-27  
**Status:** Draft (Menunggu Review Builder & Persetujuan Pengguna)  
**Terkait:** ADR-007, ADR-011, ADR-013

---

## 1. Tujuan & Latar Belakang (Intent & Why)

Saat ini sistem memiliki beberapa keterbatasan pada deteksi dan visualisasi kendaraan:
1. `VehicleDetector` bekerja secara *stateless* per frame tanpa pelacakan (`ByteTrack`), sehingga sistem tidak mengetahui apakah sebuah motor/mobil sedang **berhenti** atau **berjalan**, dan belum dapat menghitung **kecepatan**.
2. Flag `only_riders=True` di `main.py` dan `visualizer.py` menyembunyikan mobil yang pengemudinya tidak terlihat (misalnya tertutup kaca gelap), serta memunculkan label emoji (`🏍️`, `🚗`) yang tidak dapat dirender oleh `cv2.putText` OpenCV (tampil sebagai `??`).
3. Asosiasi pengendara (`find_riders`) hanya mengandalkan IoU murni (`>= 0.15`), yang sering meleset ketika rasio ukuran kotak orang dan motor/mobil berbeda jauh.
4. Pada `_handle_alert` di `main.py`, fungsi crop hanya memotong kotak manusia (`capture_human_crop`), sehingga ketika kejadian melibatkan kendaraan, tangkapan gambar tidak berfokus pada objek kendaraan seutuhnya.

**Tujuan utama:**
- Membuat deteksi dan visualisasi pengendara motor lebih akurat serta membedakan kondisi **Berhenti** vs **Berjalan** lengkap dengan **perhitungan kecepatan**.
- Menampilkan mobil (beserta kendaraan lainnya) secara bersih sebagai objek **Kendaraan** (tanpa memaksa deteksi pengemudi).
- Menjaga **deteksi pejalan kaki tetap berjalan** seperti biasa.
- **Mencegah spam Telegram:** Kendaraan yang sedang **terparkir/berhenti** hanya ditampilkan bounding box-nya di live view tanpa memicu alert/notifikasi Telegram.
- **Crop gambar kendaraan:** Saat alert/tangkapan gambar terkait kendaraan dipicu, foto yang diambil/dikirim berupa crop **objek kendaraannya saja**.

---

## 2. Goals, Non-Goals, & Anti-Goals

### Goals
1. **Pelacakan Kendaraan Persisten:** Menambahkan `VehicleTracker` berbasis `sv.ByteTrack` khusus kendaraan dengan ID unik (`#V1`, `#V2`, dst.) dan riwayat posisi/timestamp.
2. **Deteksi Kecepatan & Status Berhenti vs Berjalan:** Menghitung kecepatan halus (*smoothed speed*) dalam `px/s` dan estimasi `km/j`, dengan histeresis status `BERHENTI` vs `BERJALAN` agar getaran bounding box (*jitter*) tidak terbaca sebagai pergerakan.
3. **Asosiasi Pengendara Motor yang Lebih Akurat:** Menggunakan kombinasi *Intersection over Person* (**IoP**), **IoU**, dan posisi relatif orang di atas motor, serta menghilangkan emoji rusak pada OpenCV.
4. **Deteksi Mobil sebagai "Kendaraan":** Semua mobil dan motor ditampilkan di bounding box (`only_riders=False` untuk rendering kendaraan), di mana mobil berlabel bersih `Kendaraan`.
5. **Anti-Spam Kendaraan Terparkir:** Kendaraan berstatus `BERHENTI` hanya tampil di bounding box layar live, tidak memicu event/Telegram alert.
6. **Tangkapan Gambar Fokus Kendaraan (`capture_vehicle_crop`):** Saat alert melibatkan kendaraan (motor berjalan / mobil bergerak), snapshot di-crop fokus pada bounding box objek kendaraan saja; sedangkan alert khusus pejalan kaki tetap menggunakan `capture_human_crop`.

### Non-Goals
- Pengukuran kecepatan kalibrasi hukum/radar presisi tinggi (kecepatan `km/j` bersifat estimasi heuristik berbasis ukuran visual kendaraan kecuali pengguna menyetel faktor kalibrasi).
- Pengenalan plat nomor (ANPR/OCR).
- Menghilangkan deteksi dan rule engine pejalan kaki.

### Anti-Goals
- **Dilarang menggabungkan kendaraan ke `PersonTracker`:** Karena akan merusak *rule engine* perilaku manusia (seperti *loitering*, *fall*, *crouch*) dan sistem *Re-ID* manusia.
- **Dilarang mengirim alert Telegram untuk kendaraan terparkir/berhenti:** Menghindari banjir notifikasi palsu.

---

## 3. Pendekatan yang Dipertimbangkan (Approaches)

1. **Pendekatan 1 — `VehicleTracker` Terpisah (`ByteTrack`) + Asosiasi IoP + `capture_vehicle_crop()` *(Dipilih)***
   - Menambahkan pelacak `ByteTrack` independen di modul kendaraan.
   - Menghitung kecepatan & status berhenti/berjalan per ID kendaraan.
   - Memperbaiki asosiasi pengendara motor menggunakan IoP + penyelarasan vertikal.
   - Menambahkan `capture_vehicle_crop()` di `SnapshotScheduler`.
   - **Alasan dipilih:** Modular, performa CPU ringan (~1 ms/frame), tidak mencampuri logika `PersonTracker` / `RuleEngine` pejalan kaki, dan bekerja konsisten meski pengemudi mobil tertutup kaca.

2. **Pendekatan 2 — Menggabungkan Kendaraan ke `PersonTracker` *(Ditolak)***
   - Memasukkan class `car`/`motorcycle` ke tracker utama manusia.
   - **Alasan ditolak:** Mencemari data track manusia, memicu error logika postur/Re-ID, dan merusak pemisahan tanggung jawab.

3. **Pendekatan 3 — Tanpa Tracker Kendaraan (Stateless) *(Ditolak)***
   - Kecepatan dihitung hanya dari track orang di atas motor.
   - **Alasan ditolak:** Mobil tanpa track orang terlihat tidak bisa memiliki kecepatan ataupun status berhenti/berjalan.

---

## 4. Desain Teknis & Perubahan Komponen

### 4.1 `src/vehicle_detector.py` — Vehicle Tracking, Speed & Rider Association
- **Class Detection:** Tetap fokus pada `CAR_CLASS_ID = 2` (ditampilkan sebagai `"Kendaraan"`) dan `MOTORCYCLE_CLASS_ID = 3` (`"Motor"`).
- **`VehicleTracker` (berbasis `sv.ByteTrack`):**
  - Menyimpan riwayat `(centroid, bbox, timestamp)` per `vehicle_track_id` (maksimal ~30 titik terakhir atau jendela 3–5 detik).
  - **Perhitungan Kecepatan (Smoothed):**
    - Hitung perpindahan centroid antara titik terbaru dengan titik referensi sekitar `0.4–0.8` detik sebelumnya (bukan hanya 1 frame sebelumnya) untuk meredam *bounding box jitter*.
    - `speed_px_per_sec = distance_px / dt`
    - **Estimasi `km/h`:** Gunakan lebar/tinggi rata-rata kendaraan sebagai skala estimasi piksel-ke-meter (misal referensi panjang motor ~1.8m, mobil ~4.2m, atau faktor konfigurasi opsional `pixels_per_meter`), dikonversi ke `km/h = speed_mps * 3.6`, lalu dibulatkan.
  - **Status `BERHENTI` vs `BERJALAN` (dengan Histeresis):**
    - Ambang gerak default: `speed_px_per_sec >= 15.0` (dan perpindahan bersih `>= 8 px` dalam jendela waktu).
    - Jika kendaraan terdeteksi bergerak selama >= 2 frame beruntun -> status `"BERJALAN"`.
    - Jika kecepatan turun di bawah ambang batas selama >= 4 frame beruntun -> status `"BERHENTI"` (dan kecepatan ditampilkan `0 km/j`).
- **Akurasi Asosiasi Pengendara Motor (`find_riders`):**
  - Untuk motor (`MOTORCYCLE_CLASS_ID`): Hitung **IoP** (`inter_area / person_area`) dan **IoU**. Pengendara terkonfirmasi jika `iop >= 0.25` atau `iou >= 0.12` atau pusat tubuh bawah orang berada di atas/dalam rentang kotak motor (`px_center` dalam `[vx1 - margin, vx2 + margin]` dan `py_bottom` mendekati/di dalam `[vy1, vy2]`).
  - Untuk mobil (`CAR_CLASS_ID`): Mobil selalu diperlakukan sebagai objek `"Kendaraan"` saja (tidak memaksa deteksi/label `"Driver!"` terpisah).

### 4.2 `src/visualizer.py` — Bounding Box & Label Bersih
- **Pejalan Kaki Tetap:** Track `human` yang bukan pengendara motor tetap digambar seperti biasa (`#ID Berjalan | Skor: XX/100`).
- **Pengendara Motor:**
  - Ketika orang berasosiasi dengan motor (`Naik Motor`), kotak kendaraan & statusnya menampilkan kondisi secara akurat tanpa emoji `??`:
    - Saat berhenti: `[Motor #V1 | Naik Motor: Berhenti]`
    - Saat berjalan: `[Motor #V1 | Naik Motor: Berjalan | 22 km/j]`
  - Pada kotak manusia pengendara, label postur juga disinkronkan menjadi `Naik Motor (Berhenti)` atau `Naik Motor (Berjalan 22 km/j)` agar konsisten dengan ADR-013 (tetap kebal dari false alert Rule 11 *Berdiri Diam*).
- **Mobil / Kendaraan:**
  - Parameter default `only_riders` pada `draw_annotated_frame` diubah agar kendaraan (`Kendaraan`) tetap digambar (atau dipisahkan flag `show_parked_vehicles: bool = True`).
  - Saat parkir/diam: kotak tipis warna biru/abu dengan label `Kendaraan #V2 | Berhenti`.
  - Saat berjalan: kotak lebih tegas dengan label `Kendaraan #V2 | Berjalan | 34 km/j`.

### 4.3 `src/snapshot_scheduler.py` — Crop Objek Kendaraan
- Tambahkan fungsi `crop_vehicle_region(frame, vehicle_bboxes, padding=0.18)` dan method `capture_vehicle_crop(...)`:
  - Memotong frame secara ketat hanya pada bounding box objek kendaraan (motor/mobil yang menjadi target event) ditambah padding kecil (~18%) agar seluruh bodi kendaraan terlihat jelas tanpa mengikutsertakan objek latar lain.
- `capture_human_crop(...)` tetap dipertahankan utuh untuk event yang murni melibatkan pejalan kaki.

### 4.4 `src/main.py` & `src/api/routes.py` — Pipeline, Anti-Spam & Live View Sync
- **Pipeline (`src/main.py`):**
  - Menjalankan `vehicle_tracker.update(vehicle_result.vehicles)` setiap kali deteksi kendaraan berjalan, menghasilkan `vehicle_tracks` (berisi `track_id`, `class_id`, `bbox`, `is_moving`, `speed_px_s`, `speed_kmh`).
  - **Anti-Spam Kendaraan Terparkir:**
    - Kendaraan yang berstatus `BERHENTI` **tidak** memicu event alert ke Telegram/DB; hanya dirender bounding box-nya di live stream.
    - Jika kendaraan berstatus `BERJALAN` memicu event/alert (atau pengendara motor aktif memicu alert), `_handle_alert()` mengumpulkan bounding box kendaraan aktif (`vehicle_bboxes`) dan memanggil `capture_vehicle_crop()` sehingga **gambar yang dikirim ke Telegram adalah potongan objek kendaraannya saja**.
    - Jika event murni berasal dari pejalan kaki (tanpa kendaraan bergerak/pengendara), `_handle_alert()` tetap memakai `capture_human_crop()`.
- **Live View (`src/api/routes.py`):**
  - Meneruskan `vehicle_tracks` ke `Visualizer.draw_annotated_frame` agar tampilan web dashboard identik 1:1 dengan visualisasi snapshot.

---

## 5. Apa yang Diserahkan ke Implementer (Builder Calls)
- Penyetelan nilai default ambang kecepatan/histeresis (`15 px/s`, jendela `0.5s`, konfirmasi 2–4 frame) dan nilai default `padding=0.18` pada crop kendaraan dapat disesuaikan saat implementasi dan dikalibrasi melalui unit test.
- Memperbarui unit test lama yang mengharapkan string emoji literal (`🏍️`, `🚗`) atau `only_riders=True` sebagai default penyembunyi mobil jika diperlukan agar selaras dengan perilaku baru, sambil menjaga seluruh test suite hijau.
