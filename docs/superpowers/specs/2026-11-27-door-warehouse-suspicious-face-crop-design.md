# Design Doc: Optimasi Deteksi Orang Mencurigakan di Pintu/Gerbang & Gudang, Crop Objek Orang, dan Zoom-in Wajah Anti-Spam

**Tanggal:** 2026-11-27  
**Status:** Draft (Menunggu Review Builder & Persetujuan Pengguna)  
**Terkait:** ADR-003, ADR-011, ADR-013, ADR-021

---

## 1. Tujuan & Latar Belakang (Intent & Why)

Sistem CCTV AI Detection saat ini telah mampu mendeteksi orang, kendaraan, dan postur umum (berdiri, duduk, berjalan, jatuh, merayap/jongkok). Namun, untuk skenario keamanan spesifik seperti **area pintu/gerbang** dan **area gudang (pengambilan barang)**, pengguna memerlukan pemantauan yang lebih tajam dan barang bukti identifikasi yang lebih jelas:
1. **Pintu / Gerbang:** Deteksi orang yang keluar-masuk secara mencurigakan, berdiam lama mengawasi gerbang, mondar-mandir di depan pintu, atau menerobos saat jam rawan.
2. **Dalam Gudang:** Deteksi aktivitas pengambilan barang tanpa izin, ditandai dengan postur merunduk/jongkok di area rak/penyimpanan barang (*crouching/taking goods*) dan berdiam lama di zona barang.
3. **Kualitas Barang Bukti & Anti-Spam:**
   - Foto bukti di Telegram harus terfokus pada **objek orangnya saja** (*person crop* ketat), bukan foto lanskap CCTV yang terlalu luas.
   - Saat terindikasi sangat mencurigakan (atau mengambil barang / jam malam), sistem secara otomatis mengekstrak foto **zoom-in wajah pelaku** (*face crop*).
   - **Anti-Spam:** Seluruh bukti (foto badan + foto wajah) wajib dikirimkan dalam **1 notifikasi saja (Telegram Media Group / Album)** tanpa dering notifikasi beruntun yang mengganggu pengguna.

---

## 2. Goals, Non-Goals, & Anti-Goals

### Goals
1. **Crop Wajah Cerdas (`capture_face_crop`):** Mengekstrak area wajah/kepala menggunakan pose keypoints (mata, hidung, telinga) yang disempurnakan dengan detektor wajah OpenCV / upper-body ROI tanpa memerlukan model deep learning tambahan yang berat.
2. **Crop Objek Orang Ketat (`capture_human_crop`):** Memastikan foto utama terfokus proporsional pada pelaku yang memicu alert.
3. **Aturan Khusus Pintu/Gerbang & Gudang:**
   - Menambahkan preset rule perilaku untuk deteksi pintu/gerbang (mondar-mandir, dwell time pintu, penyeberangan garis gerbang).
   - Menambahkan rule perilaku gudang: postur merunduk/jongkok di area penyimpanan barang (`warehouse_taking_goods`) yang langsung menaikkan skor kecurigaan ke level tinggi.
4. **Anti-Spam Telegram (Single Bubble Media Group):**
   - Menggabungkan foto tubuh dan foto wajah ke dalam 1 pesan album Telegram (`send_media_group` menggunakan `InputMediaPhoto`). Pengguna hanya menerima **1 kali notifikasi ringkas** berisi 2 foto berdampingan.
   - Jika wajah tidak terdeteksi (misal membelakangi kamera), sistem dengan anggun hanya mengirim foto badan tanpa error.
   - Cooldown 45–60 detik per event/pelaku dan stability window untuk mencegah false positive dari orang yang sekadar melintas normal.

### Non-Goals
- Face Recognition / Database Pencocokan Identitas KTP/Biometrik (fokus pada ekstraksi foto wajah beresolusi tinggi untuk bukti visual manusia, bukan pencocokan nama orang di database).
- Pengenalan objek barang spesifik seperti kardus/palet (menggunakan kombinasi deteksi manusia + zona rak/gudang + postur merunduk/mengambil barang).

### Anti-Goals
- **Dilarang membombardir pesan Telegram terpisah (Spamming):** Jangan kirim foto badan lalu 2 detik kemudian kirim foto wajah dalam pesan terpisah.
- **Dilarang membebani FPS pemrosesan dengan model deep learning wajah raksasa:** Sistem harus tetap berjalan mulus pada CPU dan laptop pengguna.

---

## 3. Pendekatan yang Dipertimbangkan (Approaches)

1. **Pendekatan 1 — Hybrid Multi-Crop: 1 Notifikasi Album Telegram + Pose/Upper-ROI Face Extractor *(Dipilih)***
   - Mengekstrak wajah dari bounding box orang menggunakan pose keypoints kepala (titik 0..4: hidung, mata, telinga) atau fallback upper-body ROI (top 25-35% bounding box) yang disempurnakan detektor OpenCV.
   - Mengirimkan 1 pesan Telegram berupa album media (`InputMediaPhoto`) yang memuat foto tubuh dan foto wajah sekaligus.
   - **Alasan dipilih:** 100% anti-spam (hanya 1 dering), bukti visual sangat lengkap, ringan dan cepat (~0–2 ms per snapshot), serta bekerja konsisten tanpa dependensi berat.

2. **Pendekatan 2 — Notifikasi Bertahap / Escalation Sequential *(Ditolak)***
   - Kirim foto tubuh dulu, lalu jika masih ada di lokasi kirim foto wajah.
   - **Alasan ditolak:** Menimbulkan notifikasi ganda yang dirasa seperti spam oleh pengguna, serta berisiko terlambat mengirim wajah jika pelaku langsung melarikan diri setelah mengambil barang.

3. **Pendekatan 3 — Dedicated Deep Learning Face Detector (InsightFace / MTCNN) *(Ditolak)***
   - Menjalankan model neural network terpisah untuk deteksi wajah.
   - **Alasan ditolak:** Menambah konsumsi RAM $>500\text{ MB}$, memperlambat frame rate video stream, dan memperbesar risiko kegagalan instalasi pada mesin pengguna.

---

## 4. Desain Teknis & Arsitektur Komponen

### 4.1 Modul Ekstraksi Wajah & Snapshot (`src/snapshot_scheduler.py`)
- **Penentuan Target Pelaku pada Multi-Person:**
  - Pada kejadian yang melibatkan lebih dari satu orang, `capture_face_crop` secara spesifik mengisolasi orang yang memiliki **skor kecurigaan tertinggi** (`primary_track_id = max(event.track_ids, key=lambda tid: scores[tid])`) atau pelaku yang memicu rule kritis, bukan sembarang orang pertama di frame.
- **`crop_face_region(frame: np.ndarray, bbox: Sequence[float], keypoints: Optional[np.ndarray] = None, padding: float = 0.3) -> Optional[np.ndarray]`:**
  - **Deteksi Keterlihatan Wajah (Face Visibility Gate):**
    - Jika `keypoints` tersedia: periksa titik mata dan hidung (indeks 0, 1, 2). Jika confidence titik wajah $< 0.25$ (menandakan pelaku membelakangi kamera atau wajah tertutup penuh), `crop_face_region` mengembalikan `None`.
    - Jika keypoints tidak tersedia: gunakan detektor wajah OpenCV (`haarcascade_frontalface_default.xml` atau profil haar). Jika wajah tidak terkonfirmasi dan tidak menghadap depan, sistem mengembalikan `None`.
    - Dengan demikian, jika pelaku membelakangi kamera, sistem tidak akan mengirim foto belakang kepala, melainkan anggun mengirimkan **1 foto seluruh badan** saja.
  - Jika wajah terkonfirmasi menghadap kamera: potong area kepala/wajah dengan padding 30%, dibatasi batas dimensi gambar (`np.clip`).
- **`capture_face_crop(camera_id: str, event_id: str, bbox: Sequence[float], keypoints: Optional[np.ndarray] = None, frame_override: Optional[np.ndarray] = None) -> Optional[str]`:**
  - Menyimpan foto wajah dengan nama file: `{camera_id}_{short_event}_{timestamp}_face.jpg`. Mengembalikan `None` jika wajah tidak terdeteksi menghadap kamera.

### 4.2 Aturan Perilaku & Rule Engine (`src/rule_engine.py` & `config/rules.yaml`)
- **Rule Pintu & Gerbang:**
  - `gate_door_loitering`: Berdiam di zona pintu/gerbang $\ge 15\text{ detik}$ (Skor +35).
  - `gate_line_crossing`: Menyeberang garis virtual gerbang/pintu (`LineCrossing`) (Skor dasar +40 di siang hari, dan otomatis terkalibrasi menjadi +80 di malam hari melalui `night_mode_multiplier = 2.0`).
  - `door_back_and_forth`: Mondar-mandir di dekat pintu/gerbang dengan $\ge 3$ kali pergantian arah (Skor +35).
- **Rule Gudang (Mengambil Barang):**
  - `warehouse_taking_goods`: Terdeteksi di `warehouse_zone` atau `storage_zone` sambil melakukan postur `crouch_like` / `CROUCHING_CRAWLING` selama $\ge 2\text{ detik}$ (Skor +60).
  - `warehouse_night_presence`: Berada di gudang pada jam malam/tutup operasional (Skor +80, Critical).
  - `warehouse_rapid_departure`: Kecepatan $\ge 120\text{ px/s}$ dalam jendela waktu 5 detik setelah terdeteksi merunduk/jongkok di zona gudang (Skor +30). Status transisi dicatat pada riwayat track di `FeatureExtractor`.

### 4.3 Pengiriman Telegram Album Anti-Spam (`src/telegram_notifier.py`)
- Memperbarui method `send_alert`:
  - Parameter baru: `face_snapshot_path: Optional[str] = None`.
  - Jika **kedua** snapshot tersedia (`snapshot_path` dan `face_snapshot_path`):
    - Gunakan `bot.send_media_group(chat_id=..., media=[InputMediaPhoto(body_bytes, caption=...), InputMediaPhoto(face_bytes)])`.
    - Pesan Telegram tampil sebagai satu album 2 foto elegan tanpa spam.
  - Jika hanya foto tubuh yang ada (wajah tidak terlihat): kirim single photo normal.

### 4.4 Integrasi Pipeline (`src/main.py`)
- Di dalam `_handle_alert()`:
  1. Kumpulkan bounding box manusia aktif.
  2. Ambil keypoints pose manusia aktif (jika ada).
  3. Panggil `capture_human_crop()` untuk foto fokus tubuh pelaku.
  4. Jika event mencurigakan melibatkan indikasi tinggi (skor $\ge 60$ dengan triggered rules pintu/gudang/merunduk atau skor $\ge 80$): panggil `capture_face_crop()`.
  5. Teruskan kedua path foto ke `self.telegram.send_alert(..., snapshot_path=crop_snapshot, face_snapshot_path=face_snapshot)`.

---

## 5. Yang Diserahkan ke Builder (Builder Calls)
- Penyesuaian persentase margin padding crop wajah (default 30% di sekitar kepala).
- Penanganan jika `InputMediaPhoto` Telegram gagal karena ukuran/timeout, dengan fallback otomatis ke pengiriman foto utama saja.
- Format nama caption Telegram yang memuat info status postur ("Merunduk di Gudang" / "Menerobos Gerbang").

---

## 6. Rencana Pengujian (Testing Strategy)
- `tests/test_face_crop.py`: Uji `crop_face_region` dengan keypoints kepala dan dengan fallback upper-body.
- `tests/test_warehouse_door_rules.py`: Uji trigger rule gerbang dan rule gudang mengambil barang.
- `tests/test_telegram_album_alert.py`: Uji pengiriman album Telegram saat ada crop badan + crop wajah.
- Menjaga seluruh 111 test yang sudah ada tetap 100% passing.
