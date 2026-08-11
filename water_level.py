# -*- coding: utf-8 -*-
"""
WATER LEVEL MEASUREMENT SYSTEM v2
==================================
Sistem Pengukuran Ketinggian Air Sungai Menggunakan Staff Gauge

Disesuaikan untuk papan meteran dengan zona warna:
  ┌──────────┐ 4.0 m
  │  MERAH   │ ─── BAHAYA
  ├──────────┤ 3.5 m
  │  ORANGE  │ ─── WASPADA
  ├──────────┤ 2.5 m
  │  KUNING  │ ─── SEDANG (dengan garis pengukuran / ruler)
  │ |||||||  │
  ├──────────┤ 1.0 m
  │  HIJAU   │ ─── RENDAH / AMAN
  └──────────┘ 0.0 m
  ~~~~~~~~~~~ ← batas air (water line)

Pipeline Pemrosesan:
  Frame → ROI Crop → BGR→HSV → Segmentasi Warna → Deteksi Batas Air
  → Hitung Ketinggian → Smoothing → Dashboard + Logging

Teknik Akurasi:
  1. Multi-column scanning (scan ~50 kolom, ambil median)
  2. Dual-direction scan (dari bawah ke atas DAN dari atas ke bawah)
  3. Morphological ops (close + open) untuk bersihkan noise
  4. Temporal smoothing (median dari N frame terakhir)
  5. Ruler line filtering (abaikan garis hitam pada zona kuning)
  6. Confidence scoring berdasarkan konsistensi kolom

Kontrol:
  R = Reset/Pilih ulang ROI
  C = Kalibrasi (tandai titik 0m dan 4m)
  L = Toggle logging ON/OFF
  P = Pause/Resume
  S = Screenshot
  D = Toggle debug view
  Q = Keluar

@author: aaron
"""

import cv2
import numpy as np
import json
import os
import time
import csv
import math
import threading
from datetime import datetime
from collections import deque, Counter


class ThreadedCapture:
    """Baca frame di background thread — hilangkan blocking cap.read() di main loop."""

    def __init__(self, src):
        self._src = src
        self.cap = cv2.VideoCapture(src)
        self.ret, self.frame = self.cap.read()
        self._lock = threading.Lock()
        self._t = threading.Thread(target=self._reader, daemon=True)
        self._t.start()

    def _reader(self):
        while True:
            ret, frame = self.cap.read()
            if not ret:
                # ponytail: reconnect on drop, critical for RTSP/IP cam
                time.sleep(2)
                self.cap.release()
                self.cap = cv2.VideoCapture(self._src)
                continue
            with self._lock:
                self.ret, self.frame = ret, frame

    def read(self):
        with self._lock:
            return self.ret, self.frame.copy() if self.frame is not None else (False, None)

    def isOpened(self):
        return self.cap.isOpened()

    def set(self, prop, val):
        self.cap.set(prop, val)

    def release(self):
        self.cap.release()

# ============================================
# KONFIGURASI
# ============================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config/config_water.json")
LOG_FILE = os.path.join(SCRIPT_DIR, "water_level_log.csv")
SCREENSHOT_DIR = os.path.join(SCRIPT_DIR, "screenshots")

EXTRA_ROTATION_DEG = 5  # ubah nilai ini kalau masih miring (+ = kiri, - = kanan)

def preprocess_frame(frame):
    frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    h, w = frame.shape[:2]
    frame = frame[h - w:, :]
    if EXTRA_ROTATION_DEG != 0:
        M = cv2.getRotationMatrix2D((w // 2, w // 2), EXTRA_ROTATION_DEG, 1.0)
        frame = cv2.warpAffine(frame, M, (w, w))
    return frame

# Zona warna dari BAWAH ke ATAS pada staff gauge
ZONA_ORDER = ["hijau", "kuning", "orange", "merah"]

# Default zona warna (di-override oleh config)
DEFAULT_ZONES = {
    "hijau": {
        "nama": "AMAN (< 120 cm)", "level": "AMAN",
        "hsv_min": [40, 50, 40], "hsv_max": [90, 255, 200],
        "tinggi_min_m": 0.0, "tinggi_max_m": 1.0,
        "warna_display": [0, 180, 0]
    },
    "kuning": {
        "nama": "SEDANG (120-150 cm)", "level": "SEDANG",
        "hsv_min": [18, 80, 100], "hsv_max": [38, 255, 255],
        "tinggi_min_m": 1.01, "tinggi_max_m": 1.5,
        "warna_display": [0, 230, 230]
    },
    "orange": {
        "nama": "WASPADA (150-200 cm)", "level": "WASPADA",
        "hsv_min": [8, 100, 120], "hsv_max": [22, 255, 255],
        "tinggi_min_m": 1.5, "tinggi_max_m": 2.0,
        "warna_display": [0, 140, 255]
    },
    "merah": {
        "nama": "BAHAYA (> 200 cm)", "level": "BAHAYA",
        "hsv_min": [0, 100, 100], "hsv_max": [8, 255, 255],
        "hsv_min_2": [168, 100, 100], "hsv_max_2": [179, 255, 255],
        "tinggi_min_m": 2.0, "tinggi_max_m": 2.5,
        "warna_display": [0, 0, 240]
    }
}

# Warna status untuk tampilan
LEVEL_COLORS = {
    "RENDAH":  (0, 200, 0),
    "SEDANG":  (0, 220, 220),
    "TINGGI":  (0, 140, 255),
    "BAHAYA":  (0, 0, 255),
    "UNKNOWN": (128, 128, 128)
}

# Alert text
LEVEL_ALERTS = {
    "RENDAH":  "✓ AMAN - Ketinggian normal",
    "SEDANG":  "⚠ WASPADA - Ketinggian mulai naik",
    "TINGGI":  "⚠⚠ SIAGA - Ketinggian tinggi!",
    "BAHAYA":  "🚨 BAHAYA - Evakuasi segera!",
    "UNKNOWN": "? Tidak terdeteksi"
}


# ============================================
# UTILITAS
# ============================================

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"zones": DEFAULT_ZONES, "roi": None, "kalibrasi": None, 
            "sumber_video": 0, "smoothing_frames": 10}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    print(f"[OK] Config disimpan: {CONFIG_FILE}")


# ============================================
# ROI SELECTOR
# ============================================

class ROISelector:
    """Pilih area papan meteran dengan klik titik-titik polygon."""

    def __init__(self):
        self.points = []
        self.hover = None

    def _mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_MOUSEMOVE:
            self.hover = (x, y)
        elif event == cv2.EVENT_LBUTTONDOWN:
            self.points.append((x, y))
        elif event == cv2.EVENT_RBUTTONDOWN:
            if self.points:
                self.points.pop()

    def select(self, frame):
        """Klik titik-titik untuk definisikan polygon ROI. Return (bbox, polygon) atau (None, None)."""
        self.points = []
        self.hover = None
        win = "PILIH ROI - Klik titik sudut papan meteran"
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win, 900, 650)
        cv2.setMouseCallback(win, self._mouse)

        print("\n" + "=" * 55)
        print("  PILIH AREA PAPAN METERAN (POLYGON)")
        print("  → Klik kiri : tambah titik")
        print("  → Klik kanan: hapus titik terakhir")
        print("  → ENTER = Konfirmasi (min. 3 titik) | ESC = Batal")
        print("=" * 55)

        while True:
            disp = frame.copy()

            overlay = disp.copy()
            cv2.rectangle(overlay, (0, 0), (disp.shape[1], 68), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.7, disp, 0.3, 0, disp)
            cv2.putText(disp, "Klik sudut-sudut PAPAN METERAN (polygon)",
                        (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
            cv2.putText(disp,
                        f"Titik: {len(self.points)} | Kanan=Hapus | ENTER=OK (min 3) | ESC=Batal",
                        (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 180, 180), 1)

            # Isi polygon semi-transparan
            if len(self.points) >= 3:
                pts_arr = np.array(self.points, dtype=np.int32)
                ov2 = disp.copy()
                cv2.fillPoly(ov2, [pts_arr], (0, 255, 0))
                cv2.addWeighted(ov2, 0.15, disp, 0.85, 0, disp)
                cv2.polylines(disp, [pts_arr], True, (0, 200, 0), 1)

            # Garis antar titik
            if len(self.points) >= 2:
                cv2.polylines(disp, [np.array(self.points, dtype=np.int32)], False, (0, 255, 0), 2)

            # Garis hover ke titik berikutnya
            if self.points and self.hover:
                cv2.line(disp, self.points[-1], self.hover, (0, 255, 255), 1)

            # Titik-titik
            for i, pt in enumerate(self.points):
                cv2.circle(disp, pt, 6, (0, 255, 0), -1)
                cv2.circle(disp, pt, 8, (255, 255, 255), 1)
                cv2.putText(disp, str(i + 1), (pt[0] + 10, pt[1] - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

            cv2.imshow(win, disp)
            key = cv2.waitKey(1) & 0xFF

            if key == 13 and len(self.points) >= 3:  # ENTER
                cv2.destroyWindow(win)
                pts_arr = np.array(self.points)
                x1, y1 = pts_arr.min(axis=0).tolist()
                x2, y2 = pts_arr.max(axis=0).tolist()
                bbox = [int(x1), int(y1), int(x2), int(y2)]
                polygon = [list(p) for p in self.points]
                print(f"[ROI] {len(self.points)} titik, BBox: {bbox}")
                return bbox, polygon
            elif key == 27:  # ESC
                cv2.destroyWindow(win)
                return None, None


# ============================================
# CALIBRATION TOOL
# ============================================

class CalibrationTool:
    """Kalibrasi 2 titik referensi dengan nilai cm bebas."""

    def __init__(self):
        self.points = []
        self.values_cm = []

    # ponytail: fixed reference values, user clicks 4 positions
    REF_CM = [0.0, 50.0, 100.0, 250.0]

    def _mouse(self, event, x, y, flags, param):
        n = len(self.REF_CM)
        if event == cv2.EVENT_LBUTTONDOWN and len(self.points) < n:
            self.points.append((x, y))
            self.values_cm.append(self.REF_CM[len(self.points) - 1])
            print(f"[CALIB] {self.REF_CM[len(self.points)-1]:.0f}cm → y={y}px")

    def calibrate(self, roi_frame, total_m=4.0):
        self.points = []
        self.values_cm = []
        n = len(self.REF_CM)
        win = f"KALIBRASI - Klik {n} titik"
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(win, self._mouse)

        labels = [f"{int(v)} cm" for v in self.REF_CM]
        colors = [(180, 180, 180), (0, 200, 255), (255, 165, 0), (0, 0, 255)]
        msgs   = [f"Klik angka {int(v)} cm" for v in self.REF_CM] + ["ENTER untuk konfirmasi"]

        while True:
            disp = roi_frame.copy()
            cv2.putText(disp, msgs[min(len(self.points), n)], (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            for i, pt in enumerate(self.points):
                cv2.circle(disp, pt, 8, colors[i], -1)
                cv2.putText(disp, labels[i], (pt[0]+12, pt[1]+5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, colors[i], 2)

            cv2.imshow(win, disp)
            key = cv2.waitKey(1) & 0xFF

            if key == 13 and len(self.points) == n:
                cv2.destroyWindow(win)
                ys  = [pt[1] for pt in self.points]
                cms = self.values_cm[:]
                # sort by y descending (bawah = y besar = cm kecil)
                paired = sorted(zip(ys, cms), reverse=True)
                ys_sorted  = [p[0] for p in paired]
                cms_sorted = [p[1] for p in paired]
                calib = {
                    "y_bottom":      ys_sorted[0],
                    "y_top":         ys_sorted[-1],
                    "cm_bottom":     cms_sorted[0],
                    "cm_top":        cms_sorted[-1],
                    "ys":            ys_sorted,
                    "cms":           cms_sorted,
                    "total_height_m": cms_sorted[-1] / 100.0,
                    "px_per_meter":  (ys_sorted[0] - ys_sorted[-1]) / (cms_sorted[-1] - cms_sorted[0]) * 100,
                }
                print(f"[CALIB] {n} titik tersimpan")
                return calib
            elif key == 27:
                cv2.destroyWindow(win)
                return None


# ============================================
# KALMAN FILTER 1D
# ============================================

class KalmanFilter1D:
    """Kalman Filter untuk smoothing 1D signal."""

    def __init__(self, process_variance=1e-3, measurement_variance=5e-2):
        self.x = 0.0          # State (terestimasi)
        self.p = 1.0          # Covariance
        self.q = process_variance
        self.r = measurement_variance
        self.is_initialized = False

    def update(self, measurement):
        if not self.is_initialized:
            self.x = measurement
            self.is_initialized = True
            return self.x

        # 1. Prediction (asumsi model konstan tanpa velocity untuk saat ini)
        self.p = self.p + self.q

        # 2. Update (Kalman Gain)
        k = self.p / (self.p + self.r)
        self.x = self.x + k * (measurement - self.x)
        self.p = (1 - k) * self.p

        return self.x


# ============================================
# WATER LEVEL DETECTOR - SISTEM UTAMA
# ============================================

class WaterLevelDetector:
    """
    Sistem pengukuran ketinggian air real-time.
    
    Prinsip:
    - Staff gauge berwarna dari bawah (hijau) ke atas (merah)
    - Ketika air naik, warna bagian bawah tenggelam
    - Sistem mendeteksi BATAS antara area papan (berwarna) dan area air/non-papan
    - Batas tersebut = posisi permukaan air
    - Posisi dikonversi ke meter berdasarkan kalibrasi atau rasio
    """
    
    def __init__(self, video_source=0):
        self.config = load_config()
        # Pakai URL tersimpan di config kalau tidak ada override eksplisit
        if video_source == 0:
            video_source = self.config.get("sumber_video", 0)
        self.zones = self.config.get("zones", DEFAULT_ZONES)
        self.roi = self.config.get("roi", None)
        self.roi_polygon = self.config.get("roi_polygon", None)
        self.kalibrasi = self.config.get("kalibrasi", None)
        self._poly_mask = None
        self._build_poly_mask()
        self.kalibrasi_geometri = self.config.get("kalibrasi_geometri", {})
        self.M = None
        if self.kalibrasi_geometri.get("aktif", False):
            pts_src = np.array(self.kalibrasi_geometri["points_src"], dtype=np.float32)
            pts_dst = np.array(self.kalibrasi_geometri["points_dst"], dtype=np.float32)
            self.M = cv2.getPerspectiveTransform(pts_src, pts_dst)
            self.tgt_w = self.kalibrasi_geometri["target_width"]
            self.tgt_h = self.kalibrasi_geometri["target_height"]
            print("[INFO] Homography loaded!")
            
        self.video_source = video_source
        
        # Temporal smoothing
        n = self.config.get("smoothing_frames", 10)
        self.height_buf = deque(maxlen=n)
        self.zone_buf = deque(maxlen=n)
        self.wline_buf = deque(maxlen=n)
        
        # Sparkline (grafik mini)
        self.sparkline = deque(maxlen=150)
        
        # State
        self.paused = False
        self.logging = False
        self.debug_view = False
        self.last_log_t = 0
        self.log_interval_s = 5
        
        # FPS
        self.fps_t = time.time()
        self.fps_n = 0
        self.fps = 0
        
        # Alert flash
        self.alert_flash = False
        self.alert_timer = 0

        # Wave animation phase (increment tiap frame)
        self.wave_phase = 0.0

        # Telemetry (MQTT + InfluxDB) — optional, degrades gracefully
        try:
            from telemetry import Telemetry
            self.telemetry = Telemetry()
        except Exception as e:
            print(f"[TELEMETRY] Tidak dimuat: {e}")
            self.telemetry = None

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

    def _build_poly_mask(self):
        """Precompute polygon mask sekali saat ROI di-set."""
        if not self.roi or not self.roi_polygon:
            self._poly_mask = None
            return
        x1, y1, x2, y2 = self.roi
        h, w = y2 - y1, x2 - x1
        poly_local = np.array(
            [[p[0] - x1, p[1] - y1] for p in self.roi_polygon],
            dtype=np.int32
        )
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [poly_local], 255)
        self._poly_mask = mask

    # ------------------------------------------
    # SEGMENTASI WARNA
    # ------------------------------------------
    
    def make_board_mask(self, hsv):
        """
        Deteksi papan meteran putih via brightness + Otsu.
        Adaptif terhadap pencahayaan — tidak bergantung pada zona warna.
        """
        v = hsv[:, :, 2]   # Value (kecerahan)
        s = hsv[:, :, 1]   # Saturation
        # Otsu cari threshold optimal pada channel V secara otomatis
        _, thresh_v = cv2.threshold(v, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Papan putih: bright (lolos Otsu) DAN low-saturation (bukan warna)
        board = np.zeros(v.shape, np.uint8)
        board[(thresh_v > 0) & (s < 100)] = 255
        k5 = np.ones((5, 5), np.uint8)
        board = cv2.morphologyEx(board, cv2.MORPH_CLOSE, k5, iterations=3)
        board = cv2.morphologyEx(board, cv2.MORPH_OPEN,  k5, iterations=2)
        return board
    
    # ------------------------------------------
    # DETEKSI BATAS AIR (WATER LINE)
    # ------------------------------------------
    
    def detect_water_line(self, board_mask, roi_bgr=None):
        """
        Deteksi garis batas air: multi-column scan + Laplacian refinement.

        1. Column scan dari bawah → kandidat y per kolom → median
        2. Laplacian refinement: cari horizontal edge paling tajam
           di pita ±band px sekitar median → presisi sub-piksel
        """
        h, w = board_mask.shape[:2]
        candidates = []
        min_consecutive = max(5, h // 30)

        n_cols = min(80, w)
        step = max(1, w // n_cols)
        margin = w // 10

        for col in range(margin + step // 2, w - margin, step):
            column = board_mask[:, col]
            consecutive = 0
            water_line_y = None
            for row in range(h - 1, -1, -1):
                if column[row] > 0:
                    consecutive += 1
                    if consecutive >= min_consecutive:
                        water_line_y = row + consecutive - 1
                        break
                else:
                    consecutive = 0
            if water_line_y is not None:
                candidates.append(water_line_y)

        if not candidates:
            return h - 1, 0.0

        y_wl = int(np.median(candidates))

        # Laplacian refinement — cari edge paling tajam di dekat kandidat
        if roi_bgr is not None:
            band = max(20, h // 15)
            y0, y1 = max(0, y_wl - band), min(h, y_wl + band)
            if y1 - y0 > 4:
                gray = cv2.cvtColor(roi_bgr[y0:y1], cv2.COLOR_BGR2GRAY)
                lap = cv2.Laplacian(gray.astype(np.float32), cv2.CV_32F)
                sharpness = np.var(lap, axis=1)
                y_wl = y0 + int(np.argmax(sharpness))

        if len(candidates) >= 5:
            iqr = np.percentile(candidates, 75) - np.percentile(candidates, 25)
            confidence = max(0.1, min(1.0, 1.0 - (iqr / h) * 2))
        else:
            confidence = 0.2

        return y_wl, confidence
    
    # ------------------------------------------
    # PERHITUNGAN KETINGGIAN
    # ------------------------------------------
    
    def calc_height(self, y_waterline, roi_h):
        """
        Konversi posisi piksel batas air → ketinggian dalam meter.
        
        Jika ada kalibrasi:
          Gunakan mapping linear y_bottom(0m) → y_top(4m)
        
        Jika tidak ada kalibrasi:
          Gunakan rasio posisi relatif di dalam ROI
          y dekat bawah ROI → air rendah
          y dekat atas ROI → air tinggi
        """
        total_m = 4.0  # Total range default
        
        if self.kalibrasi:
            ys  = self.kalibrasi.get("ys",  [self.kalibrasi["y_bottom"], self.kalibrasi["y_top"]])
            cms = self.kalibrasi.get("cms", [self.kalibrasi.get("cm_bottom", 0.0), self.kalibrasi.get("cm_top", 250.0)])
            height_cm = float(np.interp(y_waterline, list(reversed(ys)), list(reversed(cms))))
            result = np.clip(height_cm, min(cms), max(cms)) / 100.0
            return result
        else:
            ratio = (roi_h - y_waterline) / roi_h if roi_h > 0 else 0
            ratio = np.clip(ratio, 0.0, 1.0)
            return ratio * total_m
    
    def get_level(self, height_m):
        """Tentukan level berdasarkan ketinggian."""
        for zk in reversed(ZONA_ORDER):
            z = self.zones[zk]
            if height_m >= z["tinggi_min_m"]:
                return zk, z.get("level", "UNKNOWN")
        return "hijau", "RENDAH"

    def smooth(self, height_m, zone_key, y_wl):
        """Temporal smoothing menggunakan Kalman Filter."""
        if not hasattr(self, 'kf_h'):
            self.kf_h = KalmanFilter1D(process_variance=1e-4, measurement_variance=1e-1)
            self.kf_y = KalmanFilter1D(process_variance=1, measurement_variance=50)
            
        sm_height = self.kf_h.update(height_m)
        sm_wl = int(self.kf_y.update(y_wl))
        
        # Zona stabil = modus dari buffer lama (zona kan diskrit)
        self.zone_buf.append(zone_key)
        zone_counts = Counter(self.zone_buf)
        sm_zone = zone_counts.most_common(1)[0][0]
        
        return sm_height, sm_zone, sm_wl
    
    # ------------------------------------------
    # DASHBOARD / TAMPILAN
    # ------------------------------------------
    
    def draw_dashboard(self, frame, height_m, zone_key, confidence):
        """Buat canvas dashboard 1100x700 dengan frame kamera tertanam di kiri."""
        # ── Dimensi canvas ──
        CW, CH   = 1100, 700
        HDR_H    = 42
        FTR_H    = 32
        RIGHT_W  = 310
        SPARK_H  = 88
        GAP      = 4

        CAM_X2  = CW - RIGHT_W - GAP
        CAM_Y1  = HDR_H
        CAM_Y2  = CH - FTR_H - SPARK_H - GAP
        SP_Y1   = CH - FTR_H - SPARK_H
        SP_Y2   = CH - FTR_H
        RP_X1   = CW - RIGHT_W
        FTR_Y   = CH - FTR_H

        # ── Warna (BGR) ──
        C_BG     = (22,  14,  10)
        C_PANEL  = (32,  21,  13)
        C_BORDER = (53,  37,  28)
        C_DIM    = (62,  46,  30)
        C_MED    = (74,  58,  42)
        C_BRAND  = (232, 184, 122)
        C_GREEN  = (120, 184,  58)
        C_BLUE   = (240, 184,  74)
        ZONE_ACCENT = {
            "AMAN": (120,184,58), "RENDAH": (120,184,58),
            "SIAGA": (32,200,220), "SEDANG": (32,200,220),
            "WASPADA": (32,130,220), "TINGGI": (32,130,220),
            "BAHAYA": (48,32,200), "UNKNOWN": (128,128,128),
        }
        level  = self.zones[zone_key].get("level", "AMAN")
        accent = ZONE_ACCENT.get(level, (128, 128, 128))

        # ── Canvas ──
        dash = np.full((CH, CW, 3), C_BG, dtype=np.uint8)

        # ════════════════════════════════
        # HEADER
        # ════════════════════════════════
        dash[:HDR_H] = C_PANEL
        cv2.line(dash, (0, HDR_H - 1), (CW, HDR_H - 1), C_BORDER, 1)

        cv2.putText(dash, "RIVER EYE", (10, 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, C_BRAND, 1, cv2.LINE_AA)
        cv2.putText(dash, "SISTEM MONITORING KETINGGIAN AIR SUNGAI",
                    (10, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.28, C_DIM, 1, cv2.LINE_AA)
        cv2.line(dash, (108, 0), (108, HDR_H), C_BORDER, 1)

        chips = [
            ("STATUS", "AKTIF"),
            ("SUMBER", str(getattr(self, "video_source", "-"))),
            ("FPS",    str(self.fps)),
            ("WAKTU",  datetime.now().strftime("%H:%M:%S")),
        ]
        cx = 116
        for ckey, cval in chips:
            cv2.putText(dash, ckey, (cx, 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.24, C_DIM, 1, cv2.LINE_AA)
            vc = C_GREEN if cval == "AKTIF" else C_MED
            cv2.putText(dash, cval, (cx, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3, vc, 1, cv2.LINE_AA)
            cx += max(len(ckey), len(cval)) * 8 + 28
            cv2.line(dash, (cx - 6, 0), (cx - 6, HDR_H), C_BORDER, 1)

        api_x = CW - 230
        cv2.line(dash, (api_x, 0), (api_x, HDR_H), C_BORDER, 1)
        api_ok = (self.telemetry is not None and
                  getattr(self.telemetry, "_connected", False))
        dot_c = C_GREEN if api_ok else (48, 32, 200)
        blink_on = int(time.time() * 2) % 2 == 0
        if api_ok and blink_on:
            cv2.circle(dash, (api_x + 12, 21), 4, dot_c, -1)
        else:
            cv2.circle(dash, (api_x + 12, 21), 4, dot_c, 1)
        api_txt = "API TERHUBUNG" if api_ok else "API TERPUTUS"
        cv2.putText(dash, api_txt, (api_x + 22, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.28, dot_c, 1, cv2.LINE_AA)
        cv2.putText(dash, "HTTP POST", (api_x + 22, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.24, C_DIM, 1, cv2.LINE_AA)

        # ════════════════════════════════
        # KAMERA EMBED
        # ════════════════════════════════
        fh, fw = frame.shape[:2]
        cam_w  = CAM_X2
        cam_h  = CAM_Y2 - CAM_Y1
        scale  = min(cam_w / fw, cam_h / fh)
        nw, nh = int(fw * scale), int(fh * scale)
        ox = (cam_w - nw) // 2
        oy = CAM_Y1 + (cam_h - nh) // 2
        dash[oy:oy + nh, ox:ox + nw] = cv2.resize(frame, (nw, nh))
        cv2.rectangle(dash, (0, CAM_Y1), (CAM_X2, CAM_Y2), C_BORDER, 1)
        cv2.putText(dash, "LIVE FEED", (6, CAM_Y1 + 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.26, C_DIM, 1, cv2.LINE_AA)
        if self.logging:
            rec_blink = int(time.time() * 2) % 2 == 0
            if rec_blink:
                cv2.circle(dash, (CAM_X2 - 24, CAM_Y1 + 10), 4, (48, 32, 200), -1)
            cv2.putText(dash, "REC", (CAM_X2 - 16, CAM_Y1 + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.26, (48, 32, 200), 1, cv2.LINE_AA)

        # ════════════════════════════════
        # SPARKLINE
        # ════════════════════════════════
        self.sparkline.append(height_m)
        sp_w = CAM_X2
        spark = np.full((SPARK_H, sp_w, 3), (8, 5, 5), dtype=np.uint8)
        for zk in ["hijau", "kuning", "orange", "merah"]:
            r = self.zones[zk]["tinggi_max_m"] / 4.0
            ly = int(SPARK_H - r * SPARK_H)
            zc = tuple(max(0, c // 6) for c in self.zones[zk].get("warna_bgr", (60, 60, 60)))
            cv2.line(spark, (0, ly), (sp_w, ly), zc, 1)
        data = list(self.sparkline)
        if len(data) > 1:
            for i in range(1, len(data)):
                x1p = int((i - 1) / 150 * sp_w)
                x2p = int(i / 150 * sp_w)
                r1 = float(np.clip(data[i - 1] / 4.0, 0, 1))
                r2 = float(np.clip(data[i] / 4.0, 0, 1))
                y1p = int(SPARK_H - r1 * SPARK_H)
                y2p = int(SPARK_H - r2 * SPARK_H)
                d = data[i]
                pc = (C_GREEN if d < 1.0 else
                      (32, 200, 220) if d < 2.5 else
                      (32, 130, 220) if d < 3.5 else (48, 32, 200))
                cv2.line(spark, (x1p, y1p), (x2p, y2p), pc, 1, cv2.LINE_AA)
        dash[SP_Y1:SP_Y2, 0:sp_w] = spark
        cv2.rectangle(dash, (0, SP_Y1), (sp_w, SP_Y2), C_BORDER, 1)
        cv2.putText(dash, "RIWAYAT KETINGGIAN (150 FRAME TERAKHIR)",
                    (6, SP_Y1 + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.24, C_DIM, 1)

        # ════════════════════════════════
        # PANEL KANAN
        # ════════════════════════════════
        cv2.line(dash, (RP_X1 - 1, HDR_H), (RP_X1 - 1, FTR_Y), C_BORDER, 1)
        ry = HDR_H

        def sec_label(y, text):
            dash[y:y + 18, RP_X1:] = (18, 12, 10)
            cv2.putText(dash, text, (RP_X1 + 8, y + 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.26, C_DIM, 1)
            cv2.line(dash, (RP_X1, y + 18), (CW, y + 18), C_BORDER, 1)
            return y + 18

        # ── Big metric ──
        BIG_H = 138
        dash[ry:ry + BIG_H, RP_X1:] = C_PANEL
        cv2.putText(dash, "KETINGGIAN AIR TERDETEKSI",
                    (RP_X1 + 8, ry + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.26, C_DIM, 1)
        h_str = f"{height_m * 100:.1f}"
        cv2.putText(dash, h_str, (RP_X1 + 10, ry + 82),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.8, accent, 2, cv2.LINE_AA)
        cv2.putText(dash, "CENTIMETER", (RP_X1 + 10, ry + 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, C_DIM, 1)
        bw = len(level) * 9 + 16
        cv2.rectangle(dash, (RP_X1 + 10, ry + 108), (RP_X1 + 10 + bw, ry + 128), accent, 1)
        cv2.putText(dash, level, (RP_X1 + 16, ry + 122),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, accent, 1, cv2.LINE_AA)
        cv2.line(dash, (RP_X1, ry + BIG_H), (CW, ry + BIG_H), C_BORDER, 1)
        ry += BIG_H

        # ── Zona table ──
        ry = sec_label(ry, "REFERENSI ZONA KETINGGIAN")
        zone_rows = [
            ("merah",  "BAHAYA",   "> 200 cm",   (48, 32, 200)),
            ("orange", "WASPADA",  "150-200 cm", (32, 130, 220)),
            ("kuning", "SEDANG",   "100-150 cm", (32, 200, 220)),
            ("hijau",  "AMAN",     "< 100 cm",   (120, 184, 58)),
        ]
        for zk, zlabel, zrange, zc in zone_rows:
            active = (zk == zone_key)
            row_bg = (26, 32, 16) if active else C_PANEL
            cv2.rectangle(dash, (RP_X1 + 4, ry + 2), (CW - 4, ry + 22), row_bg, -1)
            cv2.rectangle(dash, (RP_X1 + 4, ry + 2), (CW - 4, ry + 22),
                          zc if active else C_BORDER, 1)
            cv2.rectangle(dash, (RP_X1 + 10, ry + 8), (RP_X1 + 16, ry + 16), zc, -1)
            nc = zc if active else C_DIM
            cv2.putText(dash, zlabel, (RP_X1 + 22, ry + 17),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3, nc, 1)
            cv2.putText(dash, zrange, (CW - 68, ry + 17),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.26, C_DIM, 1)
            if active:
                cv2.putText(dash, "<", (CW - 14, ry + 17),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.3, zc, 1)
            ry += 26
        cv2.line(dash, (RP_X1, ry), (CW, ry), C_BORDER, 1)

        # ── Progress bar ──
        ry = sec_label(ry, "POSISI RELATIF  (0 - 250 CM)")
        bx1, bx2 = RP_X1 + 10, CW - 10
        bw2 = bx2 - bx1
        fill_w = int(bw2 * np.clip(height_m / 2.5, 0, 1))
        cv2.rectangle(dash, (bx1, ry + 8), (bx2, ry + 16), (30, 20, 15), -1)
        cv2.rectangle(dash, (bx1, ry + 8), (bx2, ry + 16), C_BORDER, 1)
        if fill_w > 0:
            cv2.rectangle(dash, (bx1, ry + 8), (bx1 + fill_w, ry + 16), accent, -1)
        for lbl, pos in [("0", 0.0), ("120", 0.48), ("150", 0.6), ("200", 0.8), ("250", 1.0)]:
            lx = bx1 + int(bw2 * pos)
            cv2.putText(dash, lbl, (lx - 4, ry + 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.22, C_DIM, 1)
        ry += 32
        cv2.line(dash, (RP_X1, ry), (CW, ry), C_BORDER, 1)

        # ── Confidence ──
        cx1, cx2 = RP_X1 + 10, CW - 52
        cw2 = cx2 - cx1
        cfill = int(cw2 * confidence)
        cv2.putText(dash, "CONFIDENCE", (RP_X1 + 8, ry + 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.26, C_DIM, 1)
        cv2.rectangle(dash, (cx1, ry + 18), (cx2, ry + 22), (30, 20, 15), -1)
        cv2.rectangle(dash, (cx1, ry + 18), (cx2, ry + 22), C_BORDER, 1)
        if cfill > 0:
            cv2.rectangle(dash, (cx1, ry + 18), (cx1 + cfill, ry + 22), C_BLUE, -1)
        cv2.putText(dash, f"{confidence * 100:.0f}%", (CW - 48, ry + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, C_BLUE, 1)
        ry += 28
        cv2.line(dash, (RP_X1, ry), (CW, ry), C_BORDER, 1)

        # ── API Data ──
        ry = sec_label(ry, "DATA TERKIRIM KE SERVER")
        api_data = [
            ("ketinggian", f"{height_m * 100:.1f} cm"),
            ("status",     level),
            ("zone",       zone_key),
            ("confidence", f"{confidence:.2f}"),
        ]
        for tk, tv in api_data:
            cv2.putText(dash, tk, (RP_X1 + 8, ry + 11),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.26, C_DIM, 1)
            vc = C_GREEN if tv not in ("BAHAYA", "WASPADA") else (48, 32, 200)
            cv2.putText(dash, tv, (CW - 8 - len(tv) * 7, ry + 11),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.28, vc, 1)
            ry += 16
        cv2.putText(dash, "interval: 2s  |  HTTP POST JSON",
                    (RP_X1 + 8, ry + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.22, (30, 18, 12), 1)

        # ════════════════════════════════
        # FOOTER
        # ════════════════════════════════
        dash[FTR_Y:] = C_PANEL
        cv2.line(dash, (0, FTR_Y), (CW, FTR_Y), C_BORDER, 1)
        footer_items = [
            ("LOGGING",   "AKTIF"     if self.logging else "NONAKTIF"),
            ("API",       "TERHUBUNG" if api_ok else "TERPUTUS"),
            ("ROI",       "TERSET"    if self.roi else "BELUM"),
            ("KALIBRASI", "AKTIF"     if self.kalibrasi else "BELUM"),
        ]
        fx = 8
        for fk, fv in footer_items:
            cv2.putText(dash, fk, (fx, FTR_Y + 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.24, C_DIM, 1)
            fvc = C_GREEN if fv in ("AKTIF", "TERHUBUNG", "TERSET") else C_DIM
            cv2.putText(dash, fv, (fx, FTR_Y + 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.26, fvc, 1)
            fw2 = max(len(fk), len(fv)) * 8 + 24
            fx += fw2
            cv2.line(dash, (fx - 4, FTR_Y), (fx - 4, CH), C_BORDER, 1)

        keys = ["[R]Reset", "[C]Calib", "[L]Log", "[P]Pause", "[S]Shot", "[D]Debug", "[Q]Quit"]
        kx = CW - 8
        for k in reversed(keys):
            kx -= len(k) * 6 + 8
            cv2.putText(dash, k, (kx, FTR_Y + 19),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.24, C_DIM, 1)

        # ── Update wave phase (sekali per frame) ──
        self.wave_phase = (self.wave_phase + 0.08) % (2 * math.pi)

        return dash
    
    def draw_roi_overlay(self, frame, y_wl, zone_key):
        """Gambar ROI box dan animasi gelombang air pada frame kamera."""
        if not self.roi:
            return frame

        x1, y1, x2, y2 = self.roi
        level = self.zones[zone_key].get("level", "UNKNOWN")
        lc = LEVEL_COLORS.get(level, (128, 128, 128))
        roi_w = x2 - x1

        # Polygon atau rectangle
        if self.roi_polygon:
            pts = np.array(self.roi_polygon, dtype=np.int32)
            cv2.polylines(frame, [pts], True, (53, 37, 28), 1)
        else:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (53, 37, 28), 1)
        cv2.putText(frame, "STAFF GAUGE", (x1, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, (53, 37, 28), 1)

        wy_global = y1 + y_wl

        # Animasi gelombang sinus
        amplitude  = 4
        wavelength = max(60, roi_w // 3)
        xs = np.arange(x1, x2, 2)
        if len(xs) == 0:
            return frame
        ys = (wy_global + amplitude * np.sin(
            2 * math.pi * (xs - x1) / wavelength + self.wave_phase
        )).astype(int)
        ys = np.clip(ys, y1, y2)

        # Area air semi-transparan di bawah gelombang
        pts_fill = np.array(
            [[x1, y2]] +
            list(zip(xs.tolist(), ys.tolist())) +
            [[x2 - 1, y2]],
            dtype=np.int32
        )
        overlay = frame.copy()
        cv2.fillPoly(overlay, [pts_fill], (80, 45, 20))
        cv2.addWeighted(overlay, 0.22, frame, 0.78, 0, frame)

        # Garis gelombang
        pts_wave = np.array(
            list(zip(xs.tolist(), ys.tolist())),
            dtype=np.int32
        ).reshape(-1, 1, 2)
        cv2.polylines(frame, [pts_wave], False, lc, 2, cv2.LINE_AA)

        # Label
        label_y = int(np.mean(ys))
        cv2.putText(frame, "BATAS AIR", (x2 + 8, label_y + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, lc, 1, cv2.LINE_AA)

        return frame
    
    # ------------------------------------------
    # LOGGING
    # ------------------------------------------
    
    def log_data(self, height_m, zone_key, confidence):
        now = time.time()
        if now - self.last_log_t < self.log_interval_s:
            return
        self.last_log_t = now
        
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        exists = os.path.exists(LOG_FILE)
        
        with open(LOG_FILE, 'a', newline='') as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(["Timestamp", "Ketinggian_m", "Zona", "Level", "Confidence"])
            w.writerow([ts, f"{height_m:.3f}", zone_key,
                        self.zones[zone_key].get("level", "?"), f"{confidence:.3f}"])
    
    # ------------------------------------------
    # LOOP UTAMA
    # ------------------------------------------
    
    def run(self):
        print("\n" + "=" * 60)
        print("  WATER LEVEL MEASUREMENT SYSTEM v2")
        print("  Monitoring Ketinggian Air - Staff Gauge")
        print("=" * 60)
        
        cap = ThreadedCapture(self.video_source)
        if not cap.isOpened():
            print("[ERROR] Kamera/video tidak bisa dibuka!")
            return
        print("[OK] Kamera aktif!")
        
        # Ambil frame pertama untuk ROI
        ret, first = cap.read()
        if not ret:
            print("[ERROR] Tidak bisa baca frame!")
            return

        first = preprocess_frame(first)

        if self.M is not None:
            first = cv2.warpPerspective(first, self.M, (self.tgt_w, self.tgt_h))
        
        # ROI Selection (jika belum ada)
        if not self.roi:
            print("\n[INFO] Silakan pilih area papan meteran...")
            self.roi, self.roi_polygon = ROISelector().select(first)
            if self.roi:
                self.config["roi"] = self.roi
                self.config["roi_polygon"] = self.roi_polygon
                save_config(self.config)
                self._build_poly_mask()
        
        # Setup windows
        cv2.namedWindow("Water Level Monitor", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Water Level Monitor", 1100, 700)
        cv2.namedWindow("ROI Detail", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("ROI Detail", 250, 450)
        cv2.namedWindow("Color Segmentation", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Color Segmentation", 250, 450)
        
        print("\n=== KONTROL ===")
        print("  R = Reset ROI     C = Kalibrasi     L = Logging ON/OFF")
        print("  P = Pause         S = Screenshot     D = Debug view")
        print("  Q = Keluar")
        print("=" * 50)
        
        frame = first  # Gunakan first frame sebagai fallback
        
        while True:
            if not self.paused:
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                frame = preprocess_frame(frame)
                if self.M is not None:
                    frame = cv2.warpPerspective(frame, self.M, (self.tgt_w, self.tgt_h))
            
            # FPS
            self.fps_n += 1
            if time.time() - self.fps_t > 1.0:
                self.fps = self.fps_n
                self.fps_n = 0
                self.fps_t = time.time()
            
            # Defaults
            height_m = 0.0
            zone_key = "hijau"
            confidence = 0.0
            y_wl = 0
            
            if self.roi:
                x1, y1, x2, y2 = self.roi
                fh, fw = frame.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(fw, x2), min(fh, y2)
                
                roi = frame[y1:y2, x1:x2]

                if roi.size > 0:
                    if self._poly_mask is not None:
                        roi = cv2.bitwise_and(roi, roi, mask=self._poly_mask)

                    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                    roi_h, roi_w = roi.shape[:2]
                    
                    # 1. Deteksi papan (brightness-based)
                    board_mask = self.make_board_mask(hsv)

                    # 2. Deteksi water line + Laplacian refinement
                    y_wl, confidence = self.detect_water_line(board_mask, roi)
                    
                    # 4. Hitung ketinggian
                    raw_height = self.calc_height(y_wl, roi_h)
                    zone_key, _ = self.get_level(raw_height)
                    
                    # 5. Smoothing
                    height_m, zone_key, y_wl = self.smooth(raw_height, zone_key, y_wl)
                    height_m = self.calc_height(y_wl, roi_h)
                    zone_key, _ = self.get_level(height_m)

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

                    # 6. Tampilkan ROI detail
                    roi_disp = roi.copy()
                    lc = LEVEL_COLORS.get(self.zones[zone_key].get("level", "UNKNOWN"), (255,255,255))
                    cv2.line(roi_disp, (0, y_wl), (roi_w, y_wl), lc, 3)
                    
                    # Label ketinggian di ROI
                    cv2.putText(roi_disp, f"{height_m:.2f}m", (10, y_wl - 10),
                                 cv2.FONT_HERSHEY_SIMPLEX, 0.5, lc, 2)
                    
                    cv2.imshow("ROI Detail", roi_disp)
                    
                    # 7. Board mask view (brightness detection)
                    seg_view = cv2.cvtColor(board_mask, cv2.COLOR_GRAY2BGR)
                    cv2.line(seg_view, (0, y_wl), (roi_w, y_wl), (0, 0, 255), 2)
                    cv2.imshow("Color Segmentation", seg_view)
                    
                    # 8. Debug view (jika aktif)
                    if self.debug_view:
                        cv2.imshow("Board Mask", board_mask)
                    
                    # 9. Overlay pada frame asli
                    frame = self.draw_roi_overlay(frame, y_wl, zone_key)
            
            # Dashboard
            dash = self.draw_dashboard(frame, height_m, zone_key, confidence)
            cv2.imshow("Water Level Monitor", dash)
            
            # Logging (CSV)
            if self.logging:
                self.log_data(height_m, zone_key, confidence)

            # Telemetry: kirim ke MQTT + InfluxDB (selalu aktif, rate-limited)
            if self.roi and self.telemetry and confidence > 0.2:
                level_str = self.zones[zone_key].get("level", "UNKNOWN")
                self.telemetry.send(height_m, zone_key, level_str, confidence)

            # Keyboard
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord('r'):
                ret2, f2 = cap.read()
                if ret2:
                    new_roi, new_polygon = ROISelector().select(preprocess_frame(f2))
                    if new_roi:
                        self.roi = new_roi
                        self.roi_polygon = new_polygon
                        self.kalibrasi = None
                        self.config["roi"] = self.roi
                        self.config["roi_polygon"] = new_polygon
                        self.config["kalibrasi"] = None
                        save_config(self.config)
                        self._build_poly_mask()
            elif key == ord('c'):
                if self.roi:
                    ret2, f2 = cap.read()
                    if ret2:
                        f2 = preprocess_frame(f2)
                        x1, y1, x2, y2 = self.roi
                        cal = CalibrationTool().calibrate(f2[y1:y2, x1:x2], 4.0)
                        if cal:
                            self.kalibrasi = cal
                            self.config["kalibrasi"] = cal
                            save_config(self.config)
                else:
                    print("[WARN] Pilih ROI dulu (tekan R)")
            elif key == ord('l'):
                self.logging = not self.logging
                print(f"[LOG] {'AKTIF → ' + LOG_FILE if self.logging else 'NONAKTIF'}")
            elif key == ord('p'):
                self.paused = not self.paused
                print(f"[{'PAUSED' if self.paused else 'RUNNING'}]")
            elif key == ord('s'):
                os.makedirs(SCREENSHOT_DIR, exist_ok=True)
                fp = os.path.join(SCREENSHOT_DIR, datetime.now().strftime("ss_%Y%m%d_%H%M%S.png"))
                cv2.imwrite(fp, dash)
                print(f"[SCREENSHOT] {fp}")
            elif key == ord('d'):
                self.debug_view = not self.debug_view
                if not self.debug_view:
                    cv2.destroyWindow("Board Mask")
                print(f"[DEBUG] {'ON' if self.debug_view else 'OFF'}")
        
        cap.release()
        cv2.destroyAllWindows()
        if self.telemetry:
            self.telemetry.close()
        print("\n[EXIT] Selesai.")


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        src = sys.argv[1]
        try:
            src = int(src)
        except ValueError:
            pass
    else:
        print("  1. Webcam (index 0)")
        print("  2. IP Camera / CCTV")
        c = input("Pilihan (1/2): ").strip()
        if c == "1":   src = 0
        elif c == "2": src = input("URL: ").strip()
        else:          src = 0

    WaterLevelDetector(video_source=src).run()
