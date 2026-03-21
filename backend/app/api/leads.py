import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks

from app.models.lead import LeadRequest, LeadResponse
from app.services.conversation_logger import conversation_logger
from app.services.telegram_service import telegram_service

logger = logging.getLogger(__name__)

router = APIRouter()

leads_storage: list[dict] = []


@router.post("/", response_model=LeadResponse)
async def create_lead(request: LeadRequest, background_tasks: BackgroundTasks):
    lead_id = str(uuid.uuid4())[:8]
    lead = {
        "id": lead_id,
        "name": request.name,
        "phone": request.phone,
        "message": request.message,
        "source": request.source,
        "session_id": request.session_id,
        "created_at": datetime.now().isoformat(),
    }
    leads_storage.append(lead)
    logger.info("New lead: %s — %s (%s)", lead_id, request.name, request.phone)

    conversation_logger.log_lead(lead)
    background_tasks.add_task(telegram_service.send_lead_notification, lead)

    return LeadResponse(lead_id=lead_id)


@router.get("/")
async def list_leads():
    return {"leads": leads_storage, "total": len(leads_storage)}


@router.post("/test-telegram")
async def test_telegram():
    """Отправить тестовое сообщение в Telegram для проверки настроек."""
    success = await telegram_service.send_test_message()
    if success:
        return {"status": "ok", "message": "Тестовое сообщение отправлено в Telegram"}
    return {
        "status": "error",
        "message": "Не удалось отправить. Проверьте TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в .env",
    }
