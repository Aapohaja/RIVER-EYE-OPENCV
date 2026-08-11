# -*- coding: utf-8 -*-
"""
RIVER EYE — Sistem Monitoring Ketinggian Air Sungai
Menu utama.
"""

import sys
import os
import re

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from colorama import init as colorama_init, Fore, Style
    colorama_init()
    _C  = Fore.CYAN
    _W  = Fore.WHITE
    _Y  = Fore.YELLOW
    _DIM = Style.DIM
    _R  = Style.RESET_ALL
except ImportError:
    _C = _W = _Y = _DIM = _R = ""


def _line(char="─", width=54):
    return char * width


def _box_top(width=54):
    return "  " + "┌" + _line("─", width) + "┐"


def _box_bot(width=54):
    return "  " + "└" + _line("─", width) + "┘"


def _box_row(text="", width=54):
    # Calculate visual length, ignoring ANSI codes
    visual_len = len(re.sub(r'\x1b\[[0-9;]*m', '', text))
    pad = width - visual_len
    return "  │ " + text + " " * max(0, pad - 1) + "│"


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
        FloodDashboard(source=source).run_image("samples/gambar air lebih tinggi.png")

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
