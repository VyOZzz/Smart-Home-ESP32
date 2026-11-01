# Project context

Use this context when changing code or documentation in this repository.

## Current demo hardware

- The host is a MacBook. It runs Docker Desktop, Mosquitto, FastAPI, the web
  frontend and Gemini integration.
- The MacBook's built-in microphone and speakers are used for voice, music and
  fire alerts. Its built-in camera is not used.
- One ESP32 DevKit (`esp32dev`) controls four LEDs over Wi-Fi/MQTT only.
- A second ESP32 DevKit reads an installed DHT11 module with DATA on GPIO 4.
  Its MQTT device ID is `esp32-sensor` and sensor ID is `room-1`.
- A separate Imou Ranger 2 3MP IP camera (`IPC-A32EP-L`) streams RTSP over
  LAN/Wi-Fi to FastAPI on the MacBook. Camera wiring and acquisition are
  independent of the ESP32. Its LAN address may change through DHCP.
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
- Fire detection is an educational camera demo. FastAPI reads the IP camera via OpenCV VideoCapture
  independently of Gemini sessions, but it is not a continuous safety
  monitoring system and does not replace a certified smoke/heat detector.
- Never commit `backend/.env`, `esp32-firmware/include/config.h` or
  `esp32-sensor-firmware/include/config.h`.

- Configure HOME_CAMERA_RTSP_URL only in backend/.env; never expose its URL or
  credentials in frontend responses or logs. The known camera is an Imou
  Ranger 2 3MP (`IPC-A32EP-L`), so do not ask for its brand/model again. Never
  request the camera password. Do not persist its DHCP address as a fixed
  project fact; discover or confirm the current LAN address when needed. Store
  the current non-secret address in ignored `backend/data/camera_ip.txt`; this
  overrides only the host in HOME_CAMERA_RTSP_URL after a backend restart.
- Camera capture and fire detection must run without a Gemini session.
- Serve JPEG/MJPEG through the backend; browser media access is microphone-only.

## Environment node

- The installed environment node is the ESP32 DevKit + DHT11 in
  `esp32-sensor-firmware/`, with DATA on GPIO 4.
- Readings use `smarthome/sensors/room-1/state`; availability uses
  `smarthome/esp32-sensor/status`.
- FastAPI ingests readings independently of Gemini, validates them, stores a
  bounded SQLite history and exposes current/history/WebSocket APIs. Gemini may
  only read the latest backend state through `get_environment`.
- Both ESP32 firmwares and FastAPI support local MQTT without TLS and cloud MQTT
  with TLS. Never commit cloud credentials, Wi-Fi credentials, CA secrets,
  `backend/.env`, `esp32-firmware/include/config.h` or
  `esp32-sensor-firmware/include/config.h`.
- Do not claim the cloud path has passed a physical test until a cloud account
  has been connected and verified.
