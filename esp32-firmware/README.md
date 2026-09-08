# ESP32 light firmware

Firmware nhận lệnh MQTT và điều khiển bốn LED đại diện cho bốn phòng. Camera,
microphone, loa, Gemini và nhận diện hình ảnh chạy trên MacBook.

## Sơ đồ phần cứng hiện tại

| Đèn | MQTT ID | GPIO |
| --- | --- | ---: |
| Phòng khách | `living-room` | 16 |
| Phòng ngủ | `bedroom` | 17 |
| Nhà bếp | `kitchen` | 18 |
| Ban công | `balcony` | 19 |

Mỗi LED cần một điện trở 330 Ω riêng:

```text
3V3 → điện trở 330 Ω → chân dài LED (+) → chân ngắn LED (-) → GPIO
```

Đầu ra được cấu hình active-LOW: lệnh `ON` đặt GPIO xuống LOW và làm LED sáng.
Khi ESP32 khởi động, bốn LED được đặt về trạng thái tắt.

## Cấu hình và nạp firmware

1. Sao chép `include/config.example.h` thành `include/config.h` nếu file chưa có.
2. Điền Wi-Fi và IPv4 LAN của MacBook đang chạy MQTT broker.
3. Cắm ESP32 bằng cáp USB truyền dữ liệu.
4. Chạy PlatformIO Upload.
5. Mở Serial Monitor ở `115200` baud.

Không đặt `MQTT_HOST` thành `localhost`: trên ESP32, địa chỉ đó trỏ về chính
ESP32. MacBook và ESP32 phải ở cùng mạng Wi-Fi.

## MQTT protocol

- Lệnh: `smarthome/lights/<id>/set` với payload `ON` hoặc `OFF`.
- Trạng thái xác nhận: `smarthome/lights/<id>/state`.
- Yêu cầu đồng bộ: `smarthome/esp32/get-state`.
- Trạng thái kết nối: `smarthome/esp32/status`.
- Điều khiển cả bốn đèn: `smarthome/lights/all/set`.

Topic `/state` xác nhận trạng thái GPIO mà firmware đã đặt. Với mô hình hiện
tại, LED cung cấp phản hồi trực quan cho người dùng.

Không đấu điện lưới vào breadboard hoặc ESP32.
