import asyncio

from typing import List, Optional, Literal

from mimetypes import guess_type
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel, confloat, constr

from app.services.esp32_gateway import DeviceCommandTimeoutError, DeviceUnavailableError
from app.services.smart_home_service import LightState, MusicPlaybackState, get_smart_home_service
from app.services.ip_camera_service import get_ip_camera_service


router = APIRouter(prefix="/smart-home", tags=["smart-home"])

smart_home_service = get_smart_home_service()
camera_service = get_ip_camera_service()


class LightRequest(BaseModel):
    location: constr(strip_whitespace=True, min_length=1)


class LightResponse(BaseModel):
    location: str
    is_on: bool
    device_online: bool


class MusicRequest(BaseModel):
    title: constr(strip_whitespace=True, min_length=1)


class MusicPlaybackStateResponse(BaseModel):
    requested_title: Optional[str]
    matched_song: Optional[str]
    status: Literal["stopped", "playing", "paused"]
    position_seconds: float
    duration_seconds: Optional[float]
    updated_at: float

    @classmethod
    def from_state(cls, state: MusicPlaybackState) -> "MusicPlaybackStateResponse":
        return cls(
            requested_title=state.requested_title,
            matched_song=state.matched_song,
            status=state.status,
            position_seconds=state.position_seconds,
            duration_seconds=state.duration_seconds,
            updated_at=state.updated_at,
        )


class MusicResponse(BaseModel):
    selected_song: str
    stream_url: str
    playback_state: MusicPlaybackStateResponse


class MusicSeekRequest(BaseModel):
    position_seconds: confloat(ge=0)


def _serialize_light(state: LightState) -> dict:
    return {
        "location": state.location,
        "is_on": state.is_on,
        "device_online": state.device_online,
    }


def _control_light(location: str, turn_on: bool) -> LightState:
    try:
        return (
            smart_home_service.turn_on_light(location)
            if turn_on
            else smart_home_service.turn_off_light(location)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DeviceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DeviceCommandTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc


@router.get("/lights", response_model=List[LightResponse])
def list_lights() -> List[LightResponse]:
    return [LightResponse(**_serialize_light(state)) for state in smart_home_service.get_lights()]


@router.get("/lights/{location}", response_model=LightResponse)
def get_light(location: str) -> LightResponse:
    state = smart_home_service.lighting_service.get_light_state(location)
    return LightResponse(**_serialize_light(state))


@router.post("/lights/on", response_model=LightResponse)
def turn_on_light(payload: LightRequest) -> LightResponse:
    state = _control_light(payload.location, True)
    return LightResponse(**_serialize_light(state))


@router.post("/lights/off", response_model=LightResponse)
def turn_off_light(payload: LightRequest) -> LightResponse:
    state = _control_light(payload.location, False)
    return LightResponse(**_serialize_light(state))


@router.get("/music/library", response_model=List[str])
def list_music_library() -> List[str]:
    return smart_home_service.list_music()


@router.post("/music/play", response_model=MusicResponse)
def play_music(payload: MusicRequest) -> MusicResponse:
    selected = smart_home_service.play_music(payload.title)
    if not selected:
        raise HTTPException(status_code=404, detail="Không tìm được bài hát phù hợp")
    file_path = smart_home_service.get_song_file(selected)
    if not file_path:
        raise HTTPException(status_code=404, detail="Không tìm được file bài hát phù hợp")
    query = urlencode({"title": selected})
    stream_url = f"/smart-home/music/stream?{query}"
    state = smart_home_service.get_music_playback_state()
    return MusicResponse(
        selected_song=selected,
        stream_url=stream_url,
        playback_state=MusicPlaybackStateResponse.from_state(state),
    )


@router.get("/music/state", response_model=MusicPlaybackStateResponse)
def get_music_state() -> MusicPlaybackStateResponse:
    state = smart_home_service.get_music_playback_state()
    return MusicPlaybackStateResponse.from_state(state)


@router.post("/music/pause", response_model=MusicPlaybackStateResponse)
def pause_music() -> MusicPlaybackStateResponse:
    paused = smart_home_service.pause_music()
    state = smart_home_service.get_music_playback_state()
    if not paused:
        raise HTTPException(status_code=409, detail="Không có bài hát nào đang phát")
    return MusicPlaybackStateResponse.from_state(state)


@router.post("/music/resume", response_model=MusicPlaybackStateResponse)
def resume_music() -> MusicPlaybackStateResponse:
    resumed = smart_home_service.continue_music()
    state = smart_home_service.get_music_playback_state()
    if not resumed:
        raise HTTPException(status_code=409, detail="Không có bài hát nào để tiếp tục")
    return MusicPlaybackStateResponse.from_state(state)


@router.post("/music/seek", response_model=MusicPlaybackStateResponse)
def seek_music(payload: MusicSeekRequest) -> MusicPlaybackStateResponse:
    state = smart_home_service.seek_music(payload.position_seconds)
    return MusicPlaybackStateResponse.from_state(state)


@router.get("/music/stream")
def stream_music(title: str) -> FileResponse:
    file_path = smart_home_service.get_song_file(title)
    if not file_path:
        raise HTTPException(status_code=404, detail="Không tìm được file bài hát phù hợp")
    media_type, _ = guess_type(file_path.name)
    return FileResponse(file_path, media_type=media_type or "audio/mpeg", filename=file_path.name)


@router.get("/camera/status")
def get_camera_status() -> dict:
    return camera_service.status()


@router.get("/camera/snapshot")
def get_camera_snapshot() -> Response:
    frame = camera_service.latest_frame
    if frame is None:
        raise HTTPException(status_code=503, detail="Camera IP chưa cung cấp khung hình")
    return Response(
        frame,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )


@router.get("/camera/stream")
async def stream_camera() -> StreamingResponse:
    async def generate_frames():
        version = -1
        while True:
            try:
                frame, version = await camera_service.wait_for_frame(version)
            except RuntimeError:
                await asyncio.sleep(0.5)
                continue
            yield (
                b"--frame\r\nContent-Type: image/jpeg\r\n"
                + f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii")
                + frame
                + b"\r\n"
            )

    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store"},
    )


@router.websocket("/camera/updates")
async def stream_camera_updates(websocket: WebSocket) -> None:
    await websocket.accept()
    queue = await camera_service.add_listener()
    try:
        while True:
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=20)
            except asyncio.TimeoutError:
                payload = {"type": "camera_status", **camera_service.status()}
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        pass
    finally:
        camera_service.remove_listener(queue)


@router.websocket("/lights/stream")
async def stream_light_updates(websocket: WebSocket) -> None:
    await websocket.accept()
    queue = await smart_home_service.lighting_service.add_listener()
    try:
        while True:
            message = await queue.get()
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass
    finally:
        smart_home_service.lighting_service.remove_listener(queue)


@router.websocket("/music/updates")
async def stream_music_updates(websocket: WebSocket) -> None:
    await websocket.accept()
    queue = await smart_home_service.add_music_listener()
    try:
        while True:
            message = await queue.get()
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass
    finally:
        smart_home_service.remove_music_listener(queue)
