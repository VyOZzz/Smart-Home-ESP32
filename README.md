# Smart Home ESP32

![Python](https://img.shields.io/badge/Python-FastAPI-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-TypeScript-61DAFB?logo=react&logoColor=20232A)
![ESP32](https://img.shields.io/badge/ESP32-PlatformIO-E7352C?logo=espressif&logoColor=white)
![MQTT](https://img.shields.io/badge/MQTT-Mosquitto-660066?logo=eclipsemosquitto&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

Project nhà thông minh phục vụ học tập, chạy trên MacBook với Docker Desktop,
Mosquitto, FastAPI và React. Hệ thống hiện dùng hai ESP32:

- ESP32 thứ nhất điều khiển bốn LED qua MQTT.
- ESP32 thứ hai đọc DHT11 ở GPIO4 và gửi nhiệt độ/độ ẩm qua MQTT.

Camera dùng trong project là camera IP truyền RTSP qua mạng LAN. Microphone và
loa dùng của MacBook; camera tích hợp trên MacBook không được sử dụng.

> Đây là prototype IoT phục vụ học tập và trình diễn trong mạng LAN, không phải
> hệ thống an toàn hoặc điều khiển điện dân dụng đã được chứng nhận.

## Mục lục

- [Tính năng nổi bật](#tính-năng-nổi-bật)
- [Phạm vi đã xác nhận](#phạm-vi-đã-xác-nhận)
- [Kiến trúc hiện tại](#kiến-trúc-hiện-tại)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Phần cứng và đấu dây](#phần-cứng-và-đấu-dây)
- [Cấu hình](#cấu-hình)
- [Build và nạp firmware](#build-và-nạp-firmware)
- [Chạy hệ thống](#chạy-hệ-thống)
- [MQTT topics](#mqtt-topics)
- [Kiểm thử](#kiểm-thử)
- [Kịch bản demo ngắn](#kịch-bản-demo-ngắn)
- [Giới hạn và bảo mật](#giới-hạn-và-bảo-mật)

## Tính năng nổi bật

- Điều khiển bốn đèn mô phỏng bằng LED từ web/API hoặc lệnh giọng nói Gemini.
- Xác nhận lệnh hai chiều: dashboard chỉ đổi trạng thái sau khi ESP32 phản hồi
  qua MQTT, đồng thời hiển thị timeout, mất kết nối và quá trình đồng bộ lại.
- Thu thập nhiệt độ/độ ẩm từ DHT11, cung cấp REST API và cập nhật WebSocket.
- Lưu lịch sử dữ liệu môi trường trong SQLite với dung lượng được giới hạn.
- Nhận luồng RTSP từ camera IP, cung cấp JPEG/MJPEG và phát hiện cháy thử nghiệm
  độc lập với phiên Gemini.
- Phát nhạc, hội thoại realtime và điều khiển thiết bị bằng Gemini function
  calling khi có API key hợp lệ.
- Docker Compose đóng gói frontend, backend và Mosquitto để dựng môi trường
  demo nhất quán.

## Phạm vi đã xác nhận

Các kết quả dưới đây đã được kiểm tra trong quá trình hoàn thiện project:

- Hai firmware ESP32 build và nạp thành công bằng PlatformIO.
- ESP32 đèn kết nối Wi-Fi/MQTT và phản hồi trạng thái của bốn GPIO.
- DHT11 đọc được nhiệt độ/độ ẩm thực tế và publish đúng MQTT topic.
- Backend chỉ cập nhật đèn sau khi nhận phản hồi `/state` từ ESP32.
- API và WebSocket nhận được dữ liệu DHT11 thực tế.
- Backend tests đạt 37/37 tại lần kiểm thử hoàn thiện.
- Frontend production build thành công.
- Khi Mosquitto dừng, API báo offline; khi broker chạy lại, ESP32 và backend tự
  kết nối lại.

Các phần sau có code nhưng cần cấu hình/kiểm tra riêng trước khi trình bày:

- Gemini cần `GOOGLE_API_KEY` hợp lệ và kết nối Internet.
- Camera cần URL RTSP đúng theo hãng/model và phải truy cập được trong LAN.
- Phát nhạc cần trình duyệt cho phép âm thanh và loa MacBook hoạt động.
- Node DHT22 trong `environment-firmware/` là tùy chọn, chưa kiểm thử vật lý.
- MQTT cloud/TLS chưa được xác nhận bằng tài khoản cloud thật.

## Kiến trúc hiện tại

```mermaid
flowchart LR
    web["React web"] <-->|"REST + WebSocket"| api["FastAPI trên MacBook"]
    api <-->|"MQTT"| broker["Mosquitto trên MacBook"]
    broker <-->|"set, state, status"| lights["ESP32 đèn: GPIO 16-19"]
    broker <-->|"state, status, get-state"| sensor["ESP32 + DHT11: GPIO4"]
    api --> history["SQLite lịch sử cảm biến"]
    camera["Camera IP"] -->|"RTSP qua LAN"| api
    api -.->|"Khi có API key"| gemini["Gemini API"]
    api --> speaker["Nhạc và cảnh báo qua loa MacBook"]
```

FastAPI đọc camera IP độc lập với phiên Gemini. Việc đóng Gemini không được làm
dừng camera capture hoặc xử lý ảnh.

## Công nghệ sử dụng

| Thành phần | Công nghệ |
| --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Backend | Python, FastAPI, Uvicorn, WebSocket |
| IoT | ESP32 DevKit, Arduino framework, PlatformIO |
| Messaging | MQTT, Eclipse Mosquitto, PubSubClient |
| Dữ liệu | SQLite, JSON state |
| AI & media | Google Gemini, OpenCV, RTSP/MJPEG, Mutagen |
| Triển khai | Docker Compose, Nginx |

## Luồng điều khiển đèn

```mermaid
sequenceDiagram
    actor User as Người dùng
    participant Web as Web
    participant API as FastAPI
    participant MQTT as Mosquitto
    participant ESP as ESP32 đèn
    participant LED as LED vật lý

    User->>Web: Bật hoặc tắt một phòng
    Web->>API: Gửi lệnh
    API->>MQTT: Publish /set
    MQTT->>ESP: Chuyển lệnh ON hoặc OFF
    ESP->>LED: Đặt GPIO active-LOW
    ESP->>MQTT: Publish /state
    MQTT->>API: Trạng thái đã thực hiện
    API-->>Web: Trả kết quả và cập nhật realtime
```

Backend không đổi trạng thái chỉ dựa vào lệnh gửi đi. Nếu ESP32 không phản hồi
đúng `/state` trong thời hạn cấu hình, API báo timeout.

## Phần cứng và đấu dây

### Bốn LED

| Khu vực | MQTT ID | GPIO |
| --- | --- | ---: |
| Phòng khách | `living-room` | 16 |
| Phòng ngủ | `bedroom` | 17 |
| Nhà bếp | `kitchen` | 18 |
| Ban công | `balcony` | 19 |

Mỗi LED dùng một điện trở 330 Ω:

```mermaid
flowchart LR
    supply["3V3"] --> resistor["Điện trở 330 Ω"]
    resistor --> anode["Chân dài LED (+)"]
    anode --> cathode["Chân ngắn LED (-)"]
    cathode --> gpio["GPIO 16, 17, 18 hoặc 19"]
```

Firmware dùng active-LOW: `ON` là GPIO `LOW`, `OFF` là GPIO `HIGH`.

### DHT11 module 3 chân

| DHT11 | ESP32 cảm biến |
| --- | --- |
| `VCC/+` | `3V3` |
| `DATA/S/OUT` | `D4/GPIO4` |
| `GND/-` | `GND` |

Đọc nhãn trực tiếp trên module vì thứ tự chân có thể khác nhau giữa các hãng.

> Project chỉ dùng điện áp thấp từ ESP32. Không đấu điện lưới vào breadboard.

## Cấu trúc chính

```text
Smart-Home-ESP32/
├── backend/                    # FastAPI, MQTT, camera, Gemini, SQLite
├── frontend/                   # React web app
├── mqtt/                       # Mosquitto configuration
├── esp32-firmware/             # Firmware điều khiển bốn LED
├── esp32-sensor-firmware/      # Firmware DHT11 GPIO4 đang dùng
├── environment-firmware/       # DHT22 tùy chọn, chưa test vật lý
├── android-app/                # Ứng dụng Android trong repository
└── docker-compose.yml          # MQTT, backend và frontend
```

## Cấu hình

### Backend

```bash
cp backend/.env.example backend/.env
```

Nếu dùng Gemini, điền API key trong `backend/.env`:

```env
GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY
```

Nếu dùng camera, chỉ đặt URL RTSP trong `backend/.env`:

```env
HOME_CAMERA_RTSP_URL=rtsp://user:password@camera-ip:554/path-theo-model
```

Không đoán RTSP path khi chưa biết hãng/model camera. Không đưa URL hoặc thông
tin đăng nhập camera vào frontend, log hoặc commit.

Backend chạy trong Docker dùng `MQTT_HOST=mqtt`. ESP32 không dùng tên này.

### Hai ESP32

Tạo file cấu hình cục bộ:

```bash
cp esp32-firmware/include/config.example.h \
  esp32-firmware/include/config.h

cp esp32-sensor-firmware/include/config.example.h \
  esp32-sensor-firmware/include/config.h
```

Lấy IPv4 LAN của MacBook:

```bash
ipconfig getifaddr en0
```

Điền cùng Wi-Fi và IP MacBook vào cả hai file `config.h`:

```cpp
#define WIFI_SSID "TEN_WIFI"
#define WIFI_PASSWORD "MAT_KHAU_WIFI"
#define MQTT_HOST "IPV4_LAN_CUA_MACBOOK"
#define MQTT_PORT 1883
```

Không dùng `localhost`, `127.0.0.1` hoặc `mqtt` làm `MQTT_HOST` trên ESP32.

## Build và nạp firmware

Liệt kê cổng USB:

```bash
ls /dev/cu.*
```

Nạp đúng từng board bằng cổng tường minh:

```bash
pio run -d esp32-firmware \
  -t upload --upload-port /dev/cu.usbserial-XXXX
```

```bash
pio run -d esp32-sensor-firmware \
  -t upload --upload-port /dev/cu.usbserial-YYYY
```

Serial Monitor dùng baud 115200:

```bash
pio device monitor --port /dev/cu.usbserial-XXXX --baud 115200
```

Log mong đợi:

```text
[WiFi] Connected
[MQTT] Connected
```

## Chạy hệ thống

Mở Docker Desktop rồi chạy:

```bash
cd /Users/vypham/Project/Smart-Home-ESP32
docker compose up -d --build
docker compose ps
```

Địa chỉ sử dụng:

- Web: <http://localhost:5173>
- Backend API: <http://localhost:8000>
- Swagger: <http://localhost:8000/docs>
- MQTT trên MacBook: `localhost:1883`

`iot-mqtt` và `iot-backend` phải hiện `healthy`; `iot-frontend` phải hiện `Up`.

## MQTT topics

### ESP32 đèn

| Topic | Chức năng |
| --- | --- |
| `smarthome/lights/<id>/set` | Gửi lệnh `ON` hoặc `OFF` |
| `smarthome/lights/<id>/state` | ESP32 xác nhận trạng thái GPIO |
| `smarthome/lights/all/set` | Điều khiển cả bốn đèn |
| `smarthome/esp32/get-state` | Yêu cầu đồng bộ bốn trạng thái |
| `smarthome/esp32/status` | Online/offline retained + Last Will |

### ESP32 DHT11

| Topic | Chức năng |
| --- | --- |
| `smarthome/sensors/room-1/state` | Nhiệt độ/độ ẩm retained |
| `smarthome/esp32-sensor/status` | Online/offline retained + Last Will |
| `smarthome/sensors/room-1/get-state` | Yêu cầu đọc và gửi ngay |

Payload DHT11:

```json
{"device_id":"esp32-sensor","sensor_id":"room-1","name":"Phòng 1","temperature":28.0,"humidity":65.0,"temperature_unit":"C"}
```

Theo dõi toàn bộ MQTT traffic:

```bash
docker compose exec mqtt mosquitto_sub \
  -h localhost -t "smarthome/#" -v
```

## Đổi mạng khi mang đi demo

Firmware hiện lưu SSID, mật khẩu và IP broker trong `config.h`. Khi đổi mạng:

1. Cho MacBook và hai ESP32 dùng cùng một Wi-Fi 2.4 GHz.
2. Lấy IPv4 LAN mới của MacBook.
3. Cập nhật hai file `config.h`.
4. Nạp lại hai ESP32.

Nên dùng hotspot hoặc Internet Sharing riêng với SSID/mật khẩu cố định. Wi-Fi
trường có thể bật client isolation làm ESP32 không truy cập được MacBook.

## Kiểm thử

```bash
# Firmware
pio run -d esp32-firmware
pio run -d esp32-sensor-firmware

# Backend trong Docker image
docker compose run --rm --no-deps backend \
  python -m unittest discover -s tests -v

# Frontend
npm --prefix frontend run build

# Docker Compose
docker compose config
```

Kiểm tra API khi hệ thống đang chạy:

```bash
curl http://localhost:8000/smart-home/lights
curl http://localhost:8000/smart-home/environment
```

## Kịch bản demo ngắn

1. Chạy `docker compose up -d` và mở <http://localhost:5173>.
2. Xác nhận hai ESP32 online.
3. Bật/tắt từng phòng và đối chiếu LED vật lý.
4. Quan sát nhiệt độ/độ ẩm DHT11 cập nhật.
5. Nếu Gemini đã cấu hình và kiểm tra trước, thử lệnh điều khiển bằng giọng nói.
6. Nếu RTSP đã cấu hình và kiểm tra trước, mở camera IP.
7. Rút/cắm lại một ESP32 để demo offline và reconnect.

## Giới hạn và bảo mật

- Bốn LED chỉ đại diện cho bốn đèn, không điều khiển tải điện lưới.
- `/state` xác nhận mức GPIO, không đo độ sáng thực tế của LED.
- Phát hiện cháy qua camera chỉ là demo giáo dục, có thể báo sai hoặc bỏ sót.
- Hệ thống không thay thế đầu báo khói/nhiệt được chứng nhận.
- Đây không phải hệ thống an toàn giám sát liên tục.
- Mosquitto hiện cho phép kết nối ẩn danh để demo trong LAN; không mở cổng 1883
  trực tiếp ra Internet.
- Firmware hiện cần nạp lại khi đổi SSID hoặc IP broker.

Không commit:

- `backend/.env`
- `esp32-firmware/include/config.h`
- `esp32-sensor-firmware/include/config.h`
- `environment-firmware/include/config.h`
- Wi-Fi/MQTT credentials, Gemini API key, CA certificate hoặc RTSP credentials

## Phần mở rộng DHT22

`environment-firmware/` là firmware tùy chọn cho ESP32 + DHT22, DATA ở GPIO23,
device ID `esp32-environment`. Node này chưa được xác nhận bằng phần cứng thật và
không thuộc luồng DHT11 đang dùng trong demo hiện tại.

## Đóng góp

Issue và pull request đều được chào đón. Trước khi gửi thay đổi:

1. Không commit API key, thông tin Wi-Fi, MQTT, RTSP hoặc certificate.
2. Chạy test backend, build frontend và build firmware có liên quan.
3. Mô tả rõ phần cứng đã kiểm thử thực tế và phần nào mới chỉ được mô phỏng.
4. Cập nhật tài liệu nếu thay đổi API, MQTT topic, sơ đồ chân hoặc quy trình cài
   đặt.

## Giấy phép

Repository hiện chưa công bố file `LICENSE`. Mặc định tác giả giữ toàn bộ quyền;
hãy liên hệ tác giả trước khi phân phối hoặc tái sử dụng project ngoài phạm vi
được cho phép.
