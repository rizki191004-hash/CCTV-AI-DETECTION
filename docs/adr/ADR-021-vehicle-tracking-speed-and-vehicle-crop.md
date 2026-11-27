# ADR-021: Vehicle Tracking, Speed Estimation, Anti-Spam Gate, and Vehicle-Focused Crop

## Status
Accepted

## Context
Pada sistem CCTV AI Detection sebelumnya:
1. `VehicleDetector` bekerja secara *stateless* tanpa pelacakan frame-ke-frame (`ByteTrack`), sehingga sistem tidak dapat membedakan apakah kendaraan sedang berhenti atau berjalan, dan tidak ada perhitungan kecepatan.
2. Mobil yang tidak terdeteksi pengemudinya (misalnya karena kaca gelap atau sudut kamera) disembunyikan oleh filter `only_riders=True`, dan label pengendara menggunakan karakter emoji (`🏍️`, `🚗`) yang rusak ketika dirender dengan `cv2.putText` OpenCV (menghasilkan karakter `??`).
3. Kendaraan yang terparkir atau diam berisiko memicu spam alert jika disamakan dengan pergerakan mencurigakan.
4. Ketika event melibatkan kendaraan bermotor, fungsi snapshot Telegram hanya memotong kotak manusia (`capture_human_crop`), sehingga gambar tidak memperlihatkan objek kendaraan seutuhnya.

## Decision
1. **Dedicated `VehicleTracker` (`ByteTrack` terpisah)**:
   - Dibuat kelas `VehicleTracker` di `src/vehicle_tracker.py` menggunakan `supervision.ByteTrack` khusus untuk mendeteksi mobil dan motor dengan ID unik (`#V1`, `#V2`, dst.).
   - Pelacakan dipisahkan dari `PersonTracker` agar tidak mencemari fitur postur, rule engine perilaku manusia, dan sistem Re-ID pejalan kaki.
   - Digunakan ambang pencocokan `minimum_matching_threshold = 0.95` untuk mengatasi pergerakan cepat kendaraan antar frame.

2. **Smoothed Speed Calculation & Histeresis Status**:
   - Kecepatan dihitung dengan jendela waktu bergerak (`0.5s`) untuk meredam jitter bounding box.
   - Ambang batas gerakan: `>= 15.0 px/s`.
   - Histeresis: Memerlukan 2 frame berurutan di atas ambang untuk beralih ke `BERJALAN`, dan 4 frame berurutan di bawah ambang untuk beralih ke `BERHENTI` (kecepatan menjadi `0 km/j`).
   - Estimasi kecepatan `km/j` dikonversi berdasarkan ukuran fisik referensi kendaraan (panjang motor ~1.8m, mobil ~4.2m).

3. **Visualisasi Bersih & Mobil sebagai "Kendaraan"**:
   - Karakter emoji dihapus dan diganti dengan teks ASCII bersih (`Naik Motor`, `Mengemudi`).
   - Mobil dan motor ditampilkan di layar live MJPEG (`only_riders=False`).
   - Mobil berlabel bersih: `Kendaraan #V2 | Berhenti` atau `Kendaraan #V2 | Berjalan | 34 km/j`.
   - Motor berlabel: `Motor #V1 | Naik Motor: Berhenti` atau `Motor #V1 | Naik Motor: Berjalan | 22 km/j`.
   - Pejalan kaki tetap terdeteksi normal dengan skeletal pose dan rule engine aslinya.

4. **Anti-Spam Kendaraan Terparkir**:
   - Kendaraan yang berstatus `BERHENTI` hanya menampilkan bounding box di live view web dashboard dan **tidak** memicu notifikasi/alert ke Telegram.

5. **Tangkapan Gambar Fokus Objek Kendaraan (`capture_vehicle_crop`)**:
   - Ditambahkan `crop_vehicle_region` dan `capture_vehicle_crop` di `src/snapshot_scheduler.py` dengan padding 18%.
   - Saat event terkait kendaraan aktif/bergerak terjadi, snapshot yang dikirim ke Telegram di-crop berfokus pada objek kendaraannya saja (bukan crop manusia).
   - Event khusus pejalan kaki tetap menggunakan `capture_human_crop`.

## Consequences
- Bounding box motor dan mobil kini memiliki identitas persisten dan indikator kecepatan yang stabil tanpa glitch atau jitter.
- Tampilan teks di live stream dan snapshot bebas dari karakter emoji rusak (`??`).
- Pengguna tidak terganggu spam alert Telegram dari kendaraan yang hanya terparkir di depan CCTV.
- Foto bukti alert Telegram untuk pengendara motor atau mobil bergerak kini menampilkan wujud kendaraannya secara utuh dan jelas.
- Seluruh 111 unit & integration test lulus 100%.
