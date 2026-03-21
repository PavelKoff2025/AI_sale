from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    session_id: str | None = None
    metadata: dict | None = None


class Source(BaseModel):
    title: str
    chunk_id: str
    score: float
    url: str = ""


class ChatResponse(BaseModel):
    session_id: str
    message: str
    sources: list[Source] = []
    intent: str = "general"
    tokens_used: int = 0
