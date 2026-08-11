import cv2
import numpy as np
import time
import os
import sys
from flood_detection import FloodDashboard, round_rect, LEVEL_COLORS

class FloodSimulation(FloodDashboard):
    def __init__(self, source=0):
        super().__init__(source=source, is_image=False)
        self.source = source
        # Rentang warna HSV untuk benda biru
        self.lower_blue = np.array([90, 50, 50])
        self.upper_blue = np.array([130, 255, 255])
        
    def process_frame(self, frame):
        h, w = frame.shape[:2]
        
        # Mirror frame
        frame = cv2.flip(frame, 1)
        frame_bg = frame.copy()
        
        roi_img = frame
        roi_offset = (0, 0)
        roi_h, roi_w = roi_img.shape[:2]

        hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
        
        # 1. GRAYSCALE (Simulasi saja pakai Value dari HSV)
        proc_gray = hsv[:,:,2]
        proc_gray_bgr = cv2.cvtColor(proc_gray, cv2.COLOR_GRAY2BGR)
        
        # 2. THRESHOLD (Warna Biru)
        mask = cv2.inRange(hsv, self.lower_blue, self.upper_blue)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        proc_thresh_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        
        # 3. MENCARI KONTUR / DETEKSI GARIS
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        BATAS_BAWAH = roi_h - 50
        BATAS_ATAS = 100
        
        y_line = BATAS_BAWAH
        proc_edge = np.zeros_like(roi_img)
        
        if contours:
            c = max(contours, key=cv2.contourArea)
            if cv2.contourArea(c) > 1000:
                x, y, bw, bh = cv2.boundingRect(c)
                y_line = y
                cv2.rectangle(proc_edge, (x, y), (x+bw, y+bh), (0, 255, 0), 2)
                
        if y_line > BATAS_BAWAH: y_line = BATAS_BAWAH
        if y_line < BATAS_ATAS: y_line = BATAS_ATAS
        
        cv2.line(proc_edge, (0, y_line), (roi_w, y_line), (0, 0, 255), 2)
        
        # Hitung Persentase & CM
        persentase = ((BATAS_BAWAH - y_line) / (BATAS_BAWAH - BATAS_ATAS))
        cm_val = persentase * 400.0 # Maks 400 cm
        
        height_m = cm_val / 100.0
        active_zone = "hijau"
        
        # Mapping dari ZONA_ORDER di parent class
        from flood_detection import ZONA_ORDER
        for zk in reversed(ZONA_ORDER):
            if height_m >= self.zones[zk]["tinggi_min_m"]:
                active_zone = zk
                break
                
        level = self.zones[active_zone].get("level", "AMAN")
        
        # 4. HITUNG KETINGGIAN (Panel 4)
        proc_calc = roi_img.copy()
        cv2.line(proc_calc, (0, y_line), (roi_w, y_line), (0,0,255), 2)
        cv2.putText(proc_calc, f"{cm_val:.1f} cm", (10, y_line-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 2)

        # Skala pixel per cm untuk dashboard
        px_per_cm = (BATAS_BAWAH - BATAS_ATAS) / 400.0 if BATAS_BAWAH != BATAS_ATAS else 1.0

        return frame_bg, roi_offset, cm_val, level, y_line, px_per_cm, proc_gray_bgr, proc_thresh_bgr, proc_edge, proc_calc

    def run_webcam(self):
        print("[INFO] Membuka Webcam...")
        cap = cv2.VideoCapture(self.source)
        
        if not cap.isOpened():
            print("[ERROR] Kamera tidak bisa dibuka!")
            return
            
        cv2.namedWindow("Flood Detection Simulation", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Flood Detection Simulation", 1280, 720)
        
        print("\n[INFO] Simulasi berjalan.")
        print("Gunakan benda berwarna BIRU (seperti buku/kertas) dan gerakkan naik-turun di depan kamera.")
        print("Tekan 'Q' untuk keluar.")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            results = self.process_frame(frame)
            dash = self.create_dashboard(frame, results)
            
            cv2.imshow("Flood Detection Simulation", dash)
            
            if cv2.waitKey(30) & 0xFF == ord('q'):
                break
                
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    src = 0
    if len(sys.argv) > 1:
        try:
            src = int(sys.argv[1])
        except ValueError:
            src = sys.argv[1]
            
    sim = FloodSimulation(source=src)
    sim.run_webcam()
