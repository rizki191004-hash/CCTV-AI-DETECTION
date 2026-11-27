# ADR-022: Deteksi Pintu/Gudang, Isolasi Tersangka, Crop Wajah Frontal, dan Anti-Spam Album Telegram

## Status
Accepted

## Context
Kebutuhan operasional CCTV AI Detection pada area pintu gerbang dan dalam gudang:
1. **Area Keluar-Masuk Pintu / Gerbang**: Membutuhkan deteksi khusus orang mencurigakan yang mondar-mandir (*loitering*) di zona perimeter pintu masuk/keluar.
2. **Area Dalam Gudang**: Membutuhkan deteksi gerak-gerik pengambilan barang ilegal, ditandai dengan posisi jongkok/membungkuk mencurigakan di rak penyimpanan barang disusul gerakan cepat meninggalkan area (*rapid departure*).
3. **Kebutuhan Snapshot Objek**: Pengguna menginginkan alert hanya meng-crop orang yang mencurigakan (bukan seluruh frame latar belakang), dan jika masih mencurigakan serta wajahnya terlihat, sistem harus melakukan zoom-in crop pada wajah tersangka.
4. **Kendala Anti-Spam Notifikasi**: Pengiriman dua foto terpisah (crop tubuh + crop wajah) menyebabkan spam notifikasi dan 2 kali dering pesan di Telegram. Notifikasi harus disatukan menjadi 1 gelembung pesan (*Media Group/Album*) dengan 1 dering saja.
5. **Kendala Wajah Membelakangi Kamera**: Jika tersangka membelakangi kamera, crop kepala bagian belakang tidak bernilai investigatif dan tidak boleh dikirimkan.

## Decision

1. **Rule Perilaku Gudang & Gerbang Pintu (`src/tracker.py`, `src/feature_extractor.py`, `src/rule_engine.py`, `config/rules.yaml`)**:
   - Menambahkan riwayat `recent_crouch_timestamp` pada `TrackHistory` dan `time_since_crouch_sec` pada `TrackFeatures`.
   - Menambahkan rule `warehouse_taking_goods`: mendeteksi jongkok/posisi rendah di zona penyimpanan barang gudang (`score: 40`, otomatis menjadi `80` di malam hari via `night_mode_multiplier`).
   - Menambahkan rule `warehouse_rapid_departure`: mendeteksi pergerakan cepat (kecepatan `>= 120 px/s`) yang terjadi dalam waktu `<= 5.0 detik` setelah jongkok (`score: 45`).
   - Menambahkan rule `gate_door_loitering`: mendeteksi orang berdiam di zona gerbang/pintu (`score: 35`).

2. **Ekstraksi Wajah & Validasi Visibilitas Frontal (`src/snapshot_scheduler.py`)**:
   - Mengimplementasikan `crop_face_region(frame, bbox, keypoints, padding=0.3)`:
     - Memeriksa keypoints wajah (hidung: 0, mata kiri: 1, mata kanan: 2).
     - **Gate Visibilitas**: Jika confidence keypoints wajah `< 0.25` (tersangka membelakangi kamera), fungsi langsung mengembalikan `None`.
     - Jika wajah frontal terkonfirmasi, dilakukan crop presisi dengan margin padding 30% pada bounding box wajah.
   - Mengimplementasikan `SnapshotScheduler.capture_face_crop(...)` yang menyimpan foto wajah dengan penamaan terstruktur `{camera_id}_{short_event}_{timestamp}_face.jpg`.

3. **Isolasi Tersangka Utama pada Event Multi-Person (`src/main.py`)**:
   - Jika terdapat banyak orang dalam satu event, sistem mengisolasi tersangka utama berdasarkan skor kecurigaan tertinggi:
     `primary_track_id = max(target_ids, key=lambda tid: getattr(scores.get(tid), "total_score", 0.0))`
   - Crop wajah hanya diekstrak dari tersangka utama tersebut jika skor event `>= 60` atau memicu rule kecurigaan tinggi (`warehouse_taking_goods`, `warehouse_rapid_departure`, `gate_door_loitering`, `suspicious_crouching`, dll.).

4. **Notifikasi Album Anti-Spam Telegram (`src/telegram_notifier.py`)**:
   - Menambahkan parameter `face_snapshot_path: Optional[str] = None` pada `send_alert()`.
   - Mengimplementasikan `_send_media_group_photos()` menggunakan `telegram.InputMediaPhoto` untuk menyatukan foto crop tubuh dan crop wajah dalam **1 Album Telegram**.
   - Caption detail, rincian skor, tombol video, dan informasi alert digabungkan pada foto pertama.
   - Pengguna hanya menerima **1 kali dering notifikasi** tanpa spam.
   - Dilengkapi fallback: jika pengiriman album gagal atau jika wajah tidak terlihat (tersangka membelakangi kamera), sistem tetap mengirimkan 1 foto crop tubuh secara andal.

## Consequences
- Deteksi pencurian/pengambilan barang di gudang dan intruksi pintu gerbang menjadi sangat akurat.
- Bukti visual yang dikirim ke Telegram sangat informatif: foto tubuh untuk mengenali pakaian/postur, dan foto zoom-in wajah untuk identifikasi identitas.
- Tidak ada spam notifikasi: 1 event = 1 album = 1 dering Telegram.
- Tidak ada foto bagian belakang kepala yang tidak berguna saat orang membelakangi kamera.
- 125 unit dan integrasi test lulus 100% tanpa regresi.
