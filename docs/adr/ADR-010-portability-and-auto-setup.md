# ADR-010: Portabilitas & Auto-Setup untuk Distribusi

**Tanggal:** 2026-11-17  
**Status:** Accepted  
**Decider:** Tim CCTV AI

---

## Konteks

Aplikasi CCTV AI Detection perlu dapat dijalankan di perangkat Windows lain
(misal PC teman, kantor) tanpa memerlukan pengetahuan teknis mendalam.
Distribusi dilakukan via ZIP yang dibagikan secara manual.

Tantangan:
- 13 package Python perlu diinstall
- Konfigurasi Telegram Token wajib diisi sebelum bisa dipakai
- Model AI (~13 MB) harus ikut dalam ZIP
- Shortcut Desktop membutuhkan langkah tambahan

---

## Keputusan

**Buat `setup.bat`** — script Windows Batch yang melakukan semua setup dalam satu kali double-click.

---

## Alternatif yang Dipertimbangkan

| Alternatif | Alasan Ditolak |
|-----------|---------------|
| PyInstaller `.exe` | Kompleks, ukuran besar (100MB+), sulit debug |
| Docker | Terlalu teknis untuk pengguna awam |
| Manual README instruksi | Error-prone, banyak langkah manual |
| `setup.bat` ✅ | Sederhana, standar Windows, semua orang bisa double-click |

---

## Implementasi

### File yang dibuat:
- `setup.bat` — installer utama (5 langkah otomatis)
- `DISTRIBUSI.md` — checklist isi ZIP & panduan penerima

### Alur `setup.bat`:
```
[1/5] Cek Python terinstall → error jika tidak ada
[2/5] Upgrade pip
[3/5] pip install -r requirements.txt
[4/5] Jika .env belum ada → tanya TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID
[5/5] Tawari buat shortcut Desktop (opsional, y/n)
```

### Prasyarat pengguna:
- Windows 10/11
- Python 3.11+ (install manual, centang "Add to PATH")
- Koneksi internet (untuk download package)

---

## Konsekuensi

✅ Pengguna awam bisa setup dalam ~10 menit  
✅ `.env` tidak ikut ZIP (token aman)  
✅ Model `.pt` ikut ZIP (tidak perlu download ulang)  
⚠️ `torchreid` kadang butuh Visual C++ Build Tools — dicatat di DISTRIBUSI.md  
⚠️ Python tetap harus diinstall manual oleh penerima  

