from pydantic import BaseModel, Field


class LeadRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    phone: str = Field(..., min_length=5, max_length=30)
    message: str = ""
    source: str = "chat_widget"
    session_id: str | None = None


class LeadResponse(BaseModel):
    status: str = "ok"
    lead_id: str = ""
    message: str = "Заявка принята! Мы свяжемся с вами в ближайшее время."
