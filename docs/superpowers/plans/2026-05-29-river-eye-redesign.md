# River Eye — Dashboard Redesign & MQTT Completion

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign semua dashboard OpenCV ke gaya Professional Terminal dengan animasi gelombang air, dan lengkapi integrasi MQTT ke semua mode.

**Architecture:** Setiap file yang berubah tetap berdiri sendiri — tidak ada modul baru yang dibuat. `water_level.py` mendapat fungsi `draw_dashboard()` yang sepenuhnya baru (canvas 1100×700 terpisah dari frame kamera) dan `draw_roi_overlay()` yang diupdate dengan animasi gelombang. `flood_detection.py` mendapat gaya yang sama plus Telemetry. `telemetry.py` mendapat dua topic MQTT baru. `protel.py` mendapat menu terminal yang bersih.

**Tech Stack:** Python 3.x, OpenCV 4.x, NumPy, paho-mqtt, colorama (optional)

---

## File Map

| File | Perubahan |
|---|---|
| `water_level.py` | Tambah `self.wave_phase` di `__init__`; update `draw_roi_overlay()` (gelombang); bangun ulang `draw_dashboard()` (canvas baru) |
| `flood_detection.py` | Tambah `self.wave_phase`, `self.telemetry` di `__init__`; bangun ulang `create_dashboard()`; update `run_image()` (loop + telemetry) |
| `telemetry.py` | Tambah 2 topic di `_publish_mqtt()`: `river-eye/zone` dan `river-eye/confidence` |
| `protel.py` | Rewrite menu dengan box-drawing ASCII, tanpa emoji, pakai colorama optional |
| `requirements.txt` | Tambah `colorama>=0.4.6` |
| `tests/test_telemetry_topics.py` | Test baru: verifikasi topic baru dipublish |

---

## Konstanta Warna (BGR — digunakan di semua task)

Referensi warna yang dipakai konsisten di `water_level.py` dan `flood_detection.py`:

```python
# Semua warna dalam format BGR (OpenCV)
C_BG        = (22,  14,  10)   # #0a0e16 — background utama
C_PANEL     = (32,  21,  13)   # #0d1520 — panel/header/footer
C_BORDER    = (53,  37,  28)   # #1c2535 — garis pemisah
C_DIM       = (62,  46,  30)   # teks redup (label section)
C_TXT_MED   = (74,  58,  42)   # teks menengah
C_BRAND     = (232, 184, 122)  # #7ab8e8 — nama sistem (cyan)
C_GREEN     = (120, 184,  58)  # #3ab878 — zona AMAN / aksen utama
C_BLUE      = (240, 184,  74)  # #4ab8f0 — confidence / MQTT

ZONE_ACCENT = {          # warna aksen per level (BGR)
    "AMAN":    (120, 184,  58),
    "RENDAH":  (120, 184,  58),
    "SIAGA":   ( 32, 200, 220),
    "SEDANG":  ( 32, 200, 220),
    "WASPADA": ( 32, 130, 220),
    "TINGGI":  ( 32, 130, 220),
    "BAHAYA":  ( 48,  32, 200),
    "UNKNOWN": (128, 128, 128),
}
```

---

## Task 1: telemetry.py — Tambah Topic MQTT Baru

**Files:**
- Modify: `telemetry.py`
- Create: `tests/test_telemetry_topics.py`

- [ ] **Step 1.1: Buat direktori tests dan tulis test**

Buat file `tests/test_telemetry_topics.py`:

```python
# tests/test_telemetry_topics.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch, call

def _make_telemetry():
    """Buat Telemetry instance dengan MQTT client yang di-mock."""
    with patch("paho.mqtt.client.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.connect.return_value = None
        mock_client.loop_start.return_value = None

        import importlib
        import telemetry as tel_mod
        importlib.reload(tel_mod)  # reload agar patch diterapkan

        t = tel_mod.Telemetry.__new__(tel_mod.Telemetry)
        t._mqtt = mock_client
        t._influx = None
        t._write_api = None
        t._influx_org = "river-eye"
        t._influx_bucket = "flood-monitoring"
        t._topic_prefix = "river-eye"
        t._interval = 0
        t._last_send = 0
        return t, mock_client

def test_new_topics_published():
    t, mock_client = _make_telemetry()

    payload = {
        "timestamp": "2026-01-01T00:00:00+00:00",
        "height_m": 0.853,
        "height_cm": 85.3,
        "zone": "hijau",
        "level": "AMAN",
        "confidence": 0.78,
    }
    t._publish_mqtt(payload)

    published_topics = [c.args[0] for c in mock_client.publish.call_args_list]
    assert "river-eye/zone" in published_topics, f"river-eye/zone tidak dipublish. Topics: {published_topics}"
    assert "river-eye/confidence" in published_topics, f"river-eye/confidence tidak dipublish. Topics: {published_topics}"

def test_zone_value_correct():
    t, mock_client = _make_telemetry()
    payload = {
        "timestamp": "2026-01-01T00:00:00+00:00",
        "height_m": 0.853, "height_cm": 85.3,
        "zone": "hijau", "level": "AMAN", "confidence": 0.78,
    }
    t._publish_mqtt(payload)
    calls = {c.args[0]: c.args[1] for c in mock_client.publish.call_args_list}
    assert calls.get("river-eye/zone") == "hijau"
    assert calls.get("river-eye/confidence") == "0.78"

if __name__ == "__main__":
    test_new_topics_published()
    test_zone_value_correct()
    print("OK — semua test lulus")
```

- [ ] **Step 1.2: Jalankan test — harus GAGAL dulu**

```
cd C:\Users\aaron\OneDrive\Desktop\PCV\protel
python tests/test_telemetry_topics.py
```

Expected: `AssertionError: river-eye/zone tidak dipublish`

- [ ] **Step 1.3: Update `_publish_mqtt()` di `telemetry.py`**

Cari blok `_publish_mqtt` (sekitar baris 129–141) dan ganti dengan:

```python
def _publish_mqtt(self, payload: dict):
    if not self._mqtt:
        return
    try:
        prefix = self._topic_prefix
        self._mqtt.publish(f"{prefix}/data",       json.dumps(payload),          qos=1, retain=True)
        self._mqtt.publish(f"{prefix}/height_cm",  str(payload["height_cm"]),    qos=0, retain=True)
        self._mqtt.publish(f"{prefix}/height_m",   str(payload["height_m"]),     qos=0, retain=True)
        self._mqtt.publish(f"{prefix}/level",      payload["level"],             qos=1, retain=True)
        self._mqtt.publish(f"{prefix}/zone",       payload["zone"],              qos=0, retain=True)
        self._mqtt.publish(f"{prefix}/confidence", str(payload["confidence"]),   qos=0, retain=True)
    except Exception as e:
        print(f"[TELEMETRY] MQTT publish error: {e}")
```

- [ ] **Step 1.4: Jalankan test — harus LULUS**

```
python tests/test_telemetry_topics.py
```

Expected: `OK — semua test lulus`

- [ ] **Step 1.5: Commit**

```
git add telemetry.py tests/test_telemetry_topics.py
git commit -m "feat: add river-eye/zone and river-eye/confidence mqtt topics"
```

---

## Task 2: protel.py — Rapikan Menu Terminal

**Files:**
- Modify: `protel.py`
- Modify: `requirements.txt`

- [ ] **Step 2.1: Update `requirements.txt`**

Tambah baris di akhir file `requirements.txt`:

```
colorama>=0.4.6
```

- [ ] **Step 2.2: Install colorama**

```
pip install colorama
```

- [ ] **Step 2.3: Tulis ulang `protel.py`**

Ganti seluruh isi `protel.py` dengan:

```python
# -*- coding: utf-8 -*-
"""
RIVER EYE — Sistem Monitoring Ketinggian Air Sungai
Menu utama.
"""

import sys
import os

try:
    from colorama import init as colorama_init, Fore, Style
    colorama_init()
    _C  = Fore.CYAN
    _W  = Fore.WHITE
    _Y  = Fore.YELLOW
    _G  = Fore.GREEN
    _DIM = Style.DIM
    _R  = Style.RESET_ALL
except ImportError:
    _C = _W = _Y = _G = _DIM = _R = ""


def _line(char="─", width=54):
    return char * width


def _box_top(width=54):
    return "  " + "┌" + _line("─", width) + "┐"


def _box_bot(width=54):
    return "  " + "└" + _line("─", width) + "┘"


def _box_row(text="", width=54):
    pad = width - len(text)
    return "  │ " + text + " " * (pad - 1) + "│"


def pilih_sumber():
    print()
    print("  " + _line("─", 46))
    print(f"  {_C}PILIH SUMBER VIDEO{_R}")
    print("  " + _line("─", 46))
    print(f"  {_DIM}[1]{_R} Webcam bawaan         (index 0)")
    print(f"  {_DIM}[2]{_R} Webcam external        (index 1)")
    print(f"  {_DIM}[3]{_R} IP Camera / CCTV       (URL)")
    print(f"  {_DIM}[4]{_R} File Video             (path)")
    print("  " + _line("─", 46))

    c = input(f"\n  {_Y}Pilihan (1/2/3/4):{_R} ").strip()

    if c == "1":
        return 0
    elif c == "2":
        return 1
    elif c == "3":
        return input(f"  {_Y}URL:{_R} ").strip()
    elif c == "4":
        return input(f"  {_Y}Path file video:{_R} ").strip()
    else:
        print("  Default: webcam 0")
        return 0


def main():
    print()
    print(_box_top(54))
    print(_box_row())
    print(_box_row(f"{_C}  RIVER EYE  v2{_R}  —  Monitoring Ketinggian Air"))
    print(_box_row(f"  OpenCV + HSV Segmentation + Staff Gauge"))
    print(_box_row())
    print(_box_bot(54))
    print()
    print(f"  {_C}MENU UTAMA{_R}")
    print("  " + _line("─", 46))
    print(f"  {_W}[1]  HSV CALIBRATOR{_R}")
    print(f"  {_DIM}     Kalibrasi range warna HSV per zona.{_R}")
    print()
    print(f"  {_W}[2]  WATER LEVEL MONITOR{_R}")
    print(f"  {_DIM}     Deteksi ketinggian air real-time via kamera.{_R}")
    print(f"  {_DIM}     Data dikirim ke MQTT otomatis.{_R}")
    print()
    print(f"  {_W}[3]  FLOOD DETECTION DASHBOARD{_R}")
    print(f"  {_DIM}     Analisis gambar statis dengan dashboard penuh.{_R}")
    print()
    print(f"  {_W}[4]  SIMULASI BANJIR WEBCAM{_R}")
    print(f"  {_DIM}     Simulasi dengan benda biru di depan kamera.{_R}")
    print()
    print(f"  {_W}[5]  KELUAR{_R}")
    print("  " + _line("─", 46))

    choice = input(f"\n  {_Y}Pilihan (1-5):{_R} ").strip()

    if choice == "1":
        print(f"\n  Menjalankan HSV Calibrator...\n")
        from hsv_calibrator import HSVCalibrator
        source = pilih_sumber()
        HSVCalibrator(video_source=source).run()

    elif choice == "2":
        print(f"\n  Menjalankan Water Level Monitor...\n")
        from water_level import WaterLevelDetector
        source = pilih_sumber()
        WaterLevelDetector(video_source=source).run()

    elif choice == "3":
        print(f"\n  Menjalankan Flood Detection Dashboard...\n")
        from flood_detection import FloodDashboard
        source = pilih_sumber()
        FloodDashboard(source=source).run_image("gambar air lebih tinggi.png")

    elif choice == "4":
        print(f"\n  Menjalankan Simulasi Banjir Webcam...\n")
        from flood_simulation import FloodSimulation
        source = pilih_sumber()
        FloodSimulation(source=source).run_webcam()

    elif choice == "5":
        print(f"\n  Sampai jumpa.\n")
        sys.exit(0)

    else:
        print(f"\n  {_DIM}Pilihan tidak valid.{_R}")
        main()


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
```

- [ ] **Step 2.4: Verifikasi visual**

```
python protel.py
```

Expected: menu tampil dengan border box rapi, teks berwarna, tanpa emoji. Tekan 5 untuk keluar.

- [ ] **Step 2.5: Commit**

```
git add protel.py requirements.txt
git commit -m "feat: rewrite protel.py menu with clean box layout and colorama"
```

---

## Task 3: water_level.py — Wave Animation + draw_roi_overlay

**Files:**
- Modify: `water_level.py`

- [ ] **Step 3.1: Tambah `import math` di baris import atas `water_level.py`**

Cari blok import (sekitar baris 1–10) dan tambahkan:

```python
import math
```

- [ ] **Step 3.2: Tambah `self.wave_phase` di `__init__` `WaterLevelDetector`**

Cari baris `self.alert_flash = False` (sekitar baris 335) dan tambahkan setelahnya:

```python
        # Wave animation phase (increment tiap frame)
        self.wave_phase = 0.0
```

- [ ] **Step 3.3: Ganti seluruh method `draw_roi_overlay` dengan versi beranimasi**

Cari method `draw_roi_overlay` (sekitar baris 696–720) dan ganti seluruhnya:

```python
    def draw_roi_overlay(self, frame, y_wl, zone_key):
        """Gambar ROI box dan animasi gelombang air pada frame kamera."""
        if not self.roi:
            return frame

        x1, y1, x2, y2 = self.roi
        level = self.zones[zone_key].get("level", "UNKNOWN")
        lc = LEVEL_COLORS.get(level, (128, 128, 128))
        roi_w = x2 - x1

        # ROI box (lebih redup dari sebelumnya)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (53, 37, 28), 1)
        cv2.putText(frame, "STAFF GAUGE", (x1, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, (53, 37, 28), 1)

        wy_global = y1 + y_wl

        # ── Animasi gelombang sinus ──
        amplitude  = 4
        wavelength = max(60, roi_w // 3)
        xs = np.arange(x1, x2, 2)
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

        # Label "BATAS AIR"
        label_y = int(np.mean(ys))
        cv2.putText(frame, "BATAS AIR", (x2 + 8, label_y + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, lc, 1, cv2.LINE_AA)

        return frame
```

- [ ] **Step 3.4: Verifikasi cepat (tidak perlu kamera nyata)**

```
python -c "
import cv2, numpy as np, math
from water_level import WaterLevelDetector, LEVEL_COLORS
d = WaterLevelDetector.__new__(WaterLevelDetector)
d.roi = [50, 50, 200, 300]
d.zones = {'hijau': {'level':'AMAN'}}
d.wave_phase = 0.0
frame = np.zeros((400, 640, 3), dtype=np.uint8)
result = d.draw_roi_overlay(frame, 100, 'hijau')
print('OK shape:', result.shape)
"
```

Expected: `OK shape: (400, 640, 3)`

- [ ] **Step 3.5: Commit**

```
git add water_level.py
git commit -m "feat: add sine wave water animation to draw_roi_overlay"
```

---

## Task 4: water_level.py — Bangun Ulang draw_dashboard

**Files:**
- Modify: `water_level.py`

- [ ] **Step 4.1: Ganti seluruh method `draw_dashboard` dengan versi baru**

Cari method `draw_dashboard` (sekitar baris 560–694) dan ganti seluruhnya dengan kode berikut. Perhatikan: method ini sekarang mengembalikan canvas 1100×700 terpisah (bukan frame yang dimodifikasi).

```python
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

        # Brand
        cv2.putText(dash, "RIVER EYE", (10, 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, C_BRAND, 1, cv2.LINE_AA)
        cv2.putText(dash, "SISTEM MONITORING KETINGGIAN AIR SUNGAI",
                    (10, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.28, C_DIM, 1, cv2.LINE_AA)
        cv2.line(dash, (108, 0), (108, HDR_H), C_BORDER, 1)

        # Status chips
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

        # MQTT indicator
        mqtt_x = CW - 230
        cv2.line(dash, (mqtt_x, 0), (mqtt_x, HDR_H), C_BORDER, 1)
        mqtt_ok = (self.telemetry is not None and
                   getattr(self.telemetry, "_mqtt", None) is not None)
        dot_c = C_GREEN if mqtt_ok else (48, 32, 200)
        blink_on = int(time.time() * 2) % 2 == 0
        if mqtt_ok and blink_on:
            cv2.circle(dash, (mqtt_x + 12, 21), 4, dot_c, -1)
        else:
            cv2.circle(dash, (mqtt_x + 12, 21), 4, dot_c, 1)
        mqtt_txt = "MQTT TERHUBUNG" if mqtt_ok else "MQTT TERPUTUS"
        cv2.putText(dash, mqtt_txt, (mqtt_x + 22, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.28, dot_c, 1, cv2.LINE_AA)
        cv2.putText(dash, "localhost:1883", (mqtt_x + 22, 32),
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
        sp_w = SP_X2 = CAM_X2
        spark = np.full((SPARK_H, sp_w, 3), (8, 5, 5), dtype=np.uint8)
        # Garis referensi zona
        for zk in ["hijau", "kuning", "orange", "merah"]:
            r = self.zones[zk]["tinggi_max_m"] / 4.0
            ly = int(SPARK_H - r * SPARK_H)
            zc = tuple(max(0, c // 6) for c in self.zones[zk].get("warna_bgr", (60, 60, 60)))
            cv2.line(spark, (0, ly), (sp_w, ly), zc, 1)
        # Plot data
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

        # Helper: section label
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
            ("merah",  "BAHAYA",  "> 350 cm", (48, 32, 200)),
            ("orange", "WASPADA", "250-350",  (32, 130, 220)),
            ("kuning", "SIAGA",   "100-250",  (32, 200, 220)),
            ("hijau",  "AMAN",    "0-100 cm", (120, 184, 58)),
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
        ry = sec_label(ry, "POSISI RELATIF  (0 - 400 CM)")
        bx1, bx2 = RP_X1 + 10, CW - 10
        bw2 = bx2 - bx1
        fill_w = int(bw2 * np.clip(height_m / 4.0, 0, 1))
        cv2.rectangle(dash, (bx1, ry + 8), (bx2, ry + 16), (30, 20, 15), -1)
        cv2.rectangle(dash, (bx1, ry + 8), (bx2, ry + 16), C_BORDER, 1)
        if fill_w > 0:
            cv2.rectangle(dash, (bx1, ry + 8), (bx1 + fill_w, ry + 16), accent, -1)
        for lbl, pos in [("0", 0.0), ("100", 0.25), ("250", 0.625), ("350", 0.875), ("400", 1.0)]:
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

        # ── MQTT topics ──
        ry = sec_label(ry, "MQTT DATA TERKIRIM")
        mqtt_topics = [
            ("height_cm",  f"{height_m * 100:.1f}"),
            ("height_m",   f"{height_m:.3f}"),
            ("level",      level),
            ("zone",       zone_key),
            ("confidence", f"{confidence:.2f}"),
        ]
        for tk, tv in mqtt_topics:
            cv2.putText(dash, tk, (RP_X1 + 8, ry + 11),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.26, C_DIM, 1)
            vc = C_GREEN if tv not in ("BAHAYA", "WASPADA") else (48, 32, 200)
            cv2.putText(dash, tv, (CW - 8 - len(tv) * 7, ry + 11),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.28, vc, 1)
            ry += 16
        cv2.putText(dash, "interval: 2s  qos: 1  retain: true",
                    (RP_X1 + 8, ry + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.22, (30, 18, 12), 1)

        # ════════════════════════════════
        # FOOTER
        # ════════════════════════════════
        dash[FTR_Y:] = C_PANEL
        cv2.line(dash, (0, FTR_Y), (CW, FTR_Y), C_BORDER, 1)
        footer_items = [
            ("LOGGING",   "AKTIF"     if self.logging else "NONAKTIF"),
            ("MQTT",      "TERHUBUNG" if mqtt_ok else "TERPUTUS"),
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

```

- [ ] **Step 4.2: Update `run()` — ganti baris imshow dan screenshot agar pakai canvas baru**

Cari baris (sekitar 880–881):
```python
            frame = self.draw_dashboard(frame, height_m, zone_key, confidence)
            cv2.imshow("Water Level Monitor", frame)
```

Ganti dengan:
```python
            dash = self.draw_dashboard(frame, height_m, zone_key, confidence)
            cv2.imshow("Water Level Monitor", dash)
```

Lalu cari blok screenshot di keyboard handler (sekitar baris 926–930):
```python
            elif key == ord('s'):
                os.makedirs(SCREENSHOT_DIR, exist_ok=True)
                fp = os.path.join(SCREENSHOT_DIR, datetime.now().strftime("ss_%Y%m%d_%H%M%S.png"))
                cv2.imwrite(fp, frame)
                print(f"[SCREENSHOT] {fp}")
```

Ganti `frame` dengan `dash` agar screenshot menyimpan canvas penuh:
```python
            elif key == ord('s'):
                os.makedirs(SCREENSHOT_DIR, exist_ok=True)
                fp = os.path.join(SCREENSHOT_DIR, datetime.now().strftime("ss_%Y%m%d_%H%M%S.png"))
                cv2.imwrite(fp, dash)
                print(f"[SCREENSHOT] {fp}")
```

- [ ] **Step 4.3: Update ukuran window di `run()` agar cocok dengan canvas 1100×700**

Cari:
```python
        cv2.resizeWindow("Water Level Monitor", 1100, 700)
```

Sudah benar — tidak perlu diubah.

- [ ] **Step 4.4: Verifikasi smoke test**

```
python -c "
import cv2, numpy as np, math, time
from collections import deque
from water_level import WaterLevelDetector, DEFAULT_ZONES, LEVEL_COLORS

d = WaterLevelDetector.__new__(WaterLevelDetector)
d.zones = DEFAULT_ZONES
d.zone_buf = deque(maxlen=10)
d.sparkline = deque(maxlen=150)
d.wave_phase = 0.0
d.video_source = 0
d.fps = 28
d.logging = False
d.roi = [50, 50, 200, 300]
d.kalibrasi = None
d.telemetry = None

frame = np.zeros((480, 640, 3), dtype=np.uint8)
dash = d.draw_dashboard(frame, 0.85, 'hijau', 0.78)
print('OK canvas size:', dash.shape)
assert dash.shape == (700, 1100, 3), f'Shape salah: {dash.shape}'
print('PASS')
"
```

Expected: `OK canvas size: (700, 1100, 3)` dan `PASS`

- [ ] **Step 4.5: Commit**

```
git add water_level.py
git commit -m "feat: rebuild draw_dashboard with 1100x700 canvas, zone table, mqtt panel"
```

---

## Task 5: flood_detection.py — Gaya + Telemetry

**Files:**
- Modify: `flood_detection.py`

- [ ] **Step 5.1: Tambah `import math` di baris import `flood_detection.py`**

Cari blok import (baris 1–6) dan tambahkan:

```python
import math
```

- [ ] **Step 5.2: Tambah `wave_phase` dan `telemetry` di `__init__` FloodDashboard**

Cari bagian akhir `__init__` (sekitar baris 103), tepat sebelum `except: pass`, tambahkan setelah blok try/except selesai:

```python
        # Wave animation
        self.wave_phase = 0.0

        # Telemetry (MQTT) — optional
        try:
            from telemetry import Telemetry
            self.telemetry = Telemetry()
        except Exception as e:
            print(f"[TELEMETRY] Tidak dimuat: {e}")
            self.telemetry = None
```

- [ ] **Step 5.3: Ganti seluruh method `create_dashboard` dengan versi baru**

Cari method `create_dashboard` (sekitar baris 250–425) dan ganti seluruhnya:

```python
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

        # MQTT indicator di header
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
        scale = min(cam_w / fw, cam_h / fh)
        nw, nh = int(fw * scale), int(fh * scale)
        ox = (cam_w - nw) // 2
        oy = CAM_Y1 + (cam_h - nh) // 2
        dash[oy:oy + nh, ox:ox + nw] = cv2.resize(frame_bg, (nw, nh))

        # Animasi gelombang di atas kamera
        g_y_wl = int(roi_offset[1] + y_wl)
        scaled_y = int(g_y_wl * scale)
        wave_y = oy + scaled_y
        if CAM_Y1 < wave_y < CAM_Y2:
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
            ("1. GRAYSCALE",        p_gray),
            ("2. THRESHOLD",        p_thresh),
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
        # Tentukan zone aktif dari cm_val
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
            ("height_m",   f"{cm_val/100.0:.3f}"),
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

        # Update wave phase
        self.wave_phase = (self.wave_phase + 0.08) % (2 * math.pi)

        return dash
```

- [ ] **Step 5.4: Ganti `run_image()` dengan versi loop + telemetry**

Cari method `run_image` (sekitar baris 427–445) dan ganti seluruhnya:

```python
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
```

- [ ] **Step 5.5: Verifikasi smoke test flood_detection**

```
python -c "
import cv2, numpy as np, math, time
from flood_detection import FloodDashboard, ZONA_ORDER

d = FloodDashboard.__new__(FloodDashboard)
from flood_detection import load_zones
d.zones = load_zones()
d.roi = None
d.kalibrasi_geometri = {}
d.M = None
d.wave_phase = 0.0
d.start_time = time.time()
d.telemetry = None

frame = np.zeros((480, 640, 3), dtype=np.uint8)
import numpy as np
p_img = np.zeros((480, 200, 3), dtype=np.uint8)
results = (frame, (0,0), 85.0, 'AMAN', 100, 1.2, p_img, p_img, p_img, p_img)
dash = d.create_dashboard(frame, results)
print('OK shape:', dash.shape)
assert dash.shape == (720, 1280, 3)
print('PASS')
"
```

Expected: `OK shape: (720, 1280, 3)` dan `PASS`

- [ ] **Step 5.6: Commit**

```
git add flood_detection.py
git commit -m "feat: redesign flood dashboard, add wave animation and mqtt telemetry"
```

---

## Task 6: Final Verification & Commit

**Files:** semua

- [ ] **Step 6.1: Jalankan semua test**

```
python tests/test_telemetry_topics.py
```

Expected: `OK — semua test lulus`

- [ ] **Step 6.2: Jalankan protel.py dan verifikasi menu**

```
python protel.py
```

Expected: menu tampil rapi dengan border box, warna, tanpa emoji. Tekan 5 untuk keluar.

- [ ] **Step 6.3: Commit final**

```
git add requirements.txt
git commit -m "chore: finalize requirements and river eye redesign complete"
```
