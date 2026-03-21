import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.middleware import RequestLoggingMiddleware

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.rag.engine import rag_engine
    from app.services.conversation_logger import conversation_logger
    await rag_engine.initialize()
    stats = await rag_engine.get_collection_stats()
    conversation_logger.log_event("startup", {
        "company": settings.company_name,
        "model": settings.openai_model,
        "rag_documents": stats.get("document_count", 0),
    })
    logging.getLogger(__name__).info(
        "Backend Agent started. Company: %s", settings.company_name
    )
    yield


app = FastAPI(
    title=f"{settings.company_name} — AI Agent API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.websocket("/ws/chat")
async def websocket_chat(websocket):
    from app.api.chat import handle_websocket_chat
    await handle_websocket_chat(websocket)
