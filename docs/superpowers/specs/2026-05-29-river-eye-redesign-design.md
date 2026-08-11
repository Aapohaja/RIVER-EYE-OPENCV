# River Eye — Dashboard Redesign & MQTT Completion

**Date:** 2026-05-29  
**Status:** Approved

---

## Scope

Dua deliverable utama:
1. Redesign visual dashboard OpenCV (`water_level.py` + `flood_detection.py`) ke gaya Professional Terminal — gelap, tanpa emoji, terbaca dari jauh, dengan animasi permukaan air.
2. Melengkapi integrasi MQTT: `flood_detection.py` belum publish sama sekali, `telemetry.py` perlu topic tambahan.

---

## 1. Visual Style

- **Palet:** Background `#0a0e16`, panel `#0d1520`, border `#1c2535`, aksen `#3ab878` (hijau) dan `#4ab8f0` (biru)
- **Font:** `cv2.FONT_HERSHEY_SIMPLEX` — ukuran konsisten, semua label HURUF KAPITAL
- **Tidak ada emoji.** Semua indikator berbasis teks atau simbol ASCII.

---

## 2. `water_level.py` — `draw_dashboard()` dibangun ulang

### Header bar (strip atas, tinggi ~40px)
- Kiri: nama `RIVER EYE` + subtitle `SISTEM MONITORING KETINGGIAN AIR SUNGAI`
- Tengah: chip-chip kecil — STATUS / SUMBER / FPS / WAKTU / UPTIME
- Kanan: MQTT indicator — dot berkedip (hijau = terhubung, merah = terputus) + teks `MQTT TERHUBUNG` / `MQTT TERPUTUS` + host

### Kamera feed (panel kiri, area utama)
- Sub-header: `LIVE FEED | Sumber: webcam:0 | 28 fps | REC`
- Ruler (mistar) vertikal di tepi kiri: 0–400 cm dengan tick mayor setiap 100cm
- Gauge strip warna di posisi asli
- **Animasi permukaan air:**
  - Garis batas air diganti kurva sinus: `y = y_wl + A * sin(2π * x/λ + phase)`
  - A = 4px (amplitudo), λ = lebar frame / 3 (panjang gelombang), phase diincrement tiap frame
  - `cv2.polylines()` menggambar kurva dari array titik
  - Area bawah kurva diisi warna `(20, 45, 80)` semi-transparan (alpha blend)
  - Efek shimmer: strip horizontal tipis di atas garis, opacity berubah berdasarkan sin(phase * 2)
- Floating readout kanan bawah: angka ketinggian besar + unit + zona
- Label `BATAS AIR` di ujung kiri garis air

### Panel kanan (lebar ~300px)
Tersusun dari section terpisah, dari atas ke bawah:

1. **Big metric** — angka ketinggian (font besar), unit CM, badge status (AMAN / SIAGA / WASPADA / BAHAYA) dengan warna aksen sesuai zona
2. **Referensi Zona** — tabel 4 baris, row zona aktif di-highlight dengan border dan background berbeda, pointer `<` di kanan
3. **Posisi Relatif** — progress bar horizontal 0–400cm, label tick di bawah
4. **Confidence** — label + progress bar + angka persen
5. **MQTT Publishing** — daftar topic dan nilai saat ini: `river-eye/height_cm`, `river-eye/height_m`, `river-eye/level`, `river-eye/zone`, `river-eye/confidence`; catatan interval + qos

### Footer bar (strip bawah, tinggi ~30px)
- Kiri: chip status — LOGGING ON/OFF, MQTT status, ROI status, KALIBRASI status
- Kanan: keybind `[R] [C] [L] [P] [S] [D] [Q]` dengan label

### Sparkline (kiri bawah, di atas footer)
- Grafik riwayat 150 frame
- Garis referensi zona horizontal (redup) dengan label teks
- Warna garis data berubah sesuai zona aktif saat ini

---

## 3. `flood_detection.py` — `create_dashboard()` disesuaikan

- Gaya visual sama persis dengan `water_level.py` di atas
- Karena ini mode gambar statis (bukan live), animasi gelombang tetap berjalan (phase diincrement di loop display `cv2.waitKey`)
- **Tambah integrasi `Telemetry`:** inisialisasi `Telemetry()` di `__init__`, panggil `telemetry.send()` setelah `process_frame()`, tutup di akhir `run_image()`

---

## 4. `telemetry.py` — topic tambahan

Tambah dua topic baru di `_publish_mqtt()`:
- `river-eye/zone` → `payload["zone"]` (string: `"hijau"` / `"kuning"` / `"orange"` / `"merah"`)
- `river-eye/confidence` → `str(payload["confidence"])`

MQTT topics lengkap setelah perubahan:

| Topic | Isi | QoS | Retain |
|---|---|---|---|
| `river-eye/data` | JSON lengkap | 1 | true |
| `river-eye/height_cm` | angka float | 0 | true |
| `river-eye/height_m` | angka float | 0 | true |
| `river-eye/level` | `AMAN` / `SIAGA` / `WASPADA` / `BAHAYA` | 1 | true |
| `river-eye/zone` | `hijau` / `kuning` / `orange` / `merah` | 0 | true |
| `river-eye/confidence` | angka float 0.0–1.0 | 0 | true |

---

## 5. `protel.py` — menu terminal dirapikan

- Hapus semua emoji
- Gunakan box-drawing ASCII untuk border menu
- Tambah `colorama` untuk teks berwarna minimal (judul cyan, item putih, prompt kuning)
- Fallback graceful jika `colorama` tidak terinstall (tidak ada warna, layout tetap rapi)

---

## 6. File yang diubah

| File | Perubahan |
|---|---|
| `water_level.py` | Bangun ulang `draw_dashboard()`, tambah animasi gelombang |
| `flood_detection.py` | Sesuaikan `create_dashboard()`, tambah `Telemetry` |
| `telemetry.py` | Tambah 2 topic MQTT baru |
| `protel.py` | Rapikan menu terminal |
| `requirements.txt` | Tambah `colorama>=0.4.6` |

---

## 7. Yang tidak berubah

- Logika deteksi (`process_frame`, `detect_water_line`, `make_zone_mask`, dll.) — tidak disentuh
- Format payload JSON `river-eye/data` — hanya ditambah field, tidak dihapus
- `config_water.json`, `hsv_calibrator.py`, `flood_simulation.py` — tidak disentuh
