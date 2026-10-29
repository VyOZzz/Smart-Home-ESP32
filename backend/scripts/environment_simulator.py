#!/usr/bin/env python3
"""Publish DHT11-like MQTT data so the backend can be tested without hardware."""

from __future__ import annotations

import argparse
import json
import math
import os
import signal
import ssl
import sys
import time
from pathlib import Path

import paho.mqtt.client as mqtt
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.getenv("MQTT_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")))
    parser.add_argument(
        "--device-id", default=os.getenv("ENVIRONMENT_DEVICE_ID", "esp32-sensor")
    )
    parser.add_argument(
        "--sensor-id", default=os.getenv("ENVIRONMENT_SENSOR_ID", "room-1")
    )
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--temperature", type=float, default=26.0)
    parser.add_argument("--humidity", type=float, default=60.0)
    args = parser.parse_args()

    state_topic = f"smarthome/sensors/{args.sensor_id}/state"
    status_topic = f"smarthome/{args.device_id}/status"
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"{args.device_id}-simulator",
        protocol=mqtt.MQTTv311,
    )
    username = os.getenv("MQTT_USERNAME")
    if username:
        client.username_pw_set(username, os.getenv("MQTT_PASSWORD"))
    if env_bool("MQTT_TLS_ENABLED"):
        client.tls_set(
            ca_certs=os.getenv("MQTT_TLS_CA_CERT") or None,
            certfile=os.getenv("MQTT_TLS_CERTFILE") or None,
            keyfile=os.getenv("MQTT_TLS_KEYFILE") or None,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
        )
        client.tls_insecure_set(env_bool("MQTT_TLS_INSECURE"))

    offline_payload = json.dumps({"device_id": args.device_id, "online": False})
    client.will_set(status_topic, offline_payload, qos=1, retain=True)
    stopped = False

    def stop(signum, frame) -> None:
        nonlocal stopped
        del signum, frame
        stopped = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    client.connect(args.host, args.port, keepalive=30)
    client.loop_start()
    client.publish(
        status_topic,
        json.dumps({"device_id": args.device_id, "online": True}),
        qos=1,
        retain=True,
    ).wait_for_publish()
    print(f"Environment simulator connected for {args.device_id}", flush=True)
    started_at = time.monotonic()
    try:
        while not stopped:
            elapsed = time.monotonic() - started_at
            payload = {
                "device_id": args.device_id,
                "sensor_id": args.sensor_id,
                "name": "Phòng 1",
                "temperature": round(args.temperature + math.sin(elapsed / 30.0), 2),
                "humidity": round(args.humidity + 2 * math.sin(elapsed / 45.0), 2),
                "temperature_unit": "C",
            }
            client.publish(state_topic, json.dumps(payload), qos=1, retain=True)
            print(
                f"Published {payload['temperature']:.2f} C, "
                f"{payload['humidity']:.2f}% RH",
                flush=True,
            )
            deadline = time.monotonic() + max(0.5, args.interval)
            while not stopped and time.monotonic() < deadline:
                time.sleep(0.1)
    finally:
        if client.is_connected():
            client.publish(status_topic, offline_payload, qos=1, retain=True).wait_for_publish()
        client.disconnect()
        client.loop_stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
