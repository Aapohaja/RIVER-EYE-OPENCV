# -*- coding: utf-8 -*-
"""Generate sistem dokumentasi PDF untuk River Eye."""

from fpdf import FPDF
from datetime import datetime

C_GOLD   = (200, 140, 50)
C_DARK   = (30,  20,  10)
C_GRAY   = (90,  90,  90)
C_LIGHT  = (50,  50,  50)
C_WHITE  = (255, 255, 255)
C_GREEN  = (60,  160,  60)
C_ORANGE = (220, 130,  30)
C_RED    = (200,  50,  50)
C_BLUE   = (50,  100, 200)


class Doc(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*C_GOLD)
        self.cell(0, 7, "RIVER EYE - Dokumentasi Sistem Deteksi Ketinggian Air", align="L")
        self.set_text_color(*C_GRAY)
        self.cell(0, 7, datetime.now().strftime("%d %B %Y"), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*C_GOLD)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*C_GRAY)
        self.cell(0, 8, f"Halaman {self.page_no()} | River Eye Sistem Monitoring Ketinggian Air Sungai", align="C")

    def h1(self, text):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*C_GOLD)
        self.set_fill_color(28, 18, 8)
        self.cell(0, 9, f"  {text}", new_x="LMARGIN", new_y="NEXT", fill=True)
        self.ln(2)
        self.set_text_color(*C_LIGHT)

    def h2(self, text):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*C_ORANGE)
        self.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
        self.set_text_color(*C_LIGHT)

    def body(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*C_LIGHT)
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def code(self, lines):
        self.set_font("Courier", "", 9)
        self.set_fill_color(238, 232, 220)
        self.set_text_color(25, 25, 25)
        for line in lines:
            self.cell(0, 5.2, line, new_x="LMARGIN", new_y="NEXT", fill=True)
        self.ln(3)
        self.set_text_color(*C_LIGHT)

    def kv(self, key, val, vc=None):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*C_ORANGE)
        self.cell(52, 6, key, border="B")
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*(vc or C_LIGHT))
        self.cell(0, 6, val, border="B", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*C_LIGHT)

    def step_box(self, num, title, desc, color=C_BLUE):
        self.set_fill_color(*color)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*C_WHITE)
        self.cell(8, 7, str(num), fill=True, align="C")
        self.set_text_color(*C_DARK)
        self.cell(50, 7, f"  {title}")
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*C_LIGHT)
        self.cell(0, 7, desc, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def zone_row(self, warna, label, rentang, color):
        self.set_fill_color(*color)
        self.cell(6, 7, "", fill=True)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*C_LIGHT)
        self.cell(30, 7, f"  {label}")
        self.set_font("Helvetica", "", 10)
        self.cell(45, 7, warna)
        self.cell(0, 7, rentang, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def divider(self):
        self.set_draw_color(180, 130, 60)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)


pdf = Doc()
pdf.set_auto_page_break(auto=True, margin=18)
pdf.set_margins(12, 14, 12)

# ==========================================
# COVER
# ==========================================
pdf.add_page()
pdf.ln(10)
pdf.set_font("Helvetica", "B", 26)
pdf.set_text_color(*C_GOLD)
pdf.cell(0, 14, "RIVER EYE", align="C", new_x="LMARGIN", new_y="NEXT")

pdf.set_font("Helvetica", "", 13)
pdf.set_text_color(*C_GRAY)
pdf.cell(0, 8, "Sistem Monitoring Ketinggian Air Sungai", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(2)

pdf.set_draw_color(*C_GOLD)
pdf.set_line_width(0.6)
pdf.line(35, pdf.get_y(), 175, pdf.get_y())
pdf.ln(6)

pdf.set_font("Helvetica", "B", 11)
pdf.set_text_color(*C_LIGHT)
pdf.cell(0, 7, "Dokumentasi Teknis: Koneksi Sistem & Cara Kerja Deteksi", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 10)
pdf.set_text_color(*C_GRAY)
pdf.cell(0, 6, f"Versi 1.0  |  {datetime.now().strftime('%d %B %Y')}", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(10)
pdf.set_line_width(0.2)

# Ringkasan cover
pdf.set_fill_color(28, 18, 8)
pdf.set_font("Helvetica", "", 10)
pdf.set_text_color(*C_GRAY)
items = [
    "Bab 1  -  Gambaran Umum Sistem",
    "Bab 2  -  Diagram Koneksi Lengkap",
    "Bab 3  -  Staff Gauge & Zona Ketinggian",
    "Bab 4  -  Pipeline Deteksi (7 Tahap)",
    "Bab 5  -  Cara Kerja Kalibrasi",
    "Bab 6  -  Spesifikasi Teknis",
]
for item in items:
    pdf.cell(0, 7, f"     {item}", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(1)

# ==========================================
# BAB 1 - GAMBARAN UMUM
# ==========================================
pdf.add_page()
pdf.h1("Bab 1  -  Gambaran Umum Sistem")
pdf.body(
    "River Eye adalah sistem pemantauan ketinggian air sungai secara real-time menggunakan "
    "kamera IP (CCTV) dan computer vision. Kamera memotret papan pengukur (staff gauge) yang "
    "dipasang di tepi sungai. Sistem memproses gambar setiap frame untuk menentukan posisi "
    "permukaan air, menghitung ketinggian dalam sentimeter, lalu mengirimkan data ke server "
    "pusat melalui HTTP API."
)

pdf.h2("Komponen Utama")
comps = [
    ("IP Camera",         "Menangkap video stream (MJPEG) dari lokasi sungai"),
    ("water_level.py",    "Engine utama: deteksi frame, hitung ketinggian, smoothing"),
    ("telemetry.py",      "Pengirim data: HTTP POST JSON ke server setiap 2 detik"),
    ("config_water.json", "Konfigurasi ROI, kalibrasi titik referensi, zona ketinggian"),
    ("Server API",        "Menerima & menyimpan data: http://100.71.62.6:3000/api/logs"),
    ("Staff Gauge",       "Papan pengukur putih di sungai dengan skala 0-250 cm"),
]
for name, desc in comps:
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*C_ORANGE)
    pdf.cell(48, 6, f"  {name}")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*C_LIGHT)
    pdf.cell(0, 6, desc, new_x="LMARGIN", new_y="NEXT")
pdf.ln(4)

pdf.h2("Hardware yang Digunakan")
pdf.kv("Kamera",       "IP Camera dengan MJPEG stream")
pdf.kv("URL Stream",   "http://100.83.7.110:8081/stream")
pdf.kv("Komputer",     "Raspberry Pi 3 / PC Windows")
pdf.kv("Koneksi",      "WiFi / LAN lokal")
pdf.ln(4)

# ==========================================
# BAB 2 - DIAGRAM KONEKSI
# ==========================================
pdf.add_page()
pdf.h1("Bab 2  -  Diagram Koneksi Sistem")

pdf.h2("Alur Koneksi End-to-End")
pdf.code([
    "                    LAPANGAN                                SERVER",
    "",
    "  [ SUNGAI ]",
    "      |",
    "  [ Staff Gauge ]  <-- kamera merekam papan pengukur",
    "      |",
    "  [ IP Camera ]    stream: http://100.83.7.110:8081/stream",
    "      |  (MJPEG over HTTP)",
    "      v",
    "  [ Raspberry Pi / PC ]",
    "      |  water_level.py berjalan terus-menerus",
    "      |  - Baca frame dari kamera (background thread)",
    "      |  - Proses gambar (OpenCV)",
    "      |  - Hitung ketinggian air (cm)",
    "      |",
    "      |  (HTTP POST JSON, setiap 2 detik)",
    "      v",
    "  [ Server API ]   http://100.71.62.6:3000/api/logs",
    "      |",
    "  [ Database ]  <-- data tersimpan & bisa diakses dashboard",
])

pdf.h2("Format Data yang Dikirim ke Server")
pdf.code([
    "  Method : HTTP POST",
    "  URL    : http://100.71.62.6:3000/api/logs",
    "  Header : Content-Type: application/json",
    "           x-api-key: qwertyui",
    "  Body   : {",
    '             "location_id":    1,',
    '             "water_level_cm": 139.3',
    "           }",
])

pdf.h2("Kondisi Pengiriman Data")
pdf.body(
    "Data hanya dikirim ke server apabila:\n"
    "  (a)  ROI sudah dipilih (area papan pengukur sudah ditandai)\n"
    "  (b)  Confidence score deteksi > 0.20\n"
    "  (c)  Sudah lewat minimal 2 detik sejak pengiriman terakhir\n"
    "  (d)  Library 'requests' tersedia di Python"
)

pdf.h2("Koneksi Background Thread (ThreadedCapture)")
pdf.body(
    "Kamera dibaca menggunakan background thread terpisah agar proses deteksi tidak "
    "terhambat oleh waktu tunggu jaringan. Jika koneksi kamera terputus (misal: mati "
    "listrik, gangguan WiFi), sistem otomatis mencoba reconnect setiap 2 detik tanpa "
    "perlu restart manual."
)

# ==========================================
# BAB 3 - STAFF GAUGE
# ==========================================
pdf.add_page()
pdf.h1("Bab 3  -  Staff Gauge & Zona Ketinggian Air")

pdf.h2("Apa itu Staff Gauge?")
pdf.body(
    "Staff gauge (papan pengukur) adalah papan berskala yang dipasang tegak di tepi sungai. "
    "Papan ini berwarna putih dengan angka hitam yang menunjukkan ketinggian air dalam sentimeter. "
    "Ketika air naik, permukaan air bergerak ke atas pada papan. Sistem mendeteksi di mana "
    "permukaan air berada pada papan tersebut untuk menentukan ketinggian aktual."
)

pdf.h2("Tampilan Fisik Staff Gauge")
pdf.code([
    "  +----------------+  <-- puncak papan (~250 cm)",
    "  |  -250-         |",
    "  |  -200-         |  Angka dan garis skala",
    "  |  -150-         |  tercetak jelas (hitam)",
    "  |  -100-         |",
    "  |  ~~~~~~~~~~~~~~~~  <-- permukaan air (contoh: 120 cm)",
    "  |  (air/sungai)  |",
    "  +----------------+",
    "",
    "  Papan berwarna PUTIH dengan angka HITAM",
    "  Skala: setiap 10 cm ada garis, setiap 50 cm ada angka besar",
])

pdf.h2("Zona Ketinggian Air")
pdf.body("Berdasarkan ketinggian yang terdeteksi, sistem menentukan status bahaya:")
pdf.ln(2)

header_y = pdf.get_y()
pdf.set_fill_color(200, 180, 140)
pdf.set_font("Helvetica", "B", 10)
pdf.set_text_color(*C_DARK)
pdf.cell(6,  7, "")
pdf.cell(30, 7, "  Status",  fill=True)
pdf.cell(45, 7, "Warna Zona", fill=True)
pdf.cell(50, 7, "Rentang",   fill=True)
pdf.cell(0,  7, "Tindakan",  fill=True, new_x="LMARGIN", new_y="NEXT")
pdf.ln(1)

zones = [
    (C_RED,    "BAHAYA",  "Merah",  "> 200 cm",       "Evakuasi segera"),
    (C_ORANGE, "WASPADA", "Orange", "150 - 200 cm",   "Siaga, pantau terus"),
    ((180,160,20), "SEDANG", "Kuning", "100 - 150 cm","Waspada"),
    (C_GREEN,  "AMAN",    "Putih",  "0 - 100 cm",     "Normal"),
]
for color, label, warna, rentang, aksi in zones:
    pdf.set_fill_color(*color)
    pdf.cell(6, 7, "", fill=True)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*C_LIGHT)
    pdf.cell(30, 7, f"  {label}")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(45, 7, warna)
    pdf.cell(50, 7, rentang)
    pdf.cell(0,  7, aksi, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

pdf.ln(4)
pdf.h2("Mengapa Sistem Bisa Membaca Ketinggian?")
pdf.body(
    "Prinsip dasarnya sederhana:\n\n"
    "1. Papan pengukur berwarna PUTIH (cerah) terlihat jelas di atas permukaan air\n"
    "2. Air sungai berwarna GELAP (cokelat/hitam)\n"
    "3. Ada batas kontras yang jelas antara putih (papan) dan gelap (air)\n"
    "4. Sistem mencari di mana batas ini berada\n"
    "5. Posisi batas dikonversi ke sentimeter menggunakan kalibrasi"
)

# ==========================================
# BAB 4 - PIPELINE DETEKSI
# ==========================================
pdf.add_page()
pdf.h1("Bab 4  -  Pipeline Deteksi (7 Tahap)")

pdf.body(
    "Setiap frame video melewati 7 tahap pemrosesan berurutan sebelum "
    "menghasilkan nilai ketinggian air dalam sentimeter:"
)
pdf.ln(2)

steps = [
    (C_BLUE,   "Akuisisi Frame",
     "Kamera -> background thread -> frame terbaru siap diproses"),
    (C_BLUE,   "Preprocessing",
     "Rotasi frame + crop + koreksi perspektif (opsional homography)"),
    ((80,120,60), "Crop ROI",
     "Potong hanya area papan pengukur sesuai polygon yang dipilih user"),
    ((80,120,60), "Board Mask (Otsu)",
     "Deteksi piksel cerah+rendah saturasi = papan putih; gelap = air/background"),
    (C_ORANGE, "Column Scan",
     "Scan 80 kolom dari bawah ke atas, cari transisi gelap->putih per kolom"),
    (C_ORANGE, "Laplacian Refinement",
     "Cari horizontal edge paling tajam di sekitar hasil scan = batas air presisi"),
    (C_RED,    "Kalman + Kirim",
     "Smoothing Kalman Filter -> hitung cm -> HTTP POST ke server"),
]
for i, (color, title, desc) in enumerate(steps, 1):
    pdf.step_box(i, title, desc, color)

pdf.ln(4)
pdf.divider()

pdf.h2("Tahap 3 Detail: Board Mask")
pdf.body(
    "Board Mask adalah gambar hitam-putih di mana piksel PUTIH = papan pengukur "
    "dan piksel HITAM = air atau background."
)
pdf.body(
    "Cara kerja:\n"
    "  1. Konversi frame BGR ke ruang warna HSV\n"
    "  2. Ambil channel V (kecerahan) dan S (saturasi)\n"
    "  3. Jalankan Otsu thresholding pada channel V\n"
    "     -> Otsu secara otomatis mencari nilai threshold optimal\n"
    "     -> Piksel cerah (papan) = putih, piksel gelap (air) = hitam\n"
    "  4. Filter tambahan: saturation < 100 (papan putih = tidak berwarna)\n"
    "  5. Morphological operations untuk bersihkan noise"
)
pdf.code([
    "  Frame BGR -> HSV -> channel V (kecerahan)",
    "                   -> channel S (saturasi)",
    "  Otsu threshold pada V -> papan cerah = putih",
    "  Filter: hanya piksel dengan S < 100 (tidak berwarna)",
    "  Morphological CLOSE (3x) -> tutup lubang kecil",
    "  Morphological OPEN  (2x) -> hapus noise titik kecil",
    "  Hasil: Board Mask bersih",
])

pdf.h2("Tahap 4 Detail: Column Scan")
pdf.body(
    "Sistem men-scan 80 kolom secara merata di seluruh lebar ROI "
    "(mengabaikan 10% tepi kiri dan kanan untuk menghindari noise)."
)
pdf.body(
    "Untuk setiap kolom:\n"
    "  - Scan dari BAWAH ke ATAS\n"
    "  - Cari deretan piksel putih (papan) yang berurutan (min. roi_h/30 piksel)\n"
    "  - Titik paling bawah dari deretan pertama = kandidat batas air\n"
    "  Dari 80 kandidat, ambil MEDIAN (tidak terpengaruh outlier)"
)
pdf.code([
    "  ROI (dari bawah ke atas):",
    "  ...(air gelap)...",
    "  ...(air gelap)...",
    "  ~~~~~~~~~~~~~~~~~~  <- kandidat water line (transisi gelap->putih)",
    "  ...(papan putih)..",
    "  ...(papan putih)..",
    "  ...(papan putih)..",
])

pdf.h2("Tahap 5 Detail: Laplacian Refinement")
pdf.body(
    "Setelah mendapat estimasi kasar dari column scan, sistem mencari posisi "
    "paling presisi dalam jendela +/- 20 piksel di sekitar estimasi tersebut."
)
pdf.body(
    "Laplacian mengukur ketajaman perubahan kecerahan per baris. "
    "Baris dengan variance Laplacian tertinggi = baris dengan perubahan "
    "paling tajam = tepat di batas antara air dan papan."
)

# ==========================================
# BAB 5 - KALIBRASI
# ==========================================
pdf.add_page()
pdf.h1("Bab 5  -  Cara Kerja Kalibrasi")

pdf.body(
    "Kalibrasi menghubungkan posisi piksel pada gambar dengan nilai sentimeter "
    "di dunia nyata. Tanpa kalibrasi, sistem hanya bisa memberikan estimasi kasar. "
    "Dengan kalibrasi, sistem memberikan hasil dalam sentimeter yang akurat."
)

pdf.h2("Proses Kalibrasi (Tekan C di Dashboard)")
pdf.code([
    "  1. Tekan C -> muncul jendela kalibrasi",
    "  2. Klik angka  50 cm pada papan -> titik referensi bawah",
    "  3. Klik angka 100 cm pada papan -> titik referensi tengah",
    "  4. Klik angka 250 cm pada papan -> titik referensi atas",
    "  5. Tekan ENTER -> kalibrasi tersimpan ke config_water.json",
])

pdf.h2("Cara Sistem Mengkonversi Piksel ke Sentimeter")
pdf.body(
    "Setelah kalibrasi, sistem menyimpan peta:\n"
    "     y_pixel [448] -> 50 cm\n"
    "     y_pixel [397] -> 100 cm\n"
    "     y_pixel [154] -> 250 cm\n\n"
    "Untuk setiap water line yang terdeteksi, sistem melakukan interpolasi linear "
    "di antara titik-titik referensi ini:"
)
pdf.code([
    "  Contoh: water line terdeteksi di y = 420 piksel",
    "  -> Interpolasi antara [448,50cm] dan [397,100cm]",
    "  -> height = 50 + (448-420)/(448-397) * (100-50)",
    "  -> height = 50 + 0.55 * 50 = 77.5 cm",
])

pdf.h2("Confidence Score")
pdf.body(
    "Confidence score (0.0 - 1.0) mengukur seberapa konsisten deteksi antar kolom:\n\n"
    "  IQR = selisih antara persentil 75 dan 25 dari semua kandidat kolom\n"
    "  Confidence = 1.0 - (IQR / tinggi_ROI) * 2\n\n"
    "  IQR kecil = semua kolom sepakat -> confidence tinggi (mendekati 1.0)\n"
    "  IQR besar = kolom-kolom tidak konsisten -> confidence rendah\n\n"
    "Data hanya dikirim ke server jika confidence > 0.20"
)

pdf.h2("Mengapa Confidence Bisa Rendah?")
reasons = [
    "Tiang/objek menghalangi sebagian kolom scan",
    "Permukaan air bergerak cepat (banjir deras)",
    "Refleksi cahaya kuat pada permukaan air",
    "ROI terlalu kecil / tidak mencakup permukaan air",
    "Pencahayaan buruk (malam tanpa lampu)",
]
for r in reasons:
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*C_LIGHT)
    pdf.cell(0, 6, f"  - {r}", new_x="LMARGIN", new_y="NEXT")
pdf.ln(3)

pdf.h2("Smoothing: Kalman Filter")
pdf.body(
    "Posisi water line diperhalus menggunakan Kalman Filter 1D untuk mengurangi "
    "getaran/jitter antar frame. Ini mencegah nilai ketinggian loncat-loncat "
    "meski permukaan air sedikit bergerak."
)

# ==========================================
# BAB 6 - SPESIFIKASI TEKNIS
# ==========================================
pdf.add_page()
pdf.h1("Bab 6  -  Spesifikasi Teknis & Pengoperasian")

pdf.h2("Spesifikasi Sistem")
pdf.kv("Bahasa Pemrograman", "Python 3.x")
pdf.kv("Library Utama",      "OpenCV >= 4.8, NumPy >= 1.24, requests >= 2.31")
pdf.kv("Sumber Video",       "http://100.83.7.110:8081/stream  (MJPEG)")
pdf.kv("Server API",         "http://100.71.62.6:3000/api/logs")
pdf.kv("API Key",            "qwertyui  (header: x-api-key)")
pdf.kv("Interval Kirim",     "Setiap 2 detik (jika confidence > 0.20)")
pdf.kv("Log Lokal",          "water_level_log.csv  (aktifkan dengan tombol L)")
pdf.kv("Hardware Minimum",   "Raspberry Pi 3 / setara")
pdf.ln(4)

pdf.h2("Kontrol Keyboard Dashboard")
controls = [
    ("R", "Reset ROI  -  pilih ulang area papan pengukur (polygon 4+ titik)"),
    ("C", "Kalibrasi  -  klik 3 titik referensi (50, 100, 250 cm)"),
    ("L", "Toggle logging CSV ON/OFF"),
    ("P", "Pause / Resume stream video"),
    ("S", "Screenshot dashboard ke folder screenshots/"),
    ("D", "Toggle debug view (Board Mask)"),
    ("Q", "Keluar dari aplikasi"),
]
for key, desc in controls:
    pdf.set_fill_color(*C_ORANGE)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*C_WHITE)
    pdf.cell(10, 6, key, fill=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*C_LIGHT)
    pdf.cell(0, 6, f"   {desc}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

pdf.ln(4)
pdf.h2("Cara Menjalankan Sistem")
pdf.code([
    "  # Dengan URL kamera langsung (tidak perlu input manual):",
    "  python water_level.py http://100.83.7.110:8081/stream",
    "",
    "  # Atau lewat menu utama:",
    "  python protel.py",
    "",
    "  # Test pada gambar dataset:",
    "  python test_dataset.py",
    "  python test_dataset.py --reset   <- untuk pilih ulang ROI",
])

pdf.h2("Urutan Setup Pertama Kali")
pdf.code([
    "  1. Jalankan: python water_level.py http://100.83.7.110:8081/stream",
    "  2. Tekan R  -> klik 4 sudut papan pengukur (sertakan area air di bawah)",
    "              -> ENTER untuk konfirmasi",
    "  3. Tekan C  -> klik angka  50 cm pada papan",
    "              -> klik angka 100 cm pada papan",
    "              -> klik angka 250 cm pada papan",
    "              -> ENTER untuk simpan kalibrasi",
    "  4. Sistem siap! Data terkirim otomatis ke server setiap 2 detik",
])

pdf.ln(4)
pdf.divider()
pdf.set_font("Helvetica", "I", 9)
pdf.set_text_color(*C_GRAY)
pdf.cell(0, 6,
    "Akurasi sistem bergantung pada kualitas ROI dan kalibrasi. "
    "Lakukan kalibrasi ulang jika kamera bergeser.",
    align="C", new_x="LMARGIN", new_y="NEXT")

# Save
out = r"C:\Users\aaron\OneDrive\Desktop\PCV\protel\River_Eye_System_Documentation.pdf"
pdf.output(out)
print(f"PDF berhasil dibuat: {out}")
