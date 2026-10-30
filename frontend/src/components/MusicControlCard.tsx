import type { FormEvent } from "react";

import { HomeIcon } from "@/components/icons/HomeIcons";
import { formatDuration } from "@/lib/format";
import type { MusicPlaybackState } from "@/types/smart-home";

interface MusicControlCardProps {
  musicState: MusicPlaybackState | null; liveMusicPosition: number; musicTitle: string;
  onMusicTitleChange: (value: string) => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  audioPlayerRef: React.RefObject<HTMLAudioElement>; currentSong: { title: string; url: string } | null;
  sortedLibrary: string[]; onMusicPause: () => void; onMusicPlay: () => void; onTimeUpdate: (time: number) => void;
}

export function MusicControlCard({ musicState, liveMusicPosition, musicTitle, onMusicTitleChange, onSubmit, audioPlayerRef, currentSong, sortedLibrary, onMusicPause, onMusicPlay, onTimeUpdate }: MusicControlCardProps) {
  const duration = musicState?.duration_seconds ?? 0;
  const progress = duration > 0 ? Math.min((liveMusicPosition / duration) * 100, 100) : 0;
  return (
    <section id="music" className="music-section" aria-labelledby="music-title">
      <div className="record-art" aria-hidden="true"><span className="record-ring" /><HomeIcon name="music" /></div>
      <div className="music-main">
        <p className="eyebrow">Âm thanh trong nhà</p><h2 id="music-title">Một bản nhạc cho khoảnh khắc này.</h2>
        <form className="music-search" onSubmit={onSubmit}>
          <label htmlFor="song-title" className="sr-only">Tên bài hát</label>
          <input id="song-title" value={musicTitle} onChange={(event) => onMusicTitleChange(event.target.value)} placeholder="Tìm một bài trong thư viện…" />
          <button type="submit"><HomeIcon name="music" />Tìm & phát</button>
        </form>
        <div className="now-playing">
          <div><span>{musicState?.status === "playing" ? "Đang phát" : musicState?.status === "paused" ? "Đang tạm dừng" : "Sẵn sàng"}</span><strong>{musicState?.matched_song ?? "Chưa chọn bài hát"}</strong></div>
          <span className="music-time">{formatDuration(liveMusicPosition)} / {duration ? formatDuration(duration) : "--:--"}</span>
        </div>
        <div className="progress-rail" aria-hidden="true"><span style={{ width: `${progress}%` }} /></div>
        <audio ref={audioPlayerRef} controls autoPlay playsInline preload="auto" src={currentSong?.url} onPause={onMusicPause} onPlay={onMusicPlay} onTimeUpdate={(event) => onTimeUpdate(event.currentTarget.currentTime)}>Trình duyệt không hỗ trợ phát nhạc.</audio>
      </div>
      <aside className="music-library"><p>Thư viện trên MacBook</p><span>{sortedLibrary.length} bài có sẵn</span><div>{sortedLibrary.length ? sortedLibrary.map((song) => <button key={song} type="button" onClick={() => onMusicTitleChange(song)}>{song}</button>) : <em>Thư viện trống</em>}</div></aside>
    </section>
  );
}
