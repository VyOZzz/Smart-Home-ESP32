# ESP32 DHT11 sensor firmware

Firmware PlatformIO cho ESP32 DevKit thứ hai và module DHT11 3 chân:

- `VCC/+` → `3V3`
- `DATA/S/OUT` → `D4` / `GPIO4`
- `GND/-` → `GND`

Tạo cấu hình cục bộ và đặt `MQTT_HOST` thành IPv4 LAN của MacBook chạy
Mosquitto. Không dùng `localhost`, `127.0.0.1` hoặc `mqtt`.

```bash
cp include/config.example.h include/config.h
pio run -e esp32dev
pio run -e esp32dev -t upload --upload-port /dev/cu.usbserial-XXXX
pio device monitor --port /dev/cu.usbserial-XXXX --baud 115200
```

`include/config.h` và `.pio/` bị Git bỏ qua. Firmware đọc DHT11 mỗi 5 giây,
tự kết nối lại Wi-Fi/MQTT, giữ retained state/status và đặt Last Will offline.

| Topic | Mục đích |
| --- | --- |
| `smarthome/sensors/room-1/state` | JSON nhiệt độ/độ ẩm retained |
| `smarthome/esp32-sensor/status` | Trạng thái online/offline retained |
| `smarthome/sensors/room-1/get-state` | Yêu cầu gửi mẫu ngay |

Payload state:

```json
{"device_id":"esp32-sensor","sensor_id":"room-1","name":"Phòng 1","temperature":28.0,"humidity":65.0,"temperature_unit":"C"}
```
