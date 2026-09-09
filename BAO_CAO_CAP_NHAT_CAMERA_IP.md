# Báo cáo cập nhật camera IP trong nhà

## Kiến trúc đúng yêu cầu

Camera giám sát/IP trong nhà truyền RTSP qua LAN/Wi-Fi trực tiếp tới FastAPI
trên MacBook. OpenCV VideoCapture giải mã khung hình; tác vụ riêng phát hiện
màu/vùng giống lửa rồi gửi cảnh báo và âm thanh tới web trên MacBook.
Camera tích hợp MacBook không được dùng; microphone và loa vẫn phục vụ giọng
nói, nhạc và cảnh báo. Camera không nối dây với ESP32.

Web/API/Gemini → FastAPI → MQTT → ESP32 DevKit → đúng bốn LED.
Phòng khách GPIO 16, phòng ngủ GPIO 17, nhà bếp GPIO 18, ban công GPIO 19.
Mỗi LED có điện trở 330 Ω, active-LOW: ON = LOW, OFF = HIGH.
Backend chỉ xác nhận lệnh đèn sau bản tin smarthome/lights/<id>/state phù hợp.
Firmware chỉ còn Wi-Fi/MQTT và điều khiển đèn; đã bỏ HTTP camera và cấu hình chân camera.

## Backend và web

Service camera khởi động/dừng theo lifespan FastAPI, không phụ thuộc phiên Gemini.
Đọc RTSP trong worker để không chặn event loop, giới hạn timeout mở/đọc và tự
kết nối lại. Khung rỗng, sai định dạng, mã hóa lỗi hoặc quá lớn bị loại bỏ;
không phục vụ ảnh cũ khi mất kết nối. Tác vụ phát hiện cháy độc lập với tác vụ đọc.
Web lấy snapshot/MJPEG và trạng thái online/offline qua backend; URL và thông tin
đăng nhập không xuất hiện trong response. Lỗi native được thay bằng thông báo an toàn.
Khi gửi hình cho Gemini, web lấy JPEG mới nhất từ backend.
Trình duyệt chỉ xin quyền microphone cho giọng nói, không xin quyền camera.
Nút bật âm thanh cho phép nghe cảnh báo qua loa MacBook khi trang web đang mở.

## Cấu hình còn chờ thiết bị

Cần hãng và model camera để xác nhận hỗ trợ và đường dẫn RTSP. Không yêu cầu
người dùng gửi mật khẩu. HOME_CAMERA_RTSP_URL được điền riêng trong backend/.env;
file mẫu để trống và chỉ minh họa cú pháp. ONVIF có thể dùng để lấy URI stream,
chưa triển khai dò ONVIF tự động. Không commit .env hoặc include/config.h.

## Kiểm chứng

Test tự động mô phỏng mất kết nối, mở thất bại, reconnect, khung không hợp lệ,
ẩn thông tin đăng nhập, vòng đời service và phát hiện cháy độc lập với Gemini.
Build frontend và firmware, chạy test backend; kết quả thực tế ghi ở cuối báo cáo.
Cần thử với camera thật sau khi biết model: ngắt/cấp lại mạng camera, kiểm tra
web tự phục hồi và đèn MQTT vẫn độc lập. Dữ liệu hội thoại, đèn và phiên hiện có
được giữ nguyên trong quá trình sửa.

## Giới hạn demo

Thuật toán màu có thể báo nhầm hoặc bỏ sót. Đây là demo giáo dục, không phải hệ
thống báo cháy an toàn và không thay thế cảm biến khói/nhiệt được chứng nhận.
Backend cần đang chạy và truy cập được camera. Âm thanh qua web cần trang mở,
người dùng bật âm thanh và loa MacBook không bị tắt.

## Kết quả kiểm tra tự động

- Firmware `pio run -e esp32dev`: PASS; RAM 44.776 byte, flash 733.933 byte.
- Frontend `tsc --noEmit` và `npm run build`: PASS. Sửa hai lỗi kiểu dữ liệu âm
  thanh có sẵn (thuộc tính playsinline và sao chép PCM vào AudioBuffer).
- Backend: 29 test PASS trên Python 3.12/OpenCV 5 trong container kiểm thử riêng,
  dùng source mới, tắt mạng và không mount dữ liệu hoặc cấu hình bí mật.
- Kiểm tra native RTSP với địa chỉ loopback không phục vụ: lỗi không lộ thông
  tin đăng nhập; API status và snapshot 200/503 đúng kỳ vọng.
- Ba file JSON hội thoại, trạng thái đèn và phiên giống hệt trước khi sửa.
- Chưa thử camera thật; chờ hãng/model trước khi chốt URL RTSP và thử phần cứng.
