from __future__ import annotations

import os
import ipaddress

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(BACKEND_ROOT / ".env")

# Native FFmpeg errors can contain credential-bearing URLs.
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "-8"
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")


def _env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    return Path(value) if value else default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "f", "no", "n", "off"}:
        return False
    return default


def _env_str(name: str, default: Optional[str]) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return default
    return value


def _camera_rtsp_url() -> str:
    """Override only the RTSP host from a non-secret local file when present."""
    rtsp_url = _env_str("HOME_CAMERA_RTSP_URL", "") or ""
    ip_file = _env_path(
        "HOME_CAMERA_IP_FILE", BACKEND_ROOT / "data" / "camera_ip.txt"
    )
    try:
        camera_ip = ip_file.read_text(encoding="utf-8").strip()
    except OSError:
        return rtsp_url
    if not camera_ip:
        return rtsp_url
    try:
        ipaddress.ip_address(camera_ip)
        parsed = urlsplit(rtsp_url)
        port = parsed.port
    except (ValueError, TypeError):
        return rtsp_url
    if parsed.scheme not in {"rtsp", "rtsps"} or not parsed.hostname:
        return rtsp_url

    userinfo, separator, _host = parsed.netloc.rpartition("@")
    host = f"[{camera_ip}]" if ":" in camera_ip else camera_ip
    host_port = f"{host}:{port}" if port is not None else host
    netloc = f"{userinfo}@{host_port}" if separator else host_port
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


@dataclass
class Settings:
    app_name: str = field(default_factory=lambda: _env_str("APP_NAME", "IoT Smart Home"))
    google_api_key: Optional[str] = field(
        default_factory=lambda: _env_str("GOOGLE_API_KEY", None)
    )
    gemini_model: str = field(
        default_factory=lambda: _env_str("GEMINI_MODEL", "gemini-3.1-flash-live-preview")
    )
    gemini_tts_model: str = field(
        default_factory=lambda: _env_str("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
    )
    gemini_image_model: str = field(
        default_factory=lambda: _env_str("GEMINI_IMAGE_MODEL", "gemini-3.5-flash")
    )
    conversation_history_file: Path = field(
        default_factory=lambda: _env_path(
            "CONVERSATION_HISTORY_FILE", Path("data") / "conversation_history.json"
        )
    )
    session_handle_file: Path = field(
        default_factory=lambda: _env_path(
            "SESSION_HANDLE_FILE", Path("data") / "session_handle.json"
        )
    )
    session_timeout_seconds: int = field(
        default_factory=lambda: _env_int("SESSION_TIMEOUT_SECONDS", 300)
    )
    light_state_file: Path = field(
        default_factory=lambda: _env_path("LIGHT_STATE_FILE", Path("data") / "light_state.json")
    )
    music_directory: Path = field(
        default_factory=lambda: _env_path("MUSIC_DIRECTORY", Path("music"))
    )
    music_similarity_threshold: float = field(
        default_factory=lambda: _env_float("MUSIC_SIMILARITY_THRESHOLD", 0.72)
    )
    websocket_ping_interval: int = field(
        default_factory=lambda: _env_int("WEBSOCKET_PING_INTERVAL", 10)
    )
    websocket_receive_timeout: int = field(
        default_factory=lambda: _env_int("WEBSOCKET_RECEIVE_TIMEOUT", 30)
    )
    websocket_config_timeout: int = field(
        default_factory=lambda: _env_int("WEBSOCKET_CONFIG_TIMEOUT", 10)
    )
    save_captured_image: bool = field(
        default_factory=lambda: _env_bool("SAVE_CAPTURED_IMAGE", False)
    )
    captured_images_directory: Path = field(
        default_factory=lambda: _env_path("CAPTURED_IMAGES_DIRECTORY", Path("data") / "images")
    )
    capture_interval_seconds: float = field(
        default_factory=lambda: max(0.1, _env_float("CAPTURE_INTERVAL_SECONDS", 0.5))
    )
    fire_alert_cooldown_seconds: float = field(
        default_factory=lambda: max(0.0, _env_float("FIRE_ALERT_COOLDOWN_SECONDS", 10.0))
    )
    fire_alert_audio_file: Path = field(
        default_factory=lambda: _env_path(
            "FIRE_ALERT_AUDIO_FILE", Path("data") / "fire_alert_audio.b64"
        )
    )
    home_camera_rtsp_url: str = field(
        repr=False, default_factory=_camera_rtsp_url
    )
    camera_capture_interval_seconds: float = field(
        default_factory=lambda: max(
            0.2, _env_float("CAMERA_CAPTURE_INTERVAL_SECONDS", 0.5)
        )
    )
    camera_request_timeout_seconds: float = field(
        default_factory=lambda: max(0.2, _env_float("CAMERA_REQUEST_TIMEOUT_SECONDS", 2.0))
    )
    camera_reconnect_interval_seconds: float = field(
        default_factory=lambda: max(0.1, _env_float("CAMERA_RECONNECT_INTERVAL_SECONDS", 2.0))
    )
    camera_max_frame_bytes: int = field(
        default_factory=lambda: max(1024, _env_int("CAMERA_MAX_FRAME_BYTES", 512_000))
    )
    mqtt_host: str = field(default_factory=lambda: _env_str("MQTT_HOST", "mqtt"))
    mqtt_port: int = field(default_factory=lambda: _env_int("MQTT_PORT", 1883))
    mqtt_client_id: str = field(
        default_factory=lambda: _env_str("MQTT_CLIENT_ID", "smarthome-backend")
    )
    mqtt_username: Optional[str] = field(
        default_factory=lambda: _env_str("MQTT_USERNAME", None)
    )
    mqtt_password: Optional[str] = field(
        repr=False, default_factory=lambda: _env_str("MQTT_PASSWORD", None)
    )
    mqtt_tls_enabled: bool = field(
        default_factory=lambda: _env_bool("MQTT_TLS_ENABLED", False)
    )
    mqtt_tls_ca_cert: Optional[Path] = field(
        default_factory=lambda: (
            _env_path("MQTT_TLS_CA_CERT", Path(""))
            if _env_str("MQTT_TLS_CA_CERT", "")
            else None
        )
    )
    mqtt_tls_certfile: Optional[Path] = field(
        default_factory=lambda: (
            _env_path("MQTT_TLS_CERTFILE", Path(""))
            if _env_str("MQTT_TLS_CERTFILE", "")
            else None
        )
    )
    mqtt_tls_keyfile: Optional[Path] = field(
        default_factory=lambda: (
            _env_path("MQTT_TLS_KEYFILE", Path(""))
            if _env_str("MQTT_TLS_KEYFILE", "")
            else None
        )
    )
    mqtt_tls_insecure: bool = field(
        default_factory=lambda: _env_bool("MQTT_TLS_INSECURE", False)
    )
    mqtt_command_timeout_seconds: float = field(
        default_factory=lambda: max(0.1, _env_float("MQTT_COMMAND_TIMEOUT_SECONDS", 3.0))
    )
    environment_device_id: str = field(
        default_factory=lambda: _env_str("ENVIRONMENT_DEVICE_ID", "esp32-sensor")
    )
    environment_sensor_id: str = field(
        default_factory=lambda: _env_str("ENVIRONMENT_SENSOR_ID", "room-1")
    )
    environment_stale_after_seconds: float = field(
        default_factory=lambda: max(
            1.0, _env_float("ENVIRONMENT_STALE_AFTER_SECONDS", 30.0)
        )
    )
    environment_history_db: Path = field(
        default_factory=lambda: _env_path(
            "ENVIRONMENT_HISTORY_DB", Path("data") / "environment_history.db"
        )
    )
    environment_history_max_rows: int = field(
        default_factory=lambda: max(
            1, _env_int("ENVIRONMENT_HISTORY_MAX_ROWS", 10_000)
        )
    )
    default_lights: tuple[tuple[str, bool], ...] = field(
        default_factory=lambda: (
            ("Phòng khách", False),
            ("Phòng ngủ", False),
            ("Nhà bếp", False),
            ("Ban công", False),
        )
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
