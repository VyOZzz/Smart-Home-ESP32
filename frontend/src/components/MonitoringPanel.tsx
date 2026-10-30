import { HomeIcon } from "@/components/icons/HomeIcons";
import { cn } from "@/lib/utils";

interface MonitoringPanelProps {
  isCameraStreaming: boolean;
  toggleCameraStream: () => void;
  cameraError: string | null;
  cameraOnline: boolean;
  alertAudioEnabled: boolean;
  enableAlertAudio: () => void;
}

export function MonitoringPanel({ isCameraStreaming, toggleCameraStream, cameraError, cameraOnline, alertAudioEnabled, enableAlertAudio }: MonitoringPanelProps) {
  return (
    <section id="monitoring" className="home-section" aria-labelledby="monitoring-title">
      <div className="section-heading">
        <div><p className="eyebrow">Quan sát độc lập</p><h2 id="monitoring-title">Góc an tâm</h2></div>
        <p className="section-note">Camera IP được FastAPI đọc trực tiếp, không phụ thuộc phiên Gemini.</p>
      </div>
      <div className="monitor-layout">
        <div className="camera-frame">
          <div className="camera-meta">
            <span className={cn("signal-badge", cameraOnline && "is-good")}><span />Camera IP · {cameraOnline ? "online" : "offline"}</span>
            <button type="button" className="text-button" onClick={toggleCameraStream}>{isCameraStreaming ? "Ẩn hình ảnh" : "Xem trực tiếp"}</button>
          </div>
          <div className="camera-viewport">
            <img src={isCameraStreaming && cameraOnline ? "/smart-home/camera/stream" : undefined} alt="Luồng trực tiếp từ camera IP trong nhà" className={cn(isCameraStreaming && cameraOnline && "is-visible")} />
            <div className="camera-placeholder">
              <HomeIcon name="camera" />
              <p>{cameraOnline ? "Hình ảnh đang được ẩn" : "Camera chưa cung cấp khung hình"}</p>
              <span>Backend vẫn chạy phát hiện cháy độc lập</span>
            </div>
            <span className="viewfinder viewfinder--one" aria-hidden="true" /><span className="viewfinder viewfinder--two" aria-hidden="true" />
          </div>
          {cameraError ? <p className="inline-error" role="alert">{cameraError}</p> : null}
        </div>

        <aside className="safety-note">
          <span className="safety-icon"><HomeIcon name="shield" /></span>
          <p className="eyebrow">Fire detection</p>
          <h3>Quan sát có trách nhiệm</h3>
          <p>Đây là demo giáo dục xử lý hình ảnh. Không phải hệ thống giám sát liên tục và không thay thế đầu báo khói hoặc nhiệt đã được chứng nhận.</p>
          <button type="button" className="ambient-button ambient-button--quiet" onClick={enableAlertAudio}>
            <HomeIcon name="volume" />{alertAudioEnabled ? "Âm thanh cảnh báo đã bật" : "Bật âm thanh trên MacBook"}
          </button>
          <small>Trình duyệt không truy cập webcam. Camera truyền qua backend dưới dạng JPEG/MJPEG.</small>
        </aside>
      </div>
    </section>
  );
}
