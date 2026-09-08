# Smart Home ESP32

Hệ thống nhà thông minh ứng dụng **ESP32**, **MQTT** và **trí tuệ nhân tạo Gemini**, cho phép người dùng giám sát và điều khiển các thiết bị trong nhà thông qua giao diện web hoặc ứng dụng Android.

ESP32 đóng vai trò là bộ điều khiển thiết bị tại hiện trường: kết nối Wi-Fi, nhận lệnh qua MQTT, điều khiển bốn kênh relay và gửi trạng thái hoạt động về hệ thống theo thời gian thực. Backend FastAPI xử lý nghiệp vụ, kết nối trợ lý AI, quản lý nhạc và làm cầu nối giữa giao diện người dùng với ESP32.

## Tính năng chính

- Bật hoặc tắt đèn độc lập tại phòng khách, phòng ngủ, nhà bếp và ban công.
- Điều khiển đồng thời toàn bộ thiết bị được kết nối với relay.
- Đồng bộ trạng thái thiết bị theo thời gian thực qua MQTT và WebSocket.
- Tương tác với trợ lý Gemini bằng văn bản, giọng nói và hình ảnh.
- Điều khiển thiết bị bằng câu lệnh tự nhiên, chẳng hạn như “Bật đèn phòng khách”.
- Phát, tạm dừng, tiếp tục và tua nhạc từ thư viện trên máy chủ.
- Nhận hình ảnh từ camera để hỗ trợ phát hiện dấu hiệu cháy và phát cảnh báo.
- Sử dụng trên cả trình duyệt web và ứng dụng Android.
- Tự động kết nối lại Wi-Fi và MQTT khi đường truyền bị gián đoạn.
- Khởi động relay ở trạng thái an toàn, tránh thiết bị bật ngoài ý muốn.

## Kiến trúc hệ thống

```text
Web React / Ứng dụng Android
              │
       HTTP + WebSocket
              │
       Backend FastAPI
        ├── Gemini AI
        ├── Xử lý hình ảnh
        ├── Thư viện nhạc
        └── MQTT Client
              │
      Eclipse Mosquitto
              │
          Wi-Fi / MQTT
              │
            ESP32
              │
      Module relay 4 kênh
              │
       Đèn / thiết bị điện
```

## Công nghệ sử dụng

| Thành phần | Công nghệ |
| --- | --- |
| Vi điều khiển | ESP32, Arduino Framework, PlatformIO |
| Giao tiếp IoT | Wi-Fi, MQTT, Eclipse Mosquitto |
| Backend | Python, FastAPI, WebSocket |
| Trí tuệ nhân tạo | Google Gemini Live API |
| Xử lý hình ảnh | OpenCV, NumPy |
| Web frontend | React, TypeScript, Vite, Tailwind CSS |
| Ứng dụng di động | Kotlin, Jetpack Compose, Retrofit, OkHttp |
| Triển khai dịch vụ | Docker, Docker Compose |

## Phần cứng

- Một bo mạch ESP32.
- Module relay 4 kênh 5 V, ưu tiên loại có opto cách ly.
- Nguồn điện phù hợp cho ESP32 và module relay.
- Dây jumper.
- Đèn LED và điện trở 220–330 Ω để kiểm thử, hoặc thiết bị điện phù hợp khi triển khai thực tế.
- Camera, micro và loa nếu sử dụng đầy đủ chức năng hình ảnh, giọng nói và cảnh báo.

### Sơ đồ chân mặc định

| Khu vực | MQTT ID | GPIO |
| --- | --- | ---: |
| Phòng khách | `living-room` | 16 |
| Phòng ngủ | `bedroom` | 17 |
| Nhà bếp | `kitchen` | 18 |
| Ban công | `balcony` | 19 |

Firmware được cấu hình mặc định cho relay **active-LOW**. Có thể thay đổi hằng số `RELAY_ACTIVE_LOW` trong `esp32-firmware/src/main.cpp` nếu module relay sử dụng mức kích hoạt HIGH.

> **Cảnh báo an toàn:** Chỉ nên dùng LED hoặc tải điện áp thấp trong giai đoạn kiểm thử. Không đấu nối điện lưới 220 V nếu chưa có kiến thức chuyên môn, thiết bị cách ly và biện pháp bảo vệ phù hợp.

## Cấu trúc thư mục

```text
Smart-Home-ESP32/
├── android-app/       # Ứng dụng Android bằng Jetpack Compose
├── backend/           # API, WebSocket, Gemini và xử lý nghiệp vụ
├── esp32-firmware/    # Firmware điều khiển relay cho ESP32
├── frontend/          # Giao diện web React
├── mqtt/              # Cấu hình Eclipse Mosquitto
├── data/              # Dữ liệu dùng chung và âm thanh cảnh báo
├── docker-compose.yml # Khởi chạy MQTT, backend và frontend
└── requirements.txt   # Thư viện Python
```

## Yêu cầu cài đặt

Tùy theo cách chạy, máy phát triển cần có:

- Git.
- Docker Desktop và Docker Compose.
- Python 3.10 trở lên.
- Node.js 18 trở lên và npm.
- VS Code cùng extension PlatformIO IDE để nạp firmware.
- Android Studio nếu muốn chạy ứng dụng Android.
- Một Google Gemini API key cho các chức năng AI.

## Cấu hình dự án

### 1. Tải mã nguồn

```bash
git clone <repository-url>
cd Smart-Home-ESP32
```

### 2. Cấu hình backend

Tạo file môi trường từ mẫu:

```bash
cp backend/.env.example backend/.env
```

Mở `backend/.env` và thay giá trị sau bằng API key của bạn:

```env
GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY
```

Khi chạy toàn bộ hệ thống bằng Docker Compose, `MQTT_HOST` sẽ tự động được đặt thành tên dịch vụ `mqtt`. Khi chạy backend trực tiếp trên máy, sử dụng:

```env
MQTT_HOST=localhost
MQTT_PORT=1883
```

### 3. Cấu hình ESP32

Nếu chưa có file cấu hình, sao chép file mẫu:

```bash
cp esp32-firmware/include/config.example.h esp32-firmware/include/config.h
```

Sau đó cập nhật thông tin mạng trong `esp32-firmware/include/config.h`:

```cpp
#define WIFI_SSID "TEN_WIFI"
#define WIFI_PASSWORD "MAT_KHAU_WIFI"

#define MQTT_HOST "192.168.1.10"
#define MQTT_PORT 1883
```

`MQTT_HOST` phải là địa chỉ IPv4 LAN của máy đang chạy Mosquitto. Không sử dụng `localhost` hoặc `127.0.0.1` trong firmware vì các địa chỉ này sẽ trỏ về chính ESP32.

ESP32 và máy chủ phải kết nối cùng một mạng Wi-Fi. Đồng thời, cổng TCP `1883` cần được cho phép qua tường lửa của máy chủ.

## Khởi chạy bằng Docker

Đây là cách nhanh nhất để chạy MQTT broker, backend và frontend:

```bash
docker compose up --build -d
docker compose ps
```

Sau khi các container hoạt động:

- Giao diện web: <http://localhost:5173>
- Backend API: <http://localhost:8000>
- Tài liệu API: <http://localhost:8000/docs>
- MQTT broker: `localhost:1883`

Xem nhật ký hệ thống:

```bash
docker compose logs -f
```

Dừng các dịch vụ:

```bash
docker compose down
```

## Khởi chạy ở chế độ phát triển

Trước tiên, khởi động MQTT broker:

```bash
docker compose up -d mqtt
```

Tạo môi trường Python và cài thư viện:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Cài thư viện frontend:

```bash
cd frontend
npm install
cd ..
```

Khởi động backend và frontend bằng script:

```bash
chmod +x start.sh
./start.sh
```

Hoặc chạy từng thành phần trong hai terminal riêng biệt:

```bash
cd backend
uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8000
```

```bash
cd frontend
npm run dev
```

## Nạp firmware vào ESP32

1. Mở thư mục `esp32-firmware` bằng VS Code.
2. Kết nối ESP32 với máy tính qua USB.
3. Chọn **PlatformIO: Upload** để biên dịch và nạp firmware.
4. Mở **Serial Monitor** với baud rate `115200`.
5. Kiểm tra log kết nối Wi-Fi, MQTT và trạng thái relay.

Cũng có thể sử dụng PlatformIO CLI:

```bash
cd esp32-firmware
pio run --target upload
pio device monitor --baud 115200
```

## Kiểm tra MQTT

Theo dõi toàn bộ message của hệ thống:

```bash
docker compose exec mqtt mosquitto_sub -h localhost -t "smarthome/#" -v
```

Gửi lệnh bật đèn phòng khách:

```bash
docker compose exec mqtt mosquitto_pub \
  -h localhost \
  -t "smarthome/lights/living-room/set" \
  -m "ON"
```

Các topic chính:

| Topic | Chức năng |
| --- | --- |
| `smarthome/lights/<id>/set` | Gửi lệnh bật/tắt một relay |
| `smarthome/lights/<id>/state` | Nhận trạng thái của một relay |
| `smarthome/lights/all/set` | Điều khiển tất cả relay |
| `smarthome/esp32/get-state` | Yêu cầu ESP32 gửi lại toàn bộ trạng thái |
| `smarthome/esp32/status` | Theo dõi trạng thái online/offline của ESP32 |

Payload điều khiển hợp lệ gồm `ON`, `OFF`, `1`, `0`, `true`, `false`, `{"on":true}` và `{"on":false}`.

## Chạy ứng dụng Android

1. Mở thư mục `android-app` trong Android Studio.
2. Đợi Gradle đồng bộ các thư viện.
3. Cấu hình địa chỉ backend nếu không sử dụng máy chủ mặc định:

```properties
APP_API_BASE_URL=http://192.168.1.10:8000/
APP_WS_BASE_URL=ws://192.168.1.10:8000
```

4. Chạy ứng dụng trên thiết bị Android hoặc máy ảo từ Android 7.0 (API 24) trở lên.
5. Cấp quyền micro và camera khi ứng dụng yêu cầu.

## API tiêu biểu

| Phương thức | Endpoint | Chức năng |
| --- | --- | --- |
| `GET` | `/smart-home/lights` | Lấy danh sách và trạng thái đèn |
| `POST` | `/smart-home/lights/on` | Bật đèn theo khu vực |
| `POST` | `/smart-home/lights/off` | Tắt đèn theo khu vực |
| `GET` | `/smart-home/music/library` | Lấy danh sách bài hát |
| `POST` | `/smart-home/music/play` | Phát bài hát |
| `POST` | `/smart-home/music/pause` | Tạm dừng nhạc |
| `POST` | `/smart-home/music/resume` | Tiếp tục phát nhạc |
| `WS` | `/ws/gemini` | Giao tiếp thời gian thực với Gemini |
| `WS` | `/smart-home/lights/stream` | Nhận cập nhật trạng thái đèn |

## Bảo mật

Cấu hình Mosquitto hiện tại cho phép kết nối ẩn danh để thuận tiện khi trình diễn trong mạng LAN. Không mở cổng `1883` trực tiếp ra Internet. Khi triển khai thực tế, cần bật xác thực tài khoản, TLS và giới hạn quyền truy cập theo từng MQTT topic.

Không commit các file chứa thông tin nhạy cảm như:

- `backend/.env`
- `esp32-firmware/include/config.h`
- API key, mật khẩu Wi-Fi hoặc thông tin đăng nhập MQTT

## Hướng phát triển

- Bổ sung cảm biến nhiệt độ, độ ẩm, khí gas và chuyển động.
- Tích hợp lịch tự động bật/tắt thiết bị.
- Gửi thông báo cháy và sự cố đến điện thoại.
- Bổ sung xác thực người dùng và phân quyền thiết bị.
- Mã hóa kết nối MQTT bằng TLS.
- Lưu dữ liệu cảm biến để thống kê và trực quan hóa.
- Hỗ trợ cập nhật firmware ESP32 qua OTA.

## Giấy phép

Dự án được xây dựng phục vụ mục đích học tập và nghiên cứu. Hãy bổ sung tệp giấy phép phù hợp trước khi phân phối hoặc sử dụng trong sản phẩm thương mại.
