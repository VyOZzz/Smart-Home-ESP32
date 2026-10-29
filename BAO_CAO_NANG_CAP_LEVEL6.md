# Báo cáo chuẩn bị nâng cấp IoT Level 6

## Mục tiêu

Mở rộng mô hình hiện tại bằng một node cảm biến độc lập, lưu và trực quan hóa dữ
liệu theo thời gian, đồng thời chuẩn bị đường kết nối MQTT cloud có TLS. Camera IP
vẫn truyền RTSP trong LAN tới MacBook; ESP32 điều khiển đèn vẫn giữ đúng bốn LED.

## Kiến trúc đã triển khai trong code

```text
ESP32 #1 → 4 LED GPIO 16/17/18/19 active-LOW
     ↕ MQTT set/state acknowledgement
FastAPI ↔ web/Gemini
     ↕ MQTT local hoặc cloud qua TLS
ESP32 #2 → DHT22 DATA GPIO 23
     ↓
nhiệt độ/độ ẩm → kiểm tra hợp lệ → SQLite giới hạn số mẫu → API/WebSocket → biểu đồ

Camera IP → RTSP/LAN → FastAPI/OpenCV → web + cảnh báo loa MacBook
```

## Phần đã code

- Firmware ESP32 đèn hỗ trợ broker LAN và broker cloud TLS, giữ nguyên bốn GPIO,
  active-LOW và cơ chế backend chỉ xác nhận khi nhận topic `/state`.
- Firmware riêng cho ESP32 thứ hai + DHT22: đọc mỗi 10 giây, lọc mẫu lỗi, Last
  Will online/offline, reconnect Wi-Fi/MQTT và yêu cầu đọc tức thời.
- Backend nhận dữ liệu độc lập với phiên Gemini, kiểm tra device ID và dải DHT22,
  phát hiện dữ liệu quá hạn, lưu lịch sử SQLite có giới hạn và phát WebSocket.
- Gemini có tool `get_environment` để đọc dữ liệu mới nhất từ backend.
- Frontend có thẻ nhiệt độ/độ ẩm, online/offline, lỗi, thời gian cập nhật và biểu
  đồ lịch sử.
- Simulator MQTT tạo dữ liệu cảm biến để test toàn bộ hệ thống trước khi mua đồ.
- Cấu hình MQTT username/password/TLS chỉ nằm trong file cục bộ đã được Git bỏ qua.

## Phần cần làm khi có linh kiện và tài khoản cloud

1. Lắp DHT22: `VCC → 3V3`, `GND → GND`, `DATA → GPIO 23` trên ESP32 thứ hai.
2. Tạo tài khoản/deployment MQTT cloud hỗ trợ TLS và lấy endpoint, port, username,
   password cùng hướng dẫn CA certificate.
3. Điền cấu hình vào `backend/.env` và hai file firmware `include/config.h`.
4. Nạp firmware đúng từng board, mở Serial Monitor và xác nhận Wi-Fi/MQTT online.
5. Kiểm tra dữ liệu thật trên web, lịch sử, lệnh hỏi Gemini và tình huống ngắt rồi
   kết nối lại từng ESP32.

Không cần cung cấp mật khẩu cloud, Wi-Fi hay camera cho báo cáo hoặc commit Git.

## Phạm vi kết luận

Code có thể được kiểm thử trước bằng simulator. Việc đạt Level 6 cuối cùng còn
phụ thuộc rubric của giảng viên và bằng chứng demo thật: node cảm biến, broker
cloud, dữ liệu lịch sử, reconnect và giao diện hoạt động cùng nhau. Phát hiện cháy
OpenCV vẫn chỉ là demo giáo dục, không thay thế thiết bị báo cháy được chứng nhận.
