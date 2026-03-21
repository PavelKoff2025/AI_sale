import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.models.chat import ChatRequest, ChatResponse
from app.services.agent_service import agent_service

logger = logging.getLogger(__name__)

router = APIRouter()


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
    await websocket.accept()
    session_id = str(uuid.uuid4())

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            session_id = data.get("session_id", session_id)

            async for chunk in agent_service.process_message_stream(
                message=message,
                session_id=session_id,
            ):
                await websocket.send_json(chunk)

            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
