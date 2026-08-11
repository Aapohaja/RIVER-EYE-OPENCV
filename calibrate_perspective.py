import cv2
import numpy as np
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config/config_water.json")

points = []
img_copy = None

def mouse_handler(event, x, y, flags, param):
    global points, img_copy
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(points) < 4:
            points.append([x, y])
            cv2.circle(img_copy, (x, y), 5, (0, 0, 255), -1)
            cv2.putText(img_copy, str(len(points)), (x+10, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
            cv2.imshow("Kalibrasi Perspektif", img_copy)

def main():
    global img_copy, points
    
    # 1. Pilih gambar
    IMAGE_FILE = None
    if len(sys.argv) > 1:
        IMAGE_FILE = sys.argv[1]
    else:
        for f in os.listdir(SCRIPT_DIR):
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')) and 'hasil' not in f.lower():
                IMAGE_FILE = os.path.join(SCRIPT_DIR, f)
                break

    if not IMAGE_FILE or not os.path.exists(IMAGE_FILE):
        print("[EROR] Gambar tidak ditemukan.")
        return

    print(f"Membuka gambar: {IMAGE_FILE}")
    img = cv2.imread(IMAGE_FILE)
    if img is None:
        print("[EROR] Gagal membaca gambar.")
        return
        
    ih, iw = img.shape[:2]
    
    # Resize untuk tampilan jika terlalu besar
    scale = 1.0
    if ih > 900 or iw > 1200:
        scale = min(900.0/ih, 1200.0/iw)
        img = cv2.resize(img, None, fx=scale, fy=scale)
        print(f"Gambar di-resize (skala {scale:.2f}) untuk layar Anda.")

    img_copy = img.copy()
    
    print("\n--- INSTRUKSI KALIBRASI PERSPEKTIF ---")
    print("Klik tepat pada 4 sudut meteran/tiang secara berurutan:")
    print(" 1. Kiri ATAS (Top-Left)")
    print(" 2. Kanan ATAS (Top-Right)")
    print(" 3. Kanan BAWAH (Bottom-Right)")
    print(" 4. Kiri BAWAH (Bottom-Left)")
    print("Tekan 'r' untuk reset titik.")
    print("Tekan panah jika tidak sengaja salah klik.")
    print("----------------------------------------\n")
    
    cv2.namedWindow("Kalibrasi Perspektif")
    cv2.setMouseCallback("Kalibrasi Perspektif", mouse_handler)

    while True:
        cv2.imshow("Kalibrasi Perspektif", img_copy)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('r'):
            points = []
            img_copy = img.copy()
            print("Titik di-reset.")
        elif key == 27 or key == ord('q'): # ESC or q
            print("Membatalkan.")
            break
        elif len(points) == 4:
            # Tunggu sedetik biar user lihat titik ke-4
            cv2.waitKey(500)
            break

    cv2.destroyAllWindows()

    if len(points) != 4:
        print("Batal menyimpan. Dibutuhkan tepat 4 titik.")
        return
        
    # Kembalikan koordinat titik ke skala asli gambar
    points_orig = [[int(x/scale), int(y/scale)] for [x, y] in points]
    
    # Asumsikan target adalah papan tegak lurus
    # Coba hitung tinggi estimasi (Max Y distance) dan lebar (Max X distance)
    # Papan staff gauge umumnya sangat tinggi dan sempit, misal aspect ratio lebar:tinggi = 1:20
    # Kita tetapkan kanvas target (destination) stabil
    w_target = 150
    h_target = 2500
    
    target_pts = [
        [0, 0],
        [w_target, 0],
        [w_target, h_target],
        [0, h_target]
    ]

    print("\n[INFO] Titik Kalibrasi (Asli):", points_orig)
    print(f"[INFO] Target Kanvas Lurus: {w_target}x{h_target} px")
    
    # Menyimpan ke config/config_water.json
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    except Exception:
        config = {}

    config["kalibrasi_geometri"] = {
        "aktif": True,
        "points_src": points_orig,
        "points_dst": target_pts,
        "target_width": w_target,
        "target_height": h_target
    }

    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
        
    print(f"\n[SUKSES] Konfigurasi kalibrasi telah disimpan ke {CONFIG_FILE}.")
    print("Sekarang test_gambar.py dan water_level.py akan otomatis menegakkan gambar.")

if __name__ == "__main__":
    main()
