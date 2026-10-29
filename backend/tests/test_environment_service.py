"""Environment MQTT ingestion, validation, staleness, TLS and history tests."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.environment_service import EnvironmentService


class EnvironmentServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.client_patch = patch("app.services.environment_service.mqtt.Client")
        client_factory = self.client_patch.start()
        self.client = client_factory.return_value
        self.service = EnvironmentService(
            host="localhost",
            port=1883,
            client_id="environment-test",
            device_id="esp32-sensor",
            sensor_id="room-1",
            history_db=Path(self.temp_dir.name) / "history.db",
            history_max_rows=2,
            stale_after_seconds=10,
        )
        self.service._on_connect(self.client, None, None, 0, None)

    def tearDown(self) -> None:
        self.client_patch.stop()
        self.temp_dir.cleanup()

    def message(self, topic: str, payload: object, *, retain: bool = False) -> None:
        self.service._on_message(
            None,
            None,
            SimpleNamespace(
                topic=topic,
                payload=json.dumps(payload).encode("utf-8"),
                retain=retain,
            ),
        )

    def reading(self, temperature: float = 26.5, humidity: float = 61.0) -> None:
        self.message(
            self.service.state_topic,
            {
                "device_id": "esp32-sensor",
                "sensor_id": "room-1",
                "name": "Phòng 1",
                "temperature": temperature,
                "humidity": humidity,
                "temperature_unit": "C",
            },
        )

    def test_valid_reading_updates_current_state_and_history(self) -> None:
        self.reading()
        current = self.service.current()
        self.assertTrue(current["online"])
        self.assertEqual(current["temperature_c"], 26.5)
        self.assertEqual(current["humidity_percent"], 61.0)
        self.assertIsNone(current["last_error"])
        self.assertTrue(current["observed_at"].endswith("Z"))
        self.assertEqual(len(self.service.history()), 1)

    def test_invalid_and_out_of_range_payloads_are_rejected(self) -> None:
        invalid_payloads = [
            {"temperature": "hot", "humidity": 50},
            {"temperature": 81, "humidity": 50},
            {"temperature": 20, "humidity": 101},
            {"device_id": "wrong", "temperature": 20, "humidity": 50},
            {"sensor_id": "wrong", "temperature": 20, "humidity": 50},
            {"temperature": 20, "humidity": 50, "temperature_unit": "F"},
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                self.message(self.service.state_topic, payload)
        self.assertIsNone(self.service.current()["temperature_c"])
        self.assertEqual(self.service.history(), [])
        self.assertIsNotNone(self.service.current()["last_error"])

    def test_stale_offline_and_retained_online_do_not_claim_liveness(self) -> None:
        with patch("app.services.environment_service.time.monotonic", return_value=100.0):
            self.reading()
        with patch("app.services.environment_service.time.monotonic", return_value=111.0):
            current = self.service.current()
        self.assertFalse(current["online"])
        self.assertIn("quá hạn", current["last_error"])

        self.message(
            self.service.status_topic,
            {"device_id": "esp32-sensor", "online": True},
            retain=True,
        )
        self.assertFalse(self.service.current()["online"])
        self.message(
            self.service.status_topic,
            {"device_id": "esp32-sensor", "online": False},
        )
        self.assertIn("offline", self.service.current()["last_error"])

    def test_disconnect_and_reconnect_resubscribe_without_losing_reading(self) -> None:
        self.reading()
        self.service._on_disconnect(None, None, None, 1, None)
        self.assertFalse(self.service.current()["online"])
        self.assertIn("MQTT", self.service.current()["last_error"])
        self.service._on_connect(self.client, None, None, 0, None)
        self.assertEqual(self.client.subscribe.call_count, 4)
        self.assertEqual(self.service.current()["temperature_c"], 26.5)

    def test_history_is_bounded_and_returned_oldest_to_newest(self) -> None:
        self.reading(20, 50)
        self.reading(21, 51)
        self.reading(22, 52)
        history = self.service.history(limit=100)
        self.assertEqual([item["temperature_c"] for item in history], [21.0, 22.0])

    def test_tls_configuration_uses_certificate_verification(self) -> None:
        with patch("app.services.environment_service.mqtt.Client") as factory:
            EnvironmentService(
                host="example.emqxsl.com",
                port=8883,
                client_id="tls-test",
                device_id="esp32-sensor",
                sensor_id="room-1",
                history_db=Path(self.temp_dir.name) / "tls.db",
                tls_enabled=True,
                tls_ca_cert="ca.pem",
            )
        client = factory.return_value
        tls_kwargs = client.tls_set.call_args.kwargs
        self.assertEqual(tls_kwargs["ca_certs"], "ca.pem")
        client.tls_insecure_set.assert_called_once_with(False)


if __name__ == "__main__":
    unittest.main()
