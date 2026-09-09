"""Read a LAN RTSP camera independently of browser and Gemini sessions."""
from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from typing import Optional
from urllib.parse import urlsplit

from app.core.config import settings
import cv2
import numpy as np
from app.services.fire_detection_service import FireDetectionService

logger = logging.getLogger(__name__)


class IpCameraService:
    def __init__(self, rtsp_url=None, capture_interval=None, request_timeout=None,
                 reconnect_interval=None, fire_detection_service=None, capture_factory=None):
        self._rtsp_url = settings.home_camera_rtsp_url if rtsp_url is None else rtsp_url
        self.capture_interval = settings.camera_capture_interval_seconds if capture_interval is None else capture_interval
        self.request_timeout = settings.camera_request_timeout_seconds if request_timeout is None else request_timeout
        self.reconnect_interval = settings.camera_reconnect_interval_seconds if reconnect_interval is None else reconnect_interval
        self.fire_detection_service = fire_detection_service or FireDetectionService()
        self._capture_factory = capture_factory or cv2.VideoCapture
        self._capture = None
        self._task = None
        self._detection_task = None
        self._latest_frame = None
        self._latest_frame_at = None
        self._last_encoded_at = 0.0
        self._online = False
        self._last_error = "Camera IP đang khởi tạo"
        self._frame_version = 0
        self._frame_condition = asyncio.Condition()
        self._listeners: set[asyncio.Queue] = set()

    def start(self):
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._capture_loop())
            self._detection_task = asyncio.create_task(self._detection_loop())

    async def stop(self):
        tasks = [task for task in (self._task, self._detection_task) if task is not None]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._task = self._detection_task = None
        await self._set_status(False, "Camera IP đã dừng")

    @property
    def latest_frame(self):
        # Never serve a cached frame as live after a disconnect or stalled reader.
        if (not self._online or self._latest_frame_at is None or
                time.monotonic() - self._latest_frame_at > self.request_timeout + self.capture_interval + 1):
            return None
        return self._latest_frame

    def status(self):
        age = None if self._latest_frame_at is None else max(0, time.monotonic() - self._latest_frame_at)
        available = self.latest_frame is not None
        return {"source": "ip-camera", "online": self._online and available,
                "frame_available": available,
                "frame_age_seconds": round(age, 2) if age is not None else None,
                "last_error": self._last_error if not self._online or available else "Khung hình camera IP đã quá hạn"}

    async def add_listener(self):
        queue = asyncio.Queue(maxsize=8)
        self._listeners.add(queue)
        await queue.put({"type": "camera_status", **self.status()})
        return queue

    def remove_listener(self, queue):
        self._listeners.discard(queue)

    async def wait_for_frame(self, version):
        async with self._frame_condition:
            await self._frame_condition.wait_for(lambda: self._frame_version > version or not self._online)
            frame = self.latest_frame
            if frame is None:
                raise RuntimeError(self.status()["last_error"] or "Camera IP chưa có ảnh")
            return frame, self._frame_version

    async def _run_io(self, function):
        # Cancellation must finish native I/O before release() touches its capture.
        task = asyncio.create_task(asyncio.to_thread(function))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            with contextlib.suppress(Exception):
                await task
            raise

    def _release(self):
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def _fetch_frame(self):
        if not self._rtsp_url:
            raise ValueError("Chưa cấu hình HOME_CAMERA_RTSP_URL trong backend/.env")
        try:
            parsed = urlsplit(self._rtsp_url)
            valid = parsed.scheme in {"rtsp", "rtsps"} and bool(parsed.hostname)
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("HOME_CAMERA_RTSP_URL phải là URL RTSP hợp lệ")
        if self._capture is None:
            # Open-only FFmpeg timeouts bound both unreachable hosts and stalled reads.
            if hasattr(cv2, "setLogLevel"):
                cv2.setLogLevel(0)
            else:
                cv2.utils.logging.setLogLevel(0)
            timeout_ms = max(1, int(self.request_timeout * 1000))
            self._capture = self._capture_factory(self._rtsp_url, cv2.CAP_FFMPEG, [
                cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms,
                cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_ms,
            ])
            if not self._capture.isOpened():
                raise ConnectionError("Không mở được camera IP; kiểm tra LAN, RTSP và cấu hình đăng nhập")
        ok, frame = self._capture.read()
        if not ok:
            raise ConnectionError("Mất kết nối camera IP hoặc không đọc được khung hình")
        if (not isinstance(frame, np.ndarray) or frame.dtype != np.uint8 or
                frame.ndim != 3 or frame.shape[2] != 3 or frame.size == 0):
            raise ValueError("Khung hình camera IP không hợp lệ")
        # Drain RTSP continuously; only encode/sample at the configured interval.
        now = time.monotonic()
        if now - self._last_encoded_at < self.capture_interval:
            return None
        ok, jpeg = cv2.imencode(".jpg", frame)
        if not ok or jpeg is None or jpeg.size == 0:
            raise ValueError("Không mã hóa được khung hình camera IP")
        data = jpeg.tobytes()
        if len(data) > settings.camera_max_frame_bytes:
            raise ValueError("Khung hình camera vượt quá giới hạn dung lượng")
        self._last_encoded_at = now
        return data

    async def _capture_loop(self):
        try:
            while True:
                try:
                    frame = await self._run_io(self._fetch_frame)
                    if frame is not None:
                        await self._store_frame(frame)
                        await self._set_status(True, None)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    # Never expose native exception text: it may contain the RTSP password.
                    safe_errors = {
                        "Chưa cấu hình HOME_CAMERA_RTSP_URL trong backend/.env",
                        "HOME_CAMERA_RTSP_URL phải là URL RTSP hợp lệ",
                        "Không mở được camera IP; kiểm tra LAN, RTSP và cấu hình đăng nhập",
                        "Mất kết nối camera IP hoặc không đọc được khung hình",
                        "Khung hình camera IP không hợp lệ",
                        "Không mã hóa được khung hình camera IP",
                        "Khung hình camera vượt quá giới hạn dung lượng",
                    }
                    error = str(exc) if str(exc) in safe_errors else "Lỗi đọc camera IP; đang kết nối lại"
                    await self._set_status(False, error)
                    await self._run_io(self._release)
                    self._last_encoded_at = 0
                    await asyncio.sleep(self.reconnect_interval)
        finally:
            await self._run_io(self._release)

    async def _detection_loop(self):
        version = -1
        while True:
            try:
                frame, version = await self.wait_for_frame(version)
            except RuntimeError:
                await asyncio.sleep(0.1)
                continue
            try:
                alert = await self.fire_detection_service.process_image(frame, "image/jpeg")
                if alert:
                    await self._broadcast(alert)
            except Exception:
                logger.warning("Không thể phân tích cháy từ khung hình camera IP")

    async def _store_frame(self, frame: bytes) -> None:
        async with self._frame_condition:
            self._latest_frame = frame
            self._latest_frame_at = time.monotonic()
            self._frame_version += 1
            self._frame_condition.notify_all()

    async def _set_status(self, online: bool, error: Optional[str]) -> bool:
        changed = online != self._online or error != self._last_error
        self._online = online
        if not online:
            self._latest_frame = None
            self._latest_frame_at = None
        self._last_error = error
        if changed:
            async with self._frame_condition:
                self._frame_condition.notify_all()
            await self._broadcast({"type": "camera_status", **self.status()})
        return changed

    async def _broadcast(self, payload: dict) -> None:
        for queue in tuple(self._listeners):
            if queue.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(payload)


_camera_service: Optional[IpCameraService] = None


def get_ip_camera_service() -> IpCameraService:
    global _camera_service
    if _camera_service is None:
        _camera_service = IpCameraService()
    return _camera_service


__all__ = ["IpCameraService", "get_ip_camera_service"]
