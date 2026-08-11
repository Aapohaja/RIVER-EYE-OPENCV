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
