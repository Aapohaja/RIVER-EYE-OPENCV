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
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 52), (22, 14, 10), -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

    cv2.putText(frame, "RIVER EYE  CAPTURE DATASET",
                (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (232, 184, 122), 1, cv2.LINE_AA)
    cv2.putText(frame, f"Tersimpan: {count} frame   |   Sumber: {source}   |   {datetime.now().strftime('%H:%M:%S')}",
                (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (62, 46, 30), 1, cv2.LINE_AA)

    overlay2 = frame.copy()
    cv2.rectangle(overlay2, (0, h - 36), (w, h), (22, 14, 10), -1)
    cv2.addWeighted(overlay2, 0.85, frame, 0.15, 0, frame)
    cv2.putText(frame, "[SPACE] Simpan frame    [Q / ESC] Keluar",
                (10, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (62, 46, 30), 1, cv2.LINE_AA)

    return frame


def flash_saved(frame):
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
            if isinstance(source, str) and os.path.isfile(source):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            print("[ERROR] Frame tidak terbaca.")
            break

        frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
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
            show_flash = 8
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
    print("  3. Export format YOLOv8 -> extract ke folder dataset/")
    print("  4. Jalankan: python train_yolo.py")


if __name__ == "__main__":
    os.chdir(SCRIPT_DIR)
    main()
