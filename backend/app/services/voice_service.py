"""
Голос: Whisper (распознавание) и OpenAI TTS (озвучка).
Работает при наличии OPENAI_API_KEY (тот же ключ, что и для чата).
"""

import logging
import os
import re
import tempfile

from app.core.config import settings

logger = logging.getLogger(__name__)

# Расширения, которые принимает Whisper API
_WHISPER_EXTS = (
    ".webm",
    ".mp3",
    ".m4a",
    ".mp4",
    ".mpeg",
    ".mpga",
    ".oga",
    ".ogg",
    ".wav",
    ".flac",
)


def _mime_for_ext(ext: str) -> str:
    m = {
        ".webm": "audio/webm",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".mp4": "audio/mp4",
        ".mpeg": "audio/mpeg",
        ".mpga": "audio/mpeg",
        ".oga": "audio/ogg",
        ".ogg": "audio/ogg",
        ".wav": "audio/wav",
        ".flac": "audio/flac",
    }
    return m.get(ext, "application/octet-stream")


def _sniff_audio_format(data: bytes) -> tuple[str, str] | None:
    if len(data) < 16:
        return None
    if data[:4] == b"caff":
        return None
    if data[:4] == b"\x1aE\xdf\xa3":
        return ".webm", "audio/webm"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return ".m4a", "audio/mp4"
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return ".wav", "audio/wav"
    if data[:4] == b"fLaC":
        return ".flac", "audio/flac"
    if data[:4] == b"OggS":
        return ".ogg", "audio/ogg"
    if data[:3] == b"ID3" or (data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
        return ".mp3", "audio/mpeg"
    return None


def normalize_whisper_filename(
    original_name: str | None,
    content_type: str | None,
    data: bytes,
) -> tuple[str, str]:
    """
    Имя и MIME для Whisper.
    Сначала сигнатура файла (браузер часто врёт в Content-Type), затем имя, затем заголовок.
    """
    sniffed = _sniff_audio_format(data)
    if sniffed:
        ext, mime = sniffed
        return f"voice{ext}", mime

    fn = (original_name or "").lower().strip()
    if fn.endswith(".3gp"):
        return "voice.mp4", "audio/mp4"
    for ext in sorted(_WHISPER_EXTS, key=len, reverse=True):
        if fn.endswith(ext):
            return f"voice{ext}", _mime_for_ext(ext)

    ct = (content_type or "").split(";")[0].strip().lower()
    if ct in ("audio/webm", "video/webm"):
        return "voice.webm", "audio/webm"
    if ct in ("audio/mp4", "audio/x-m4a", "audio/m4a"):
        return "voice.m4a", "audio/mp4"
    if ct in ("audio/mpeg", "audio/mp3"):
        return "voice.mp3", "audio/mpeg"
    if ct in ("audio/wav", "audio/x-wav", "audio/wave"):
        return "voice.wav", "audio/wav"
    if ct in ("audio/ogg", "audio/opus", "application/ogg"):
        return "voice.ogg", "audio/ogg"
    if ct in ("audio/flac", "audio/x-flac"):
        return "voice.flac", "audio/flac"
    if ct == "audio/aac":
        return "voice.m4a", "audio/mp4"

    if len(data) >= 4 and data[:4] == b"caff":
        raise ValueError(
            "Формат CAF (запись с iPhone) Whisper не принимает. Экспортируйте как m4a или mp3."
        )

    raise ValueError(
        "Формат файла не распознан. Используйте webm, mp3, m4a, wav или ogg."
    )


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

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str | None,
        content_type: str | None = None,
    ) -> str:
        if not self._client:
            raise RuntimeError("Voice service not configured")
        whisper_name, _mime = normalize_whisper_filename(filename, content_type, audio_bytes)
        suffix = whisper_name[whisper_name.rfind(".") :] if "." in whisper_name else ".bin"
        fd, path = tempfile.mkstemp(suffix=suffix)
        try:
            with os.fdopen(fd, "wb") as tmp:
                tmp.write(audio_bytes)
            with open(path, "rb") as audio_file:
                try:
                    from openai import BadRequestError

                    result = await self._client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="ru",
                    )
                except BadRequestError as e:
                    logger.warning(
                        "Whisper rejected file fn=%s ct=%s head=%s err=%s",
                        filename,
                        content_type,
                        audio_bytes[:32].hex(),
                        str(e)[:300],
                    )
                    raise ValueError(
                        "Файл не принят распознаванием. Сохраните запись как m4a или mp3 и попробуйте снова."
                    ) from e
            return result.text or ""
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

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
    def _strip_for_speech(text: str) -> str:
        s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        s = re.sub(r"[#*_`]+", "", s)
        return s.strip()


voice_service = VoiceService()
