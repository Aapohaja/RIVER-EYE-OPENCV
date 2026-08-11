# -*- coding: utf-8 -*-
"""
River Eye — Telemetry Module
Sends water level data to server via HTTP POST (JSON).
"""

import json
import time
import os
from datetime import datetime, timezone

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config/telemetry_config.json")

_DEFAULT_CONFIG = {
    "endpoint":    "http://100.71.62.6:3000/api/logs",
    "api_key":     "qwertyui",
    "location_id": 1,
    "interval_seconds": 10
}


def _load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return _DEFAULT_CONFIG


class Telemetry:
    def __init__(self):
        cfg = _load_config()
        self._endpoint    = cfg.get("endpoint",    _DEFAULT_CONFIG["endpoint"])
        self._api_key     = cfg.get("api_key",     _DEFAULT_CONFIG["api_key"])
        self._location_id = cfg.get("location_id", _DEFAULT_CONFIG["location_id"])
        self._interval    = cfg.get("interval_seconds", 2)
        self._last_send   = 0
        self._connected   = False

        try:
            import requests
            self._requests  = requests
            self._connected = True
            print(f"[TELEMETRY] HTTP POST ke: {self._endpoint}")
        except ImportError:
            self._requests = None
            print("[TELEMETRY] requests tidak tersedia — jalankan: pip install requests")

    def send(self, height_m: float, zone_key: str, level: str, confidence: float):
        now = time.time()
        if now - self._last_send < self._interval:
            return
        self._last_send = now

        payload = {
            "location_id":    self._location_id,
            "water_level_cm": round(height_m * 100.0, 1),
        }

        self._post(payload)

    def _post(self, payload: dict):
        if not self._requests:
            return
        try:
            r = self._requests.post(
                self._endpoint,
                json=payload,
                timeout=5,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key":    self._api_key,
                }
            )
            print(f"[TELEMETRY] Terkirim → {r.status_code}")
        except Exception as e:
            print(f"[TELEMETRY] Gagal kirim: {e}")

    def close(self):
        pass
