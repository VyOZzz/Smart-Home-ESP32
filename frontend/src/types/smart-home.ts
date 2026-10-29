export interface LightState {
  location: string;
  is_on: boolean;
  device_online: boolean;
}

export interface EnvironmentState {
  device_id: string;
  online: boolean;
  temperature_c: number | null;
  humidity_percent: number | null;
  observed_at: string | number | null;
  last_error: string | null;
}

export interface EnvironmentHistoryPoint {
  temperature_c: number | null;
  humidity_percent: number | null;
  observed_at: string | number;
}

export interface MusicPlaybackState {
  requested_title: string | null;
  matched_song: string | null;
  status: "stopped" | "playing" | "paused";
  position_seconds: number;
  duration_seconds: number | null;
  updated_at: number;
}

export interface MusicPlaybackResponse {
  selected_song: string;
  stream_url: string;
  playback_state: MusicPlaybackState;
}
