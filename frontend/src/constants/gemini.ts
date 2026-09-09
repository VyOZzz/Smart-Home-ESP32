export const INPUT_SAMPLE_RATE = 16000; // Sample rate expected by Gemini Live for incoming audio
export const OUTPUT_SAMPLE_RATE = 24000; // Sample rate returned by Gemini Live when synthesising speech
export const PCM_CHUNK_DURATION_MS = 100; // Chunk microphone audio in ~100ms windows for streaming
export const MAX_IMAGE_SIZE_BYTES = 4 * 1024 * 1024; // Cap image uploads at 4MB to keep websocket payload reasonable
export const CAMERA_FRAME_INTERVAL_MS = 500; // Forward the latest ESP32 frame to Gemini every 0.5s
