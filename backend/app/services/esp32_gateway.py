"""MQTT gateway between FastAPI and the ESP32 light controller."""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from typing import Callable, Optional

import paho.mqtt.client as mqtt


logger = logging.getLogger(__name__)


class Esp32GatewayError(RuntimeError):
    """Base class for errors safe to surface through the API."""


class DeviceUnavailableError(Esp32GatewayError):
    """The broker or ESP32 is not currently available."""


class DeviceCommandTimeoutError(Esp32GatewayError):
    """The ESP32 did not confirm a command before its deadline."""


@dataclass
class _PendingCommand:
    expected_on: bool
    event: threading.Event
    confirmed_on: Optional[bool] = None


StateHandler = Callable[[str, bool, dict], None]
StatusHandler = Callable[[bool], None]


class Esp32Gateway:
    """Own the MQTT connection and wait for ESP32 state acknowledgements."""

    STATUS_TOPIC = "smarthome/esp32/status"
    GET_STATE_TOPIC = "smarthome/esp32/get-state"
    STATE_PREFIX = "smarthome/lights/"
    STATE_SUFFIX = "/state"

    def __init__(
        self,
        host: str,
        port: int,
        client_id: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        command_timeout: float = 3.0,
        on_state: Optional[StateHandler] = None,
        on_status: Optional[StatusHandler] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.command_timeout = command_timeout
        self.on_state = on_state
        self.on_status = on_status
        self._connected = False
        self._device_online = False
        self._started = False
        self._state_lock = threading.RLock()
        self._command_lock = threading.Lock()
        self._pending: dict[str, _PendingCommand] = {}

        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            protocol=mqtt.MQTTv311,
        )
        if username:
            self._client.username_pw_set(username, password)
        self._client.reconnect_delay_set(min_delay=1, max_delay=15)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    @property
    def connected(self) -> bool:
        with self._state_lock:
            return self._connected

    @property
    def device_online(self) -> bool:
        with self._state_lock:
            return self._device_online

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        logger.info("Connecting MQTT gateway to %s:%s", self.host, self.port)
        self._client.connect_async(self.host, self.port, keepalive=30)
        self._client.loop_start()

    def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        try:
            self._client.disconnect()
        finally:
            self._client.loop_stop()
            self._set_connection_state(False)

    def request_state(self) -> None:
        if self.connected:
            self._client.publish(self.GET_STATE_TOPIC, "sync", qos=1, retain=False)

    def set_light(self, light_id: str, turn_on: bool) -> bool:
        """Publish a command and return only after a matching `/state` message."""

        with self._command_lock:
            if not self.connected or not self.device_online:
                raise DeviceUnavailableError("ESP32 đang offline hoặc MQTT chưa kết nối")

            pending = _PendingCommand(expected_on=turn_on, event=threading.Event())
            with self._state_lock:
                self._pending[light_id] = pending

            topic = f"smarthome/lights/{light_id}/set"
            info = self._client.publish(
                topic,
                "ON" if turn_on else "OFF",
                qos=1,
                retain=False,
            )
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                with self._state_lock:
                    self._pending.pop(light_id, None)
                raise DeviceUnavailableError("Không gửi được lệnh tới MQTT broker")

            acknowledged = pending.event.wait(self.command_timeout)
            with self._state_lock:
                self._pending.pop(light_id, None)
                online = self._connected and self._device_online

            if not acknowledged or pending.confirmed_on is None:
                if not online:
                    raise DeviceUnavailableError("ESP32 mất kết nối khi đang xử lý lệnh")
                raise DeviceCommandTimeoutError(
                    f"ESP32 không xác nhận lệnh trong {self.command_timeout:g} giây"
                )
            return pending.confirmed_on

    def _set_connection_state(self, connected: bool) -> None:
        notify_offline = False
        with self._state_lock:
            self._connected = connected
            if not connected and self._device_online:
                self._device_online = False
                notify_offline = True
            if not connected:
                for pending in self._pending.values():
                    pending.event.set()
        if notify_offline and self.on_status:
            self.on_status(False)

    def _set_device_online(self, online: bool) -> None:
        changed = False
        with self._state_lock:
            if self._device_online != online:
                self._device_online = online
                changed = True
            if not online:
                for pending in self._pending.values():
                    pending.event.set()
        if changed and self.on_status:
            self.on_status(online)

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        del userdata, flags, properties
        if reason_code != 0:
            logger.error("MQTT connection rejected: %s", reason_code)
            self._set_connection_state(False)
            return
        logger.info("MQTT gateway connected")
        self._set_connection_state(True)
        client.subscribe(self.STATUS_TOPIC, qos=1)
        client.subscribe(f"{self.STATE_PREFIX}+{self.STATE_SUFFIX}", qos=1)
        client.publish(self.GET_STATE_TOPIC, "sync", qos=1, retain=False)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties) -> None:
        del client, userdata, disconnect_flags, properties
        if reason_code != 0:
            logger.warning("MQTT gateway disconnected unexpectedly: %s", reason_code)
        self._set_connection_state(False)

    def _on_message(self, client, userdata, message) -> None:
        del client, userdata
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.warning("Ignoring invalid MQTT payload on %s", message.topic)
            return

        if message.topic == self.STATUS_TOPIC:
            if isinstance(payload, dict) and isinstance(payload.get("online"), bool):
                self._set_device_online(payload["online"])
                if payload["online"]:
                    self.request_state()
            return

        if not (
            message.topic.startswith(self.STATE_PREFIX)
            and message.topic.endswith(self.STATE_SUFFIX)
            and isinstance(payload, dict)
            and isinstance(payload.get("on"), bool)
        ):
            return

        light_id = message.topic[
            len(self.STATE_PREFIX) : -len(self.STATE_SUFFIX)
        ]
        payload_id = payload.get("id")
        if payload_id and payload_id != light_id:
            logger.warning("MQTT state id does not match topic: %s", message.topic)
            return

        self._set_device_online(True)
        if self.on_state:
            self.on_state(light_id, payload["on"], payload)

        with self._state_lock:
            pending = self._pending.get(light_id)
            if pending and pending.expected_on == payload["on"]:
                pending.confirmed_on = payload["on"]
                pending.event.set()
