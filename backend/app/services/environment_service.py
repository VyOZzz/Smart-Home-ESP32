"""MQTT ingestion and bounded local history for the independent DHT11 node."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import sqlite3
import ssl
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import paho.mqtt.client as mqtt

from app.core.config import settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EnvironmentReading:
    device_id: str
    temperature_c: float
    humidity_percent: float
    observed_at: str

    def as_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "temperature_c": self.temperature_c,
            "humidity_percent": self.humidity_percent,
            "observed_at": self.observed_at,
        }


class EnvironmentService:
    """Track one environment node without coupling it to lights or Gemini."""

    SENSOR_TOPIC_PREFIX = "smarthome/sensors/"
    MIN_TEMPERATURE_C = -40.0
    MAX_TEMPERATURE_C = 80.0
    MIN_HUMIDITY_PERCENT = 0.0
    MAX_HUMIDITY_PERCENT = 100.0

    def __init__(
        self,
        *,
        host: str,
        port: int,
        client_id: str,
        device_id: str,
        sensor_id: str,
        history_db: Path,
        history_max_rows: int = 10_000,
        stale_after_seconds: float = 30.0,
        username: Optional[str] = None,
        password: Optional[str] = None,
        tls_enabled: bool = False,
        tls_ca_cert: Optional[str] = None,
        tls_certfile: Optional[str] = None,
        tls_keyfile: Optional[str] = None,
        tls_insecure: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.device_id = device_id
        self.sensor_id = sensor_id
        self.history_db = Path(history_db)
        self.history_max_rows = max(1, history_max_rows)
        self.stale_after_seconds = max(1.0, stale_after_seconds)
        self._state_lock = threading.RLock()
        self._db_lock = threading.Lock()
        self._listener_lock = threading.Lock()
        self._listeners: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue[dict]]] = []
        self._latest: Optional[EnvironmentReading] = None
        self._last_seen_monotonic: Optional[float] = None
        self._broker_connected = False
        self._device_online = False
        self._last_error: Optional[str] = "Chưa nhận được dữ liệu cảm biến"
        self._started = False
        self._db_initialized = False

        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            protocol=mqtt.MQTTv311,
        )
        if username:
            self._client.username_pw_set(username, password)
        if tls_enabled:
            self._client.tls_set(
                ca_certs=tls_ca_cert,
                certfile=tls_certfile,
                keyfile=tls_keyfile,
                tls_version=ssl.PROTOCOL_TLS_CLIENT,
            )
            self._client.tls_insecure_set(tls_insecure)
        self._client.reconnect_delay_set(min_delay=1, max_delay=15)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    @property
    def state_topic(self) -> str:
        return f"{self.SENSOR_TOPIC_PREFIX}{self.sensor_id}/state"

    @property
    def status_topic(self) -> str:
        return f"smarthome/{self.device_id}/status"

    @property
    def request_topic(self) -> str:
        return f"{self.SENSOR_TOPIC_PREFIX}{self.sensor_id}/get-state"

    def start(self) -> None:
        if self._started:
            return
        self._ensure_database()
        self._started = True
        logger.info("Connecting environment MQTT subscriber to %s:%s", self.host, self.port)
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
            self._mark_broker_disconnected()

    def current(self) -> dict:
        with self._state_lock:
            latest = self._latest
            online = self._device_online and self._broker_connected
            last_error = self._last_error
            if online and self._is_stale_locked():
                online = False
                last_error = "Dữ liệu cảm biến đã quá hạn"
            return {
                "device_id": self.device_id,
                "online": online,
                "temperature_c": latest.temperature_c if latest else None,
                "humidity_percent": latest.humidity_percent if latest else None,
                "observed_at": latest.observed_at if latest else None,
                "last_error": last_error if not online else None,
            }

    def history(self, limit: int = 100) -> list[dict]:
        self._ensure_database()
        safe_limit = max(1, min(int(limit), 1000))
        with self._db_lock, sqlite3.connect(self.history_db) as connection:
            rows = connection.execute(
                """
                SELECT temperature_c, humidity_percent, observed_at
                FROM environment_readings
                ORDER BY id DESC LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [
            {
                "temperature_c": row[0],
                "humidity_percent": row[1],
                "observed_at": row[2],
            }
            for row in reversed(rows)
        ]

    async def add_listener(self) -> asyncio.Queue[dict]:
        queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=20)
        loop = asyncio.get_running_loop()
        with self._listener_lock:
            self._listeners.append((loop, queue))
        await queue.put({"type": "environment", **self.current()})
        return queue

    def remove_listener(self, queue: asyncio.Queue[dict]) -> None:
        with self._listener_lock:
            self._listeners = [item for item in self._listeners if item[1] is not queue]

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        del userdata, flags, properties
        if reason_code != 0:
            logger.error("Environment MQTT connection rejected: %s", reason_code)
            self._mark_broker_disconnected()
            return
        with self._state_lock:
            self._broker_connected = True
            if self._latest is None:
                self._last_error = "Đang chờ dữ liệu cảm biến"
        client.subscribe(self.state_topic, qos=1)
        client.subscribe(self.status_topic, qos=1)
        client.publish(self.request_topic, "sync", qos=1, retain=False)
        self._broadcast_current()

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties) -> None:
        del client, userdata, disconnect_flags, properties
        if reason_code != 0:
            logger.warning("Environment MQTT disconnected unexpectedly: %s", reason_code)
        self._mark_broker_disconnected()

    def _on_message(self, client, userdata, message) -> None:
        del client, userdata
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._reject("Dữ liệu cảm biến không phải JSON hợp lệ")
            return

        if message.topic == self.status_topic:
            self._handle_status(payload, retained=getattr(message, "retain", False))
        elif message.topic == self.state_topic:
            self._handle_reading(payload, retained=getattr(message, "retain", False))

    def _handle_status(self, payload: object, *, retained: bool = False) -> None:
        if not isinstance(payload, dict) or not isinstance(payload.get("online"), bool):
            self._reject("Trạng thái cảm biến không hợp lệ")
            return
        if payload.get("device_id", self.device_id) != self.device_id:
            self._reject("Device ID cảm biến không khớp")
            return
        online = payload["online"]
        # Retained online is historical and cannot prove current liveness.
        if retained and online:
            return
        with self._state_lock:
            self._device_online = online
            if not online:
                self._last_error = "ESP32 cảm biến đang offline"
        self._broadcast_current()

    def _handle_reading(self, payload: object, *, retained: bool = False) -> None:
        # A retained reading must not make a disconnected physical node appear live.
        if retained:
            return
        try:
            reading = self._validate_reading(payload)
        except ValueError as exc:
            self._reject(str(exc))
            return
        with self._state_lock:
            self._latest = reading
            self._last_seen_monotonic = time.monotonic()
            self._device_online = True
            self._last_error = None
        self._store_reading(reading)
        self._broadcast_current()

    def _validate_reading(self, payload: object) -> EnvironmentReading:
        if not isinstance(payload, dict):
            raise ValueError("Dữ liệu cảm biến phải là một object")
        if payload.get("device_id", self.device_id) != self.device_id:
            raise ValueError("Device ID cảm biến không khớp")
        if payload.get("sensor_id", self.sensor_id) != self.sensor_id:
            raise ValueError("Sensor ID không khớp")
        if payload.get("temperature_unit", "C") != "C":
            raise ValueError("Đơn vị nhiệt độ không được hỗ trợ")
        temperature = payload.get("temperature")
        humidity = payload.get("humidity")
        if (
            isinstance(temperature, bool)
            or not isinstance(temperature, (int, float))
            or isinstance(humidity, bool)
            or not isinstance(humidity, (int, float))
        ):
            raise ValueError("Nhiệt độ hoặc độ ẩm không phải số")
        temperature = float(temperature)
        humidity = float(humidity)
        if not math.isfinite(temperature) or not math.isfinite(humidity):
            raise ValueError("Nhiệt độ hoặc độ ẩm không hữu hạn")
        if not self.MIN_TEMPERATURE_C <= temperature <= self.MAX_TEMPERATURE_C:
            raise ValueError("Nhiệt độ nằm ngoài dải DHT11")
        if not self.MIN_HUMIDITY_PERCENT <= humidity <= self.MAX_HUMIDITY_PERCENT:
            raise ValueError("Độ ẩm nằm ngoài dải hợp lệ")
        observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return EnvironmentReading(self.device_id, temperature, humidity, observed_at)

    def _is_stale_locked(self) -> bool:
        return (
            self._last_seen_monotonic is None
            or time.monotonic() - self._last_seen_monotonic > self.stale_after_seconds
        )

    def _reject(self, error: str) -> None:
        with self._state_lock:
            self._device_online = False
            self._last_error = error
        logger.warning("Ignoring invalid environment MQTT payload: %s", error)
        self._broadcast_current()

    def _mark_broker_disconnected(self) -> None:
        with self._state_lock:
            self._broker_connected = False
            self._device_online = False
            self._last_error = "MQTT broker đang offline"
        self._broadcast_current()

    def _ensure_database(self) -> None:
        if self._db_initialized:
            return
        with self._db_lock:
            if self._db_initialized:
                return
            self.history_db.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.history_db) as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS environment_readings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        temperature_c REAL NOT NULL,
                        humidity_percent REAL NOT NULL,
                        observed_at TEXT NOT NULL
                    )
                    """
                )
            self._db_initialized = True

    def _store_reading(self, reading: EnvironmentReading) -> None:
        self._ensure_database()
        with self._db_lock, sqlite3.connect(self.history_db) as connection:
            connection.execute(
                """
                INSERT INTO environment_readings
                    (temperature_c, humidity_percent, observed_at)
                VALUES (?, ?, ?)
                """,
                (reading.temperature_c, reading.humidity_percent, reading.observed_at),
            )
            connection.execute(
                """
                DELETE FROM environment_readings
                WHERE id NOT IN (
                    SELECT id FROM environment_readings
                    ORDER BY id DESC LIMIT ?
                )
                """,
                (self.history_max_rows,),
            )

    def _broadcast_current(self) -> None:
        message = {"type": "environment", **self.current()}
        with self._listener_lock:
            listeners = list(self._listeners)
        for loop, queue in listeners:
            try:
                loop.call_soon_threadsafe(self._enqueue_latest, queue, message)
            except RuntimeError:
                self.remove_listener(queue)

    @staticmethod
    def _enqueue_latest(queue: asyncio.Queue[dict], message: dict) -> None:
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        queue.put_nowait(message)


_environment_service: Optional[EnvironmentService] = None


def get_environment_service() -> EnvironmentService:
    global _environment_service
    if _environment_service is None:
        _environment_service = EnvironmentService(
            host=settings.mqtt_host,
            port=settings.mqtt_port,
            client_id=f"{settings.mqtt_client_id}-environment",
            username=settings.mqtt_username,
            password=settings.mqtt_password,
            tls_enabled=settings.mqtt_tls_enabled,
            tls_ca_cert=(str(settings.mqtt_tls_ca_cert) if settings.mqtt_tls_ca_cert else None),
            tls_certfile=(str(settings.mqtt_tls_certfile) if settings.mqtt_tls_certfile else None),
            tls_keyfile=(str(settings.mqtt_tls_keyfile) if settings.mqtt_tls_keyfile else None),
            tls_insecure=settings.mqtt_tls_insecure,
            device_id=settings.environment_device_id,
            sensor_id=settings.environment_sensor_id,
            stale_after_seconds=settings.environment_stale_after_seconds,
            history_db=settings.environment_history_db,
            history_max_rows=settings.environment_history_max_rows,
        )
    return _environment_service


__all__ = ["EnvironmentReading", "EnvironmentService", "get_environment_service"]
