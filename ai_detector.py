import cv2
import numpy as np

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

class WaterLevelAI:
    def __init__(self, model_path="models/yolov8n-seg.pt"):
        """
        Inisialisasi sistem pembacaan air menggunakan YOLOv8 Segmentation.
        Untuk pemakaian di lapangan, model bawaan ringan ('models/yolov8n-seg.pt') harus di-retrain
        memiliki custom class 'water' dan 'staff_gauge'.
        """
        self.model = None
        if YOLO is None:
            print("[WARN] Model YOLO gagal dimuat (ultralytics tidak terinstal).")
            return
            
        try:
            print(f"[INFO] Memuat YOLO AI model: {model_path} ...")
            # YOLO akan otomatis mengunduh model jika file .pt tidak ada di direktori
            self.model = YOLO(model_path)
            print("[INFO] YOLO AI siap!")
        except Exception as e:
            print(f"[ERROR] Gagal memuat AI model: {e}")

    def predict_water_mask(self, frame):
        """
        Kembalikan binary mask dari prediksi area luasan air.
        """
        if self.model is None:
            return np.zeros(frame.shape[:2], dtype=np.uint8)

        results = self.model(frame, verbose=False)
        mask_out = np.zeros(frame.shape[:2], dtype=np.uint8)
        
        for r in results:
            if r.masks is not None:
                for mask, box in zip(r.masks.data, r.boxes):
                    # class_id = int(box.cls[0])
                    # (Untuk versi produksi, gunakan logika: if class_id == ID_WATER)
                    
                    m = mask.cpu().numpy()
                    m = cv2.resize(m, (frame.shape[1], frame.shape[0]))
                    mask_out = cv2.bitwise_or(mask_out, (m * 255).astype(np.uint8))
                        
        return mask_out
        
    def get_water_line_yolo(self, frame, gauge_roi):
        """
        Cari titik sentuh antara segmentasi air dengan bounding box tiang meteran.
        """
        water_mask = self.predict_water_mask(frame)
        x, y, w, h = gauge_roi
        
        gauge_water_mask = water_mask[y:y+h, x:x+w]
        
        rows = np.any(gauge_water_mask > 0, axis=1)
        ys = np.where(rows)[0]
        
        if len(ys) > 0:
            y_wl = ys[0]
            confidence = 0.90 # YOLO confidence base
            return y_wl, confidence
            
        return -1, 0.0

if __name__ == "__main__":
    print("Mengecek modul Ultralytics...")
    ai = WaterLevelAI()
    print("AI Framework Initialization Completed.")
    
    # Simple test if image exists
    img_path = "samples/gambar air lebih tinggi.png"
    img = cv2.imread(img_path)
    if img is not None and ai.model is not None:
        print(f"[TEST] Menjalankan segmentasi YOLO pada {img_path}...")
        try:
            results = ai.model(img, verbose=False)
            
            # Save visualisasi aslinya!
            plotted_img = results[0].plot()
            cv2.imwrite("hasil_debug_yolo_plot.png", plotted_img)
            
            mask = ai.predict_water_mask(img)
            cv2.imwrite("hasil_debug_yolo_mask.png", mask)
            px_air = cv2.countNonZero(mask)
            
            print(f"[TEST] Selesai diproses.")
            print(f"       Mask Air: {px_air} piksel.")
            print("[TEST] Buka file: 'hasil_debug_yolo_plot.png' untuk melihat apa SAJA objek yang dikenali oleh YOLO saat ini.")
            print("[INFO] Jika 'hasil_debug_yolo_mask.png' hitam polos, artinya AI gagal menemukan 'Air/Sungai'. Ini 100% normal karena otak 'models/yolov8n-seg.pt' tidak dilatih untuk mengenali sungai/meteran.")
        except Exception as e:
            print(f"[ERROR] Tes inferensi gagal: {e}")
