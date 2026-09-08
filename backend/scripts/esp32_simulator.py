#!/usr/bin/env python3
"""Small MQTT ESP32 simulator for backend development without hardware."""

from __future__ import annotations

import argparse
import json
import signal
import sys

import paho.mqtt.client as mqtt


LIGHTS = {
    "living-room": ("Phòng khách", 16),
    "bedroom": ("Phòng ngủ", 17),
    "kitchen": ("Nhà bếp", 18),
    "balcony": ("Ban công", 19),
}
states = {light_id: False for light_id in LIGHTS}


def state_topic(light_id: str) -> str:
    return f"smarthome/lights/{light_id}/state"


def publish_state(client: mqtt.Client, light_id: str) -> None:
    name, gpio = LIGHTS[light_id]
    payload = {
        "device_id": "esp32-main",
        "id": light_id,
        "name": name,
        "on": states[light_id],
        "gpio": gpio,
    }
    client.publish(state_topic(light_id), json.dumps(payload, ensure_ascii=False), qos=1, retain=True)


def on_connect(client, userdata, flags, reason_code, properties) -> None:
    del userdata, flags, properties
    if reason_code != 0:
        print(f"[MQTT] Connection failed: {reason_code}", flush=True)
        return
    print("[MQTT] Connected (ESP32 simulator)", flush=True)
    client.subscribe("smarthome/esp32/get-state", qos=1)
    client.subscribe("smarthome/lights/+/set", qos=1)
    client.publish(
        "smarthome/esp32/status",
        json.dumps({"device_id": "esp32-main", "online": True}),
        qos=1,
        retain=True,
    )
    for light_id in LIGHTS:
        publish_state(client, light_id)


def on_message(client, userdata, message) -> None:
    del userdata
    if message.topic == "smarthome/esp32/get-state":
        for light_id in LIGHTS:
            publish_state(client, light_id)
        return
    parts = message.topic.split("/")
    if len(parts) != 4 or parts[:2] != ["smarthome", "lights"] or parts[3] != "set":
        return
    light_id = parts[2]
    if light_id not in LIGHTS:
        return
    command = message.payload.decode("utf-8").strip().lower()
    if command not in {"on", "off", "1", "0", "true", "false"}:
        return
    states[light_id] = command in {"on", "1", "true"}
    publish_state(client, light_id)
    print(f"[RELAY] {light_id} -> {'ON' if states[light_id] else 'OFF'}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    args = parser.parse_args()

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="esp32-main-simulator",
        protocol=mqtt.MQTTv311,
    )
    client.will_set(
        "smarthome/esp32/status",
        json.dumps({"device_id": "esp32-main", "online": False}),
        qos=1,
        retain=True,
    )
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.host, args.port, keepalive=30)

    def stop(signum, frame) -> None:
        del signum, frame
        client.publish(
            "smarthome/esp32/status",
            json.dumps({"device_id": "esp32-main", "online": False}),
            qos=1,
            retain=True,
        ).wait_for_publish()
        client.disconnect()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    client.loop_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
