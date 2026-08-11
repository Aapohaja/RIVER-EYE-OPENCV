<div align="center">

# River Eye

**Real-time water level monitoring for flood-prone canals in Surabaya.**

An OpenCV-based system that reads water levels from a graduated pole using a live IP camera feed, then pushes the readings to a backend API so downstream apps can generate flood alerts and suggest safe routes.

Currently deployed at **Rumah Pintu Air Kalibokor, Keputih, Surabaya**.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8?logo=opencv&logoColor=white)
![Raspberry Pi](https://img.shields.io/badge/Raspberry_Pi-A22846?logo=raspberrypi&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-A855F7)

</div>

---

## What it does

An IP camera points at a graduated water-level pole inside a flood canal. Every 2 seconds, this program:

1. Grabs the latest frame from the camera stream.
2. Runs a 7-stage vision pipeline to detect where the water surface meets the pole.
3. Converts the detected pixel row into centimeters using a 3-point calibration.
4. Sends the result to a backend server via HTTP POST.

The server drives a live dashboard and feeds a mobile app that suggests flood-free routes to residents.

---

## Quick start

```bash
git clone https://github.com/Aapohaja/RIVER-EYE-OPENCV.git
cd RIVER-EYE-OPENCV
pip install -r requirements.txt
python main.py
```

You will need:

- Python 3.9+
- A reachable IP camera exposing an MJPEG stream (Raspberry Pi or Windows PC works fine)
- A backend endpoint that accepts `POST /logs` with JSON payload
- Calibration values for your specific pole (see `config.py`)

---

## Pipeline

The detection pipeline runs on every frame that clears the freshness check:

```
IP Camera (MJPEG stream)
        │
        ▼
[1] ThreadedCapture
    Background thread that always holds the latest frame,
    so the pipeline never blocks on I/O.
        │
        ▼
[2] Preprocessing
    Rotate frame + crop with homography to align the pole vertically.
        │
        ▼
[3] Crop ROI
    Cut out the polygonal region containing only the graduated pole.
        │
        ▼
[4] Board Mask
    Convert BGR → HSV.
    Keep pixels where V is bright and S < 100 (the white pole).
    Clean up with morphological CLOSE + OPEN.
        │
        ▼
[5] Column Scan
    Split the ROI into 80 vertical columns.
    Scan bottom to top in each column, find the dark→bright transition.
    Take the MEDIAN row across all columns as the initial water line.
        │
        ▼
[6] Laplacian Refinement
    Within ±20 px of the initial line, pick the row with the
    sharpest edge (highest Laplacian response) as the final water line.
        │
        ▼
[7] Kalman Filter 1D
    Smooth the estimate against jitter across consecutive frames.
        │
        ▼
   Confidence > 0.20?
   ┌──────────┴──────────┐
   │ Yes                 │ No
   ▼                     ▼
Convert to cm        Frame skipped
(3-point linear
 calibration at
 50 / 100 / 250 cm)
   │
   ▼
HTTP POST JSON to /logs
{ "location_id": "...", "water_level_cm": 114.8 }
   │
   ▼
Backend Server
```

Every stage exists because the naive version failed at least once in the field. The Kalman filter, for example, was added after seeing frame-to-frame jitter caused by ripples. The Laplacian refinement was added because Otsu alone kept picking the wrong row when floating debris passed through.

---

## Configuration

Key values live in `config.py`:

- `STREAM_URL` — the MJPEG endpoint of your IP camera
- `ROI_POLYGON` — 4 points defining the graduated pole area in the frame
- `CALIBRATION_POINTS` — 3 known `(pixel_row, cm)` pairs used for linear interpolation
- `API_ENDPOINT` — the backend URL that receives water level readings
- `POST_INTERVAL_SEC` — how often to send readings (default 2s)

Run the interactive calibrator once per site setup:

```bash
python calibrate.py
```

It walks you through picking the ROI polygon and marking the 50 / 100 / 250 cm reference marks visually.

---

## Tech stack

- **Python 3.9+** — everything runs here
- **OpenCV** — frame processing, HSV masking, Otsu threshold, Laplacian, morphology
- **NumPy** — column scan and Kalman math
- **requests** — POST readings to the backend
- **Raspberry Pi 4** — deployment target at the site

---

## Deployment

Currently running on a Raspberry Pi 4 mounted at Rumah Pintu Air Kalibokor, Keputih, Surabaya. The Pi is enclosed in a custom 3D-printed weather-resistant case designed in Fusion 360, alongside a wall-mount bracket for the IP camera.

The Pi runs this program as a `systemd` service so it restarts automatically after power loss.

---

## Why this project

Kalibokor sits in one of the flood-prone corridors of Keputih. During heavy rain, residents lose visibility on how fast the canal is rising until the water is already on the street. River Eye gives them a live number and a routing app that says "avoid this road, take that one" instead of leaving them to guess.

The vision side is deliberately classical (Otsu, Laplacian, Kalman) rather than deep learning. A trained YOLO model would need thousands of labeled water-line photos across every lighting condition. Classical CV with careful calibration hit the same accuracy in a fraction of the compute — which matters when the whole system runs on a Raspberry Pi under an outdoor enclosure.

---

## Author

**Aaron Smeraldo Olivier Manik**
Computer Engineering, ITS Surabaya

[GitHub](https://github.com/Aapohaja) · [LinkedIn](https://linkedin.com/in/aaron-manik)
