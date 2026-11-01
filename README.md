<div align="center">

# Smart Home ESP32

### Hệ thống nhà thông minh IoT với ESP32, MQTT, FastAPI, React và Gemini

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=20232A)](https://react.dev/)
[![ESP32](https://img.shields.io/badge/ESP32-PlatformIO-E7352C?logo=espressif&logoColor=white)](https://www.espressif.com/)
[![MQTT](https://img.shields.io/badge/MQTT-Mosquitto-660066?logo=eclipsemosquitto&logoColor=white)](https://mosquitto.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

[Tính năng](#-tính-năng-nổi-bật) ·
[Kiến trúc](#-kiến-trúc-hệ-thống) ·
[Cài đặt](#-bắt-đầu) ·
[API](#-api-reference) ·
[MQTT](#-mqtt-reference) ·
[Đóng góp](#-đóng-góp)

</div>

Smart Home ESP32 là một project IoT full-stack phục vụ học tập và trình diễn. Hệ thống kết nối dashboard web, FastAPI, Eclipse Mosquitto và các node ESP32 để điều khiển đèn, theo dõi nhiệt độ/độ ẩm, xem camera IP, phát hiện cháy thử nghiệm và tương tác bằng giọng nói với Google Gemini.

Backend chỉ xác nhận thay đổi trạng thái đèn sau khi nhận phản hồi thực tế từ ESP32. Vì vậy dashboard có thể hiển thị đúng trạng thái thiết bị, timeout, mất kết nối và quá trình đồng bộ lại thay vì chỉ mô phỏng thao tác ở giao diện.

> [!WARNING]
> Đây là prototype giáo dục chạy trong mạng LAN. Project không phải hệ thống báo cháy được chứng nhận và không được thiết kế để điều khiển trực tiếp tải điện lưới.

## ✨ Tính năng nổi bật

- **Điều khiển đèn hai chiều:** gửi lệnh từ web/API/Gemini qua MQTT và chờ ESP32 xác nhận trạng thái GPIO.
- **Giám sát môi trường:** nhận nhiệt độ, độ ẩm từ ESP32 + DHT11, lưu lịch sử bằng SQLite và cập nhật realtime qua WebSocket.
- **Camera IP:** FastAPI đọc luồng RTSP độc lập với Gemini, cung cấp snapshot JPEG và MJPEG stream cho frontend.
- **Phát hiện cháy thử nghiệm:** xử lý khung hình bằng OpenCV, giới hạn tần suất cảnh báo và hỗ trợ cảnh báo âm thanh.
- **Trợ lý Gemini Live:** hội thoại văn bản/giọng nói, phân tích ảnh và function calling để điều khiển đèn hoặc phát nhạc.
- **Trình phát nhạc:** quản lý thư viện, stream audio, phát, tạm dừng, tiếp tục và tua bài hát.
- **Theo dõi kết nối:** hiển thị trạng thái MQTT, ESP32 online/offline, dữ liệu stale và tự đồng bộ khi kết nối lại.
- **Triển khai bằng Docker:** khởi động Mosquitto, backend và frontend bằng một lệnh.

## 🏗 Kiến trúc hệ thống

```mermaid
flowchart LR
    user[Người dùng] --> web[React Web]
    web <-->|REST + WebSocket| api[FastAPI]

    api <-->|MQTT| broker[Eclipse Mosquitto]
    broker <-->|set / state / status| lights[ESP32 · 4 LED]
    broker <-->|telemetry / status| sensor[ESP32 · DHT11]

    api --> db[(SQLite History)]
    camera[Camera IP] -->|RTSP| api
    api -.->|API key| gemini[Google Gemini]
    api --> audio[Loa · Nhạc · Cảnh báo]
```

### Luồng điều khiển đèn

```mermaid
sequenceDiagram
    actor User as Người dùng
    participant UI as Web / Gemini
    participant API as FastAPI
    participant MQTT as Mosquitto
    participant ESP as ESP32

    User->>UI: Bật đèn phòng khách
    UI->>API: POST /smart-home/lights/on
    API->>MQTT: smarthome/lights/living-room/set
    MQTT->>ESP: ON
    ESP->>ESP: GPIO16 = LOW
    ESP->>MQTT: smarthome/lights/living-room/state
    MQTT->>API: Trạng thái xác nhận
    API-->>UI: Thành công + cập nhật realtime
```

## 🧰 Công nghệ sử dụng

| Lớp | Công nghệ |
| --- | --- |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Backend | Python 3.12, FastAPI, Uvicorn, WebSocket |
| AI & media | Google Gen AI SDK, Gemini Live/TTS, OpenCV, Mutagen |
| IoT | ESP32 DevKit, Arduino framework, PlatformIO |
| Messaging | MQTT, Eclipse Mosquitto, PubSubClient |
| Storage | SQLite, JSON runtime state |
| Camera | RTSP, OpenCV VideoCapture, JPEG/MJPEG |
| Infrastructure | Docker Compose, Nginx |

## 🔌 Phần cứng

### Mô hình demo hiện tại

- 01 MacBook chạy Docker Desktop, backend, frontend, Mosquitto và Gemini integration.
- 01 ESP32 DevKit điều khiển bốn LED qua MQTT.
- 01 ESP32 DevKit đọc cảm biến DHT11 tại GPIO4.
- 04 LED, mỗi LED dùng một điện trở 330 Ω.
- 01 camera IP truyền RTSP trong mạng LAN.
- Microphone và loa tích hợp trên MacBook.

### Sơ đồ chân đèn

| Khu vực | MQTT ID | GPIO | Logic |
| --- | --- | ---: | --- |
| Phòng khách | `living-room` | 16 | Active-LOW |
| Phòng ngủ | `bedroom` | 17 | Active-LOW |
| Nhà bếp | `kitchen` | 18 | Active-LOW |
| Ban công | `balcony` | 19 | Active-LOW |

Mỗi LED được mắc theo thứ tự `3V3 → điện trở 330 Ω → LED → GPIO`. Với logic active-LOW, `LOW` tương ứng bật và `HIGH` tương ứng tắt.

### DHT11

| DHT11 | ESP32 |
| --- | --- |
| `VCC` / `+` | `3V3` |
| `DATA` / `S` / `OUT` | `GPIO4` |
| `GND` / `-` | `GND` |

> [!CAUTION]
> Rút nguồn trước khi thay đổi dây. Không nối điện lưới, relay tải lớn hoặc thiết bị 220 V vào breadboard của mô hình này.

## 🚀 Bắt đầu

### Yêu cầu

- [Git](https://git-scm.com/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) có Docker Compose
- Trình duyệt hiện đại
- VS Code + [PlatformIO IDE](https://platformio.org/install/ide?install=vscode) nếu nạp firmware
- Google AI API key nếu sử dụng Gemini

### 1. Clone repository

```bash
git clone https://github.com/VyOZzz/Smart-Home-ESP32.git
cd Smart-Home-ESP32
```

### 2. Tạo file môi trường

macOS/Linux:

```bash
cp backend/.env.example backend/.env
```

Windows PowerShell:

```powershell
Copy-Item backend/.env.example backend/.env
```

Các tính năng MQTT, đèn, cảm biến và dashboard có thể chạy trong LAN mà không cần Gemini. Để bật Gemini, sửa:

```dotenv
GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY
```

Nếu sử dụng camera IP, chỉ đặt URL RTSP trong `backend/.env`:

```dotenv
HOME_CAMERA_RTSP_URL=rtsp://user:password@camera-ip:554/model-specific-path
```

Địa chỉ LAN của camera có thể thay đổi do DHCP. Để đổi IP mà không sửa URL chứa
thông tin đăng nhập, sao chép `backend/data/camera_ip.example.txt` thành
`backend/data/camera_ip.txt`, ghi IP hiện tại vào một dòng rồi khởi động lại
backend. File `camera_ip.txt` chỉ là cấu hình cục bộ và được Git bỏ qua.

Không đoán RTSP path nếu chưa biết hãng/model camera. Không commit URL hoặc thông tin đăng nhập camera.

### 3. Khởi động hệ thống

```bash
docker compose up --build -d
docker compose ps
```

| Dịch vụ | Địa chỉ |
| --- | --- |
| Web dashboard | <http://localhost:5173> |
| Backend API | <http://localhost:8000> |
| Swagger UI | <http://localhost:8000/docs> |
| MQTT broker | `localhost:1883` |

Theo dõi log:

```bash
docker compose logs -f
```

Dừng hệ thống:

```bash
docker compose down
```

## 📡 Cấu hình ESP32

Hai ESP32 và máy chạy Mosquitto phải ở cùng mạng LAN. ESP32 thường chỉ hỗ trợ Wi-Fi 2.4 GHz.

### ESP32 điều khiển đèn

```bash
cp esp32-firmware/include/config.example.h \
   esp32-firmware/include/config.h
```

### ESP32 + DHT11

```bash
cp esp32-sensor-firmware/include/config.example.h \
   esp32-sensor-firmware/include/config.h
```

Điền cấu hình mạng vào từng file `config.h`:

```cpp
#define WIFI_SSID "YOUR_WIFI_NAME"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#define MQTT_HOST "192.168.1.10"
#define MQTT_PORT 1883
```

`MQTT_HOST` trên ESP32 phải là IPv4 LAN của máy chạy Mosquitto, không phải `localhost`, `127.0.0.1` hoặc tên service Docker `mqtt`.

Build và upload:

```bash
pio run -d esp32-firmware -t upload
pio run -d esp32-sensor-firmware -t upload
```

Serial Monitor sử dụng baud `115200`.

Tài liệu chi tiết:

- [Firmware điều khiển đèn](esp32-firmware/README.md)
- [Firmware DHT11](esp32-sensor-firmware/README.md)
- [MQTT broker](mqtt/README.md)
- [Danh sách thiết bị](ITEMS.md)

## ⚙️ Cấu hình backend

Các biến phổ biến trong `backend/.env`:

| Biến | Mặc định | Mục đích |
| --- | --- | --- |
| `GOOGLE_API_KEY` | Trống | Xác thực Google Gemini |
| `GEMINI_MODEL` | `gemini-3.1-flash-live-preview` | Hội thoại realtime |
| `GEMINI_TTS_MODEL` | `gemini-2.5-flash-preview-tts` | Tạo cảnh báo giọng nói |
| `GEMINI_IMAGE_MODEL` | `gemini-3.5-flash` | Phân tích ảnh tĩnh |
| `HOME_CAMERA_RTSP_URL` | Trống | Luồng camera IP |
| `MQTT_HOST` | `mqtt` | MQTT broker của backend |
| `MQTT_PORT` | `1883` | Cổng MQTT |
| `MQTT_COMMAND_TIMEOUT_SECONDS` | `3` | Thời gian chờ ESP32 xác nhận |
| `ENVIRONMENT_STALE_AFTER_SECONDS` | `30` | Ngưỡng dữ liệu cảm biến stale |
| `ENVIRONMENT_HISTORY_MAX_ROWS` | `10000` | Số bản ghi SQLite tối đa |
| `FIRE_ALERT_COOLDOWN_SECONDS` | `10` | Khoảng nghỉ giữa cảnh báo cháy |
| `SAVE_CAPTURED_IMAGE` | `False` | Lưu khung hình đã xử lý |

Xem đầy đủ tại [`backend/.env.example`](backend/.env.example).

## 🔗 API reference

Swagger UI cung cấp schema và giao diện thử API tại <http://localhost:8000/docs>.

### REST API

| Method | Endpoint | Mô tả |
| --- | --- | --- |
| `GET` | `/smart-home/lights` | Danh sách trạng thái đèn |
| `GET` | `/smart-home/lights/{location}` | Trạng thái một đèn |
| `POST` | `/smart-home/lights/on` | Bật đèn và chờ ESP32 xác nhận |
| `POST` | `/smart-home/lights/off` | Tắt đèn và chờ ESP32 xác nhận |
| `GET` | `/smart-home/environment` | Dữ liệu môi trường mới nhất |
| `GET` | `/smart-home/environment/history` | Lịch sử nhiệt độ/độ ẩm |
| `GET` | `/smart-home/camera/status` | Trạng thái camera IP |
| `GET` | `/smart-home/camera/snapshot` | Ảnh JPEG mới nhất |
| `GET` | `/smart-home/camera/stream` | MJPEG stream |
| `GET` | `/smart-home/music/library` | Danh sách bài hát |
| `POST` | `/smart-home/music/play` | Phát bài hát |
| `POST` | `/smart-home/music/pause` | Tạm dừng |
| `POST` | `/smart-home/music/resume` | Tiếp tục phát |
| `POST` | `/smart-home/music/seek` | Tua bài hát |
| `POST` | `/assistant/chat` | Trợ lý văn bản cơ bản |

Ví dụ bật đèn:

```bash
curl -X POST http://localhost:8000/smart-home/lights/on \
  -H "Content-Type: application/json" \
  -d '{"location":"Phòng khách"}'
```

### WebSocket

| Endpoint | Dữ liệu realtime |
| --- | --- |
| `/ws/gemini` | Gemini Live, audio, ảnh và tool calls |
| `/smart-home/lights/stream` | Trạng thái đèn |
| `/smart-home/music/updates` | Trạng thái phát nhạc |
| `/smart-home/environment/updates` | Nhiệt độ và độ ẩm |
| `/smart-home/camera/updates` | Sự kiện camera và fire detection |

## 📬 MQTT reference

### ESP32 điều khiển đèn

| Topic | Chiều | Mô tả |
| --- | --- | --- |
| `smarthome/lights/<id>/set` | Backend → ESP32 | Gửi `ON` hoặc `OFF` |
| `smarthome/lights/<id>/state` | ESP32 → Backend | Xác nhận trạng thái GPIO |
| `smarthome/lights/all/set` | Backend → ESP32 | Điều khiển cả bốn đèn |
| `smarthome/esp32/get-state` | Backend → ESP32 | Yêu cầu snapshot trạng thái |
| `smarthome/esp32/status` | ESP32 → Backend | Online/offline retained + Last Will |

### ESP32 + DHT11

| Topic | Chiều | Mô tả |
| --- | --- | --- |
| `smarthome/sensors/room-1/state` | ESP32 → Backend | Nhiệt độ/độ ẩm retained |
| `smarthome/sensors/room-1/get-state` | Backend → ESP32 | Yêu cầu số đo mới nhất |
| `smarthome/esp32-sensor/status` | ESP32 → Backend | Online/offline retained + Last Will |

Payload mẫu:

```json
{
  "device_id": "esp32-sensor",
  "sensor_id": "room-1",
  "name": "Phòng 1",
  "temperature": 28.0,
  "humidity": 65.0,
  "temperature_unit": "C"
}
```

Theo dõi toàn bộ MQTT traffic:

```bash
docker compose exec mqtt \
  mosquitto_sub -h localhost -t "smarthome/#" -v
```

## 📁 Cấu trúc repository

```text
Smart-Home-ESP32/
├── backend/                    # FastAPI, MQTT, Gemini, camera và SQLite
│   ├── app/api/routes/         # REST API và WebSocket
│   ├── app/services/           # Logic nghiệp vụ và integrations
│   ├── data/                   # Runtime state và database
│   ├── music/                  # Thư viện nhạc demo
│   └── tests/                  # Backend test suite
├── frontend/                   # React + TypeScript dashboard
├── esp32-firmware/             # Firmware điều khiển bốn LED
├── esp32-sensor-firmware/      # Firmware ESP32 + DHT11 đang sử dụng
├── mqtt/                       # Eclipse Mosquitto configuration
├── docker-compose.yml          # Local orchestration
├── requirements.txt            # Python dependencies
└── ITEMS.md                    # Danh sách phần cứng
```

## 🧪 Kiểm thử

### Backend

```bash
docker compose run --rm --no-deps backend \
  python -m unittest discover -s tests -v
```

### Frontend

```bash
npm --prefix frontend ci
npm --prefix frontend run build
```

### Firmware

```bash
pio run -d esp32-firmware
pio run -d esp32-sensor-firmware
```

### Docker Compose

```bash
docker compose config
docker compose up -d --build
docker compose ps
```

## 🧭 Roadmap

- [x] Điều khiển bốn đèn qua MQTT với acknowledgement.
- [x] Dashboard web realtime.
- [x] ESP32 + DHT11 và lịch sử SQLite.
- [x] Camera IP RTSP, snapshot và MJPEG stream.
- [x] Gemini Live, function calling và điều khiển bằng giọng nói.
- [x] Phát nhạc và cảnh báo cháy thử nghiệm.
- [ ] Bổ sung xác thực người dùng và phân quyền thiết bị.
- [ ] Bật MQTT authentication/TLS cho môi trường triển khai.
- [ ] Thêm CI/CD, HTTPS, monitoring và production deployment.

## 🔐 Bảo mật và an toàn

- Mosquitto hiện cho phép kết nối ẩn danh để demo trong LAN; không public cổng `1883` ra Internet.
- Không commit `backend/.env`, các file `include/config.h`, Wi-Fi credentials, Gemini API key, MQTT password, CA certificate hoặc RTSP credentials.
- Không trả URL RTSP hoặc thông tin đăng nhập camera về frontend hay ghi vào log.
- Sử dụng MQTT TLS, tài khoản riêng cho từng thiết bị và secret manager trước khi triển khai thật.
- Fire detection qua camera có thể báo sai hoặc bỏ sót; không thay thế đầu báo khói/nhiệt đạt chuẩn.
- Mô hình hiện dùng LED điện áp thấp, không dùng relay hoặc tải điện lưới.

## 🛠 Xử lý sự cố

### ESP32 không kết nối MQTT

- Kiểm tra ESP32 và máy chạy broker đang cùng Wi-Fi 2.4 GHz.
- Dùng IPv4 LAN của máy làm `MQTT_HOST`; không dùng `localhost`.
- Cho phép inbound TCP `1883` trong firewall.
- Kiểm tra broker bằng `docker compose logs mqtt`.

### Backend không healthy

```bash
docker compose logs backend
docker compose config
```

Đảm bảo `backend/.env` tồn tại và không chứa giá trị sai kiểu.

### Camera không có hình

- Xác nhận camera và máy chủ truy cập được nhau trong LAN.
- Kiểm tra đúng RTSP path theo hãng/model.
- Không gửi password camera vào issue hoặc log công khai.

### Gemini không hoạt động

- Kiểm tra `GOOGLE_API_KEY` và quyền truy cập model.
- Kiểm tra kết nối Internet của backend.
- Các chức năng MQTT và dashboard vẫn có thể chạy khi Gemini không khả dụng.

## 🤝 Đóng góp

Issue và pull request đều được chào đón.

1. Fork repository.
2. Tạo nhánh mới: `git switch -c feature/ten-tinh-nang`.
3. Thực hiện thay đổi và bổ sung test/tài liệu liên quan.
4. Chạy backend tests, frontend build và firmware build.
5. Commit rõ ràng và mở pull request.

Khi mô tả thay đổi phần cứng, hãy phân biệt rõ nội dung đã kiểm thử thực tế và nội dung mới chỉ mô phỏng.

## 📄 Giấy phép

Repository hiện chưa công bố file `LICENSE`. Mặc định tác giả giữ toàn bộ quyền. Hãy liên hệ tác giả trước khi phân phối hoặc tái sử dụng project ngoài phạm vi được cho phép.

---

<div align="center">

Được xây dựng cho mục đích học tập, nghiên cứu và trình diễn IoT.

</div>
