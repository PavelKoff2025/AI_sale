"""
Система логирования диалогов, заявок и событий.
Пишет структурированные JSONL-файлы с ежедневной ротацией.
При включённом GOOGLE_SHEETS_ENABLED дублирует записи в Google Sheets.

Файлы:
  logs/conversations/2026-03-21.jsonl  — диалоги (вопрос + ответ + intent + sources + tokens)
  logs/leads/2026-03-21.jsonl          — заявки (имя, телефон, источник)
  logs/events/2026-03-21.jsonl         — системные события (startup, errors, telegram)
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

LOGS_DIR = Path(__file__).resolve().parents[3] / "logs"


def _get_sheets_service():
    try:
        from app.services.google_sheets_service import google_sheets_service
        return google_sheets_service
    except Exception:
        return None


class ConversationLogger:
    def __init__(self):
        self.base_dir = LOGS_DIR
        for subdir in ("conversations", "leads", "events"):
            (self.base_dir / subdir).mkdir(parents=True, exist_ok=True)
        logger.info("Logs directory: %s", self.base_dir)

    def _today_file(self, category: str) -> Path:
        date_str = datetime.now().strftime("%Y-%m-%d")
        return self.base_dir / category / f"{date_str}.jsonl"

    def _append(self, category: str, data: dict):
        data["timestamp"] = datetime.now().isoformat()
        path = self._today_file(category)

        def _write():
            try:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(data, ensure_ascii=False) + "\n")
            except Exception as e:
                logger.error("Failed to write log to %s: %s", path, e)

        try:
            loop = asyncio.get_running_loop()
            loop.run_in_executor(None, _write)
        except RuntimeError:
            _write()

    def log_conversation(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        intent: str,
        sources: list[dict],
        tokens_used: int,
        duration_ms: int = 0,
    ):
        self._append("conversations", {
            "session_id": session_id,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "intent": intent,
            "sources": sources,
            "tokens_used": tokens_used,
            "duration_ms": duration_ms,
            "model": settings.openai_model,
        })

        sheets = _get_sheets_service()
        if sheets:
            sheets.log_conversation(
                session_id=session_id,
                user_message=user_message,
                assistant_message=assistant_message,
                intent=intent,
                sources=sources,
                tokens_used=tokens_used,
                duration_ms=duration_ms,
            )

    def log_lead(self, lead: dict):
        entry = {
            "lead_id": lead.get("id", ""),
            "name": lead.get("name", ""),
            "phone": lead.get("phone", ""),
            "message": lead.get("message", ""),
            "source": lead.get("source", ""),
            "session_id": lead.get("session_id", ""),
        }
        qualification = lead.get("qualification")
        if qualification:
            entry["qualification"] = qualification
        self._append("leads", entry)

        sheets = _get_sheets_service()
        if sheets:
            sheets.log_lead(lead)

    def log_event(self, event_type: str, details: dict | None = None):
        self._append("events", {
            "event": event_type,
            "details": details or {},
        })

        sheets = _get_sheets_service()
        if sheets:
            sheets.log_event(event_type, details)

    def get_today_stats(self) -> dict:
        conversations = self._count_lines("conversations")
        leads = self._count_lines("leads")
        events = self._count_lines("events")

        intents: dict[str, int] = {}
        total_tokens = 0
        sessions: set[str] = set()

        conv_file = self._today_file("conversations")
        if conv_file.exists():
            with open(conv_file, encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        intent = entry.get("intent", "general")
                        intents[intent] = intents.get(intent, 0) + 1
                        total_tokens += entry.get("tokens_used", 0)
                        sessions.add(entry.get("session_id", ""))
                    except json.JSONDecodeError:
                        pass

        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "conversations": conversations,
            "leads": leads,
            "events": events,
            "unique_sessions": len(sessions),
            "total_tokens": total_tokens,
            "intents": dict(sorted(intents.items(), key=lambda x: -x[1])),
        }

    def get_recent_conversations(self, limit: int = 50) -> list[dict]:
        return self._read_recent("conversations", limit)

    def get_recent_leads(self, limit: int = 50) -> list[dict]:
        return self._read_recent("leads", limit)

    def get_recent_events(self, limit: int = 50) -> list[dict]:
        return self._read_recent("events", limit)

    def get_log_files(self) -> dict:
        result = {}
        for category in ("conversations", "leads", "events"):
            cat_dir = self.base_dir / category
            files = sorted(cat_dir.glob("*.jsonl"), reverse=True)
            result[category] = [
                {"date": f.stem, "size_kb": round(f.stat().st_size / 1024, 1)}
                for f in files[:30]
            ]
        return result

    def _count_lines(self, category: str) -> int:
        path = self._today_file(category)
        if not path.exists():
            return 0
        with open(path, encoding="utf-8") as f:
            return sum(1 for _ in f)

    def _read_recent(self, category: str, limit: int) -> list[dict]:
        path = self._today_file(category)
        if not path.exists():
            return []
        entries = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return list(reversed(entries[-limit:]))


conversation_logger = ConversationLogger()
