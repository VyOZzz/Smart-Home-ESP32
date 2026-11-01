# Báo cáo nâng cấp IoT Level 6

## Mục tiêu

Mô hình hiện tại có một node ESP32 + DHT11 độc lập để đo nhiệt độ, độ ẩm, lưu và
trực quan hóa dữ liệu theo thời gian. Hệ thống cũng chuẩn bị đường kết nối MQTT
cloud có TLS. Camera IP vẫn truyền RTSP trong LAN tới MacBook; ESP32 điều khiển
đèn vẫn giữ đúng bốn LED.

## Kiến trúc đã triển khai trong code

```text
ESP32 #1 → 4 LED GPIO 16/17/18/19 active-LOW
     ↕ MQTT set/state acknowledgement
FastAPI ↔ web/Gemini
     ↕ MQTT local hoặc cloud qua TLS
ESP32 #2 → DHT11 DATA GPIO 4
     ↓
nhiệt độ/độ ẩm → kiểm tra hợp lệ → SQLite giới hạn số mẫu → API/WebSocket → biểu đồ

Camera IP → RTSP/LAN → FastAPI/OpenCV → web + cảnh báo loa MacBook
```

## Phần đã code

- Firmware ESP32 đèn hỗ trợ broker LAN và broker cloud TLS, giữ nguyên bốn GPIO,
  active-LOW và cơ chế backend chỉ xác nhận khi nhận topic `/state`.
- Firmware riêng cho ESP32 thứ hai + DHT11: đọc mỗi 5 giây, lọc mẫu lỗi, Last
  Will online/offline, reconnect Wi-Fi/MQTT và yêu cầu đọc tức thời.
- Backend nhận dữ liệu độc lập với phiên Gemini, kiểm tra device ID và dải DHT11,
  phát hiện dữ liệu quá hạn, lưu lịch sử SQLite có giới hạn và phát WebSocket.
- Gemini có tool `get_environment` để đọc dữ liệu mới nhất từ backend.
- Frontend có thẻ nhiệt độ/độ ẩm, online/offline, lỗi, thời gian cập nhật và biểu
  đồ lịch sử.
- Simulator MQTT tạo dữ liệu cảm biến để test toàn bộ hệ thống trước khi mua đồ.
- Cấu hình MQTT username/password/TLS chỉ nằm trong file cục bộ đã được Git bỏ qua.

## Phần cứng đã lắp đặt

1. ESP32 thứ hai đã gắn DHT11: `VCC → 3V3`, `GND → GND`, `DATA → GPIO 4`.
2. Firmware sử dụng device ID `esp32-sensor`, sensor ID `room-1` và topic
   `smarthome/sensors/room-1/state`.

## Phần còn lại cho MQTT cloud

1. Tạo tài khoản/deployment MQTT cloud hỗ trợ TLS và lấy endpoint, port, username,
   password cùng hướng dẫn CA certificate.
2. Điền cấu hình vào `backend/.env` và hai file firmware `include/config.h`.
3. Kiểm tra dữ liệu thật trên web, lịch sử, lệnh hỏi Gemini và tình huống ngắt rồi
   kết nối lại từng ESP32.

Không cần cung cấp mật khẩu cloud, Wi-Fi hay camera cho báo cáo hoặc commit Git.

## Phạm vi kết luận

Code có thể được kiểm thử trước bằng simulator. Việc đạt Level 6 cuối cùng còn
phụ thuộc rubric của giảng viên và bằng chứng demo thật: node cảm biến, broker
cloud, dữ liệu lịch sử, reconnect và giao diện hoạt động cùng nhau. Phát hiện cháy
OpenCV vẫn chỉ là demo giáo dục, không thay thế thiết bị báo cháy được chứng nhận.
