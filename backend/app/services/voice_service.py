"""
Голос: Whisper (распознавание) и OpenAI TTS (озвучка).
Работает при наличии OPENAI_API_KEY (тот же ключ, что и для чата).
"""

import io
import logging
import re

from app.core.config import settings

logger = logging.getLogger(__name__)


class VoiceService:
    def __init__(self):
        self.enabled = bool(settings.openai_api_key.strip())
        self._client = None
        if self.enabled:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=settings.openai_api_key)
            logger.info(
                "Voice service enabled (Whisper + TTS, voice=%s)",
                settings.openai_tts_voice,
            )
        else:
            logger.warning("Voice service disabled — no OPENAI_API_KEY")

    async def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        if not self._client:
            raise RuntimeError("Voice service not configured")
        file_tuple = (filename, io.BytesIO(audio_bytes), self._guess_mime(filename))
        result = await self._client.audio.transcriptions.create(
            model="whisper-1",
            file=file_tuple,
            language="ru",
        )
        return result.text or ""

    async def synthesize(self, text: str) -> bytes:
        if not self._client:
            raise RuntimeError("Voice service not configured")
        plain = self._strip_for_speech(text)
        if not plain.strip():
            raise ValueError("Пустой текст для озвучки")

        response = await self._client.audio.speech.create(
            model=settings.openai_tts_model,
            voice=settings.openai_tts_voice,
            input=plain[:4000],
            response_format="mp3",
        )
        return response.content

    @staticmethod
    def _guess_mime(filename: str) -> str:
        lower = filename.lower()
        if lower.endswith(".webm"):
            return "audio/webm"
        if lower.endswith(".mp3"):
            return "audio/mpeg"
        if lower.endswith(".wav"):
            return "audio/wav"
        if lower.endswith(".m4a"):
            return "audio/mp4"
        return "application/octet-stream"

    @staticmethod
    def _strip_for_speech(text: str) -> str:
        s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        s = re.sub(r"[#*_`]+", "", s)
        return s.strip()


voice_service = VoiceService()
