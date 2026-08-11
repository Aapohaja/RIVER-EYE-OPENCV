# -*- coding: utf-8 -*-
"""
HSV CALIBRATOR - Tool Kalibrasi Warna Papan Meteran (Staff Gauge)
=================================================================
Alat bantu untuk menemukan nilai HSV yang tepat agar sistem
dapat membedakan setiap zona warna pada papan meteran:

  ┌──────────────┐  ← MERAH (3.5 - 4.0 m) BAHAYA
  ├──────────────┤
  │   ORANGE     │  ← ORANGE (2.5 - 3.5 m) WASPADA
  ├──────────────┤
  │   KUNING     │  ← KUNING (1.0 - 2.5 m) SEDANG
  │  ||||||||    │     (dengan garis pengukuran)
  ├──────────────┤
  │   HIJAU      │  ← HIJAU (0.0 - 1.0 m) AMAN
  └──────────────┘

Cara Pakai:
  1. Jalankan program ini
  2. Arahkan kamera ke papan meteran
  3. Pilih zona warna (tekan 1-4)
  4. Klik pada warna di frame → auto-detect HSV range
  5. Fine-tune dengan slider jika perlu
  6. Tekan 'S' untuk simpan ke config/config_water.json
  7. Tekan 'Q' untuk keluar

@author: aaron
"""

import cv2
import numpy as np
import json
import os

# ============================================
# KONFIGURASI
# ============================================

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config/config_water.json")

# Zone key yang sesuai foto staff gauge (dari bawah ke atas)
ZONA_ORDER = ["hijau", "kuning", "orange", "merah"]

# Default HSV sesuai foto papan meteran
# HSV di OpenCV: H=0-179, S=0-255, V=0-255
DEFAULT_ZONES = {
    "hijau": {
        "nama": "HIJAU (Rendah/Aman)",
        "level": "RENDAH",
        "hsv_min": [40, 50, 40],
        "hsv_max": [90, 255, 200],
        "tinggi_min_m": 0.0,
        "tinggi_max_m": 1.0,
        "warna_display": [0, 180, 0]  # BGR
    },
    "kuning": {
        "nama": "KUNING (Sedang)",
        "level": "SEDANG",
        "hsv_min": [18, 80, 100],
        "hsv_max": [38, 255, 255],
        "tinggi_min_m": 1.0,
        "tinggi_max_m": 2.5,
        "warna_display": [0, 230, 230]
    },
    "orange": {
        "nama": "ORANGE (Waspada)",
        "level": "TINGGI",
        "hsv_min": [8, 100, 120],
        "hsv_max": [22, 255, 255],
        "tinggi_min_m": 2.5,
        "tinggi_max_m": 3.5,
        "warna_display": [0, 140, 255]
    },
    "merah": {
        "nama": "MERAH (Bahaya!)",
        "level": "BAHAYA",
        "hsv_min": [0, 100, 100],
        "hsv_max": [8, 255, 255],
        "hsv_min_2": [168, 100, 100],
        "hsv_max_2": [179, 255, 255],
        "tinggi_min_m": 3.5,
        "tinggi_max_m": 4.0,
        "warna_display": [0, 0, 240]
    }
}


# ============================================
# FUNGSI UTILITAS
# ============================================

def load_config():
    """Muat konfigurasi dari file JSON, atau gunakan default."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            print(f"[INFO] Config dimuat dari: {CONFIG_FILE}")
            return config
        except Exception as e:
            print(f"[WARN] Gagal baca config: {e}")
    return {"zones": DEFAULT_ZONES, "roi": None, "sumber_video": 0, "smoothing_frames": 10}


def save_config(config):
    """Simpan konfigurasi ke file JSON."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    print(f"[OK] Config disimpan: {CONFIG_FILE}")


def nothing(x):
    pass


# ============================================
# KELAS UTAMA: HSV CALIBRATOR
# ============================================

class HSVCalibrator:
    def __init__(self, video_source=0):
        """
        HSV Calibrator untuk papan meteran staff gauge.
        
        video_source: int (webcam index) atau str (URL / path file video)
        """
        self.config = load_config()
        self.zones = self.config.get("zones", DEFAULT_ZONES)
        self.video_source = video_source
        
        # Zona yang sedang dikalibrasi (default: hijau)
        self.current_zone_key = "hijau"
        
        # Warna yang di-pick dari klik mouse
        self.picked_hsv = None
        self.current_hsv_frame = None
        
        self.setup_windows()
        
    def setup_windows(self):
        """Buat window dan trackbar."""
        cv2.namedWindow("HSV Calibrator", cv2.WINDOW_NORMAL)
        cv2.namedWindow("Mask Result", cv2.WINDOW_NORMAL)
        cv2.namedWindow("Controls", cv2.WINDOW_NORMAL)
        
        cv2.resizeWindow("HSV Calibrator", 800, 550)
        cv2.resizeWindow("Mask Result", 400, 350)
        cv2.resizeWindow("Controls", 600, 100)
        
        # Ambil HSV range zona aktif untuk posisi awal trackbar
        zona = self.zones[self.current_zone_key]
        hsv_min = zona.get("hsv_min", [0, 0, 0])
        hsv_max = zona.get("hsv_max", [179, 255, 255])
        
        cv2.createTrackbar("H Min", "Controls", hsv_min[0], 179, nothing)
        cv2.createTrackbar("S Min", "Controls", hsv_min[1], 255, nothing)
        cv2.createTrackbar("V Min", "Controls", hsv_min[2], 255, nothing)
        cv2.createTrackbar("H Max", "Controls", hsv_max[0], 179, nothing)
        cv2.createTrackbar("S Max", "Controls", hsv_max[1], 255, nothing)
        cv2.createTrackbar("V Max", "Controls", hsv_max[2], 255, nothing)
        
        cv2.setMouseCallback("HSV Calibrator", self.mouse_callback)
        
    def update_trackbars(self):
        """Sinkronkan trackbar dengan zona yang dipilih."""
        zona = self.zones[self.current_zone_key]
        hsv_min = zona.get("hsv_min", [0, 0, 0])
        hsv_max = zona.get("hsv_max", [179, 255, 255])
        
        cv2.setTrackbarPos("H Min", "Controls", hsv_min[0])
        cv2.setTrackbarPos("S Min", "Controls", hsv_min[1])
        cv2.setTrackbarPos("V Min", "Controls", hsv_min[2])
        cv2.setTrackbarPos("H Max", "Controls", hsv_max[0])
        cv2.setTrackbarPos("S Max", "Controls", hsv_max[1])
        cv2.setTrackbarPos("V Max", "Controls", hsv_max[2])
        
    def mouse_callback(self, event, x, y, flags, param):
        """Klik pada frame → ambil warna HSV dan auto-set range."""
        if event == cv2.EVENT_LBUTTONCLICK and self.current_hsv_frame is not None:
            h_frame, w_frame = self.current_hsv_frame.shape[:2]
            if 0 <= y < h_frame and 0 <= x < w_frame:
                # Ambil rata-rata area 5x5 di sekitar klik (lebih stabil)
                y1 = max(0, y - 2)
                y2 = min(h_frame, y + 3)
                x1 = max(0, x - 2)
                x2 = min(w_frame, x + 3)
                
                region = self.current_hsv_frame[y1:y2, x1:x2]
                h_val = int(np.mean(region[:, :, 0]))
                s_val = int(np.mean(region[:, :, 1]))
                v_val = int(np.mean(region[:, :, 2]))
                
                self.picked_hsv = (h_val, s_val, v_val)
                print(f"\n[PICK] HSV di ({x},{y}): H={h_val} S={s_val} V={v_val}")
                
                # Auto-set range dengan toleransi (lebih lebar untuk warna natural)
                h_tol, s_tol, v_tol = 12, 55, 55
                
                cv2.setTrackbarPos("H Min", "Controls", max(0, h_val - h_tol))
                cv2.setTrackbarPos("S Min", "Controls", max(0, s_val - s_tol))
                cv2.setTrackbarPos("V Min", "Controls", max(0, v_val - v_tol))
                cv2.setTrackbarPos("H Max", "Controls", min(179, h_val + h_tol))
                cv2.setTrackbarPos("S Max", "Controls", min(255, s_val + s_tol))
                cv2.setTrackbarPos("V Max", "Controls", min(255, v_val + v_tol))
                
                print(f"[AUTO] Range: [{max(0,h_val-h_tol)},{max(0,s_val-s_tol)},{max(0,v_val-v_tol)}]"
                      f" - [{min(179,h_val+h_tol)},{min(255,s_val+s_tol)},{min(255,v_val+v_tol)}]")
    
    def draw_info(self, frame):
        """Gambar panel informasi di frame."""
        h, w = frame.shape[:2]
        zona = self.zones[self.current_zone_key]
        warna = tuple(zona["warna_display"])
        
        # Panel atas semi-transparan
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 120), (25, 25, 25), -1)
        cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)
        
        # Judul
        cv2.putText(frame, "HSV CALIBRATOR - Staff Gauge", 
                     (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Zona aktif
        cv2.putText(frame, f"Zona: {zona['nama']}", 
                     (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.6, warna, 2)
        
        # Instruksi
        cv2.putText(frame, "[1-4] Zona | [Klik] Pick | [S] Simpan | [A] Semua | [Q] Keluar", 
                     (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (190, 190, 190), 1)
        cv2.putText(frame, f"Range: {zona['tinggi_min_m']}m - {zona['tinggi_max_m']}m", 
                     (10, 108), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 160, 160), 1)
        
        # Kotak warna zona aktif
        cv2.rectangle(frame, (w - 55, 15), (w - 10, 60), warna, -1)
        cv2.rectangle(frame, (w - 55, 15), (w - 10, 60), (255, 255, 255), 2)
        
        # Picked color info
        if self.picked_hsv:
            h_v, s_v, v_v = self.picked_hsv
            cv2.putText(frame, f"Picked: H={h_v} S={s_v} V={v_v}", 
                         (w - 250, 108), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255), 1)
        
        # Panel bawah: selector zona
        overlay2 = frame.copy()
        cv2.rectangle(overlay2, (0, h - 40), (w, h), (25, 25, 25), -1)
        cv2.addWeighted(overlay2, 0.82, frame, 0.18, 0, frame)
        
        zone_w = w // len(ZONA_ORDER)
        for i, key in enumerate(ZONA_ORDER):
            z = self.zones[key]
            c = tuple(z["warna_display"])
            x_s = i * zone_w
            
            if key == self.current_zone_key:
                cv2.rectangle(frame, (x_s, h - 40), (x_s + zone_w, h), (255, 255, 255), 2)
            
            cv2.rectangle(frame, (x_s + 5, h - 33), (x_s + 22, h - 16), c, -1)
            cv2.putText(frame, f"{i+1}: {key.upper()}", (x_s + 27, h - 17),
                         cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 200), 1)
    
    def create_all_zones_preview(self, hsv_frame, bgr_frame):
        """Preview semua zona warna dalam grid 2x2."""
        h, w = hsv_frame.shape[:2]
        sh, sw = h // 2, w // 2
        
        previews = []
        for key in ZONA_ORDER:
            zona = self.zones[key]
            lower = np.array(zona["hsv_min"])
            upper = np.array(zona["hsv_max"])
            mask = cv2.inRange(hsv_frame, lower, upper)
            
            if key == "merah" and "hsv_min_2" in zona:
                mask2 = cv2.inRange(hsv_frame, np.array(zona["hsv_min_2"]), np.array(zona["hsv_max_2"]))
                mask = cv2.bitwise_or(mask, mask2)
            
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            
            result = cv2.bitwise_and(bgr_frame, bgr_frame, mask=mask)
            result = cv2.resize(result, (sw, sh))
            
            c = tuple(zona["warna_display"])
            cv2.putText(result, f"{zona['nama']}", (5, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.45, c, 2)
            cv2.putText(result, f"{zona['tinggi_min_m']}-{zona['tinggi_max_m']}m | pixels: {cv2.countNonZero(mask)}", 
                         (5, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
            
            previews.append(result)
        
        row1 = np.hstack([previews[0], previews[1]])
        row2 = np.hstack([previews[2], previews[3]])
        return np.vstack([row1, row2])

    def run(self):
        """Loop utama kalibrator."""
        print(f"\n[INFO] Membuka: {self.video_source}")
        cap = cv2.VideoCapture(self.video_source)
        
        if not cap.isOpened():
            print("[ERROR] Kamera/video tidak bisa dibuka!")
            return
        
        print("[OK] Kamera aktif!")
        print("\n=== KONTROL ===")
        print("  1 = HIJAU    2 = KUNING    3 = ORANGE    4 = MERAH")
        print("  Klik = Pick warna    S = Simpan    A = All zones    Q = Keluar")
        print("  R = Reset zona ke default")
        print("=" * 50)
        
        show_all = False
        
        while True:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
            h0, w0 = frame.shape[:2]
            frame = frame[h0 - w0:, :]

            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            self.current_hsv_frame = hsv
            
            # Baca trackbar
            h_min = cv2.getTrackbarPos("H Min", "Controls")
            s_min = cv2.getTrackbarPos("S Min", "Controls")
            v_min = cv2.getTrackbarPos("V Min", "Controls")
            h_max = cv2.getTrackbarPos("H Max", "Controls")
            s_max = cv2.getTrackbarPos("S Max", "Controls")
            v_max = cv2.getTrackbarPos("V Max", "Controls")
            
            # Buat mask
            mask = cv2.inRange(hsv, np.array([h_min, s_min, v_min]), np.array([h_max, s_max, v_max]))
            
            if self.current_zone_key == "merah":
                zona = self.zones["merah"]
                if "hsv_min_2" in zona:
                    mask2 = cv2.inRange(hsv, np.array(zona["hsv_min_2"]), np.array(zona["hsv_max_2"]))
                    mask = cv2.bitwise_or(mask, mask2)
            
            # Morphological cleanup
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            
            # Hasil mask diterapkan ke frame
            result = cv2.bitwise_and(frame, frame, mask=mask)
            
            # Tampilkan pixel count (berguna untuk debugging)
            px_count = cv2.countNonZero(mask)
            cv2.putText(result, f"Detected pixels: {px_count}", (10, 25),
                         cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            
            # Draw info pada frame utama
            display = frame.copy()
            self.draw_info(display)
            
            cv2.imshow("HSV Calibrator", display)
            cv2.imshow("Mask Result", result)
            
            if show_all:
                all_view = self.create_all_zones_preview(hsv, frame)
                cv2.imshow("Semua Zona", all_view)
            
            # Input keyboard
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord('1'):
                self.current_zone_key = "hijau"
                self.update_trackbars()
                print(f"\n→ Zona: {self.zones['hijau']['nama']}")
            elif key == ord('2'):
                self.current_zone_key = "kuning"
                self.update_trackbars()
                print(f"\n→ Zona: {self.zones['kuning']['nama']}")
            elif key == ord('3'):
                self.current_zone_key = "orange"
                self.update_trackbars()
                print(f"\n→ Zona: {self.zones['orange']['nama']}")
            elif key == ord('4'):
                self.current_zone_key = "merah"
                self.update_trackbars()
                print(f"\n→ Zona: {self.zones['merah']['nama']}")
            elif key == ord('s'):
                self.zones[self.current_zone_key]["hsv_min"] = [h_min, s_min, v_min]
                self.zones[self.current_zone_key]["hsv_max"] = [h_max, s_max, v_max]
                self.config["zones"] = self.zones
                save_config(self.config)
            elif key == ord('r'):
                if self.current_zone_key in DEFAULT_ZONES:
                    self.zones[self.current_zone_key] = DEFAULT_ZONES[self.current_zone_key].copy()
                    self.update_trackbars()
                    print(f"\n[RESET] {self.current_zone_key} direset ke default")
            elif key == ord('a'):
                show_all = not show_all
                if not show_all:
                    cv2.destroyWindow("Semua Zona")
        
        cap.release()
        cv2.destroyAllWindows()


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("=" * 50)
    print("  HSV CALIBRATOR - Papan Meteran (Staff Gauge)")
    print("=" * 50)
    print("\nPilih sumber video:")
    print("  1. Webcam (index 0)")
    print("  2. Webcam (index 1) - Logitech C270")
    print("  3. IP Camera (CCTV/DroidCam)")
    print("  4. File Video")
    
    choice = input("\nPilihan (1/2/3/4): ").strip()
    
    if choice == "1":
        source = 0
    elif choice == "2":
        source = 1
    elif choice == "3":
        source = input("URL IP Camera: ").strip()
    elif choice == "4":
        source = input("Path file video: ").strip()
    else:
        source = 0
    
    HSVCalibrator(video_source=source).run()
