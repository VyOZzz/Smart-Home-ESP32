# Phần cứng của project

Project học tập hiện dùng **MacBook + camera IP trong nhà + ESP32 DevKit + bốn LED**.

## Phần cứng cần cho demo

- MacBook chạy Docker, MQTT broker, backend, frontend và Gemini.
- Camera IP giám sát đang treo trong nhà, có luồng RTSP truy cập được trong LAN.
  Cần xác nhận hãng/model và khả năng bật RTSP trước khi chốt cấu hình.
- Microphone và loa tích hợp trên MacBook.
- Một bo ESP32 và cáp USB truyền dữ liệu.
- Một breadboard.
- Bốn LED (có thể chọn bốn màu bất kỳ).
- Bốn điện trở 330 Ω, mỗi LED dùng một điện trở riêng.
- Dây jumper đực-đực.

Camera kết nối LAN/Wi-Fi với MacBook, dùng nguồn riêng theo thiết bị. Không nối
camera vào ESP32 và không dùng camera MacBook. Microphone và loa MacBook vẫn dùng.

## Ánh xạ đèn

| Khu vực | MQTT ID | GPIO |
| --- | --- | ---: |
| Phòng khách | `living-room` | 16 |
| Phòng ngủ | `bedroom` | 17 |
| Nhà bếp | `kitchen` | 18 |
| Ban công | `balcony` | 19 |

Firmware dùng đầu ra active-LOW. Mỗi LED được đấu theo sơ đồ:

```text
3V3 → điện trở 330 Ω → chân dài LED (+) → chân ngắn LED (-) → GPIO
```

Khi nhận lệnh `ON`, GPIO xuống LOW và LED sáng. Khi nhận `OFF`, GPIO lên HIGH
và LED tắt.

Chân dài của LED là cực dương. Chân ngắn hoặc cạnh phẳng trên vỏ LED là cực âm.
Mỗi cụm điện trở và LED phải nằm trên hàng breadboard riêng. Luôn rút cáp USB
trước khi thay đổi dây nối.

## Trình tự lắp

1. Nối chân `3V3` của ESP32 tới thanh nguồn dương trên breadboard.
2. Đấu một điện trở 330 Ω và một LED từ thanh `3V3` tới GPIO 16.
3. Cấp nguồn, thử lệnh `ON/OFF` cho phòng khách rồi rút USB.
4. Lặp lại với GPIO 17, 18 và 19.
5. Cấp nguồn lại và thử lần lượt cả bốn khu vực trên giao diện web.

## Kết nối camera IP

Camera IP → router LAN/Wi-Fi → FastAPI trên MacBook → OpenCV → web và loa MacBook.
Camera dùng Ethernet hoặc Wi-Fi theo model; không chiếm GPIO của ESP32.
Nếu thiết bị hỗ trợ ONVIF, có thể dùng thông tin profile để lấy URI RTSP;
backend hiện đọc RTSP trực tiếp, chưa tự dò thiết bị ONVIF.

## Mở rộng tùy chọn

- Cảm biến nhiệt độ/độ ẩm, chuyển động, khí gas hoặc ánh sáng.

Không đấu điện lưới vào project học tập này.
