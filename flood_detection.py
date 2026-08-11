import cv2
import numpy as np
import time
import os
import json
import sys
import math

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config/config_water.json")

# Ambil dari water_level.py / test_gambar.py
ZONA_ORDER = ["hijau", "kuning", "orange", "merah"]
DEFAULT_ZONES = {
    "hijau": {"nama": "HIJAU (Aman)", "level": "AMAN", "hsv_min": [35, 40, 40], "hsv_max": [85, 255, 220], "tinggi_min_m": 0.0, "tinggi_max_m": 1.0, "warna_bgr": (0, 180, 0)},
    "kuning": {"nama": "KUNING (Siaga)", "level": "SIAGA", "hsv_min": [18, 80, 100], "hsv_max": [38, 255, 255], "tinggi_min_m": 1.0, "tinggi_max_m": 2.5, "warna_bgr": (0, 230, 230)},
    "orange": {"nama": "ORANGE (Waspada)", "level": "WASPADA", "hsv_min": [5, 80, 100], "hsv_max": [20, 255, 255], "tinggi_min_m": 2.5, "tinggi_max_m": 3.5, "warna_bgr": (0, 140, 255)},
    "merah": {"nama": "MERAH (Bahaya!)", "level": "BAHAYA", "hsv_min": [0, 100, 100], "hsv_max": [8, 255, 255], "hsv_min_2": [165, 100, 100], "hsv_max_2": [179, 255, 255], "tinggi_min_m": 3.5, "tinggi_max_m": 4.0, "warna_bgr": (0, 0, 240)}
}

LEVEL_COLORS = {
    "AMAN": (0, 200, 0), "SIAGA": (0, 220, 220),
    "WASPADA": (0, 140, 255), "BAHAYA": (0, 0, 255),
    "UNKNOWN": (128, 128, 128)
}

def load_zones():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                cfg = json.load(f)
            zones = cfg.get("zones", DEFAULT_ZONES)
            for k in zones:
                if "warna_bgr" not in zones[k]:
                    zones[k]["warna_bgr"] = tuple(zones[k].get("warna_display", (255, 255, 255)))
                
                # Menyesuaikan label level sesuai permintaan referensi
                if zones[k]["level"] == "RENDAH": zones[k]["level"] = "AMAN"
                if zones[k]["level"] == "SEDANG": zones[k]["level"] = "SIAGA"
                if zones[k]["level"] == "TINGGI": zones[k]["level"] = "WASPADA"
            return zones
        except: pass
    return DEFAULT_ZONES

def round_rect(img, pt1, pt2, color, thickness, r, d):
    x1, y1 = pt1
    x2, y2 = pt2
    if thickness < 0:
        # Fill polygon for rounded rect
        pts = np.array([
            [x1 + r, y1], [x2 - r, y1], 
            [x2, y1], [x2, y1 + r], 
            [x2, y2 - r], [x2, y2], 
            [x2 - r, y2], [x1 + r, y2], 
            [x1, y2], [x1, y2 - r], 
            [x1, y1 + r], [x1, y1]
        ])
        cv2.fillPoly(img, [pts], color)
        
        cv2.ellipse(img, (x1 + r, y1 + r), (r, r), 180, 0, 90, color, -1)
        cv2.ellipse(img, (x2 - r, y1 + r), (r, r), 270, 0, 90, color, -1)
        cv2.ellipse(img, (x1 + r, y2 - r), (r, r), 90, 0, 90, color, -1)
        cv2.ellipse(img, (x2 - r, y2 - r), (r, r), 0, 0, 90, color, -1)
        return

    # Top left
    cv2.line(img, (x1 + r, y1), (x2 - r, y1), color, thickness)
    cv2.line(img, (x1, y1 + r), (x1, y2 - r), color, thickness)
    cv2.ellipse(img, (x1 + r, y1 + r), (r, r), 180, 0, 90, color, thickness)
    # Top right
    cv2.line(img, (x2, y1 + r), (x2, y2 - r), color, thickness)
    cv2.ellipse(img, (x2 - r, y1 + r), (r, r), 270, 0, 90, color, thickness)
    # Bottom left
    cv2.line(img, (x1 + r, y2), (x2 - r, y2), color, thickness)
    cv2.ellipse(img, (x1 + r, y2 - r), (r, r), 90, 0, 90, color, thickness)
    # Bottom right
    cv2.ellipse(img, (x2 - r, y2 - r), (r, r), 0, 0, 90, color, thickness)



class FloodDashboard:
    def __init__(self, source=None, is_image=False):
        self.zones = load_zones()
        self.is_image = is_image
        self.source = source
        self.start_time = time.time()
        
        # Load kalibrasi if exists
        self.roi = None
        self.kalibrasi_geometri = {}
        self.M = None
        
        try:
            with open(CONFIG_FILE, 'r') as f:
                cfg = json.load(f)
                self.roi = cfg.get("roi")
                kalib = cfg.get("kalibrasi_geometri", {})
                if kalib and kalib.get("aktif", False):
                    pts_src = np.array(kalib["points_src"], dtype=np.float32)
                    pts_dst = np.array(kalib["points_dst"], dtype=np.float32)
                    self.M = cv2.getPerspectiveTransform(pts_src, pts_dst)
                    self.tgt_w = kalib["target_width"]
                    self.tgt_h = kalib["target_height"]
        except: pass

        # Wave animation
        self.wave_phase = 0.0

        # Telemetry (MQTT) — optional
        try:
            from telemetry import Telemetry
            self.telemetry = Telemetry()
        except Exception as e:
            print(f"[TELEMETRY] Tidak dimuat: {e}")
            self.telemetry = None

    # --- Deteksi Tiang Ukur (dari kode user) ---
    @staticmethod
    def detect_pole(frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 11, 2)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        img_h, img_w = frame.shape[:2]
        best = None
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if h > img_h * 0.4 and w < img_w * 0.15 and w > img_w * 0.01:
                if best is None or h > cv2.boundingRect(best)[3]:
                    best = cnt
        if best is not None:
            return cv2.boundingRect(best)
        return None

    # --- Deteksi Garis Air via Profil Kecerahan (dari kode user) ---
    @staticmethod
    def detect_water_line_brightness(roi_frame):
        gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        profile = np.mean(blur, axis=1)
        mean_brightness = np.mean(profile)
        
        # Scan dari tengah ke bawah mencari crossing point
        roi_h = roi_frame.shape[0]
        start = int(roi_h * 0.3)
        for i in range(start, roi_h):
            if profile[i] < mean_brightness * 0.85:
                return i
        return -1

    @staticmethod
    def _hsv_board_mask(roi_img, zones):
        """HSV segmentasi semua zona → combined board mask."""
        hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
        h, w = roi_img.shape[:2]
        combined = np.zeros((h, w), np.uint8)
        k5 = np.ones((5, 5), np.uint8)
        for zk in ZONA_ORDER:
            z = zones[zk]
            mask = cv2.inRange(hsv, np.array(z["hsv_min"]), np.array(z["hsv_max"]))
            if zk == "merah" and "hsv_min_2" in z:
                mask2 = cv2.inRange(hsv, np.array(z["hsv_min_2"]), np.array(z["hsv_max_2"]))
                mask = cv2.bitwise_or(mask, mask2)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k5, iterations=2)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k5, iterations=1)
            combined = cv2.bitwise_or(combined, mask)
        k7 = np.ones((7, 7), np.uint8)
        return cv2.morphologyEx(combined, cv2.MORPH_CLOSE, k7, iterations=2)

    @staticmethod
    def _scan_waterline(board_mask):
        """Multi-column scan → (y_wl, confidence). Abaikan tepi 10%."""
        h, w = board_mask.shape[:2]
        min_consec = max(5, h // 30)
        step = max(1, w // min(80, w))
        margin = w // 10
        candidates = []
        for col in range(margin + step // 2, w - margin, step):
            column = board_mask[:, col]
            consec = 0
            for row in range(h - 1, -1, -1):
                if column[row] > 0:
                    consec += 1
                    if consec >= min_consec:
                        candidates.append(row + consec - 1)
                        break
                else:
                    consec = 0
        if not candidates:
            return h - 1, 0.0
        y_wl = int(np.median(candidates))
        conf = 0.2
        if len(candidates) >= 5:
            iqr = np.percentile(candidates, 75) - np.percentile(candidates, 25)
            conf = max(0.1, min(1.0, 1.0 - (iqr / h) * 2))
        return y_wl, conf

    def process_frame(self, frame):
        h, w = frame.shape[:2]

        if self.M is not None:
            frame = cv2.warpPerspective(frame, self.M, (self.tgt_w, self.tgt_h))
            h, w = frame.shape[:2]

        # ══════════════════════════════════════════════════
        # LAYER 1: HSV segmentasi (gauge berwarna)
        # ══════════════════════════════════════════════════
        if self.roi:
            x1, y1, x2, y2 = self.roi
            rx, ry, rw, rh = x1, y1, x2 - x1, y2 - y1
        else:
            rx, ry, rw, rh = 0, 0, w, h

        roi_img = frame[ry:ry + rh, rx:rx + rw]
        roi_offset = (rx, ry)
        roi_h, roi_w = roi_img.shape[:2]

        board_mask = self._hsv_board_mask(roi_img, self.zones)
        y_wl, conf = self._scan_waterline(board_mask)
        ratio = (roi_h - y_wl) / roi_h if roi_h > 0 else 0
        height_m = float(np.clip(ratio * 4.0, 0.0, 4.0))
        active_zone = "hijau"
        for zk in reversed(ZONA_ORDER):
            if height_m >= self.zones[zk]["tinggi_min_m"]:
                active_zone = zk
                break

        # ══════════════════════════════════════════════════
        # LAYER 2: Pole Detection + Brightness Profile 
        # (untuk gauge putih / non-warna)
        # ══════════════════════════════════════════════════
        if height_m < 0.05:
            pole_box = self.detect_pole(frame)
            if pole_box is not None:
                px, py, pw, ph = pole_box
                # Perlebar ROI sedikit untuk konteks
                margin = int(pw * 0.5)
                px2 = max(0, px - margin)
                pw2 = min(w, px + pw + margin) - px2
                roi_img = frame[py:py+ph, px2:px2+pw2]
                roi_offset = (px2, py)
                roi_h, roi_w = roi_img.shape[:2]
                
                # Board mask baru untuk panel OpenCV
                gray_pole = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
                _, board_mask = cv2.threshold(gray_pole, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
                
                wl_y = self.detect_water_line_brightness(roi_img)
                if wl_y != -1:
                    y_wl = wl_y
                    ratio = (roi_h - y_wl) / roi_h
                    height_m = ratio * 4.0
                    height_m = min(4.0, max(0.0, height_m))

        # ══════════════════════════════════════════════════
        # LAYER 3: Laplacian Sharpness Fallback
        # (gauge terendam dengan refleksi)
        # ══════════════════════════════════════════════════
        if height_m < 0.05:
            gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
            cx = roi_w // 2
            sw = max(10, roi_w // 4)
            strip = gray[:, max(0,cx-sw):min(roi_w,cx+sw)]
            
            laplacian = cv2.Laplacian(strip, cv2.CV_64F)
            sharpness = np.var(laplacian, axis=1)
            sk = max(21, roi_h // 30)
            if sk % 2 == 0: sk += 1
            sharp_s = cv2.GaussianBlur(sharpness.reshape(-1,1).astype(np.float32), (sk,1), 0).flatten()
            
            window = max(20, roi_h // 20)
            max_drop = 0
            best_y = roi_h - 1
            for row in range(int(roi_h * 0.25), int(roi_h * 0.85)):
                sa = np.mean(sharp_s[max(0, row-window):row])
                sb = np.mean(sharp_s[row:min(roi_h, row+window)])
                if sa > 0:
                    drop = (sa - sb) / sa
                    if drop > max_drop and drop > 0.25:
                        max_drop = drop
                        best_y = row
            if max_drop > 0.25:
                y_wl = best_y
                ratio = (roi_h - y_wl) / roi_h
                height_m = ratio * 4.0
                height_m = min(4.0, max(0.0, height_m))

        # Determine zone & level
        active_zone = "hijau"
        for zk in reversed(ZONA_ORDER):
            if height_m >= self.zones[zk]["tinggi_min_m"]:
                active_zone = zk
                break

        cm_val = height_m * 100.0
        level = self.zones[active_zone].get("level", "AMAN")
        px_per_cm = roi_h / 400.0

        # Create Process Images
        proc_gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        proc_gray_bgr = cv2.cvtColor(proc_gray, cv2.COLOR_GRAY2BGR)
        
        _, proc_thresh = cv2.threshold(proc_gray, 100, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        proc_thresh_bgr = cv2.cvtColor(proc_thresh, cv2.COLOR_GRAY2BGR)
        
        edges = cv2.Canny(board_mask, 50, 150)
        proc_edge = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        cv2.line(proc_edge, (0, y_wl), (roi_w, y_wl), (0,0,255), 2)
        
        proc_calc = roi_img.copy()
        cv2.line(proc_calc, (0, y_wl), (roi_w, y_wl), (0,0,255), 2)
        cv2.putText(proc_calc, f"{cm_val:.1f} cm", (10, max(20, y_wl-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 2)

        return frame, roi_offset, cm_val, level, y_wl, px_per_cm, proc_gray_bgr, proc_thresh_bgr, proc_edge, proc_calc

    def create_dashboard(self, frame, results):
        """Canvas 1280x720 — gaya sama dengan WaterLevelDetector."""
        frame_bg, roi_offset, cm_val, level, y_wl, px_per_cm, p_gray, p_thresh, p_edge, p_calc = results

        CW, CH   = 1280, 720
        HDR_H    = 42
        FTR_H    = 32
        RIGHT_W  = 380
        PROC_W   = 220
        GAP      = 4
        CAM_X2   = CW - RIGHT_W - PROC_W - GAP * 2
        CAM_Y1   = HDR_H
        CAM_Y2   = CH - FTR_H
        RP_X1    = CW - RIGHT_W
        PROC_X1  = CAM_X2 + GAP
        PROC_X2  = RP_X1 - GAP
        FTR_Y    = CH - FTR_H

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
        accent = ZONE_ACCENT.get(level, (128, 128, 128))

        dash = np.full((CH, CW, 3), C_BG, dtype=np.uint8)

        # ── Header ──
        dash[:HDR_H] = C_PANEL
        cv2.line(dash, (0, HDR_H - 1), (CW, HDR_H - 1), C_BORDER, 1)
        cv2.putText(dash, "RIVER EYE", (10, 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, C_BRAND, 1, cv2.LINE_AA)
        cv2.putText(dash, "ILUSTRASI PROSES DETEKSI KETINGGIAN AIR  —  MODE GAMBAR STATIS",
                    (10, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.28, C_DIM, 1, cv2.LINE_AA)
        cv2.line(dash, (110, 0), (110, HDR_H), C_BORDER, 1)

        mx = CW - 230
        cv2.line(dash, (mx, 0), (mx, HDR_H), C_BORDER, 1)
        mqtt_ok = (self.telemetry is not None and
                   getattr(self.telemetry, "_mqtt", None) is not None)
        dot_c = C_GREEN if mqtt_ok else (48, 32, 200)
        blink = int(time.time() * 2) % 2 == 0
        if mqtt_ok and blink:
            cv2.circle(dash, (mx + 12, 21), 4, dot_c, -1)
        else:
            cv2.circle(dash, (mx + 12, 21), 4, dot_c, 1)
        cv2.putText(dash, "MQTT TERHUBUNG" if mqtt_ok else "MQTT TERPUTUS",
                    (mx + 22, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.28, dot_c, 1, cv2.LINE_AA)
        cv2.putText(dash, "localhost:1883", (mx + 22, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.24, C_DIM, 1, cv2.LINE_AA)

        # ── Kamera embed (kiri) ──
        fh, fw = frame_bg.shape[:2]
        cam_w = CAM_X2
        cam_h = CAM_Y2 - CAM_Y1
        scale = min(cam_w / max(fw, 1), cam_h / max(fh, 1))
        nw, nh = int(fw * scale), int(fh * scale)
        ox = (cam_w - nw) // 2
        oy = CAM_Y1 + (cam_h - nh) // 2
        if nw > 0 and nh > 0:
            dash[oy:oy + nh, ox:ox + nw] = cv2.resize(frame_bg, (nw, nh))

        # Animasi gelombang di atas kamera
        g_y_wl = int(roi_offset[1] + y_wl)
        scaled_y = int(g_y_wl * scale)
        wave_y = oy + scaled_y
        if CAM_Y1 < wave_y < CAM_Y2 and nw > 2:
            xs = np.arange(ox, ox + nw, 2)
            ys = (wave_y + 4 * np.sin(
                2 * math.pi * (xs - ox) / max(60, nw // 3) + self.wave_phase
            )).astype(int)
            ys = np.clip(ys, CAM_Y1, CAM_Y2)
            pts_fill = np.array(
                [[ox, oy + nh]] +
                list(zip(xs.tolist(), ys.tolist())) +
                [[ox + nw - 1, oy + nh]],
                dtype=np.int32
            )
            overlay = dash.copy()
            cv2.fillPoly(overlay, [pts_fill], (80, 45, 20))
            cv2.addWeighted(overlay, 0.22, dash, 0.78, 0, dash)
            pts_wave = np.array(list(zip(xs.tolist(), ys.tolist())),
                                dtype=np.int32).reshape(-1, 1, 2)
            cv2.polylines(dash, [pts_wave], False, C_BLUE, 2, cv2.LINE_AA)
            cv2.putText(dash, "BATAS AIR", (ox + 8, wave_y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3, C_BLUE, 1, cv2.LINE_AA)

        cv2.rectangle(dash, (0, CAM_Y1), (CAM_X2, CAM_Y2), C_BORDER, 1)
        cv2.putText(dash, "INPUT GAMBAR", (6, CAM_Y1 + 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.26, C_DIM, 1)

        # ── Panel Proses OpenCV (tengah) ──
        cv2.line(dash, (PROC_X1 - 1, HDR_H), (PROC_X1 - 1, FTR_Y), C_BORDER, 1)
        cv2.line(dash, (PROC_X2 + 1, HDR_H), (PROC_X2 + 1, FTR_Y), C_BORDER, 1)
        cv2.putText(dash, "PROSES OPENCV", (PROC_X1 + 6, HDR_H + 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.26, C_DIM, 1)
        proc_imgs = [
            ("1. GRAYSCALE",         p_gray),
            ("2. THRESHOLD",         p_thresh),
            ("3. DETEKSI GARIS AIR", p_edge),
            ("4. HITUNG KETINGGIAN", p_calc),
        ]
        proc_h = (FTR_Y - HDR_H - 24) // 4
        proc_w = PROC_X2 - PROC_X1 - 8
        for i, (plabel, pimg) in enumerate(proc_imgs):
            py = HDR_H + 24 + i * proc_h
            cv2.rectangle(dash, (PROC_X1 + 4, py), (PROC_X2 - 4, py + proc_h - 4), C_PANEL, -1)
            cv2.rectangle(dash, (PROC_X1 + 4, py), (PROC_X2 - 4, py + proc_h - 4), C_BORDER, 1)
            cv2.putText(dash, plabel, (PROC_X1 + 8, py + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.26, C_MED, 1)
            ph_img, pw_img = pimg.shape[:2]
            img_h_avail = proc_h - 22
            img_w_avail = proc_w - 8
            iscale = min(img_w_avail / max(pw_img, 1), img_h_avail / max(ph_img, 1))
            inw, inh = int(pw_img * iscale), int(ph_img * iscale)
            if inw > 0 and inh > 0:
                prs = cv2.resize(pimg, (inw, inh))
                pox = PROC_X1 + 6
                poy = py + 18
                if poy + inh <= FTR_Y and pox + inw <= PROC_X2:
                    dash[poy:poy + inh, pox:pox + inw] = prs

        # ── Panel Kanan ──
        cv2.line(dash, (RP_X1 - 1, HDR_H), (RP_X1 - 1, FTR_Y), C_BORDER, 1)
        ry = HDR_H

        def sec_label(y, text):
            dash[y:y + 18, RP_X1:] = (18, 12, 10)
            cv2.putText(dash, text, (RP_X1 + 8, y + 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.26, C_DIM, 1)
            cv2.line(dash, (RP_X1, y + 18), (CW, y + 18), C_BORDER, 1)
            return y + 18

        # Big metric
        BIG_H = 138
        dash[ry:ry + BIG_H, RP_X1:] = C_PANEL
        cv2.putText(dash, "KETINGGIAN AIR TERDETEKSI",
                    (RP_X1 + 8, ry + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.26, C_DIM, 1)
        cv2.putText(dash, f"{int(cm_val)}", (RP_X1 + 10, ry + 82),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.8, accent, 2, cv2.LINE_AA)
        cv2.putText(dash, "CENTIMETER", (RP_X1 + 10, ry + 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, C_DIM, 1)
        bw = len(level) * 9 + 16
        cv2.rectangle(dash, (RP_X1 + 10, ry + 108), (RP_X1 + 10 + bw, ry + 128), accent, 1)
        cv2.putText(dash, level, (RP_X1 + 16, ry + 122),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, accent, 1, cv2.LINE_AA)
        cv2.line(dash, (RP_X1, ry + BIG_H), (CW, ry + BIG_H), C_BORDER, 1)
        ry += BIG_H

        # Zona table
        ry = sec_label(ry, "REFERENSI ZONA KETINGGIAN")
        zone_rows = [
            ("merah",  "BAHAYA",  "> 350 cm", (48, 32, 200)),
            ("orange", "WASPADA", "250-350",  (32, 130, 220)),
            ("kuning", "SIAGA",   "100-250",  (32, 200, 220)),
            ("hijau",  "AMAN",    "0-100 cm", (120, 184, 58)),
        ]
        active_zone_key = "hijau"
        for zk in reversed(ZONA_ORDER):
            if cm_val / 100.0 >= self.zones[zk]["tinggi_min_m"]:
                active_zone_key = zk
                break
        for zk, zlabel, zrange, zc in zone_rows:
            active = (zk == active_zone_key)
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

        # ── Visualisasi Air Animasi ──
        ry = sec_label(ry, "VISUALISASI KETINGGIAN AIR")
        COL_H  = 90
        COL_X1 = RP_X1 + 10
        COL_X2 = CW - 38
        COL_Y1 = ry + 4
        COL_Y2 = ry + COL_H

        for i, (zc, zh) in enumerate([
            ((48, 32, 200), COL_H // 4),
            ((32, 130, 220), COL_H // 4),
            ((32, 200, 220), COL_H // 4),
            ((120, 184, 58), COL_H - 3 * (COL_H // 4)),
        ]):
            sy1 = COL_Y1 + sum(COL_H // 4 for _ in range(i))
            cv2.rectangle(dash, (COL_X1, sy1), (COL_X1 + 10, sy1 + zh), zc, -1)
        cv2.rectangle(dash, (COL_X1, COL_Y1), (COL_X1 + 10, COL_Y2), C_BORDER, 1)

        TX1, TX2 = COL_X1 + 12, COL_X2
        TW = TX2 - TX1
        cv2.rectangle(dash, (TX1, COL_Y1), (TX2, COL_Y2), (10, 7, 5), -1)
        cv2.rectangle(dash, (TX1, COL_Y1), (TX2, COL_Y2), C_BORDER, 1)

        water_ratio = float(np.clip(cm_val / 400.0, 0, 1))
        water_y = int(COL_Y2 - water_ratio * COL_H)
        water_y = max(COL_Y1 + 2, min(COL_Y2 - 2, water_y))
        if water_y < COL_Y2 - 1 and TW > 4:
            wbody = tuple(max(0, int(c * 0.35)) for c in accent)
            cv2.rectangle(dash, (TX1 + 1, water_y + 1), (TX2 - 1, COL_Y2 - 1), wbody, -1)
            wxs = np.arange(TX1 + 1, TX2 - 1, 2)
            if len(wxs) > 0:
                wys = (water_y + 3 * np.sin(
                    2 * math.pi * (wxs - TX1) / max(20, TW // 2) + self.wave_phase * 1.5
                )).astype(int)
                wys = np.clip(wys, COL_Y1 + 1, COL_Y2 - 1)
                wpts = np.array(list(zip(wxs.tolist(), wys.tolist())),
                                dtype=np.int32).reshape(-1, 1, 2)
                cv2.polylines(dash, [wpts], False, accent, 2, cv2.LINE_AA)

        for pct, lbl in [(1.0,"4m"),(0.75,"3m"),(0.5,"2m"),(0.25,"1m"),(0.0,"0")]:
            my = int(COL_Y1 + (1.0 - pct) * COL_H)
            cv2.line(dash, (COL_X2 - 3, my), (COL_X2, my), C_DIM, 1)
            cv2.putText(dash, lbl, (COL_X2 + 3, my + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.22, C_DIM, 1)
        cv2.line(dash, (TX1, water_y), (TX2, water_y), accent, 1)

        ry = COL_Y2 + 8
        cv2.line(dash, (RP_X1, ry), (CW, ry), C_BORDER, 1)

        # Kalibrasi info
        ry = sec_label(ry, "DATA KALIBRASI")
        cv2.putText(dash, f"Tinggi max : 400 cm", (RP_X1 + 8, ry + 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.28, C_DIM, 1)
        cv2.putText(dash, f"Resolusi   : {px_per_cm:.2f} px/cm", (RP_X1 + 8, ry + 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.28, C_DIM, 1)
        ry += 34
        cv2.line(dash, (RP_X1, ry), (CW, ry), C_BORDER, 1)

        # MQTT topics
        ry = sec_label(ry, "MQTT DATA TERKIRIM")
        mqtt_topics = [
            ("height_cm",  f"{int(cm_val)}"),
            ("height_m",   f"{cm_val / 100.0:.3f}"),
            ("level",      level),
            ("zone",       active_zone_key),
        ]
        for tk, tv in mqtt_topics:
            cv2.putText(dash, tk, (RP_X1 + 8, ry + 11),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.26, C_DIM, 1)
            vc = C_GREEN if tv not in ("BAHAYA", "WASPADA") else (48, 32, 200)
            cv2.putText(dash, tv, (CW - 8 - len(tv) * 7, ry + 11),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.28, vc, 1)
            ry += 16

        # ── Footer ──
        dash[FTR_Y:] = C_PANEL
        cv2.line(dash, (0, FTR_Y), (CW, FTR_Y), C_BORDER, 1)
        cv2.putText(dash, "* Hasil dapat dipengaruhi pencahayaan, sudut kamera, dan kondisi lingkungan.",
                    (8, FTR_Y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.26, C_DIM, 1)
        cv2.putText(dash, "[Q] Keluar", (CW - 80, FTR_Y + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.26, C_DIM, 1)

        # BAHAYA flash
        if level == "BAHAYA" and int(time.time() * 3) % 2 == 0:
            cv2.rectangle(dash, (0, 0), (CW - 1, CH - 1), (48, 32, 200), 4)

        # Update wave phase
        self.wave_phase = (self.wave_phase + 0.08) % (2 * math.pi)

        return dash

    def run_image(self, img_path):
        frame = cv2.imread(img_path)
        if frame is None:
            print("Gagal membaca gambar:", img_path)
            return

        results = self.process_frame(frame)
        _, _, cm_val, level, _, _, _, _, _, _ = results

        # Kirim MQTT sekali (gambar statis)
        if self.telemetry:
            active_zone = "hijau"
            for zk in reversed(ZONA_ORDER):
                if cm_val / 100.0 >= self.zones[zk]["tinggi_min_m"]:
                    active_zone = zk
                    break
            self.telemetry.send(cm_val / 100.0, active_zone, level, 0.9)

        cv2.namedWindow("Flood Detection Dashboard", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Flood Detection Dashboard", 1280, 720)

        print("Dashboard aktif. Tekan [Q] atau [ESC] untuk keluar dan simpan.")
        last_dash = None
        while True:
            last_dash = self.create_dashboard(frame, results)
            cv2.imshow("Flood Detection Dashboard", last_dash)
            key = cv2.waitKey(30) & 0xFF
            if key in (ord('q'), 27):
                break

        out_path = (img_path.replace(".png", "_dashboard.png")
                            .replace(".jpg", "_dashboard.jpg"))
        if last_dash is not None:
            cv2.imwrite(out_path, last_dash)
            print(f"Dashboard disimpan: {out_path}")

        cv2.destroyAllWindows()
        if self.telemetry:
            self.telemetry.close()

if __name__ == "__main__":
    img_path = os.path.join(SCRIPT_DIR, "samples/gambar air lebih tinggi.png")
    if len(sys.argv) > 1:
        img_path = sys.argv[1]
        
    dashboard = FloodDashboard(is_image=True)
    dashboard.run_image(img_path)
