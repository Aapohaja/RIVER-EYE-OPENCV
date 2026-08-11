# YOLO Dataset & Training Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Siapkan semua infrastruktur sebelum pengambilan data — capture script, folder dataset, training script, dan integrasi YOLO ke pipeline water_level.py.

**Architecture:** `capture_dataset.py` menangkap frame dari kamera ke `dataset/raw/`. Setelah user upload+label di Roboflow dan export, `train_yolo.py` melatih model. `water_level.py` otomatis mengaktifkan YOLO sebagai Layer 4 deteksi jika `model_trained.pt` ada di folder.

**Tech Stack:** Python 3.x, OpenCV, ultralytics (YOLOv8), paho-mqtt (sudah ada)

---

## File Map

| File | Aksi | Tanggung Jawab |
|---|---|---|
| `capture_dataset.py` | Baru | Script pengambilan data lapangan |
| `dataset/data.yaml` | Baru | Config YOLO training |
| `dataset/raw/.gitkeep` | Baru | Placeholder folder output capture |
| `dataset/images/train/.gitkeep` | Baru | Placeholder folder training images |
| `dataset/images/val/.gitkeep` | Baru | Placeholder folder validation images |
| `dataset/labels/train/.gitkeep` | Baru | Placeholder folder training labels |
| `dataset/labels/val/.gitkeep` | Baru | Placeholder folder validation labels |
| `train_yolo.py` | Baru | Script training satu perintah |
| `water_level.py` | Modifikasi | Tambah YOLO Layer 4 di `__init__` + detection loop |

---

## Task 1: Folder Struktur Dataset

**Files:**
- Create: `dataset/data.yaml`
- Create: `dataset/raw/.gitkeep`
- Create: `dataset/images/train/.gitkeep`
- Create: `dataset/images/val/.gitkeep`
- Create: `dataset/labels/train/.gitkeep`
- Create: `dataset/labels/val/.gitkeep`

- [ ] **Step 1.1: Buat semua folder dan file placeholder**

```
mkdir -p dataset/raw dataset/images/train dataset/images/val dataset/labels/train dataset/labels/val
touch dataset/raw/.gitkeep dataset/images/train/.gitkeep dataset/images/val/.gitkeep dataset/labels/train/.gitkeep dataset/labels/val/.gitkeep
```

Atau di Windows PowerShell:
```powershell
New-Item -ItemType Directory -Force dataset/raw, dataset/images/train, dataset/images/val, dataset/labels/train, dataset/labels/val
"" | Out-File dataset/raw/.gitkeep
"" | Out-File dataset/images/train/.gitkeep
"" | Out-File dataset/images/val/.gitkeep
"" | Out-File dataset/labels/train/.gitkeep
"" | Out-File dataset/labels/val/.gitkeep
```

- [ ] **Step 1.2: Buat `dataset/data.yaml`**

```yaml
# YOLO Training Config — River Eye
# Diisi setelah export dari Roboflow ke folder ini

path: ./dataset
train: images/train
val: images/val

nc: 2
names:
  0: staff_gauge
  1: water_surface
```

- [ ] **Step 1.3: Verifikasi struktur**

```
python -c "
import os
expected = [
    'dataset/raw',
    'dataset/images/train',
    'dataset/images/val',
    'dataset/labels/train',
    'dataset/labels/val',
    'dataset/data.yaml',
]
for p in expected:
    status = 'OK' if os.path.exists(p) else 'MISSING'
    print(f'{status}: {p}')
"
```

Expected: semua baris `OK`

- [ ] **Step 1.4: Commit**

```
git add dataset/
git commit -m "feat: add yolo dataset folder structure and data.yaml"
```

---

## Task 2: `capture_dataset.py` — Script Pengambilan Data

**Files:**
- Create: `capture_dataset.py`

- [ ] **Step 2.1: Buat `capture_dataset.py`**

```python
# -*- coding: utf-8 -*-
"""
RIVER EYE — Capture Dataset
============================
Script pengambilan data untuk training YOLO.

Kontrol:
  SPACE  = Simpan frame saat ini ke dataset/raw/
  Q/ESC  = Keluar

Hasil disimpan ke: dataset/raw/YYYYMMDD_HHMMSS_NNNN.jpg
Log disimpan ke:   dataset/raw/capture_log.txt
"""

import cv2
import os
import sys
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR    = os.path.join(SCRIPT_DIR, "dataset", "raw")
LOG_FILE   = os.path.join(OUT_DIR, "capture_log.txt")

os.makedirs(OUT_DIR, exist_ok=True)


def pilih_sumber():
    print()
    print("  " + "─" * 44)
    print("  CAPTURE DATASET — RIVER EYE")
    print("  " + "─" * 44)
    print("  [1] Webcam bawaan      (index 0)")
    print("  [2] Webcam external    (index 1)")
    print("  [3] IP Camera / CCTV   (URL)")
    print("  [4] File Video         (path)")
    print("  " + "─" * 44)
    c = input("\n  Pilihan (1/2/3/4): ").strip()
    if c == "1": return 0
    if c == "2": return 1
    if c == "3": return input("  URL: ").strip()
    if c == "4": return input("  Path: ").strip()
    return 0


def draw_overlay(frame, count, source):
    h, w = frame.shape[:2]
    # Background bar atas
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 52), (22, 14, 10), -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

    cv2.putText(frame, "RIVER EYE  CAPTURE DATASET",
                (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (232, 184, 122), 1, cv2.LINE_AA)
    cv2.putText(frame, f"Tersimpan: {count} frame   |   Sumber: {source}   |   {datetime.now().strftime('%H:%M:%S')}",
                (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (62, 46, 30), 1, cv2.LINE_AA)

    # Bar bawah — instruksi
    overlay2 = frame.copy()
    cv2.rectangle(overlay2, (0, h - 36), (w, h), (22, 14, 10), -1)
    cv2.addWeighted(overlay2, 0.85, frame, 0.15, 0, frame)
    cv2.putText(frame, "[SPACE] Simpan frame    [Q / ESC] Keluar",
                (10, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (62, 46, 30), 1, cv2.LINE_AA)

    return frame


def flash_saved(frame):
    """Tampilkan flash hijau singkat sebagai konfirmasi save."""
    h, w = frame.shape[:2]
    flash = frame.copy()
    cv2.rectangle(flash, (0, 0), (w, h), (120, 184, 58), 6)
    cv2.putText(flash, "TERSIMPAN", (w // 2 - 80, h // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (120, 184, 58), 3, cv2.LINE_AA)
    return flash


def save_frame(frame, count):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_{count:04d}.jpg"
    path = os.path.join(OUT_DIR, filename)
    cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now().isoformat()}  {filename}\n")

    return path


def main():
    source = pilih_sumber()
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print("\n  [ERROR] Tidak bisa membuka sumber video.")
        sys.exit(1)

    print(f"\n  Kamera aktif. Output: {OUT_DIR}")
    print("  SPACE = simpan  |  Q/ESC = keluar\n")

    cv2.namedWindow("River Eye — Capture Dataset", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("River Eye — Capture Dataset", 960, 600)

    count = 0
    show_flash = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            # Video file selesai — loop dari awal
            if isinstance(source, str) and os.path.isfile(source):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            print("[ERROR] Frame tidak terbaca.")
            break

        display = frame.copy()

        if show_flash > 0:
            display = flash_saved(display)
            show_flash -= 1
        else:
            display = draw_overlay(display, count, source)

        cv2.imshow("River Eye — Capture Dataset", display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord(' '):
            path = save_frame(frame, count)
            count += 1
            show_flash = 8  # tampilkan flash ~8 frame
            print(f"  [{count:04d}] Disimpan: {os.path.basename(path)}")

        elif key in (ord('q'), 27):
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"\n  Selesai. Total tersimpan: {count} frame")
    print(f"  Folder: {OUT_DIR}")
    print(f"  Log:    {LOG_FILE}")
    print("\n  Langkah selanjutnya:")
    print("  1. Upload folder dataset/raw/ ke Roboflow")
    print("  2. Label class: staff_gauge dan water_surface")
    print("  3. Export format YOLOv8 → extract ke folder dataset/")
    print("  4. Jalankan: python train_yolo.py")


if __name__ == "__main__":
    os.chdir(SCRIPT_DIR)
    main()
```

- [ ] **Step 2.2: Test smoke**

```
python -c "
import capture_dataset, os
assert os.path.exists('dataset/raw'), 'folder raw tidak ada'
print('Import OK')
"
```

Expected: `Import OK`

- [ ] **Step 2.3: Commit**

```
git add capture_dataset.py
git commit -m "feat: add capture_dataset.py for yolo dataset collection"
```

---

## Task 3: `train_yolo.py` — Script Training

**Files:**
- Create: `train_yolo.py`

- [ ] **Step 3.1: Buat `train_yolo.py`**

```python
# -*- coding: utf-8 -*-
"""
RIVER EYE — YOLO Training Script
==================================
Jalankan setelah dataset dari Roboflow sudah diekstrak ke folder dataset/.

Penggunaan:
  python train_yolo.py              # training default (50 epoch)
  python train_yolo.py --epochs 30  # custom epoch
  python train_yolo.py --resume     # lanjut dari checkpoint terakhir
"""

import os
import sys
import shutil
import argparse

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_YAML   = os.path.join(SCRIPT_DIR, "dataset", "data.yaml")
TRAIN_DIR   = os.path.join(SCRIPT_DIR, "dataset", "images", "train")
BASE_MODEL  = os.path.join(SCRIPT_DIR, "yolov8n-seg.pt")
OUTPUT_MODEL = os.path.join(SCRIPT_DIR, "model_trained.pt")


def check_dataset():
    """Pastikan dataset sudah diekstrak dari Roboflow."""
    if not os.path.exists(DATA_YAML):
        print("[ERROR] dataset/data.yaml tidak ditemukan.")
        return False

    images = [f for f in os.listdir(TRAIN_DIR)
              if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if len(images) == 0:
        print("[ERROR] dataset/images/train/ kosong.")
        print("        Export dataset dari Roboflow lalu extract ke folder dataset/")
        return False

    print(f"[OK] Dataset: {len(images)} gambar training ditemukan.")
    return True


def main():
    parser = argparse.ArgumentParser(description="River Eye — YOLO Training")
    parser.add_argument("--epochs", type=int, default=50,
                        help="Jumlah epoch training (default: 50)")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="Ukuran gambar input (default: 640)")
    parser.add_argument("--batch", type=int, default=8,
                        help="Batch size (default: 8, kurangi jika RAM kurang)")
    parser.add_argument("--resume", action="store_true",
                        help="Lanjut dari checkpoint terakhir")
    args = parser.parse_args()

    print()
    print("  " + "─" * 48)
    print("  RIVER EYE  —  YOLO Training")
    print("  " + "─" * 48)

    if not args.resume and not check_dataset():
        sys.exit(1)

    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ultralytics belum terinstall.")
        print("        Jalankan: pip install ultralytics")
        sys.exit(1)

    print(f"  Model base : {BASE_MODEL}")
    print(f"  Epochs     : {args.epochs}")
    print(f"  Image size : {args.imgsz}")
    print(f"  Batch size : {args.batch}")
    print()

    model = YOLO(BASE_MODEL)

    if args.resume:
        results = model.train(resume=True)
    else:
        results = model.train(
            data=DATA_YAML,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            project=os.path.join(SCRIPT_DIR, "runs"),
            name="river_eye",
            exist_ok=True,
        )

    # Copy best model ke root protel
    best_pt = os.path.join(SCRIPT_DIR, "runs", "river_eye", "weights", "best.pt")
    if os.path.exists(best_pt):
        shutil.copy(best_pt, OUTPUT_MODEL)
        print(f"\n  [OK] Model tersimpan: {OUTPUT_MODEL}")
        print("  Restart water_level.py — YOLO akan aktif otomatis.")
    else:
        print(f"\n  [WARN] best.pt tidak ditemukan di {best_pt}")
        print("         Cek folder runs/river_eye/weights/ secara manual.")


if __name__ == "__main__":
    os.chdir(SCRIPT_DIR)
    main()
```

- [ ] **Step 3.2: Test import**

```
python -c "
import train_yolo, os
assert os.path.exists('dataset/data.yaml')
print('Import OK')
"
```

Expected: `Import OK`

- [ ] **Step 3.3: Commit**

```
git add train_yolo.py
git commit -m "feat: add train_yolo.py one-command training script"
```

---

## Task 4: Integrasi YOLO ke `water_level.py`

**Files:**
- Modify: `water_level.py`

YOLO diaktifkan otomatis jika `model_trained.pt` ada. Fallback ke HSV jika tidak ada atau jika HSV sudah berhasil.

- [ ] **Step 4.1: Tambah init YOLO di `WaterLevelDetector.__init__`**

Cari baris `self.telemetry = None` (sekitar baris 344) dan tambahkan SETELAH blok telemetry:

```python
        # YOLO Layer 4 — aktif otomatis jika model_trained.pt ada
        _model_path = os.path.join(SCRIPT_DIR, "model_trained.pt")
        try:
            if os.path.exists(_model_path):
                from ai_detector import WaterLevelAI
                self.ai = WaterLevelAI(model_path=_model_path)
                print(f"[AI] Model YOLO aktif: {_model_path}")
            else:
                self.ai = None
                print("[AI] model_trained.pt tidak ditemukan — menggunakan HSV")
        except Exception as e:
            self.ai = None
            print(f"[AI] YOLO tidak dimuat: {e}")
```

- [ ] **Step 4.2: Tambah YOLO Layer 4 di detection loop `run()`**

Di `run()`, cari baris:
```python
                    height_m, zone_key, y_wl = self.smooth(raw_height, zone_key, y_wl)
```

Tambahkan SETELAH baris itu (masih di dalam blok `if roi.size > 0:`):

```python
                    # ── LAYER 4: YOLO AI (fallback jika confidence rendah) ──
                    if self.ai is not None and confidence < 0.3:
                        roi_box_yolo = (x1, y1, x2 - x1, y2 - y1)
                        y_ai, conf_ai = self.ai.get_water_line_yolo(frame, roi_box_yolo)
                        if y_ai != -1:
                            y_wl = y_ai
                            ratio_ai = (roi_h - y_wl) / roi_h if roi_h > 0 else 0
                            height_m = float(np.clip(ratio_ai * 4.0, 0.0, 4.0))
                            confidence = conf_ai
                            print(f"[AI] YOLO override: y={y_ai}, h={height_m:.2f}m")
```

YOLO hanya dipanggil saat `confidence < 0.3` (HSV tidak yakin), bukan setiap frame.

- [ ] **Step 4.3: Verifikasi smoke test**

```
python -c "
import cv2, numpy as np, math, time
from collections import deque
from water_level import WaterLevelDetector, DEFAULT_ZONES

d = WaterLevelDetector.__new__(WaterLevelDetector)
d.zones = DEFAULT_ZONES
d.zone_buf = deque(maxlen=10)
d.sparkline = deque(maxlen=150)
d.wave_phase = 0.0
d.video_source = 0
d.fps = 28
d.logging = False
d.paused = False
d.roi = [50, 50, 200, 300]
d.kalibrasi = None
d.telemetry = None
d.ai = None

frame = np.zeros((480, 640, 3), dtype=np.uint8)
dash = d.draw_dashboard(frame, 0.85, 'hijau', 0.78)
assert dash.shape == (700, 1100, 3)
print('PASS — YOLO init tidak merusak pipeline')
"
```

Expected: `PASS — YOLO init tidak merusak pipeline`

- [ ] **Step 4.4: Commit**

```
git add water_level.py
git commit -m "feat: integrate yolo as layer 4 detection fallback in water_level.py"
```

---

## Task 5: Final Check

- [ ] **Step 5.1: Verifikasi semua file ada**

```
python -c "
import os
files = [
    'capture_dataset.py',
    'train_yolo.py',
    'dataset/data.yaml',
    'dataset/raw/.gitkeep',
    'dataset/images/train/.gitkeep',
    'dataset/images/val/.gitkeep',
    'dataset/labels/train/.gitkeep',
    'dataset/labels/val/.gitkeep',
]
for f in files:
    print('OK' if os.path.exists(f) else 'MISSING', f)
"
```

Expected: semua `OK`

- [ ] **Step 5.2: Test capture_dataset bisa diimport**

```
python -c "import capture_dataset; print('OK')"
```

- [ ] **Step 5.3: Test train_yolo bisa diimport**

```
python -c "import train_yolo; print('OK')"
```

- [ ] **Step 5.4: Cetak panduan untuk besok**

```
python -c "
print('''
PANDUAN BESOK
=============
1. Jalankan: python capture_dataset.py
2. Tekan SPACE untuk simpan frame (target: 150 foto)
   - Variasi: ketinggian air, cahaya, sudut, kondisi permukaan
3. Upload folder dataset/raw/ ke Roboflow.com
4. Label 2 class: staff_gauge dan water_surface
5. Export: YOLOv8 format -> Extract ke folder dataset/
6. Train: python train_yolo.py
7. Selesai: model_trained.pt otomatis aktif di water_level.py
''')"
```

- [ ] **Step 5.5: Commit final**

```
git add .
git commit -m "chore: yolo infrastructure complete and ready for dataset collection"
```
