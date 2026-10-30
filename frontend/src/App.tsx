import { useCallback, useEffect, useMemo, useState } from "react";

import { EnvironmentCard } from "@/components/EnvironmentCard";
import { GeminiChatCard } from "@/components/GeminiChatCard";
import { HomeIcon, type HomeIconName } from "@/components/icons/HomeIcons";
import { LightControlCard } from "@/components/LightControlCard";
import { MonitoringPanel } from "@/components/MonitoringPanel";
import { MusicControlCard } from "@/components/MusicControlCard";
import { useEnvironment } from "@/hooks/useEnvironment";
import { GEMINI_MAX_IMAGE_SIZE, useGeminiRealtime } from "@/hooks/useGeminiRealtime";
import { useLights } from "@/hooks/useLights";
import { useMusicController } from "@/hooks/useMusicController";
import { cn } from "@/lib/utils";

interface FeedbackState { message: string; isError?: boolean }

const navItems: Array<{ href: string; label: string; icon: HomeIconName }> = [
  { href: "#top", label: "Tổng quan", icon: "home" },
  { href: "#rooms", label: "Không gian", icon: "bulb" },
  { href: "#monitoring", label: "Giám sát", icon: "camera" },
  { href: "#music", label: "Âm nhạc", icon: "music" },
  { href: "#assistant", label: "Trợ lý", icon: "spark" }
];

function AmbientNav() {
  return <nav className="ambient-nav" aria-label="Điều hướng chính"><a className="nav-brand" href="#top" aria-label="Về tổng quan"><HomeIcon name="home" /></a><div>{navItems.map((item) => <a key={item.href} href={item.href} aria-label={item.label} title={item.label}><HomeIcon name={item.icon} /><span>{item.label}</span></a>)}</div><span className="nav-signature">SH</span></nav>;
}

export default function App() {
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const [now, setNow] = useState(() => new Date());
  const showFeedback = useCallback((message: string, isError = false) => setFeedback({ message, isError }), []);
  useEffect(() => { const timer = window.setInterval(() => setNow(new Date()), 30_000); return () => window.clearInterval(timer); }, []);
  useEffect(() => { if (!feedback) return; const timer = window.setTimeout(() => setFeedback(null), 7_000); return () => window.clearTimeout(timer); }, [feedback]);

  const { lights, handleLightAction, applyLightUpdate, commands, connectionState, backendOnline } = useLights({ showFeedback });
  const { environment, history: environmentHistory, isLoading: isEnvironmentLoading, connectionError } = useEnvironment();
  const { musicState, liveMusicPosition, musicTitle, setMusicTitle, audioPlayerRef, currentSong, sortedLibrary, handleMusicSubmit, handleMusicPause, handleMusicPlay, setLiveMusicPosition, beginMusicPlayback, pauseCurrentMusic, resumeCurrentMusic } = useMusicController({ showFeedback });
  const gemini = useGeminiRealtime({ showFeedback, onLightUpdate: applyLightUpdate, beginMusicPlayback, pauseCurrentMusic, resumeCurrentMusic });

  const lightsOn = lights.filter((light) => light.is_on && light.device_online).length;
  const esp32Online = lights.length > 0 && lights.every((light) => light.device_online);
  const dateLabel = useMemo(() => new Intl.DateTimeFormat("vi-VN", { weekday: "long", day: "2-digit", month: "long" }).format(now), [now]);
  const timeLabel = useMemo(() => new Intl.DateTimeFormat("vi-VN", { hour: "2-digit", minute: "2-digit" }).format(now), [now]);

  return (
    <div id="top" className="ambient-app">
      <a href="#main-content" className="skip-link">Bỏ qua điều hướng</a><AmbientNav />
      <main id="main-content" className="ambient-main">
        <header className="home-hero">
          <div className="hero-copy"><p className="eyebrow">Smart Home · ESP32</p><h1>Chào bạn,<br/><em>nhà mình đang thế nào?</em></h1><p className="hero-subtitle">Một góc điều khiển ấm áp cho bốn không gian quen thuộc.</p></div>
          <div className="hero-time"><HomeIcon name="clock" /><time dateTime={now.toISOString()}>{timeLabel}</time><span>{dateLabel}</span></div>
          <div className="home-pulse" aria-label={`Có ${lightsOn} trên 4 đèn đang bật`}><span className="pulse-orbit"><HomeIcon name="home" /></span><div><strong>{lightsOn}<small>/4</small></strong><span>không gian đang sáng</span></div></div>
          <div className="hero-line" aria-hidden="true" />
        </header>

        <section className="system-ribbon" aria-label="Trạng thái hệ thống">
          <div className={cn("system-item", backendOnline && "is-good")}><HomeIcon name="server" /><span>Backend<strong>{backendOnline ? "Sẵn sàng" : "Mất kết nối"}</strong></span></div>
          <div className={cn("system-item", connectionState === "connected" && "is-good", connectionState === "reconnecting" && "is-warn")}><HomeIcon name="wifi" /><span>MQTT stream<strong>{connectionState === "connected" ? "Đồng bộ" : connectionState === "connecting" ? "Đang kết nối" : "Đang kết nối lại"}</strong></span></div>
          <div className={cn("system-item", esp32Online && "is-good")}><HomeIcon name="power" /><span>ESP32 lights<strong>{esp32Online ? "Online" : "Offline"}</strong></span></div>
          <div className={cn("system-item", gemini.cameraOnline && "is-good")}><HomeIcon name="camera" /><span>Camera IP<strong>{gemini.cameraOnline ? "Online" : "Offline"}</strong></span></div>
          <div className={cn("system-item", gemini.isGeminiConnected && "is-good")}><HomeIcon name="spark" /><span>Gemini<strong>{gemini.isGeminiConnected ? "Đã kết nối" : "Đang chờ"}</strong></span></div>
        </section>

        <LightControlCard lights={lights} commands={commands} onLightAction={handleLightAction} />
        <MonitoringPanel isCameraStreaming={gemini.isCameraStreaming} toggleCameraStream={gemini.toggleCameraStream} cameraError={gemini.cameraError} cameraOnline={gemini.cameraOnline} alertAudioEnabled={gemini.alertAudioEnabled} enableAlertAudio={gemini.enableAlertAudio} />
        <MusicControlCard musicState={musicState} liveMusicPosition={liveMusicPosition} musicTitle={musicTitle} onMusicTitleChange={setMusicTitle} onSubmit={handleMusicSubmit} audioPlayerRef={audioPlayerRef} currentSong={currentSong} sortedLibrary={sortedLibrary} onMusicPause={() => void handleMusicPause()} onMusicPlay={() => void handleMusicPlay()} onTimeUpdate={setLiveMusicPosition} />
        <EnvironmentCard environment={environment} history={environmentHistory} isLoading={isEnvironmentLoading} connectionError={connectionError} />
        <GeminiChatCard geminiStatus={gemini.geminiStatus} isGeminiConnected={gemini.isGeminiConnected} isRecording={gemini.isRecording} toggleRecording={gemini.toggleRecording} isMicPermissionDenied={gemini.isMicPermissionDenied} recordingError={gemini.recordingError} handleImageSelect={gemini.handleImageSelect} imageInputRef={gemini.imageInputRef} selectedImagePreview={gemini.selectedImagePreview} selectedImage={gemini.selectedImage} clearSelectedImage={gemini.clearSelectedImage} sendSelectedImage={gemini.sendSelectedImage} isUploadingImage={gemini.isUploadingImage} chatMessages={gemini.chatMessages} chatContainerRef={gemini.chatContainerRef} chatInput={gemini.chatInput} onChatInputChange={gemini.setChatInput} onChatSubmit={gemini.handleChatSubmit} onChatKeyDown={gemini.handleChatKeyDown} maxImageSize={GEMINI_MAX_IMAGE_SIZE} />
        <footer className="ambient-footer"><span>Smart Home ESP32</span><p>Bốn đèn · một ESP32 · một ngôi nhà gần gũi hơn</p></footer>
      </main>
      {feedback ? <div className={cn("feedback-toast", feedback.isError && "is-error")} role={feedback.isError ? "alert" : "status"}><HomeIcon name={feedback.isError ? "alert" : "shield"} /><span>{feedback.message}</span><button type="button" onClick={() => setFeedback(null)} aria-label="Đóng thông báo">×</button></div> : null}
    </div>
  );
}
