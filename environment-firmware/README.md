# ESP32 DevKit + DHT22

Firmware cho ESP32 thứ hai đọc nhiệt độ/độ ẩm từ module DHT22 và gửi dữ liệu
độc lập qua MQTT. Board điều khiển bốn LED vẫn dùng firmware trong
`esp32-firmware/`.

## Phần cứng

Khuyến nghị dùng module DHT22 3 chân có sẵn điện trở kéo lên:

| DHT22 | ESP32 DevKit |
| --- | --- |
| `VCC` | `3V3` |
| `GND` | `GND` |
| `DATA` | `GPIO 23` |

Thứ tự chân có thể khác giữa các module; luôn đọc nhãn in trên module trước khi
cấp nguồn. Có thể đổi chân DATA bằng `DHT_DATA_PIN` trong `include/config.h`.

## Cấu hình và nạp firmware

1. Sao chép `include/config.example.h` thành `include/config.h`.
2. Điền Wi-Fi và MQTT. Với cloud, dùng endpoint, cổng TLS (thường `8883`),
   username/password và CA certificate do nhà cung cấp cấp.
3. Chạy `pio run -e esp32dev` để build.
4. Cắm đúng ESP32 thứ hai rồi chạy `pio run -e esp32dev -t upload`.
5. Theo dõi bằng `pio device monitor -b 115200`.

Không commit `include/config.h`. Không bật `MQTT_TLS_ALLOW_INSECURE` trong bản
demo cloud chính thức. Firmware tự đồng bộ giờ qua NTP trước khi mở kết nối TLS.

## MQTT protocol

- Dữ liệu giữ lại mới nhất:
  `smarthome/environment/esp32-environment/state`
- Trạng thái online/offline giữ lại:
  `smarthome/environment/esp32-environment/status`
- Yêu cầu đọc và gửi ngay:
  `smarthome/environment/esp32-environment/get-state`

Payload dữ liệu:

```json
{
  "device_id": "esp32-environment",
  "temperature_c": 27.4,
  "humidity_percent": 68.1
}
```

Payload trạng thái:

```json
{"device_id":"esp32-environment","online":true}
```

Firmware mặc định đọc mỗi 10 giây, tự kết nối lại Wi-Fi/MQTT và không publish
khi DHT22 trả về `NaN` hoặc giá trị ngoài dải đo hợp lệ.

