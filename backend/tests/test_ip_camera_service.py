"""Camera fault recovery without real hardware, Gemini sessions or persisted data."""
import asyncio
import time
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
from app.services.ip_camera_service import IpCameraService

FRAME = np.zeros((24, 32, 3), dtype=np.uint8)


def capture(*reads, opened=True):
    stream = Mock()
    stream.isOpened.return_value = opened
    stream.read.side_effect = list(reads) if reads else None
    if not reads:
        stream.read.return_value = (True, FRAME)
    return stream


class IpCameraTests(unittest.IsolatedAsyncioTestCase):
    def service(self, factory, **kwargs):
        return IpCameraService(rtsp_url="rtsp://user:private-password@192.0.2.1/live",
            capture_interval=0.001, request_timeout=0.1, reconnect_interval=0.01,
            capture_factory=factory, fire_detection_service=Mock(process_image=AsyncMock(return_value=None)),
            **kwargs)

    async def until(self, predicate):
        async def poll():
            while not predicate():
                await asyncio.sleep(0.002)
        await asyncio.wait_for(poll(), timeout=3)

    async def test_disconnect_clears_frame_then_reconnects_and_detects_without_gemini(self):
        first = capture((True, FRAME), (False, None))
        second = capture()
        factory = Mock(side_effect=[first, second])
        service = self.service(factory)
        queue = await service.add_listener()
        service.start()
        try:
            await self.until(lambda: factory.call_count == 2 and service.status()['online'])
            first.release.assert_called_once()
            self.assertTrue(service.latest_frame.startswith(b'\xff\xd8'))
            await self.until(lambda: service.fire_detection_service.process_image.await_count > 0)
            events = []
            while not queue.empty():
                events.append(queue.get_nowait())
            self.assertTrue(any(not e['online'] and 'Mất kết nối' in (e['last_error'] or '') for e in events))
            self.assertTrue(events[-1]['online'])
        finally:
            await service.stop()
        second.release.assert_called_once()
        self.assertIsNone(service.latest_frame)
        self.assertFalse(service.status()['online'])

    async def test_failed_open_reconnects(self):
        failed, recovered = capture(opened=False), capture()
        factory = Mock(side_effect=[failed, recovered])
        service = self.service(factory)
        service.start()
        try:
            await self.until(lambda: service.status()['online'])
            failed.release.assert_called_once()
            self.assertEqual(factory.call_count, 2)
            self.assertEqual(factory.call_args.args[1], cv2.CAP_FFMPEG)
            self.assertIn(cv2.CAP_PROP_READ_TIMEOUT_MSEC, factory.call_args.args[2])
        finally:
            await service.stop()

    async def test_invalid_frames_are_offline_and_never_reach_detector(self):
        for frame in [None, np.array([]), np.zeros((8, 8)), np.zeros((8, 8, 4), dtype=np.uint8), 'bad']:
            with self.subTest(frame=type(frame).__name__):
                stream = capture((True, frame))
                service = self.service(Mock(return_value=stream))
                service.reconnect_interval = 10
                service.start()
                try:
                    await self.until(lambda: service.status()['last_error'] == 'Khung hình camera IP không hợp lệ')
                    self.assertFalse(service.status()['online'])
                    self.assertIsNone(service.latest_frame)
                    service.fire_detection_service.process_image.assert_not_called()
                finally:
                    await service.stop()

    async def test_disconnect_invalidates_snapshot_and_waiters(self):
        service = self.service(Mock())
        await service._store_frame(b'jpeg')
        await service._set_status(True, None)
        waiter = asyncio.create_task(service.wait_for_frame(service._frame_version))
        await asyncio.sleep(0)
        await service._set_status(False, 'offline')
        with self.assertRaises(RuntimeError):
            await waiter
        self.assertIsNone(service.latest_frame)
        self.assertFalse(service.status()['frame_available'])

    async def test_native_error_cannot_leak_credentials(self):
        service = self.service(Mock(side_effect=RuntimeError('rtsp://user:private-password@192.0.2.1/live')))
        service.start()
        try:
            await self.until(lambda: service.status()['last_error'] == 'Lỗi đọc camera IP; đang kết nối lại')
            self.assertNotIn('private-password', str(service.status()))
            self.assertNotIn('rtsp://', str(service.status()))
        finally:
            await service.stop()

    async def test_unconfigured_or_local_source_never_opens_camera(self):
        for url in ['', '0', '/dev/video0', 'http://camera/image', 'rtsp://[invalid']:
            factory = Mock()
            service = self.service(factory)
            service._rtsp_url = url
            with self.assertRaises(ValueError):
                service._fetch_frame()
            factory.assert_not_called()

    async def test_invalid_encoded_and_oversize_frames(self):
        service = self.service(Mock(return_value=capture()))
        with patch('app.services.ip_camera_service.cv2.imencode', return_value=(False, None)):
            with self.assertRaises(ValueError):
                service._fetch_frame()
        with patch('app.services.ip_camera_service.settings.camera_max_frame_bytes', 1):
            with self.assertRaises(ValueError):
                service._fetch_frame()
        service._release()

    async def test_stale_frame_not_served(self):
        service = self.service(Mock())
        await service._store_frame(b'jpeg')
        await service._set_status(True, None)
        service._latest_frame_at = time.monotonic() - 100
        self.assertIsNone(service.latest_frame)
        self.assertFalse(service.status()['online'])

    async def test_fire_alert_broadcast_without_gemini(self):
        service = self.service(Mock(return_value=capture()))
        service.fire_detection_service.process_image.return_value = {'type': 'fire_detection_alert', 'audio_base64': 'tone'}
        queue = await service.add_listener()
        service.start()
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=3)
                if event['type'] == 'fire_detection_alert':
                    self.assertEqual(event['audio_base64'], 'tone')
                    break
        finally:
            await service.stop()

    async def test_stop_waits_for_native_read_before_releasing(self):
        import threading
        entered, finish = threading.Event(), threading.Event()
        stream = capture()
        def read():
            entered.set()
            finish.wait(2)
            return True, FRAME
        stream.read.side_effect = read
        service = self.service(Mock(return_value=stream))
        service.start()
        try:
            await self.until(entered.is_set)
            stopping = asyncio.create_task(service.stop())
            await asyncio.sleep(0.02)
            stream.release.assert_not_called()
            finish.set()
            await stopping
            stream.release.assert_called_once()
        finally:
            finish.set()
            await service.stop()


if __name__ == '__main__':
    unittest.main()
