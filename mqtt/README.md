# MQTT broker

Project dùng Eclipse Mosquitto làm cầu nối giữa FastAPI trên laptop và ESP32.
Broker lắng nghe cổng TCP `1883` và lưu retained messages vào Docker volume
`mosquitto_data`.

## Khởi động

Yêu cầu Docker Desktop đang chạy:

```powershell
docker compose up -d mqtt
docker compose ps
docker compose logs mqtt
```

Khi container healthy, điền địa chỉ IPv4 LAN của laptop vào
`esp32-firmware/include/config.h`:

```cpp
#define MQTT_HOST "192.168.1.10"
#define MQTT_PORT 1883
```

Tìm IPv4 của laptop trên Windows:

```powershell
ipconfig
```

Nếu ESP32 không kết nối được, cho phép inbound TCP port `1883` trong Windows
Firewall và kiểm tra laptop/ESP32 đang cùng mạng Wi-Fi. Không dùng `localhost`
trong firmware.

## Kiểm tra broker

Mở terminal thứ nhất:

```powershell
docker compose exec mqtt mosquitto_sub -h localhost -t "smarthome/#" -v
```

Mở terminal thứ hai:

```powershell
docker compose exec mqtt mosquitto_pub -h localhost -t "smarthome/lights/living-room/set" -m "ON"
```

Khi ESP32 đã kết nối, terminal subscribe sẽ nhận thêm trạng thái tại
`smarthome/lights/living-room/state`.

## Bảo mật

Cấu hình hiện tại dùng `allow_anonymous true` để đơn giản hóa giai đoạn demo
trong LAN. Không forward cổng `1883` trên router và không public broker ra
Internet. Trước khi triển khai thực tế, cần bật password authentication và TLS.
