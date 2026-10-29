# ESP32 DevKit: điều khiển bốn LED

Firmware chỉ kết nối Wi-Fi/MQTT, điều khiển bốn LED và gửi xác nhận trạng thái.
Camera IP truyền RTSP trực tiếp tới MacBook; không kết nối camera vào ESP32.
Microphone, loa, Gemini và OpenCV chạy trên MacBook.

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
2. Điền Wi-Fi và cấu hình MQTT:
   - Mosquitto trên MacBook: IP LAN, cổng `1883`, `MQTT_USE_TLS 0`.
   - MQTT cloud: endpoint của nhà cung cấp, thường là cổng `8883`,
     `MQTT_USE_TLS 1`, username/password và CA certificate.
3. Cắm ESP32 bằng cáp USB truyền dữ liệu.
4. Chạy PlatformIO Upload.
5. Mở Serial Monitor ở `115200` baud.

Không đặt `MQTT_HOST` thành `localhost`: trên ESP32, địa chỉ đó trỏ về chính
ESP32. MacBook và ESP32 phải ở cùng mạng Wi-Fi.

Khi dùng cloud, firmware xác thực chứng chỉ TLS theo `MQTT_CA_CERT`. Không bật
`MQTT_TLS_ALLOW_INSECURE` trong bản demo chính thức. Các giá trị bí mật chỉ nằm
trong `include/config.h`; file này đã được Git bỏ qua. Firmware tự đồng bộ giờ
qua NTP trước khi mở kết nối TLS, vì vậy mạng phải cho phép truy cập Internet.

## MQTT protocol

- Lệnh: `smarthome/lights/<id>/set` với payload `ON` hoặc `OFF`.
- Trạng thái xác nhận: `smarthome/lights/<id>/state`.
- Yêu cầu đồng bộ: `smarthome/esp32/get-state`.
- Trạng thái kết nối: `smarthome/esp32/status`.
- Điều khiển cả bốn đèn: `smarthome/lights/all/set`.

Topic `/state` xác nhận trạng thái GPIO mà firmware đã đặt. Với mô hình hiện
tại, LED cung cấp phản hồi trực quan cho người dùng.

Không đấu điện lưới vào breadboard hoặc ESP32.

Build: `pio run -e esp32dev`. Không commit `include/config.h`.
