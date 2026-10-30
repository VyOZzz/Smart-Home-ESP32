import { type ChangeEvent, type FormEvent, type KeyboardEvent } from "react";

import { HomeIcon } from "@/components/icons/HomeIcons";
import { formatFileSize } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types/chat";

interface GeminiChatCardProps {
  geminiStatus: string; isGeminiConnected: boolean; isRecording: boolean; toggleRecording: () => void;
  isMicPermissionDenied: boolean; recordingError: string | null;
  handleImageSelect: (event: ChangeEvent<HTMLInputElement>) => void; imageInputRef: React.RefObject<HTMLInputElement>;
  selectedImagePreview: string | null; selectedImage: File | null; clearSelectedImage: () => void;
  sendSelectedImage: () => Promise<void> | void; isUploadingImage: boolean; chatMessages: ChatMessage[];
  chatContainerRef: React.RefObject<HTMLDivElement>; chatInput: string; onChatInputChange: (value: string) => void;
  onChatSubmit: (event: FormEvent<HTMLFormElement>) => void; onChatKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  maxImageSize: number;
}

export function GeminiChatCard(props: GeminiChatCardProps) {
  const { geminiStatus, isGeminiConnected, isRecording, toggleRecording, isMicPermissionDenied, recordingError,
    handleImageSelect, imageInputRef, selectedImagePreview, selectedImage, clearSelectedImage, sendSelectedImage,
    isUploadingImage, chatMessages, chatContainerRef, chatInput, onChatInputChange, onChatSubmit, onChatKeyDown, maxImageSize } = props;

  return (
    <section id="assistant" className="home-section assistant-section" aria-labelledby="assistant-title">
      <div className="assistant-intro">
        <span className="assistant-mark"><HomeIcon name="spark" /></span>
        <p className="eyebrow">Trợ lý, không phải trung tâm</p>
        <h2 id="assistant-title">Gemini ở đây khi bạn cần.</h2>
        <p>Điều khiển nhà bằng văn bản hoặc giọng nói. Micro chỉ được yêu cầu khi bạn chủ động bật.</p>
        <div className={cn("assistant-connection", isGeminiConnected && "is-good")} role="status"><span />{geminiStatus}</div>
        <button type="button" className={cn("voice-orb", isRecording && "is-recording")} onClick={toggleRecording} disabled={!isGeminiConnected}>
          <HomeIcon name="mic" /><span>{isRecording ? "Dừng trò chuyện" : "Bắt đầu bằng giọng nói"}</span>
        </button>
        {isMicPermissionDenied ? <p className="inline-error" role="alert">Quyền micro bị từ chối. Hãy kiểm tra cài đặt trình duyệt.</p> : null}
        {recordingError ? <p className="inline-error" role="alert">{recordingError}</p> : null}
      </div>

      <div className="conversation-panel">
        <div className="conversation-head"><div><p className="eyebrow">Cuộc trò chuyện</p><h3>Gợi ý nhẹ nhàng cho ngôi nhà</h3></div><HomeIcon name="message" /></div>
        <div ref={chatContainerRef} className="conversation-stream" aria-live="polite">
          {chatMessages.length ? chatMessages.map((message) => (
            <div key={message.id} className={cn("message-row", `message-row--${message.role}`)}>
              <span className="message-author">{message.role === "user" ? "Bạn" : message.role === "assistant" ? "Gemini" : "Hệ thống"}</span>
              <div className="message-body">
                {message.content ? <p>{message.content}</p> : null}
                {message.imageDataUrl ? <img src={message.imageDataUrl} alt={message.role === "user" ? "Ảnh bạn đã gửi" : "Ảnh từ Gemini"} /> : null}
              </div>
              {message.streaming ? <small>Đang trả lời…</small> : null}
            </div>
          )) : <div className="conversation-empty"><HomeIcon name="leaf" /><p>Không cần phải nói gì cả.</p><span>Khi cần, hãy nhờ Gemini điều khiển đèn hoặc phát nhạc.</span></div>}
        </div>

        {selectedImagePreview ? <div className="selected-image"><img src={selectedImagePreview} alt="Ảnh đã chọn để gửi tới Gemini" /><div><strong>{selectedImage?.name}</strong><span>{selectedImage ? formatFileSize(selectedImage.size) : ""}</span></div><button type="button" onClick={clearSelectedImage}>Bỏ chọn</button></div> : null}

        <form className="composer" onSubmit={onChatSubmit}>
          <textarea aria-label="Tin nhắn gửi Gemini" value={chatInput} onChange={(event) => onChatInputChange(event.target.value)} onKeyDown={onChatKeyDown} rows={2} placeholder="Nhờ Gemini hỗ trợ…" />
          <div className="composer-actions">
            <label className={cn("icon-action", (!isGeminiConnected || isUploadingImage) && "is-disabled")} title={`Gửi ảnh tối đa ${formatFileSize(maxImageSize)}`}>
              <HomeIcon name="image" /><span className="sr-only">Chọn ảnh gửi tới Gemini</span>
              <input ref={imageInputRef} type="file" accept="image/*" onChange={handleImageSelect} disabled={!isGeminiConnected || isUploadingImage} />
            </label>
            {selectedImage ? <button type="button" className="icon-action" onClick={() => void sendSelectedImage()} disabled={!isGeminiConnected || isUploadingImage} aria-label="Gửi ảnh"><HomeIcon name="send" /></button> : null}
            <button type="submit" className="send-button" disabled={!isGeminiConnected || !chatInput.trim()}><span>Gửi</span><HomeIcon name="send" /></button>
          </div>
        </form>
      </div>
    </section>
  );
}
