import asyncio
import json
import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Literal

from app.core.config import settings
from app.services.esp32_gateway import Esp32Gateway

logger = logging.getLogger(__name__)


@dataclass
class LightState:
    location: str
    is_on: bool = False
    device_online: bool = False


class LightingService:
    """Manage the state of smart home lights."""

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        self.storage_path = storage_path or settings.light_state_file
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._states: Dict[str, LightState] = {}
        self._state_lock = threading.RLock()
        self._listeners: List[Tuple[asyncio.AbstractEventLoop, "asyncio.Queue[dict]"]] = []
        self._listener_lock = threading.Lock()
        self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _default_states(self) -> Dict[str, LightState]:
        defaults: Dict[str, LightState] = {}
        for name, is_on in settings.default_lights:
            location_key = name.lower().strip()
            defaults[location_key] = LightState(location=name, is_on=is_on)
        return defaults

    def _load(self) -> None:
        with self._state_lock:
            defaults = self._default_states()
            if not self.storage_path.exists():
                self._states = defaults
                self._persist()
                return
            try:
                with self.storage_path.open("r", encoding="utf-8") as file:
                    payload = json.load(file)
            except json.JSONDecodeError:
                logger.warning("Corrupted light state file, recreating it with defaults")
                self._states = defaults
                self._persist()
                return

            states: Dict[str, LightState] = {}
            if isinstance(payload, dict):
                for location_key, default_state in defaults.items():
                    raw_state = payload.get(location_key, {})
                    is_on = bool(raw_state.get("is_on")) if isinstance(raw_state, dict) else False
                    states[location_key] = LightState(
                        location=default_state.location,
                        is_on=is_on,
                        device_online=self._states.get(
                            location_key, LightState(default_state.location)
                        ).device_online,
                    )
            else:
                logger.warning("Unexpected light state format; recreating defaults")
                states = defaults
            self._states = states

    def _persist(self) -> None:
        with self._state_lock:
            with self.storage_path.open("w", encoding="utf-8") as file:
                json.dump(
                    {
                        loc: {"name": state.location, "is_on": state.is_on}
                        for loc, state in self._states.items()
                    },
                    file,
                    ensure_ascii=False,
                    indent=2,
                )

    # ------------------------------------------------------------------
    # Observer helpers
    # ------------------------------------------------------------------

    def _notify_listeners(self, payload: dict) -> None:
        with self._listener_lock:
            listeners = list(self._listeners)
        for loop, queue in listeners:
            try:
                loop.call_soon_threadsafe(queue.put_nowait, payload)
            except RuntimeError:
                # event loop might be closed; drop the subscriber
                self.remove_listener(queue)

    async def add_listener(self) -> "asyncio.Queue[dict]":
        loop = asyncio.get_running_loop()
        queue: "asyncio.Queue[dict]" = asyncio.Queue()
        with self._listener_lock:
            self._listeners.append((loop, queue))
        # Provide an immediate snapshot to new listeners
        snapshot = [
            {"location": state.location, "is_on": state.is_on}
            for state in self.get_all_states()
        ]
        await queue.put({"type": "snapshot", "lights": snapshot})
        return queue

    def remove_listener(self, queue: "asyncio.Queue[dict]") -> None:
        with self._listener_lock:
            self._listeners = [
                (loop, q)
                for loop, q in self._listeners
                if q is not queue
            ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def toggle_light(self, location: str, turn_on: bool) -> LightState:
        self._load()
        location_key = location.lower().strip()
        display_name = location.strip()
        state = self._states.get(location_key, LightState(location=display_name))
        state.location = display_name
        state.is_on = turn_on
        self._states[location_key] = state
        self._persist()
        logger.info("Light %s is now %s", location_key, "on" if state.is_on else "off")
        self._notify_listeners({"type": "update", "light": asdict(state)})
        return state

    def apply_device_state(self, location: str, turn_on: bool) -> LightState:
        """Store a state reported by the ESP32, never a requested state."""
        self._load()
        location_key = location.lower().strip()
        with self._state_lock:
            state = self._states.get(location_key, LightState(location=location))
            state.location = location
            state.is_on = turn_on
            state.device_online = True
            self._states[location_key] = state
            self._persist()
        logger.info("ESP32 confirmed %s -> %s", location_key, "on" if turn_on else "off")
        self._notify_listeners({"type": "update", "light": asdict(state)})
        return state

    def set_device_online(self, online: bool) -> None:
        self._load()
        with self._state_lock:
            for state in self._states.values():
                state.device_online = online
        self._notify_listeners({"type": "device_status", "online": online})

    def get_light_state(self, location: str) -> LightState:
        self._load()
        location_key = location.lower().strip()
        state = self._states.get(location_key)
        if state:
            return state
        return LightState(location=location.strip())

    def get_all_states(self) -> Iterable[LightState]:
        self._load()
        return list(self._states.values())


class MusicService:
    """Select a song that best matches the requested title."""

    def __init__(self, music_directory: Optional[Path] = None, threshold: Optional[float] = None) -> None:
        self.music_directory = music_directory or settings.music_directory
        self.threshold = threshold if threshold is not None else settings.music_similarity_threshold
        self.music_directory.mkdir(parents=True, exist_ok=True)
        self._catalog = self._build_catalog()

    def _build_catalog(self) -> List[str]:
        supported_ext = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"}
        catalog = []
        if not self.music_directory.exists():
            return catalog
        for item in self.music_directory.iterdir():
            if item.is_file() and item.suffix.lower() in supported_ext:
                catalog.append(item.stem)
        return catalog

    def refresh(self) -> None:
        self._catalog = self._build_catalog()

    def list_available_songs(self) -> List[str]:
        if not self._catalog:
            self.refresh()
        return list(self._catalog)

    def _similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(a=a.lower(), b=b.lower()).ratio()

    def choose_song(self, requested_title: str) -> Optional[str]:
        if not requested_title:
            return None
        if not self._catalog:
            self.refresh()
        if not self._catalog:
            return None
        best_match = max(
            self._catalog,
            key=lambda track: self._similarity(requested_title, track),
        )
        score = self._similarity(requested_title, best_match)
        logger.info("Best song match for '%s' is '%s' (score %.3f)", requested_title, best_match, score)
        if score >= self.threshold:
            return best_match
        return None

    def find_song_file(self, track_title: str) -> Optional[Path]:
        if not track_title:
            return None
        if not self.music_directory.exists():
            return None
        for item in self.music_directory.iterdir():
            if item.is_file() and item.stem == track_title:
                return item
        return None

    def get_song_duration(self, track_title: str) -> Optional[float]:
        file_path = self.find_song_file(track_title)
        if not file_path:
            return None
        try:
            from mutagen import File  # type: ignore
        except ImportError:
            logger.debug("mutagen library is not available; cannot determine song duration")
            return None

        try:
            audio = File(file_path)
        except Exception:  # pylint: disable=broad-except
            logger.exception("Failed to read audio metadata for %%s", file_path)
            return None

        if audio is None or getattr(audio, "info", None) is None:
            return None

        length = getattr(audio.info, "length", None)
        if length is None:
            return None
        try:
            return float(length)
        except (TypeError, ValueError):
            return None


@dataclass
class MusicPlaybackState:
    requested_title: Optional[str] = None
    matched_song: Optional[str] = None
    status: Literal["stopped", "playing", "paused"] = "stopped"
    position_seconds: float = 0.0
    duration_seconds: Optional[float] = None
    updated_at: float = field(default_factory=lambda: time.time())

    def copy(self) -> "MusicPlaybackState":
        return MusicPlaybackState(
            requested_title=self.requested_title,
            matched_song=self.matched_song,
            status=self.status,
            position_seconds=self.position_seconds,
            duration_seconds=self.duration_seconds,
            updated_at=self.updated_at,
        )

    def effective_position(self, reference_time: Optional[float] = None) -> float:
        base_position = max(self.position_seconds, 0.0)
        if self.status != "playing":
            return base_position
        now = reference_time or time.time()
        elapsed = max(0.0, now - self.updated_at)
        return base_position + elapsed


class SmartHomeService:
    def __init__(
        self,
        lighting_service: Optional[LightingService] = None,
        music_service: Optional[MusicService] = None,
        esp32_gateway: Optional[Esp32Gateway] = None,
    ) -> None:
        self.lighting_service = lighting_service or LightingService()
        self.music_service = music_service or MusicService()
        self._light_id_to_name = {
            "living-room": "Phòng khách",
            "bedroom": "Phòng ngủ",
            "kitchen": "Nhà bếp",
            "balcony": "Ban công",
        }
        self._location_aliases = {
            "living-room": "living-room",
            "phòng khách": "living-room",
            "phong khach": "living-room",
            "bedroom": "bedroom",
            "phòng ngủ": "bedroom",
            "phong ngu": "bedroom",
            "kitchen": "kitchen",
            "nhà bếp": "kitchen",
            "nha bep": "kitchen",
            "bếp": "kitchen",
            "bep": "kitchen",
            "balcony": "balcony",
            "ban công": "balcony",
            "ban cong": "balcony",
        }
        self.esp32_gateway = esp32_gateway or Esp32Gateway(
            host=settings.mqtt_host,
            port=settings.mqtt_port,
            client_id=settings.mqtt_client_id,
            username=settings.mqtt_username,
            password=settings.mqtt_password,
            command_timeout=settings.mqtt_command_timeout_seconds,
            on_state=self._handle_esp32_state,
            on_status=self.lighting_service.set_device_online,
        )
        self.esp32_gateway.on_state = self._handle_esp32_state
        self.esp32_gateway.on_status = self.lighting_service.set_device_online
        self._music_playback_state = MusicPlaybackState()
        self._music_listeners: List[
            Tuple[asyncio.AbstractEventLoop, "asyncio.Queue[dict]"]
        ] = []
        self._music_listener_lock = threading.Lock()

    def turn_on_light(self, location: str) -> LightState:
        return self._set_light(location, True)

    def turn_off_light(self, location: str) -> LightState:
        return self._set_light(location, False)

    def start(self) -> None:
        self.esp32_gateway.start()

    def stop(self) -> None:
        self.esp32_gateway.stop()

    def _resolve_light(self, location: str) -> tuple[str, str]:
        normalized = location.strip().lower()
        light_id = self._location_aliases.get(normalized)
        if not light_id:
            raise ValueError(f"Thiết bị không được hỗ trợ: {location.strip() or '(trống)'}")
        return light_id, self._light_id_to_name[light_id]

    def _set_light(self, location: str, turn_on: bool) -> LightState:
        light_id, display_name = self._resolve_light(location)
        self.esp32_gateway.set_light(light_id, turn_on)
        return self.lighting_service.get_light_state(display_name)

    def _handle_esp32_state(self, light_id: str, turn_on: bool, payload: dict) -> None:
        del payload
        display_name = self._light_id_to_name.get(light_id)
        if not display_name:
            logger.warning("Ignoring state for unknown ESP32 light id: %s", light_id)
            return
        self.lighting_service.apply_device_state(display_name, turn_on)

    def _notify_music_listeners(self, payload: dict) -> None:
        with self._music_listener_lock:
            listeners = list(self._music_listeners)
        for loop, queue in listeners:
            try:
                loop.call_soon_threadsafe(queue.put_nowait, payload)
            except RuntimeError:
                self.remove_music_listener(queue)

    async def add_music_listener(self) -> "asyncio.Queue[dict]":
        loop = asyncio.get_running_loop()
        queue: "asyncio.Queue[dict]" = asyncio.Queue()
        with self._music_listener_lock:
            self._music_listeners.append((loop, queue))
        await queue.put({"type": "snapshot", "state": self._serialize_music_state()})
        return queue

    def remove_music_listener(self, queue: "asyncio.Queue[dict]") -> None:
        with self._music_listener_lock:
            self._music_listeners = [
                (loop, q) for loop, q in self._music_listeners if q is not queue
            ]

    def _serialize_music_state(self) -> dict:
        state = self.get_music_playback_state()
        return {
            "requested_title": state.requested_title,
            "matched_song": state.matched_song,
            "status": state.status,
            "position_seconds": state.position_seconds,
            "duration_seconds": state.duration_seconds,
            "updated_at": state.updated_at,
        }

    def play_music(self, title: str) -> Optional[str]:
        matched = self.music_service.choose_song(title)
        if matched:
            self._music_playback_state = MusicPlaybackState(
                requested_title=title,
                matched_song=matched,
                status="playing",
                position_seconds=0.0,
                duration_seconds=self.music_service.get_song_duration(matched),
                updated_at=time.time(),
            )
        else:
            self._music_playback_state = MusicPlaybackState(
                requested_title=title,
                matched_song=None,
                status="stopped",
                position_seconds=0.0,
                duration_seconds=None,
                updated_at=time.time(),
            )
        self._notify_music_listeners({"type": "update", "state": self._serialize_music_state()})
        return matched

    def get_song_file(self, title: str) -> Optional[Path]:
        return self.music_service.find_song_file(title)

    def get_lights(self) -> List[LightState]:
        return list(self.lighting_service.get_all_states())

    def list_music(self) -> List[str]:
        return self.music_service.list_available_songs()

    def get_music_playback_state(self) -> MusicPlaybackState:
        state = self._music_playback_state.copy()
        state.position_seconds = state.effective_position()
        state.updated_at = time.time()
        return state

    def pause_music(self) -> bool:
        if (
            self._music_playback_state.matched_song
            and self._music_playback_state.status == "playing"
        ):
            self._music_playback_state.position_seconds = self._music_playback_state.effective_position()
            self._music_playback_state.status = "paused"
            self._music_playback_state.updated_at = time.time()
            self._notify_music_listeners(
                {"type": "update", "state": self._serialize_music_state()}
            )
            return True
        return False

    def continue_music(self) -> bool:
        if (
            self._music_playback_state.matched_song
            and self._music_playback_state.status == "paused"
        ):
            self._music_playback_state.status = "playing"
            self._music_playback_state.updated_at = time.time()
            self._notify_music_listeners(
                {"type": "update", "state": self._serialize_music_state()}
            )
            return True
        return False

    def seek_music(self, position_seconds: float) -> MusicPlaybackState:
        position = max(0.0, position_seconds)
        self._music_playback_state.position_seconds = position
        self._music_playback_state.updated_at = time.time()
        self._notify_music_listeners(
            {"type": "update", "state": self._serialize_music_state()}
        )
        return self.get_music_playback_state()


_global_smart_home_service: Optional[SmartHomeService] = None


def get_smart_home_service() -> SmartHomeService:
    global _global_smart_home_service
    if _global_smart_home_service is None:
        _global_smart_home_service = SmartHomeService()
    return _global_smart_home_service
