# ESP32 relay firmware

Firmware điều khiển bốn relay qua MQTT. Camera, microphone, nhận diện cháy và
Gemini tiếp tục chạy trên laptop; ESP32 chỉ nhận lệnh và điều khiển GPIO.

## Phần cứng mặc định

| Thiết bị | MQTT id | GPIO |
| --- | --- | ---: |
| Phòng khách | `living-room` | 16 |
| Phòng ngủ | `bedroom` | 17 |
| Nhà bếp | `kitchen` | 18 |
| Ban công | `balcony` | 19 |

Firmware mặc định cho relay active-LOW. Khi khởi động, cả bốn kênh được đưa về
trạng thái tắt trước khi kết nối mạng.

## Cấu hình và nạp code

1. Cài VS Code và extension PlatformIO IDE.
2. Mở thư mục `esp32-firmware` bằng PlatformIO.
3. Sửa `include/config.h` với Wi-Fi và địa chỉ IPv4 LAN của laptop.
4. Kết nối ESP32 bằng USB.
5. Chạy **PlatformIO: Upload**.
6. Mở Serial Monitor ở `115200` baud.

Trước khi bật ESP32, khởi động MQTT broker ở thư mục gốc của project:

```powershell
docker compose up -d mqtt
```

Không đặt `MQTT_HOST` thành `localhost` hoặc `127.0.0.1`; từ ESP32, hai địa chỉ
đó trỏ tới chính ESP32. Laptop và ESP32 phải ở cùng mạng và cổng MQTT `1883`
phải được firewall cho phép.

## MQTT protocol

Lệnh cho từng relay:

```text
smarthome/lights/living-room/set
smarthome/lights/bedroom/set
smarthome/lights/kitchen/set
smarthome/lights/balcony/set
```

Payload hợp lệ: `ON`, `OFF`, `1`, `0`, `true`, `false`, `{"on":true}` hoặc
`{"on":false}`. Backend không nên publish lệnh với cờ retained.

ESP32 phản hồi trạng thái retained trên:

```text
smarthome/lights/<id>/state
```

Ví dụ:

```json
{"device_id":"esp32-main","id":"living-room","name":"Phòng khách","on":true,"gpio":16}
```

Các topic bổ sung:

- `smarthome/lights/all/set`: bật hoặc tắt toàn bộ relay.
- `smarthome/esp32/get-state`: publish payload bất kỳ để yêu cầu snapshot.
- `smarthome/esp32/status`: trạng thái online/offline retained; offline được gửi
  bằng MQTT Last Will khi ESP32 mất kết nối bất thường.

## Thử mà chưa gắn relay

Có thể dùng LED nối tiếp điện trở 220-330 ohm để kiểm tra từng GPIO. Vì firmware
mặc định active-LOW, LED mắc từ 3.3 V qua điện trở tới GPIO sẽ sáng khi relay ở
trạng thái ON. Không nối tải điện 220 V trong giai đoạn kiểm thử.
