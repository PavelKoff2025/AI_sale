import io
import logging

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.voice_service import voice_service

logger = logging.getLogger(__name__)

router = APIRouter()


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


@router.post("/transcribe")
async def transcribe_voice(audio: UploadFile = File(...)):
    if not voice_service.enabled:
        raise HTTPException(
            status_code=503,
            detail="Голосовой ввод недоступен: не настроен OpenAI API ключ.",
        )
    data = await audio.read()
    if len(data) < 100:
        raise HTTPException(status_code=400, detail="Слишком короткая запись")
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Файл слишком большой (макс. 25 МБ)")

    filename = audio.filename or "audio.webm"
    try:
        text = await voice_service.transcribe(data, filename)
    except Exception as e:
        logger.exception("Transcription failed")
        raise HTTPException(status_code=502, detail=str(e)[:200]) from e

    return {"text": text.strip()}


@router.post("/synthesize")
async def synthesize_speech(body: TTSRequest):
    if not voice_service.enabled:
        raise HTTPException(
            status_code=503,
            detail="Озвучка недоступна: не настроен OpenAI API ключ.",
        )
    try:
        audio_bytes = await voice_service.synthesize(body.text)
    except Exception as e:
        logger.exception("TTS failed")
        raise HTTPException(status_code=502, detail=str(e)[:200]) from e

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=speech.mp3"},
    )
