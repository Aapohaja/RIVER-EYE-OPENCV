# -*- coding: utf-8 -*-
"""Generate API documentation PDF for River Eye system."""

from fpdf import FPDF
from datetime import datetime

class RiverEyePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(180, 140, 80)
        self.cell(0, 8, "RIVER EYE - Dokumentasi API & Arsitektur Sistem", align="L")
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, datetime.now().strftime("%d %B %Y"), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(80, 60, 40)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Halaman {self.page_no()} | River Eye - Sistem Monitoring Ketinggian Air Sungai", align="C")

    def section_title(self, text):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(220, 160, 60)
        self.set_fill_color(35, 25, 15)
        self.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT", fill=True)
        self.ln(2)
        self.set_text_color(50, 50, 50)

    def sub_title(self, text):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(80, 60, 40)
        self.cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)
        self.set_text_color(50, 50, 50)

    def body(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def code_block(self, lines):
        self.set_font("Courier", "", 9)
        self.set_fill_color(240, 235, 225)
        self.set_text_color(30, 30, 30)
        for line in lines:
            self.cell(0, 5.5, line, new_x="LMARGIN", new_y="NEXT", fill=True)
        self.ln(3)
        self.set_text_color(50, 50, 50)

    def key_value_row(self, key, value, key_color=(80,60,40), val_color=(30,30,30)):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*key_color)
        self.cell(55, 6, key, border="B")
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*val_color)
        self.cell(0, 6, value, border="B", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(50, 50, 50)

    def zone_row(self, warna, label, rentang, status_color):
        self.set_fill_color(*status_color)
        self.cell(6, 7, "", fill=True)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(50, 50, 50)
        self.cell(35, 7, f"  {label}")
        self.set_font("Helvetica", "", 10)
        self.cell(60, 7, warna)
        self.cell(0, 7, rentang, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)


pdf = RiverEyePDF()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()

# COVER / JUDUL
pdf.ln(5)
pdf.set_font("Helvetica", "B", 22)
pdf.set_text_color(200, 140, 50)
pdf.cell(0, 12, "RIVER EYE", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 13)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 8, "Sistem Monitoring Ketinggian Air Sungai", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(3)
pdf.set_draw_color(200, 140, 50)
pdf.set_line_width(0.5)
pdf.line(30, pdf.get_y(), 180, pdf.get_y())
pdf.ln(6)

pdf.set_font("Helvetica", "B", 11)
pdf.set_text_color(50, 50, 50)
pdf.cell(0, 7, "Dokumentasi API, Alur Data & Arsitektur Sistem", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 10)
pdf.set_text_color(120, 120, 120)
pdf.cell(0, 6, f"Versi: 2.0  |  Tanggal: {datetime.now().strftime('%d %B %Y')}", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(8)

# 1. GAMBARAN UMUM SISTEM
pdf.section_title("1.  GAMBARAN UMUM SISTEM")
pdf.body(
    "River Eye adalah sistem monitoring ketinggian air sungai secara real-time menggunakan "
    "computer vision. Kamera menangkap gambar papan staff gauge berwarna yang dipasang di tepi "
    "sungai, kemudian sistem memproses gambar tersebut untuk mengukur ketinggian air dan "
    "mengirimkan data ke server pusat melalui HTTP API."
)

pdf.sub_title("Komponen Utama:")
components = [
    ("Kamera / IP CCTV",  "Sumber video stream (webcam lokal atau IP Camera via URL)"),
    ("water_level.py",    "Engine deteksi - HSV segmentasi + Kalman filter + YOLO fallback"),
    ("telemetry.py",      "Modul pengirim data - HTTP POST JSON ke server"),
    ("config_water.json", "Konfigurasi ROI, kalibrasi, zona warna, sumber video"),
    ("Server API",        "Endpoint penerima data: http://100.71.62.6:3000/api/logs"),
]
for name, desc in components:
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(180, 120, 40)
    pdf.cell(52, 6, f"  {name}")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 6, desc, new_x="LMARGIN", new_y="NEXT")
pdf.ln(4)

# 2. ALUR DATA SISTEM
pdf.section_title("2.  ALUR DATA SISTEM (PIPELINE)")
pdf.body("Setiap frame video melewati 6 tahap pemrosesan sebelum data dikirim ke server:")
pdf.ln(2)

steps = [
    ("1", "Akuisisi Frame",       "Kamera/IP Camera -> ThreadedCapture (background thread)"),
    ("2", "Preprocessing",        "Rotasi 90 CCW + crop + homography (opsional)"),
    ("3", "Segmentasi Warna HSV", "ROI di-crop -> konversi BGR->HSV -> mask per zona warna"),
    ("4", "Deteksi Batas Air",    "Multi-column scan (80 kolom) -> median -> confidence score"),
    ("5", "Kalkulasi Ketinggian", "Pixel waterline -> interpolasi kalibrasi -> meter -> cm"),
    ("6", "Smoothing & Kirim",    "Kalman filter -> Telemetry.send() -> HTTP POST tiap 2 detik"),
]
for num, title, desc in steps:
    pdf.set_fill_color(180, 120, 40)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(8, 7, num, fill=True, align="C")
    pdf.set_text_color(60, 40, 10)
    pdf.cell(52, 7, f"  {title}")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 7, desc, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

pdf.ln(3)
pdf.sub_title("Diagram Alur:")
pdf.code_block([
    "  Kamera / IP Cam",
    "       |",
    "       v",
    "  ThreadedCapture  <-- background thread, hilangkan blocking read",
    "       |",
    "       v",
    "  preprocess_frame()  --> rotasi + crop + homography",
    "       |",
    "       v",
    "  ROI Crop + Polygon Mask",
    "       |",
    "       v",
    "  make_board_mask()  --> HSV segmentasi (hijau/kuning/orange/merah)",
    "       |",
    "       v",
    "  detect_water_line()  --> multi-column scan + median",
    "       |",
    "       +-- [confidence < 0.3] --> YOLO AI override (jika model ada)",
    "       |",
    "       v",
    "  calc_height()  --> px waterline -> interpolasi kalibrasi -> meter",
    "       |",
    "       v",
    "  smooth()  --> Kalman Filter 1D",
    "       |",
    "       v",
    "  telemetry.send()  --> HTTP POST JSON  (rate-limited 2 detik)",
    "       |",
    "       v",
    "  Server: http://100.71.62.6:3000/api/logs",
])

# 3. SPESIFIKASI API
pdf.add_page()
pdf.section_title("3.  SPESIFIKASI API")

pdf.sub_title("3.1  Endpoint")
pdf.key_value_row("Method",       "HTTP POST")
pdf.key_value_row("URL",          "http://100.71.62.6:3000/api/logs")
pdf.key_value_row("Content-Type", "application/json")
pdf.key_value_row("Auth Header",  "x-api-key: qwertyui")
pdf.key_value_row("Interval",     "Setiap 2 detik (hanya kirim jika confidence > 0.2)")
pdf.key_value_row("Location ID",  "1  (dikonfigurasi di telemetry_config.json)")
pdf.ln(5)

pdf.sub_title("3.2  Format Payload (Request Body)")
pdf.code_block([
    "  {",
    '      "location_id":    1,',
    '      "water_level_cm": 139.3',
    "  }",
])

pdf.sub_title("3.3  Contoh Full HTTP Request")
pdf.code_block([
    "  POST /api/logs HTTP/1.1",
    "  Host: 100.71.62.6:3000",
    "  Content-Type: application/json",
    "  x-api-key: qwertyui",
    "  Content-Length: 43",
    "",
    '  { "location_id": 1, "water_level_cm": 139.3 }',
])

pdf.sub_title("3.4  Penjelasan Field Payload")
pdf.key_value_row("location_id",    "ID lokasi sensor (integer). Default: 1")
pdf.key_value_row("water_level_cm", "Ketinggian air dalam sentimeter (float, 1 desimal)")
pdf.ln(5)

pdf.sub_title("3.5  Kondisi Pengiriman Data")
pdf.body(
    "Data hanya dikirim ke server apabila semua kondisi berikut terpenuhi:\n"
    "  (a)  ROI sudah di-set (papan meteran sudah dipilih)\n"
    "  (b)  Telemetry berhasil terhubung (library requests tersedia)\n"
    "  (c)  Confidence score deteksi > 0.20 (deteksi dianggap valid)\n"
    "  (d)  Sudah lewat minimal 2 detik sejak pengiriman terakhir"
)
pdf.ln(3)

pdf.sub_title("3.6  Konfigurasi Telemetry (telemetry_config.json)")
pdf.code_block([
    "  {",
    '      "endpoint":         "http://100.71.62.6:3000/api/logs",',
    '      "api_key":          "qwertyui",',
    '      "location_id":      1,',
    '      "interval_seconds": 2',
    "  }",
])
pdf.body("File ini dibaca saat startup. Jika tidak ada, sistem menggunakan nilai default di atas.")

# 4. ZONA KETINGGIAN AIR
pdf.add_page()
pdf.section_title("4.  ZONA KETINGGIAN AIR")

pdf.body(
    "Staff gauge menggunakan empat zona warna untuk menandai level ketinggian air. "
    "Sistem mendeteksi warna yang terlihat di batas air untuk menentukan status bahaya."
)
pdf.ln(3)

pdf.set_font("Helvetica", "B", 10)
pdf.set_fill_color(220, 200, 160)
pdf.cell(6, 7, "")
pdf.cell(35, 7, "  Status", fill=True)
pdf.cell(60, 7, "Zona Warna", fill=True)
pdf.cell(0, 7, "Rentang Ketinggian", fill=True, new_x="LMARGIN", new_y="NEXT")
pdf.ln(1)

zones = [
    ((200, 60, 60),  "BAHAYA",  "Merah",  "> 200 cm  (> 2.0 m)"),
    ((220, 130, 32), "WASPADA", "Orange", "150 - 200 cm  (1.5 - 2.0 m)"),
    ((180, 160, 20), "SEDANG",  "Kuning", "100 - 150 cm  (1.0 - 1.5 m)"),
    ((60,  160, 60), "AMAN",    "Hijau",  "< 100 cm  (0.0 - 1.0 m)"),
]
for color, label, warna, rentang in zones:
    pdf.zone_row(warna, label, rentang, color)

pdf.ln(5)
pdf.sub_title("Kalibrasi Aktif (dari config_water.json):")
pdf.code_block([
    "  Titik referensi kalibrasi (y pixel  ->  cm):",
    "    y = 448 px  ->   50 cm",
    "    y = 397 px  ->  100 cm",
    "    y = 154 px  ->  250 cm",
    "",
    "  px_per_meter = 147.0  (pixel per meter)",
    "  total_height = 2.5 m  (250 cm)",
])

# 5. TEKNIK DETEKSI
pdf.section_title("5.  TEKNIK DETEKSI BATAS AIR")

pdf.sub_title("5.1  Multi-Column Scanning")
pdf.body(
    "Sistem men-scan 80 kolom secara merata di seluruh lebar ROI. Pada setiap kolom, "
    "scan dilakukan dari BAWAH ke ATAS. Ketika ditemukan minimal N piksel berturut-turut "
    "yang terdeteksi sebagai warna papan (putih pada mask), baris paling bawah dari "
    "deretan itu dianggap sebagai posisi batas air."
)

pdf.sub_title("5.2  Median & Confidence Score")
pdf.body(
    "Dari seluruh kolom diambil MEDIAN posisi batas air (robust terhadap outlier). "
    "Confidence dihitung dari konsistensi antar kolom: IQR kecil = confidence tinggi. "
    "Range confidence: 0.0 - 1.0. Data hanya dikirim ke server jika confidence > 0.2."
)

pdf.sub_title("5.3  Kalman Filter Smoothing")
pdf.body(
    "Posisi batas air dan ketinggian diperhalus menggunakan Kalman Filter 1D "
    "(process_variance=1e-4, measurement_variance=0.1) untuk mengurangi jitter "
    "antar frame tanpa lag signifikan."
)

pdf.sub_title("5.4  YOLO AI Fallback (Opsional)")
pdf.body(
    "Jika model YOLO tersedia (model_trained.pt) DAN confidence HSV < 0.3, "
    "sistem menggunakan YOLO untuk mendeteksi batas air. Ini adalah Layer 4 "
    "dari pipeline deteksi sebagai fallback otomatis."
)

# 6. LOGGING LOKAL
pdf.section_title("6.  LOGGING LOKAL (CSV)")
pdf.body(
    "Selain mengirim ke server API, sistem dapat mencatat data ke file CSV lokal "
    "dengan menekan tombol L pada dashboard. File tersimpan di:"
)
pdf.code_block([
    "  protel/water_level_log.csv",
    "",
    "  Kolom: Timestamp | Ketinggian_m | Zona | Level | Confidence",
    "  Interval logging: 5 detik",
])

# 7. KONTROL KEYBOARD
pdf.section_title("7.  KONTROL KEYBOARD DASHBOARD")

controls = [
    ("R", "Reset / Pilih ulang ROI (area papan meteran)"),
    ("C", "Kalibrasi - klik 3 titik referensi (50, 100, 250 cm)"),
    ("L", "Toggle logging CSV ON/OFF"),
    ("P", "Pause / Resume stream video"),
    ("S", "Screenshot dashboard ke folder screenshots/"),
    ("D", "Toggle debug view (Board Mask)"),
    ("Q", "Keluar dari aplikasi"),
]
for key, desc in controls:
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(180, 120, 40)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(10, 6, key, fill=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 6, f"  {desc}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

# 8. RINGKASAN
pdf.add_page()
pdf.section_title("8.  RINGKASAN CEPAT")
pdf.code_block([
    "  API ENDPOINT    :  http://100.71.62.6:3000/api/logs",
    "  METHOD          :  HTTP POST",
    "  HEADER          :  Content-Type: application/json",
    "                     x-api-key: qwertyui",
    '  PAYLOAD         :  { "location_id": 1, "water_level_cm": 139.3 }',
    "  INTERVAL KIRIM  :  2 detik (hanya jika confidence > 0.2)",
    "  LOG LOKAL       :  protel/water_level_log.csv (aktifkan dengan L)",
    "  STATUS INDIKATOR:  Pojok kanan atas dashboard = API TERHUBUNG / API TERPUTUS",
])

pdf.ln(4)
pdf.body(
    "Sistem River Eye dirancang resilient: jika server tidak dapat dicapai, "
    "monitoring tetap berjalan dan data terus ditampilkan di dashboard. "
    "Gunakan logging CSV sebagai backup data saat koneksi API putus."
)

# Save
out = r"C:\Users\aaron\OneDrive\Desktop\PCV\protel\River_Eye_API_Documentation.pdf"
pdf.output(out)
print(f"PDF berhasil dibuat: {out}")
