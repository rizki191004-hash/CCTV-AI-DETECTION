from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.cell(0, 10, 'Kesimpulan: CCTV AI DETECTION', align='C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Halaman {self.page_no()}', align='C')

pdf = PDF()
pdf.add_page()
pdf.set_font('helvetica', size=12)

content = """Konsep Utama Aplikasi
Aplikasi ini adalah sebuah Sistem Keamanan CCTV Cerdas Berbasis AI (YOLOv8 + ByteTrack). Sistem ini secara aktif mendeteksi pergerakan, melacak pergerakan manusia, menganalisis perilaku mencurigakan secara otomatis, dan memberikan peringatan dini (early warning) langsung ke pengguna melalui Telegram.

Fitur dan Kemampuan Unggulan

1. Pemrosesan Cerdas (Adaptive Detection & Tracking)
- Motion Gate (MOG2): Sangat hemat resource (CPU/GPU) karena AI (YOLO) hanya aktif saat ada gerakan.
- Person Tracking: Kombinasi YOLOv8 (deteksi objek) dan ByteTrack (pelacakan rute & ID).

2. Advanced Rule Engine (Analisis Perilaku)
Sistem memiliki Rule Engine yang menilai tingkat ancaman (skor 0-100) berdasarkan:
- Masuk ke zona terlarang (Restricted Zone).
- Berkeliaran terlalu lama di satu area (Loitering).
- Bergerak mendekati kamera secara cepat.
- Aktivitas di luar jam wajar (malam hari).
- Pergerakan mondar-mandir yang mencurigakan.

3. Notifikasi Telegram Anti-Spam
- Terintegrasi langsung dengan Telegram Bot.
- Mengirim alert awal lengkap dengan foto snapshot.
- Memiliki fitur Anti-Spam & Cooldown, menghindari pesan berlebihan.
- Snapshot lanjutan dikirim secara periodik jika aktivitas masih berlanjut.

4. Dashboard dan Akses Publik (Cloudflared)
- Dashboard berbasis web lokal (FastAPI/Uvicorn).
- Akses jarak jauh tanpa Port Forwarding menggunakan Cloudflare Tunnel (cloudflared.exe) via start.bat.

5. Manajemen Data (Database)
- Menyimpan log kejadian di SQLite (data/cctv_events.db).
- Mencatat waktu kejadian, jenis rule yang terpicu, skor ancaman, dan history pelacakan.

6. Fleksibilitas Infrastruktur
- Mendukung banyak kamera (RTSP / IP Camera) via Multithreading.
- Mendukung CPU, GPU (NVIDIA CUDA), dan OpenVINO.
- Dapat dijalankan secara lokal (Virtual Environment) atau via Docker.

Kesimpulan Singkat
Aplikasi CCTV AI DETECTION adalah solusi surveillance tingkat enterprise yang praktis. Kombinasi efisiensi deteksi, akurasi AI mutakhir, kecerdasan Rule Engine, dan kemudahan akses remote via Telegram & Cloudflare menjadikannya sistem keamanan yang sangat proaktif dan fungsional."""

pdf.multi_cell(w=0, h=7, text=content)
    
pdf.output('Kesimpulan_CCTV_AI_DETECTION.pdf')
print("PDF created successfully!")
