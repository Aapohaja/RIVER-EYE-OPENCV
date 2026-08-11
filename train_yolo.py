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

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_YAML    = os.path.join(SCRIPT_DIR, "dataset", "data.yaml")
TRAIN_DIR    = os.path.join(SCRIPT_DIR, "dataset", "images", "train")
BASE_MODEL   = os.path.join(SCRIPT_DIR, "models/yolov8n-seg.pt")
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
