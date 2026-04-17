from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.knowledge import router as knowledge_router
from app.api.leads import router as leads_router
from app.api.analytics import router as analytics_router
from app.api.voice import router as voice_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(chat_router, tags=["chat"])
api_router.include_router(voice_router, prefix="/voice", tags=["voice"])
api_router.include_router(knowledge_router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(leads_router, prefix="/leads", tags=["leads"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
