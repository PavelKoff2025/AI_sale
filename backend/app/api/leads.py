import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends

from app.core.dependencies import verify_admin_key
from app.models.lead import LeadRequest, LeadResponse
from app.services.conversation_logger import conversation_logger
from app.services.qualification_service import qualification_service
from app.services.session_service import session_service

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_db():
    from app.core.database import get_db
    return await get_db()


async def _enrich_and_notify(lead: dict):
    """Анализ квалификации + отправка в Telegram (выполняется в background)."""
    from app.services.telegram_service import telegram_service
    history = session_service.get_history(lead.get("session_id", ""))
    qualification = await qualification_service.analyze(history)
    lead["qualification"] = qualification

    db = await _get_db()
    try:
        await db.execute(
            "UPDATE leads SET qualification = ? WHERE id = ?",
            (qualification, lead["id"]),
        )
        await db.commit()
    except Exception as e:
        logger.error("Failed to update lead qualification: %s", e)

    conversation_logger.log_lead(lead)
    await telegram_service.send_lead_notification(lead)


@router.post("/", response_model=LeadResponse)
async def create_lead(request: LeadRequest, background_tasks: BackgroundTasks):
    lead_id = str(uuid.uuid4())[:8]
    created_at = datetime.now().isoformat()
    lead = {
        "id": lead_id,
        "name": request.name,
        "phone": request.phone,
        "message": request.message,
        "source": request.source,
        "session_id": request.session_id,
        "created_at": created_at,
    }

    db = await _get_db()
    try:
        await db.execute(
            "INSERT INTO leads (id, name, phone, message, source, session_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (lead_id, request.name, request.phone, request.message,
             request.source, request.session_id, created_at),
        )
        await db.commit()
    except Exception as e:
        logger.error("Failed to persist lead: %s", e)

    logger.info("New lead: %s — %s (%s)", lead_id, request.name, request.phone)

    background_tasks.add_task(_enrich_and_notify, lead)

    return LeadResponse(lead_id=lead_id)


@router.get("/", dependencies=[Depends(verify_admin_key)])
async def list_leads():
    db = await _get_db()
    async with db.execute(
        "SELECT id, name, phone, message, source, session_id, qualification, created_at "
        "FROM leads ORDER BY created_at DESC LIMIT 1000"
    ) as cursor:
        rows = await cursor.fetchall()
    leads = [dict(row) for row in rows]
    return {"leads": leads, "total": len(leads)}


@router.post("/test-telegram", dependencies=[Depends(verify_admin_key)])
async def test_telegram():
    """Отправить тестовое сообщение в Telegram для проверки настроек."""
    from app.services.telegram_service import telegram_service
    success = await telegram_service.send_test_message()
    if success:
        return {"status": "ok", "message": "Тестовое сообщение отправлено в Telegram"}
    return {
        "status": "error",
        "message": "Не удалось отправить. Проверьте TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в .env",
    }
