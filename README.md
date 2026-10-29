# Smart Home ESP32

Hệ thống nhà thông minh ứng dụng **ESP32**, **MQTT** và **trí tuệ nhân tạo Gemini**, cho phép người dùng giám sát và điều khiển các thiết bị trong nhà thông qua giao diện web hoặc ứng dụng Android.

ESP32 đóng vai trò là bộ điều khiển thiết bị tại hiện trường: kết nối Wi-Fi, nhận lệnh qua MQTT, điều khiển bốn LED đại diện cho bốn phòng và gửi trạng thái hoạt động về hệ thống theo thời gian thực. Backend FastAPI xử lý nghiệp vụ, kết nối trợ lý AI, quản lý nhạc và làm cầu nối giữa giao diện người dùng với ESP32.

## Phạm vi bản demo

- MacBook chạy Docker Desktop, MQTT broker, backend và frontend.
- Camera IP trong nhà truyền RTSP qua LAN/Wi-Fi cung cấp hình ảnh. Microphone và loa
  tích hợp trên MacBook vẫn dùng cho giọng nói và âm thanh phản hồi.
- ESP32 DevKit, camera IP riêng biệt và bốn LED là phần cứng hiện trường. LED là thiết bị
  đầu ra thật của mô hình, không phải trạng thái giả chỉ tồn tại trên giao diện.
- Danh sách thiết bị điều khiển gồm đúng bốn khu vực: phòng khách, phòng ngủ,
  nhà bếp và ban công.
- Project không sử dụng Raspberry Pi, module công suất hoặc điện lưới.

ESP32 thứ hai dùng module **DHT11** tại GPIO4 để gửi nhiệt độ/độ ẩm của Phòng 1
qua MQTT. Backend lưu lịch sử SQLite và cập nhật card môi trường theo thời gian
thực. Thư mục `environment-firmware/` vẫn là phần mở rộng DHT22 tùy chọn đã
chuẩn bị; không coi node DHT22 hoặc MQTT cloud là đã kiểm thử vật lý.

## Tính năng chính

- Bật hoặc tắt đèn độc lập tại phòng khách, phòng ngủ, nhà bếp và ban công.
- Điều khiển đồng thời bốn LED đại diện cho bốn đèn trong nhà.
- Đồng bộ trạng thái thiết bị theo thời gian thực qua MQTT và WebSocket.
- Tương tác với trợ lý Gemini bằng văn bản, giọng nói và hình ảnh.
- Điều khiển thiết bị bằng câu lệnh tự nhiên, chẳng hạn như “Bật đèn phòng khách”.
- Phát, tạm dừng, tiếp tục và tua nhạc từ thư viện trên máy chủ.
- Backend tự đọc luồng RTSP từ camera IP để phát hiện dấu hiệu cháy bằng
  OpenCV, hiển thị cảnh báo và phát âm thanh qua loa MacBook.
- Sử dụng trên cả trình duyệt web và ứng dụng Android.
- Tự động kết nối lại Wi-Fi và MQTT khi đường truyền bị gián đoạn.
- Khởi động các đầu ra GPIO ở trạng thái tắt.

## Kiến trúc hệ thống

```text
Camera IP trong nhà → RTSP/LAN → FastAPI trên MacBook → OpenCV
                                      ├→ JPEG/MJPEG → web
                                      ├→ cảnh báo WebSocket → web + loa MacBook
                                      └→ khung hình mới nhất → Gemini (khi cần)
Web/API/Gemini → FastAPI → MQTT → ESP32 DevKit → 4 LED
                              ← /state xác nhận ←
ESP32 DevKit #2 + DHT11 GPIO4 → MQTT LAN → FastAPI → SQLite → web/Gemini
Micro MacBook → web → Gemini → âm thanh → loa MacBook
```

Khi điều khiển đèn, backend không cập nhật trạng thái theo yêu cầu gửi đi. Nó
chỉ báo thành công sau khi ESP32 phản hồi trên topic `/state`. Nhờ đó, giao diện
có thể phân biệt lệnh đã được thiết bị thực thi với trạng thái phần mềm tạm thời.

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

- Hai bo mạch ESP32 DevKit.
- Camera IP giám sát trong nhà có hỗ trợ RTSP trong LAN.
- Một breadboard.
- Bốn LED và bốn điện trở 330 Ω.
- Một module DHT11 3 chân và dây jumper.
- Micro và loa tích hợp trên MacBook.

DHT11 dùng `VCC/+ → 3V3`, `DATA/S/OUT → D4 (GPIO4)` và `GND/- → GND`.
Node DHT22 trong `environment-firmware/` là phần mở rộng tùy chọn riêng, chưa
được xác nhận bằng phần cứng.

Danh sách kiểm kê và sơ đồ đấu chi tiết nằm trong [ITEMS.md](ITEMS.md).

### Sơ đồ chân mặc định

| Khu vực | MQTT ID | GPIO |
| --- | --- | ---: |
| Phòng khách | `living-room` | 16 |
| Phòng ngủ | `bedroom` | 17 |
| Nhà bếp | `kitchen` | 18 |
| Ban công | `balcony` | 19 |

Firmware được cấu hình **active-LOW** để LED sáng khi nhận lệnh `ON`. Mỗi LED
đấu từ `3V3` qua một điện trở 330 Ω tới GPIO tương ứng.

> Project hiện chỉ dùng điện áp thấp từ ESP32. Không đấu điện lưới vào breadboard.

## Cấu trúc thư mục

```text
Smart-Home-ESP32/
├── android-app/       # Ứng dụng Android bằng Jetpack Compose
├── backend/           # API, WebSocket, Gemini và xử lý nghiệp vụ
├── esp32-firmware/    # Firmware điều khiển bốn LED qua ESP32
├── esp32-sensor-firmware/ # Firmware ESP32 thứ hai + DHT11 GPIO4
├── environment-firmware/ # Node DHT22 tùy chọn, chưa kiểm thử vật lý
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

Docker Compose đặt `MQTT_HOST=mqtt`, là tên dịch vụ broker trong mạng Docker.
Khi chạy backend trực tiếp trên máy với broker Docker, dùng:

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

### 4. Cấu hình camera IP

Trước khi chốt đường dẫn RTSP, cần cung cấp **hãng và model camera**. Không gửi
mật khẩu camera. Backend hiện dùng RTSP trực tiếp; ONVIF có thể giúp lấy URI
stream theo profile của thiết bị, nhưng chưa có tự động khám phá ONVIF.

Điền URL tại máy của bạn trong `backend/.env` (mẫu cú pháp, chưa phải cấu hình
cho camera cụ thể):

```env
HOME_CAMERA_RTSP_URL=rtsp://user:password@192.168.1.100:554/<duong-dan-theo-model>
CAMERA_CAPTURE_INTERVAL_SECONDS=0.5
CAMERA_REQUEST_TIMEOUT_SECONDS=2
CAMERA_RECONNECT_INTERVAL_SECONDS=2
CAMERA_MAX_FRAME_BYTES=512000
```

Mã hóa phần trăm các ký tự đặc biệt trong tên đăng nhập/mật khẩu khi ghép URL.
Giữ URL trống nếu chưa xác nhận model: web sẽ báo chưa cấu hình, không tự dùng
camera MacBook. URL chỉ được backend đọc; API và frontend không trả URL này.
Không ghi đè file `.env` đang có; chỉ bổ sung biến mới rồi khởi động lại backend.

MacBook (và container backend) cần truy cập được IP/cổng RTSP của camera trong
LAN. RTSP dùng TCP; ưu tiên substream độ phân giải thấp nếu khung JPEG quá lớn
hoặc tải giải mã cao. Không dùng `localhost` làm địa chỉ camera.

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
5. Kiểm tra log kết nối Wi-Fi, MQTT và trạng thái các đèn.

Cũng có thể sử dụng PlatformIO CLI:

```bash
cd esp32-firmware
pio run --target upload
pio device monitor --baud 115200
```

## Nạp firmware ESP32 cảm biến DHT11

Firmware riêng nằm trong `esp32-sensor-firmware/` và không thay đổi firmware
điều khiển bốn đèn. Sao chép file mẫu rồi điền Wi-Fi và IPv4 LAN của MacBook:

```bash
cp esp32-sensor-firmware/include/config.example.h \
  esp32-sensor-firmware/include/config.h
cd esp32-sensor-firmware
pio run -e esp32dev
pio run -e esp32dev -t upload --upload-port /dev/cu.usbserial-XXXX
pio device monitor --port /dev/cu.usbserial-XXXX --baud 115200
```

Nối `VCC → 3V3`, `GND → GND`, `DATA → D4/GPIO4`. Firmware đọc mỗi 5 giây,
in Serial 115200, tự reconnect Wi-Fi/MQTT, gửi state retained và dùng retained
Last Will để báo offline. Luôn chỉ định `--upload-port` sau khi kiểm tra danh
sách `/dev/cu.*`, tránh nạp nhầm ESP32 điều khiển đèn.

Trên MacBook, khởi động toàn bộ stack bằng:

```bash
docker compose up -d --build
docker compose ps
```

Firmware ESP32 phải dùng IPv4 LAN của MacBook cho `MQTT_HOST`; không dùng
`localhost`, `127.0.0.1` hoặc tên service `mqtt`. Chỉ backend trong Docker dùng
`MQTT_HOST=mqtt`.

Khi cần test không có board DHT11, chạy simulator:

```bash
python backend/scripts/environment_simulator.py --host localhost --interval 2
```

Mở <http://localhost:5173> để xem nhiệt độ, độ ẩm, trạng thái và biểu đồ. Dừng
simulator bằng `Ctrl+C`; giao diện sẽ chuyển sang offline hoặc dữ liệu quá hạn.

## Node ESP32 + DHT22 tùy chọn

`environment-firmware/` là firmware DHT22 GPIO23 đã chuẩn bị cho mở rộng Level
6. Đây là firmware thay thế/tùy chọn và chưa được xác nhận bằng phần cứng.

## Chuyển từ MQTT LAN sang MQTT cloud

Phần này áp dụng cho firmware đèn và node DHT22 tùy chọn vốn đã hỗ trợ TLS;
firmware DHT11 hiện dùng broker LAN. Điền endpoint, cổng, username và password
vào `backend/.env`, `esp32-firmware/include/config.h` và
`environment-firmware/include/config.h`. Không commit các giá trị này.

```dotenv
MQTT_HOST=<cloud-endpoint>
MQTT_PORT=8883
MQTT_USERNAME=<username>
MQTT_PASSWORD=<password>
MQTT_TLS_ENABLED=True
MQTT_TLS_INSECURE=False
```

Trên firmware đặt `MQTT_USE_TLS 1`, cổng theo nhà cung cấp và CA certificate
được họ hướng dẫn. Backend Docker đọc trực tiếp các biến từ `backend/.env`;
không còn khóa cứng host `mqtt`. Khi dùng broker Mosquitto trong Docker, giữ
`MQTT_HOST=mqtt`, port `1883` và tắt TLS. Khi chạy FastAPI trực tiếp trên macOS
với broker Docker, dùng `MQTT_HOST=localhost`.

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
| `smarthome/lights/<id>/set` | Gửi lệnh bật/tắt một đèn |
| `smarthome/lights/<id>/state` | Nhận trạng thái của một đèn |
| `smarthome/lights/all/set` | Điều khiển tất cả đèn |
| `smarthome/esp32/get-state` | Yêu cầu ESP32 gửi lại toàn bộ trạng thái |
| `smarthome/esp32/status` | Theo dõi trạng thái online/offline của ESP32 |
| `smarthome/sensors/room-1/state` | Nhiệt độ/độ ẩm DHT11, retained |
| `smarthome/esp32-sensor/status` | Online/offline của ESP32 cảm biến, retained + Last Will |
| `smarthome/sensors/room-1/get-state` | Yêu cầu node DHT11 đọc và gửi ngay |

Payload điều khiển hợp lệ gồm `ON`, `OFF`, `1`, `0`, `true`, `false`, `{"on":true}` và `{"on":false}`.

## Kịch bản trình diễn

1. Chạy `docker compose up -d --build` và xác nhận MQTT, backend, frontend đều
   hoạt động.
2. Cấp nguồn ESP32; giao diện hiển thị thiết bị online và bốn trạng thái đèn.
3. Bật/tắt từng đèn trên web và đối chiếu LED vật lý với trạng thái giao diện.
4. Nói “bật đèn phòng khách”; Gemini gọi công cụ điều khiển và LED GPIO 16 sáng.
5. Yêu cầu phát một bài hát, sau đó thử tạm dừng và tiếp tục.
6. Chọn **Xem camera IP**, hướng camera IP vào ảnh/video thử nghiệm có vùng
   giống ngọn lửa và kiểm tra cảnh báo hình ảnh cùng âm thanh.
7. Rút nguồn ESP32; giao diện phải báo offline và API phải từ chối lệnh mới.
8. Cắm lại ESP32; thiết bị tự kết nối và backend đồng bộ lại bốn trạng thái.

## Tiêu chí hoàn thành

- `[WiFi] Connected` và `[MQTT] Connected` xuất hiện trên Serial Monitor.
- Lệnh từ nút web và Gemini đều làm đúng LED thay đổi.
- Mỗi lệnh chỉ thành công sau khi có phản hồi `/state` từ ESP32.
- Giao diện nhận cập nhật thời gian thực và hiển thị offline rõ ràng.
- Camera IP qua backend cung cấp ảnh; trình duyệt không xin quyền webcam MacBook.
- Microphone, loa và trình phát nhạc hoạt động trên MacBook.
- Khởi động lại broker hoặc ESP32 không làm mất khả năng đồng bộ.

## Chạy ứng dụng Android

1. Mở thư mục `android-app` trong Android Studio.
2. Đợi Gradle đồng bộ các thư viện.
3. Cấu hình địa chỉ backend nếu không sử dụng máy chủ mặc định:

```properties
APP_API_BASE_URL=http://192.168.1.10:8000/
APP_WS_BASE_URL=ws://192.168.1.10:8000
```

4. Chạy ứng dụng trên thiết bị Android hoặc máy ảo từ Android 7.0 (API 24) trở lên.
5. Cấp quyền micro khi dùng hội thoại giọng nói.

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
| `GET` | `/smart-home/camera/status` | Trạng thái camera IP |
| `GET` | `/smart-home/camera/snapshot` | Khung JPEG mới nhất |
| `GET` | `/smart-home/camera/stream` | Luồng MJPEG cho giao diện |
| `WS` | `/smart-home/camera/updates` | Trạng thái và cảnh báo cháy |
| `GET` | `/smart-home/environment` | Mẫu DHT11 mới nhất và trạng thái node |
| `GET` | `/smart-home/environment/history` | Lịch sử nhiệt độ/độ ẩm cục bộ |
| `WS` | `/smart-home/environment/updates` | Cập nhật môi trường thời gian thực |
| `WS` | `/ws/gemini` | Giao tiếp thời gian thực với Gemini |
| `WS` | `/smart-home/lights/stream` | Nhận cập nhật trạng thái đèn |

## Bảo mật

Cấu hình Mosquitto hiện tại cho phép kết nối ẩn danh để thuận tiện khi trình diễn trong mạng LAN. Không mở cổng `1883` trực tiếp ra Internet. Khi triển khai thực tế, cần bật xác thực tài khoản, TLS và giới hạn quyền truy cập theo từng MQTT topic.

Không commit các file chứa thông tin nhạy cảm như:

- `backend/.env`
- `esp32-firmware/include/config.h`
- `esp32-sensor-firmware/include/config.h`
- `environment-firmware/include/config.h`
- API key, mật khẩu Wi-Fi hoặc thông tin đăng nhập MQTT

## Giới hạn của bản demo

- Bốn LED đại diện cho đèn gia dụng; project không đóng/ngắt tải điện bên ngoài.
- Topic `/state` xác nhận mức GPIO đã đặt. Nó không phải cảm biến độc lập kiểm
  tra độ sáng của LED.
- Nhận diện cháy dựa trên xử lý hình ảnh và chỉ mang tính minh họa học tập, không
  thay thế đầu báo cháy chuyên dụng.
- Camera là demo giáo dục: nhận diện dựa trên màu sắc có thể báo nhầm và không
  thay thế đầu báo khói/nhiệt chuyên dụng.
- Backend chỉ giám sát khi đang chạy và còn truy cập được camera IP trong mạng LAN;
  đây không phải hệ thống an toàn hoạt động liên tục.
- MQTT đang cho phép kết nối ẩn danh trong mạng LAN để thuận tiện trình diễn.

## Hướng phát triển

- Nếu cần Level 6, lắp và kiểm thử riêng node DHT22 trong
  `environment-firmware/`; hiện chưa có xác nhận phần cứng cho node tùy chọn này.
- Đưa cả hai ESP32 và backend lên cùng broker MQTT cloud có TLS rồi đo reconnect.
- Bổ sung cảm biến khí gas và chuyển động.
- Tích hợp lịch tự động bật/tắt thiết bị.
- Gửi thông báo cháy và sự cố đến điện thoại.
- Bổ sung xác thực người dùng và phân quyền thiết bị.
- Mã hóa kết nối MQTT bằng TLS.
- Lưu dữ liệu cảm biến để thống kê và trực quan hóa.
- Hỗ trợ cập nhật firmware ESP32 qua OTA.

## Giấy phép

Dự án được xây dựng phục vụ mục đích học tập và nghiên cứu. Hãy bổ sung tệp giấy phép phù hợp trước khi phân phối hoặc sử dụng trong sản phẩm thương mại.

## Kiểm tra camera IP

- Chạy `python -m unittest discover -s backend/tests` từ gốc project.
- Build web: `cd frontend && npm run build`.
- Build firmware: `cd esp32-firmware && pio run -e esp32dev`.
- Chạy backend, mở web: trạng thái camera phải hiện online và xem được MJPEG.
- Ngắt mạng/nguồn camera: web báo offline, snapshot trả 503; bốn LED vẫn điều khiển được.
- Khôi phục camera: backend tự kết nối lại, web nhận ảnh mới. Rút ESP32 chỉ làm
  đèn offline, không ảnh hưởng camera.
- Thử ảnh/video vùng màu giống lửa khi không mở phiên Gemini; kiểm tra cảnh báo
  web và loa MacBook. Nhấn **Bật âm thanh cảnh báo** để trình duyệt cho phép phát
  âm thanh; giữ trang web mở. Phát hiện vẫn chạy khi đóng web nhưng loa qua web
  cần trang hoạt động. Đây là demo giáo dục, không thay thế đầu báo khói/nhiệt.

Camera được đọc liên tục để tránh tồn đọng bộ đệm; khoảng lấy mẫu quy định tốc
độ JPEG/OpenCV. Timeout giới hạn thao tác mở/đọc, lỗi được ẩn thông tin đăng nhập,
khung lỗi hoặc quá hạn không được gửi cho web/Gemini. Phát hiện cháy dùng tác vụ
riêng để không chặn việc lấy khung hình mới.
