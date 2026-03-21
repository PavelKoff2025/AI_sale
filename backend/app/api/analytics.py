import logging

from fastapi import APIRouter, Query

from app.rag.engine import rag_engine
from app.services.conversation_logger import conversation_logger
from app.services.session_service import session_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def get_analytics():
    sessions = session_service._sessions
    total_sessions = len(sessions)
    total_messages = sum(
        len(s["messages"]) for s in sessions.values()
    )

    rag_stats = await rag_engine.get_collection_stats()
    log_stats = conversation_logger.get_today_stats()

    return {
        "sessions": {
            "active": total_sessions,
            "total_messages": total_messages,
        },
        "rag": rag_stats,
        "logs_today": log_stats,
    }


@router.get("/logs/conversations")
async def get_conversation_logs(limit: int = Query(default=50, le=200)):
    return {"entries": conversation_logger.get_recent_conversations(limit)}


@router.get("/logs/leads")
async def get_lead_logs(limit: int = Query(default=50, le=200)):
    return {"entries": conversation_logger.get_recent_leads(limit)}


@router.get("/logs/events")
async def get_event_logs(limit: int = Query(default=50, le=200)):
    return {"entries": conversation_logger.get_recent_events(limit)}


@router.get("/logs/files")
async def get_log_files():
    return conversation_logger.get_log_files()
