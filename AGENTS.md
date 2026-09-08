# Project context

Use this context when changing code or documentation in this repository.

## Current demo hardware

- The host is a MacBook. It runs Docker Desktop, Mosquitto, FastAPI, the web
  frontend and Gemini integration.
- The MacBook's built-in camera, microphone and speakers are used for video,
  voice, music and fire alerts.
- The field device is one `esp32dev` board connected over Wi-Fi/MQTT.
- Four LEDs on a breadboard represent the four room lights. Each LED has its own
  330 Ω resistor and is connected to GPIO 16, 17, 18 or 19.
- Outputs are active-LOW: `ON` means GPIO LOW and `OFF` means GPIO HIGH.
- Do not describe Raspberry Pi, relay boards or mains-powered loads as part of
  the current project.

## Device model

| Location | MQTT ID | GPIO |
| --- | --- | ---: |
| Phòng khách | `living-room` | 16 |
| Phòng ngủ | `bedroom` | 17 |
| Nhà bếp | `kitchen` | 18 |
| Ban công | `balcony` | 19 |

There are exactly four controllable lights. Do not add “Nhà tắm” without an
explicit new requirement.

## Required behavior

- Commands originate from the web/API or a Gemini tool call and are published
  to `smarthome/lights/<id>/set`.
- Backend state changes only after the ESP32 publishes a matching
  `smarthome/lights/<id>/state` acknowledgement.
- Broker/device disconnection, command timeout and reconnect synchronization
  must remain visible to the frontend.
- Fire detection is an educational camera demo. The camera stream currently
  depends on an active Gemini WebSocket session and is not a continuous safety
  monitoring system.
- Never commit `backend/.env` or `esp32-firmware/include/config.h`.
