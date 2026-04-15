import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.models.chat import ChatRequest, ChatResponse
from app.services.agent_service import agent_service

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_WS_CONNECTIONS = 15
_active_ws: set[str] = set()
_ws_lock = asyncio.Lock()


def get_active_connections_count() -> int:
    return len(_active_ws)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.session_id:
        request.session_id = str(uuid.uuid4())

    response = await agent_service.process_message(
        message=request.message,
        session_id=request.session_id,
        metadata=request.metadata,
    )
    return response


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    if not request.session_id:
        request.session_id = str(uuid.uuid4())

    async def event_generator():
        async for chunk in agent_service.process_message_stream(
            message=request.message,
            session_id=request.session_id,
            metadata=request.metadata,
        ):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def handle_websocket_chat(websocket: WebSocket):
    async with _ws_lock:
        if len(_active_ws) >= MAX_WS_CONNECTIONS:
            await websocket.close(code=1013, reason="Too many connections")
            logger.warning("WebSocket rejected: limit %d reached", MAX_WS_CONNECTIONS)
            return
        await websocket.accept()
        session_id = str(uuid.uuid4())
        ws_id = session_id
        _active_ws.add(ws_id)
    logger.info("WebSocket connected: %s (active: %d)", ws_id, len(_active_ws))

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            session_id = data.get("session_id", session_id)

            metadata = data.get("metadata")
            async for chunk in agent_service.process_message_stream(
                message=message,
                session_id=session_id,
                metadata=metadata,
            ):
                await websocket.send_json(chunk)

            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", session_id)
    finally:
        _active_ws.discard(ws_id)
        logger.info("WebSocket closed: %s (active: %d)", ws_id, len(_active_ws))
