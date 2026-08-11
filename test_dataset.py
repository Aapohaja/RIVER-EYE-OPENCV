# -*- coding: utf-8 -*-
"""
Test deteksi ketinggian air pada dataset gambar.

Cara pakai:
  python test_dataset.py             # proses semua gambar di dataset/raw/
  python test_dataset.py --reset     # pilih ulang ROI

Kontrol saat melihat hasil:
  N / SPACE  = gambar berikutnya
  P          = gambar sebelumnya
  Q / ESC    = keluar
"""

import cv2
import numpy as np
import os
import sys
import json
import glob

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROI_FILE   = os.path.join(SCRIPT_DIR, "config", "test_roi.json")
IMG_DIR    = os.path.join(SCRIPT_DIR, "dataset", "raw")


# ── Simpan / load ROI test ──────────────────────────────────────────────────

def save_test_roi(polygon, bbox):
    data = {"polygon": polygon, "bbox": bbox}
    with open(ROI_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[ROI] Disimpan: {ROI_FILE}")

def load_test_roi():
    if os.path.exists(ROI_FILE):
        with open(ROI_FILE) as f:
            d = json.load(f)
        return d["polygon"], d["bbox"]
    return None, None


# ── Polygon ROI selector ────────────────────────────────────────────────────

def select_polygon_roi(img):
    """Klik 4+ titik polygon di sekitar papan meteran. Return (polygon, bbox)."""
    h, w = img.shape[:2]
    scale  = min(900 / h, 650 / w, 1.0)
    dw, dh = int(w * scale), int(h * scale)
    disp   = cv2.resize(img, (dw, dh))

    points = []
    hover  = [None]

    def mouse(event, x, y, flags, param):
        if event == cv2.EVENT_MOUSEMOVE:
            hover[0] = (x, y)
        elif event == cv2.EVENT_LBUTTONDOWN:
            points.append((x, y))
        elif event == cv2.EVENT_RBUTTONDOWN:
            if points:
                points.pop()

    win = "Klik 4 sudut PAPAN METERAN  [ENTER=OK | Kanan=Hapus | ESC=Batal]"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, dw, dh)
    cv2.setMouseCallback(win, mouse)

    while True:
        frame = disp.copy()
        cv2.rectangle(frame, (0, 0), (dw, 44), (0, 0, 0), -1)
        cv2.putText(frame, "Klik 4 sudut papan meteran putih (kiri=tambah, kanan=hapus)",
                    (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(frame, f"Titik: {len(points)} | ENTER=OK (min 4) | ESC=Batal",
                    (8, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 180, 180), 1)

        if len(points) >= 3:
            pts = np.array(points, dtype=np.int32)
            ov  = frame.copy()
            cv2.fillPoly(ov, [pts], (0, 255, 0))
            cv2.addWeighted(ov, 0.18, frame, 0.82, 0, frame)
            cv2.polylines(frame, [pts], True, (0, 200, 0), 1)
        if len(points) >= 2:
            cv2.polylines(frame, [np.array(points, dtype=np.int32)], False, (0, 255, 0), 2)
        if points and hover[0]:
            cv2.line(frame, points[-1], hover[0], (0, 255, 255), 1)
        for i, pt in enumerate(points):
            cv2.circle(frame, pt, 6, (0, 255, 0), -1)
            cv2.circle(frame, pt, 8, (255, 255, 255), 1)
            cv2.putText(frame, str(i + 1), (pt[0] + 10, pt[1] - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

        cv2.imshow(win, frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 13 and len(points) >= 4:
            break
        elif key == 27:
            cv2.destroyWindow(win)
            return None, None

    cv2.destroyWindow(win)

    pts_disp = np.array(points, dtype=np.float32)
    pts_orig = (pts_disp / scale).astype(int).tolist()
    arr = np.array(pts_orig)
    bbox = [int(arr[:,0].min()), int(arr[:,1].min()),
            int(arr[:,0].max()), int(arr[:,1].max())]
    return pts_orig, bbox


# ── Deteksi (Option B: Otsu + Laplacian) ────────────────────────────────────

def detect(img, polygon, bbox):
    x1, y1, x2, y2 = bbox
    x1 = max(0, x1); y1 = max(0, y1)
    x2 = min(img.shape[1], x2); y2 = min(img.shape[0], y2)

    roi      = img[y1:y2, x1:x2].copy()
    roi_h, roi_w = roi.shape[:2]

    # Polygon mask
    poly_local = np.array([[p[0]-x1, p[1]-y1] for p in polygon], dtype=np.int32)
    pmask = np.zeros((roi_h, roi_w), np.uint8)
    cv2.fillPoly(pmask, [poly_local], 255)
    roi_m = cv2.bitwise_and(roi, roi, mask=pmask)

    # Board mask: Otsu pada V channel + filter saturation
    hsv = cv2.cvtColor(roi_m, cv2.COLOR_BGR2HSV)
    v, s = hsv[:, :, 2], hsv[:, :, 1]
    _, tv = cv2.threshold(v, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    board = np.zeros(v.shape, np.uint8)
    board[(tv > 0) & (s < 100)] = 255
    board = cv2.bitwise_and(board, pmask)
    k5 = np.ones((5, 5), np.uint8)
    board = cv2.morphologyEx(board, cv2.MORPH_CLOSE, k5, iterations=3)
    board = cv2.morphologyEx(board, cv2.MORPH_OPEN,  k5, iterations=2)

    # Column scan dari bawah ke atas
    min_con = max(5, roi_h // 30)
    step    = max(1, roi_w // 80)
    margin  = roi_w // 10
    cands   = []
    for col in range(margin + step // 2, roi_w - margin, step):
        col_data = board[:, col]
        consec   = 0
        for row in range(roi_h - 1, -1, -1):
            if col_data[row] > 0:
                consec += 1
                if consec >= min_con:
                    cands.append(row + consec - 1)
                    break
            else:
                consec = 0

    if not cands:
        return None, None, None, board

    y_raw = int(np.median(cands))

    # Laplacian refinement
    band = max(20, roi_h // 15)
    y0b, y1b = max(0, y_raw - band), min(roi_h, y_raw + band)
    gray = cv2.cvtColor(roi_m[y0b:y1b], cv2.COLOR_BGR2GRAY)
    lap  = cv2.Laplacian(gray.astype(np.float32), cv2.CV_32F)
    y_wl = y0b + int(np.argmax(np.var(lap, axis=1)))

    iqr  = np.percentile(cands, 75) - np.percentile(cands, 25)
    conf = max(0.1, min(1.0, 1.0 - (iqr / roi_h) * 2))

    # Estimasi tinggi (ratio, tanpa kalibrasi)
    ratio     = (roi_h - y_wl) / roi_h
    height_cm = ratio * 250.0

    return y_wl, conf, height_cm, board


# ── Render hasil ─────────────────────────────────────────────────────────────

def render(img, polygon, bbox, y_wl, conf, height_cm, board, fname, idx, total):
    x1, y1, x2, y2 = bbox
    roi_h = y2 - y1
    out = img.copy()

    # Polygon ROI
    cv2.polylines(out, [np.array(polygon, dtype=np.int32)], True, (0, 255, 0), 2)

    # Garis referensi ketinggian: 250, 100, 50, 0 cm
    ref_marks = [
        (250, (255, 200,  50), "250"),
        (100, (255, 165,   0), "100"),
        ( 50, (  0, 200, 255), " 50"),
        (  0, (180, 180, 180), "  0"),
    ]
    for ref_cm, ref_color, ref_label in ref_marks:
        ry = y1 + int(roi_h * (1.0 - ref_cm / 250.0))
        ry = max(y1, min(y2, ry))
        # garis solid tipis di dalam ROI
        cv2.line(out, (x1, ry), (x2, ry), ref_color, 2)
        # label dengan background hitam di sisi kiri dalam ROI
        lbl = f"{ref_label} cm"
        (tw, th), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        lx, ly = x1 + 4, ry - 4
        ly = max(y1 + th + 4, min(y2 - 4, ly))
        cv2.rectangle(out, (lx - 2, ly - th - 2), (lx + tw + 2, ly + 2), (0, 0, 0), -1)
        cv2.putText(out, lbl, (lx, ly),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, ref_color, 1, cv2.LINE_AA)

    if y_wl is not None:
        wl_g = y1 + y_wl
        cv2.line(out, (x1, wl_g), (x2, wl_g), (0, 0, 255), 3)

        label = f"~{height_cm:.0f} cm  conf={conf:.2f}"
        cv2.putText(out, label, (x1 + 4, max(30, wl_g - 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 255), 2, cv2.LINE_AA)
    else:
        cv2.putText(out, "Tidak terdeteksi", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # Info bar bawah
    h, w = out.shape[:2]
    cv2.rectangle(out, (0, h - 38), (w, h), (22, 14, 10), -1)
    nav = f"[{idx+1}/{total}] {fname}  |  N=Next  P=Prev  R=ROI  Q=Quit"
    cv2.putText(out, nav, (8, h - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 180, 180), 1)

    # Board mask (kecil, pojok kanan)
    bh, bw = board.shape[:2]
    scale  = min(200 / bw, 300 / bh)
    bsmall = cv2.resize(cv2.cvtColor(board, cv2.COLOR_GRAY2BGR),
                        (int(bw * scale), int(bh * scale)))
    if y_wl is not None:
        wl_s = int(y_wl * scale)
        cv2.line(bsmall, (0, wl_s), (bsmall.shape[1], wl_s), (0, 0, 255), 1)
    bsh, bsw = bsmall.shape[:2]
    ox, oy = w - bsw - 4, h - 38 - bsh - 4
    cv2.rectangle(out, (ox - 1, oy - 1), (ox + bsw, oy + bsh), (80, 80, 80), 1)
    out[oy:oy+bsh, ox:ox+bsw] = bsmall

    # Scale untuk display
    dh = min(900, h)
    dw = int(w * dh / h)
    return cv2.resize(out, (dw, dh))


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    reset = "--reset" in sys.argv

    # Ambil daftar gambar
    exts   = ["*.jpg", "*.jpeg", "*.png"]
    images = []
    for ext in exts:
        images += glob.glob(os.path.join(IMG_DIR, ext))
    images = sorted(images)

    if not images:
        print(f"[ERROR] Tidak ada gambar di {IMG_DIR}")
        return

    print(f"[INFO] {len(images)} gambar ditemukan di dataset/raw/")

    # Load / pilih ROI
    polygon, bbox = load_test_roi()
    if polygon is None or reset:
        print("[ROI] Pilih area papan meteran pada gambar pertama...")
        first = cv2.imread(images[0])
        polygon, bbox = select_polygon_roi(first)
        if polygon is None:
            print("[BATAL]"); return
        save_test_roi(polygon, bbox)
    else:
        print(f"[ROI] Tersimpan dipakai: bbox={bbox}")
        print("      Jalankan dengan --reset untuk pilih ulang ROI")

    # Loop tampil gambar
    cv2.namedWindow("Deteksi Dataset", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Deteksi Dataset", 540, 900)

    idx = 0
    while True:
        img  = cv2.imread(images[idx])
        fname = os.path.basename(images[idx])

        y_wl, conf, height_cm, board = detect(img, polygon, bbox)
        disp = render(img, polygon, bbox, y_wl, conf, height_cm,
                      board, fname, idx, len(images))

        cv2.imshow("Deteksi Dataset", disp)

        if y_wl is not None:
            print(f"[{idx+1:03d}/{len(images)}] {fname}  >> {height_cm:.0f} cm  conf={conf:.2f}")
        else:
            print(f"[{idx+1:03d}/{len(images)}] {fname}  >> TIDAK TERDETEKSI")

        key = cv2.waitKey(0) & 0xFF
        if key in (ord('q'), 27):
            break
        elif key in (ord('n'), ord(' ')):
            idx = min(idx + 1, len(images) - 1)
        elif key == ord('p'):
            idx = max(idx - 1, 0)
        elif key == ord('r'):
            new_poly, new_bbox = select_polygon_roi(img)
            if new_poly:
                polygon, bbox = new_poly, new_bbox
                save_test_roi(polygon, bbox)
                print("[ROI] Diperbarui")

    cv2.destroyAllWindows()
    print("Selesai.")


if __name__ == "__main__":
    main()
