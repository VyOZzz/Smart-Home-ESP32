"""Commands must wait for device state; never connect a real MQTT broker."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.esp32_gateway import Esp32Gateway, DeviceCommandTimeoutError, DeviceUnavailableError
from app.services.smart_home_service import SmartHomeService


class LightAcknowledgementTests(unittest.TestCase):
    def setUp(self):
        with patch('app.services.esp32_gateway.mqtt.Client'):
            self.gateway = Esp32Gateway('localhost', 1883, 'test', command_timeout=0.01, on_state=Mock())
        self.gateway._connected = self.gateway._device_online = True
        self.gateway._client.publish.return_value = SimpleNamespace(rc=0)

    def ack(self, state, payload_id='living-room'):
        self.gateway._on_message(None, None, SimpleNamespace(
            topic='smarthome/lights/living-room/state',
            payload=json.dumps({'id': payload_id, 'on': state}).encode()))

    def test_publish_without_ack_times_out_and_does_not_update_state(self):
        with self.assertRaises(DeviceCommandTimeoutError):
            self.gateway.set_light('living-room', True)
        self.gateway.on_state.assert_not_called()
        self.gateway._client.publish.assert_called_once_with(
            'smarthome/lights/living-room/set', 'ON', qos=1, retain=False)

    def test_matching_state_ack_completes_command(self):
        def publish(*args, **kwargs):
            self.gateway.on_state.assert_not_called()
            self.ack(True)
            return SimpleNamespace(rc=0)
        self.gateway._client.publish.side_effect = publish
        self.assertTrue(self.gateway.set_light('living-room', True))
        self.gateway.on_state.assert_called_once()

    def test_mismatched_value_does_not_complete_command(self):
        def publish(*args, **kwargs):
            self.ack(False)
            return SimpleNamespace(rc=0)
        self.gateway._client.publish.side_effect = publish
        with self.assertRaises(DeviceCommandTimeoutError):
            self.gateway.set_light('living-room', True)

    def test_wrong_payload_id_does_not_update_state(self):
        self.ack(True, payload_id='bedroom')
        self.gateway.on_state.assert_not_called()

    def test_offline_command_does_not_publish(self):
        self.gateway._device_online = False
        with self.assertRaises(DeviceUnavailableError):
            self.gateway.set_light('living-room', True)
        self.gateway._client.publish.assert_not_called()

    def test_retained_state_does_not_revive_offline_device(self):
        self.gateway._device_online = False
        self.gateway._on_message(None, None, SimpleNamespace(
            topic='smarthome/lights/living-room/state', retain=True,
            payload=b'{"id":"living-room","on":true}'))
        self.assertFalse(self.gateway.device_online)
        self.gateway.on_state.assert_not_called()

    def test_retained_online_requests_fresh_state_before_online(self):
        self.gateway._device_online = False
        self.gateway._on_message(None, None, SimpleNamespace(
            topic='smarthome/esp32/status', retain=True,
            payload=b'{"online":true}'))
        self.assertFalse(self.gateway.device_online)
        self.gateway._client.publish.assert_called_once_with(
            'smarthome/esp32/get-state', 'sync', qos=1, retain=False)
        self.ack(False)
        self.assertTrue(self.gateway.device_online)

    def test_retained_matching_state_cannot_acknowledge_command(self):
        def publish(*args, **kwargs):
            self.gateway._on_message(None, None, SimpleNamespace(
                topic='smarthome/lights/living-room/state', retain=True,
                payload=b'{"id":"living-room","on":true}'))
            return SimpleNamespace(rc=0)
        self.gateway._client.publish.side_effect = publish
        with self.assertRaises(DeviceCommandTimeoutError):
            self.gateway.set_light('living-room', True)
        self.gateway.on_state.assert_not_called()

    def test_combined_room_names_resolve_to_two_supported_lights(self):
        service = SmartHomeService(
            lighting_service=Mock(), music_service=Mock(), esp32_gateway=Mock()
        )
        self.assertEqual(
            service.resolve_light_locations("ban công và nhà bếp"),
            ["Nhà bếp", "Ban công"],
        )

    def test_gateway_can_enable_verified_mqtt_tls(self):
        with patch('app.services.esp32_gateway.mqtt.Client') as factory:
            Esp32Gateway(
                'example.emqxsl.com', 8883, 'tls-test',
                username='device', password='secret',
                tls_enabled=True, tls_ca_cert='ca.pem',
            )
        client = factory.return_value
        client.username_pw_set.assert_called_once_with('device', 'secret')
        self.assertEqual(client.tls_set.call_args.kwargs['ca_certs'], 'ca.pem')
        client.tls_insecure_set.assert_called_once_with(False)
