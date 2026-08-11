# YOLO Dataset & Training Infrastructure

**Date:** 2026-05-29  
**Status:** Approved

---

## Scope

Siapkan semua infrastruktur sebelum pengambilan data besok:
1. Script capture dataset dari kamera
2. Folder struktur dataset (YOLO format)
3. Config template `data.yaml` untuk training Roboflow export
4. Script training `train_yolo.py`
5. Integrasi YOLO ke pipeline `water_level.py` (auto-aktif jika `model_trained.pt` ada)

Workflow: `capture_dataset.py` → upload Roboflow → label → export → `train_yolo.py` → `model_trained.pt`

---

## Classes

| ID | Nama | Deskripsi |
|---|---|---|
| 0 | `staff_gauge` | Batang papan meteran berwarna |
| 1 | `water_surface` | Permukaan/batas air |

---

## 1. `capture_dataset.py`

Script interaktif untuk pengambilan data besok di lapangan.

- Buka kamera (pilih source: webcam / IP cam / file)
- Live preview fullscreen
- **SPACE** → simpan frame ke `dataset/raw/YYYYMMDD_HHMMSS_NNNN.jpg`
- **Q** → keluar
- Tampilkan counter frame tersimpan di overlay
- Tampilkan timestamp dan source aktif
- Simpan log sederhana: `dataset/raw/capture_log.txt` (waktu + filename)

---

## 2. Folder Struktur

```
protel/
└── dataset/
    ├── raw/              ← output capture_dataset.py (upload ke Roboflow)
    ├── images/
    │   ├── train/        ← diisi setelah export dari Roboflow
    │   └── val/
    ├── labels/
    │   ├── train/
    │   └── val/
    └── data.yaml         ← config YOLO training
```

Folder `images/` dan `labels/` dibuat kosong dengan `.gitkeep`. User mengisi setelah export dari Roboflow.

---

## 3. `dataset/data.yaml`

```yaml
path: ./dataset
train: images/train
val: images/val

nc: 2
names:
  0: staff_gauge
  1: water_surface
```

---

## 4. `train_yolo.py`

Script satu perintah: `python train_yolo.py`

- Cek apakah `dataset/images/train/` sudah berisi gambar
- Training dengan `yolov8n-seg.pt` sebagai base (fine-tune)
- Parameter default: epochs=50, imgsz=640, batch=8
- Output: `runs/segment/train/weights/best.pt`
- Setelah selesai: copy `best.pt` ke `model_trained.pt` di root protel

---

## 5. Integrasi `ai_detector.py` → `water_level.py`

`WaterLevelDetector.__init__`:
- Cek apakah `model_trained.pt` ada di folder
- Jika ada: inisialisasi `WaterLevelAI(model_path="model_trained.pt")`, print `[AI] Model YOLO aktif`
- Jika tidak: `self.ai = None`, print `[AI] Model belum dilatih — menggunakan HSV`

Di detection loop (setelah Layer 3 Laplacian fallback), tambahkan Layer 4:
```
if self.ai and height_m < 0.05:
    y_ai, conf_ai = self.ai.get_water_line_yolo(frame, roi_box)
    if y_ai != -1:
        y_wl = y_ai
        # hitung ulang height_m dari y_ai
```

YOLO hanya dipanggil sebagai **last resort** jika HSV gagal (height < 0.05m).

---

## Files Dibuat/Diubah

| File | Aksi |
|---|---|
| `capture_dataset.py` | Baru |
| `dataset/raw/.gitkeep` | Baru |
| `dataset/images/train/.gitkeep` | Baru |
| `dataset/images/val/.gitkeep` | Baru |
| `dataset/labels/train/.gitkeep` | Baru |
| `dataset/labels/val/.gitkeep` | Baru |
| `dataset/data.yaml` | Baru |
| `train_yolo.py` | Baru |
| `ai_detector.py` | Minor update (tidak ada perubahan interface) |
| `water_level.py` | Tambah YOLO Layer 4 di `__init__` + detection loop |
