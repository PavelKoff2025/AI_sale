"""Tests for Pydantic models validation."""

import pytest
from pydantic import ValidationError

from app.models.chat import ChatRequest, ChatResponse, Source
from app.models.lead import LeadRequest, LeadResponse


class TestChatRequest:
    def test_valid(self):
        req = ChatRequest(message="Привет")
        assert req.message == "Привет"
        assert req.session_id is None

    def test_with_session(self):
        req = ChatRequest(message="Тест", session_id="abc-123")
        assert req.session_id == "abc-123"

    def test_empty_message_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="")

    def test_too_long_message_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="x" * 5001)


class TestChatResponse:
    def test_defaults(self):
        resp = ChatResponse(session_id="s1", message="Ответ")
        assert resp.intent == "general"
        assert resp.tokens_used == 0
        assert resp.sources == []


class TestSource:
    def test_minimal(self):
        src = Source(title="Page", chunk_id="abc", score=0.85)
        assert src.url == ""


class TestLeadRequest:
    def test_valid(self):
        req = LeadRequest(name="Иван", phone="+74959087474")
        assert req.source == "chat_widget"
        assert req.message == ""

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            LeadRequest(name="", phone="+71234567890")

    def test_phone_too_short(self):
        with pytest.raises(ValidationError):
            LeadRequest(name="Иван", phone="123")


class TestLeadResponse:
    def test_defaults(self):
        resp = LeadResponse()
        assert resp.status == "ok"
        assert "Заявка принята" in resp.message
