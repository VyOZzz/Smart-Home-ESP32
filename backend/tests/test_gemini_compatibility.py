"""Regression checks for Gemini Live and TTS API compatibility.

Run from the repository root: python -m unittest discover -s backend/tests
"""

import base64
import json
import os
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import WebSocketDisconnect
from google.genai import types

from app.core.config import Settings, settings
from app.services.gemini_service import GeminiService
from app.services.notification_voice_service import NotificationVoiceService


class GeminiCompatibilityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Avoid creating clients or touching persisted device/session state.
        self.service = GeminiService.__new__(GeminiService)

    def test_live_config_uses_native_audio_without_language_code(self):
        config = self.service._create_live_config(None)
        self.assertEqual(config.response_modalities, [types.Modality.AUDIO])
        self.assertIsNone(config.speech_config.language_code)
        self.assertIsNotNone(config.input_audio_transcription)
        self.assertIsNotNone(config.output_audio_transcription)
        self.assertIn("tiếng Việt", config.system_instruction)

    async def test_multiple_text_turns_use_realtime_input(self):
        websocket = SimpleNamespace(receive_text=AsyncMock(side_effect=[
            json.dumps({"text": "Xin chào"}),
            json.dumps({"text": "Bạn có nghe tôi không?"}),
            WebSocketDisconnect(),
        ]))
        session = SimpleNamespace(send_realtime_input=AsyncMock())
        self.service._append_to_conversation_history = Mock()
        await self.service._relay_client_to_gemini(websocket, session)
        self.assertEqual(session.send_realtime_input.await_count, 2)
        session.send_realtime_input.assert_any_await(text="Xin chào")
        session.send_realtime_input.assert_any_await(text="Bạn có nghe tôi không?")
        self.assertEqual(self.service._append_to_conversation_history.call_count, 2)

    async def test_camera_and_microphone_use_explicit_fields(self):
        session = SimpleNamespace(send_realtime_input=AsyncMock())
        self.service._maybe_handle_fire_detection = AsyncMock()
        with patch.object(settings, "save_captured_image", False):
            for mime, field in [("image/jpeg", "video"), ("audio/pcm;rate=16000", "audio")]:
                session.send_realtime_input.reset_mock()
                await self.service._process_realtime_media_chunk(None, session, {
                    "mime_type": mime,
                    "data": base64.b64encode(b"sample").decode(),
                })
                kwargs = session.send_realtime_input.call_args.kwargs
                self.assertEqual(set(kwargs), {field})
                self.assertEqual(kwargs[field].data, b"sample")
                self.assertEqual(kwargs[field].mime_type, mime)
        self.service._maybe_handle_fire_detection.assert_awaited_once()

    async def test_tool_event_does_not_drop_accompanying_audio_and_transcript(self):
        response = types.LiveServerMessage(
            tool_call=types.LiveServerToolCall(function_calls=[
                types.FunctionCall(id="call-1", name="pause_music", args={})
            ]),
            server_content=types.LiveServerContent(
                output_transcription=types.Transcription(text="Đã tạm dừng.", finished=True),
                model_turn=types.Content(parts=[types.Part(
                    inline_data=types.Blob(data=b"audio", mime_type="audio/pcm;rate=24000")
                )]),
            ),
        )

        async def receive():
            yield response
            raise WebSocketDisconnect()

        self.service._current_assistant_output = ""
        self.service._handle_tool_calls = AsyncMock()
        self.service._send_safely = AsyncMock()
        self.service._enqueue_audio_chunk = AsyncMock()
        self.service._append_to_conversation_history = Mock()
        websocket = SimpleNamespace(client_state=SimpleNamespace(name="CONNECTED"))
        await self.service._relay_gemini_to_client(websocket, SimpleNamespace(receive=receive))
        self.service._handle_tool_calls.assert_awaited_once()
        self.service._enqueue_audio_chunk.assert_awaited_once()
        self.service._append_to_conversation_history.assert_called_once_with("assistant", "Đã tạm dừng.")

    async def test_uploaded_image_and_question_share_one_request(self):
        generate = AsyncMock(return_value=SimpleNamespace(text="Có ngọn lửa trong ảnh."))
        self.service.client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
        self.service._send_safely = AsyncMock()
        self.service._maybe_handle_fire_detection = AsyncMock()
        self.service._append_to_conversation_history = Mock()
        await self.service._handle_image_analysis(None, {
            "mime_type": "image/png", "data": base64.b64encode(b"image bytes").decode(),
            "prompt": "Ảnh có gì?",
        })
        content = generate.call_args.kwargs["contents"][0]
        self.assertEqual(content.parts[0].inline_data.data, b"image bytes")
        self.assertEqual(content.parts[0].inline_data.mime_type, "image/png")
        self.assertEqual(content.parts[1].text, "Ảnh có gì?")
        self.assertEqual(generate.call_args.kwargs["model"], settings.gemini_image_model)
        self.service._maybe_handle_fire_detection.assert_awaited_once_with(None, b"image bytes", "image/png")
        self.service._send_safely.assert_awaited_once_with(None, {
            "type": "image_analysis_result", "text": "Có ngọn lửa trong ảnh.",
        })

    async def test_image_api_failure_still_runs_fire_detection(self):
        generate = AsyncMock(side_effect=RuntimeError("API unavailable"))
        self.service.client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
        self.service._send_safely = AsyncMock()
        self.service._maybe_handle_fire_detection = AsyncMock()
        await self.service._handle_image_analysis(None, {
            "mime_type": "image/jpeg", "data": base64.b64encode(b"image").decode(), "prompt": "Mô tả ảnh",
        })
        self.service._maybe_handle_fire_detection.assert_awaited_once()
        self.assertEqual(self.service._send_safely.call_args.args[1]["type"], "image_analysis_error")

    async def test_invalid_uploaded_image_is_rejected_before_api_call(self):
        self.service.client = Mock()
        self.service._send_safely = AsyncMock()
        self.service._maybe_handle_fire_detection = AsyncMock()
        await self.service._handle_image_analysis(None, {
            "mime_type": "image/png", "data": "not base64!", "prompt": "Mô tả ảnh",
        })
        self.service.client.aio.models.generate_content.assert_not_called()
        self.service._maybe_handle_fire_detection.assert_not_awaited()
        self.assertEqual(self.service._send_safely.call_args.args[1]["type"], "image_analysis_error")

    async def test_notification_uses_tts_model_and_returns_audio(self):
        generate = AsyncMock(return_value=types.GenerateContentResponse(candidates=[
            types.Candidate(content=types.Content(parts=[types.Part(
                inline_data=types.Blob(data=b"speech", mime_type="audio/pcm;rate=24000")
            )]))
        ]))
        client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
        with patch.object(settings, "gemini_model", "gemini-3.1-flash-live-preview"), \
             patch.object(settings, "gemini_tts_model", "gemini-2.5-flash-preview-tts"):
            service = NotificationVoiceService(client=client)
        result = await service.generate_voice_notification_base64("Xin chào")
        self.assertEqual(base64.b64decode(result), b"speech")
        self.assertEqual(generate.call_args.kwargs["model"], "gemini-2.5-flash-preview-tts")

    def test_model_defaults_and_independent_overrides(self):
        with patch.dict(os.environ, {}, clear=True):
            config = Settings()
        self.assertEqual(config.gemini_model, "gemini-3.1-flash-live-preview")
        self.assertEqual(config.gemini_tts_model, "gemini-2.5-flash-preview-tts")
        with patch.dict(os.environ, {"GEMINI_MODEL": "custom-live", "GEMINI_TTS_MODEL": "custom-tts"}):
            config = Settings()
        self.assertEqual(config.gemini_model, "custom-live")
        self.assertEqual(config.gemini_tts_model, "custom-tts")


if __name__ == "__main__":
    unittest.main()
