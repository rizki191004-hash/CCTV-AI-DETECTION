# ADR-020: Cache-Busting and Force Reload for Dashboard UI

## Status
Accepted

## Context
Pada pengujian antarmuka web di browser (baik `localhost:8000` maupun Cloudflare Quick Tunnel), pengguna mendapati bahwa tombol merah **"Matikan Seluruh Sistem"** yang telah diimplementasikan pada ADR-019 belum tampak di browser. Pada tangkapan layar browser pengguna, status header masih menampilkan string lama dalam Bahasa Inggris: `🟢 Backend Connected` (seharusnya `Backend Terhubung`) dan tanpa tombol shutdown.

Penyelidikan teknis mengungkap akar masalah:
1. **Aggressive Browser HTTP Caching**: Endpoint FastAPI `/` dan `SPAFallbackMiddleware` yang menyajikan `dashboard/dist/index.html` menggunakan `FileResponse` tanpa header `Cache-Control`. Browser modern (seperti Microsoft Edge dan Google Chrome) menyimpan `index.html` di dalam Disk Cache lokal secara agresif sehingga terus menyajikan bundle lama dan tidak meminta bundle JavaScript terbaru (`index-DswZc-GZ.js`).
2. **Missing Meta Cache-Busting in HTML**: File template `dashboard/index.html` tidak memiliki tag meta anti-cache seperti `<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />`.
3. **Background Process State**: Server Python yang sedang berjalan di latar belakang sebelumnya belum dimatikan saat kompilasi asset baru selesai.

## Decision
1. **HTTP Response Cache-Busting Headers**:
   - Di `src/api/server.py`, tambahkan header anti-cache pada setiap penyajian `index.html`:
     ```python
     HTML_NO_CACHE_HEADERS = {
         "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
         "Pragma": "no-cache",
         "Expires": "0",
     }
     ```
   - Terapkan pada route root `GET /` dan `SPAFallbackMiddleware`.
2. **HTML Meta Tag Cache-Busting**:
   - Tambahkan tag meta `Cache-Control`, `Pragma`, dan `Expires` pada `dashboard/index.html` agar proxy maupun browser langsung merefresh halaman.
3. **Rebuild & Pre-bundle Dist**:
   - Jalankan `npm run build` untuk menghasilkan bundle terbaru di `dashboard/dist/` dengan meta tag anti-cache.
4. **Petunjuk Reload Keras (Hard Refresh)**:
   - Instruksikan pengguna untuk melakukan **Ctrl + F5** (atau **Shift + F5**) di Microsoft Edge/Chrome untuk membuang cache lama browser yang masih tersisa di memori browser.

## Consequences
- Halaman web `http://localhost:8000` dan Cloudflare Tunnel dijamin langsung memuat script terbaru tanpa terjebak di bundle lama.
- Tombol **"Matikan Seluruh Sistem"** (di header atas, di sidebar bawah, dan di tab Settings) langsung terlihat dan berfungsi untuk menghentikan seluruh sistem AI secara aman.
