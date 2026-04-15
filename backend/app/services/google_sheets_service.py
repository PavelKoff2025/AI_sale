"""
Сервис записи логов в Google Sheets.

Таблица содержит 3 листа:
  - Диалоги (conversations)
  - Заявки (leads)
  - События (events)

Запись происходит асинхронно в background, не блокируя основной поток.
При ошибке — логирует и продолжает работу (Sheets не критичен).
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

from app.core.config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_CONVERSATIONS = "Диалоги"
SHEET_LEADS = "Заявки"
SHEET_EVENTS = "События"

CONVERSATIONS_HEADERS = [
    "Дата/Время", "Session ID", "Вопрос клиента", "Ответ AI",
    "Intent", "Источники (RAG)", "Токены", "Время ответа (мс)",
]

LEADS_HEADERS = [
    "Дата/Время", "ID заявки", "Имя", "Телефон", "Сообщение",
    "Источник", "Session ID",
    "Квалификация", "Тёплый контур", "Бюджет от 1.8 млн", "Готовность к встрече",
    "Резюме",
]

EVENTS_HEADERS = [
    "Дата/Время", "Тип события", "Детали",
]


class GoogleSheetsService:
    def __init__(self):
        self.enabled = settings.google_sheets_enabled
        self._client = None
        self._spreadsheet = None

        if not self.enabled:
            logger.info("Google Sheets logging disabled")
            return

        try:
            creds_path = self._resolve_creds_path()
            if not creds_path.exists():
                logger.warning(
                    "Google Sheets credentials not found at %s — disabled", creds_path
                )
                self.enabled = False
                return

            creds = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
            self._client = gspread.authorize(creds)

            if not settings.google_sheets_spreadsheet_id:
                logger.warning("GOOGLE_SHEETS_SPREADSHEET_ID not set — disabled")
                self.enabled = False
                return

            self._spreadsheet = self._client.open_by_key(
                settings.google_sheets_spreadsheet_id
            )
            self._ensure_sheets()
            logger.info(
                "Google Sheets connected: %s", self._spreadsheet.title
            )
        except Exception as e:
            logger.error("Google Sheets init failed: %s", e)
            self.enabled = False

    def _resolve_creds_path(self) -> Path:
        p = Path(settings.google_sheets_credentials_file)
        if p.is_absolute():
            return p
        return Path(__file__).resolve().parents[3] / p

    def _ensure_sheets(self):
        existing = [ws.title for ws in self._spreadsheet.worksheets()]
        sheet_headers = {
            SHEET_CONVERSATIONS: CONVERSATIONS_HEADERS,
            SHEET_LEADS: LEADS_HEADERS,
            SHEET_EVENTS: EVENTS_HEADERS,
        }
        for sheet_name, headers in sheet_headers.items():
            if sheet_name not in existing:
                ws = self._spreadsheet.add_worksheet(
                    title=sheet_name, rows=1000, cols=len(headers)
                )
                ws.append_row(headers)
                ws.format("1", {"textFormat": {"bold": True}})
                logger.info("Created sheet: %s", sheet_name)
            else:
                ws = self._spreadsheet.worksheet(sheet_name)
                first_row = ws.row_values(1)
                if not first_row:
                    ws.append_row(headers)
                    ws.format("1", {"textFormat": {"bold": True}})

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
        if not self.enabled:
            return
        sources_str = "; ".join(
            f"{s.get('title', '')} ({s.get('score', 0):.2f})" for s in sources
        ) if sources else "—"

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            session_id,
            user_message[:500],
            assistant_message[:1000],
            intent,
            sources_str,
            tokens_used,
            duration_ms,
        ]
        self._append_async(SHEET_CONVERSATIONS, row)

    def log_lead(self, lead: dict):
        if not self.enabled:
            return

        qual = lead.get("qualification", {})
        temp_map = {"hot": "ГОРЯЧИЙ", "warm": "ТЁПЛЫЙ", "cold": "ХОЛОДНЫЙ"}

        def _param(key: str) -> str:
            p = qual.get(key, {})
            status = {"yes": "Да", "no": "Нет", "unknown": "?"}.get(
                p.get("status", "unknown"), "?"
            )
            detail = p.get("detail", "")
            return f"{status}: {detail}" if detail else status

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            lead.get("id", ""),
            lead.get("name", ""),
            lead.get("phone", ""),
            lead.get("message", ""),
            lead.get("source", ""),
            lead.get("session_id", ""),
            temp_map.get(qual.get("lead_temperature", ""), "—"),
            _param("warm_contour"),
            _param("budget_ok"),
            _param("meeting_ready"),
            qual.get("summary", ""),
        ]
        self._append_async(SHEET_LEADS, row)

    def log_event(self, event_type: str, details: dict | None = None):
        if not self.enabled:
            return
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            event_type,
            str(details or {}),
        ]
        self._append_async(SHEET_EVENTS, row)

    def _append_async(self, sheet_name: str, row: list):
        try:
            loop = asyncio.get_running_loop()
            loop.run_in_executor(None, self._append_row, sheet_name, row)
        except RuntimeError:
            self._append_row(sheet_name, row)

    def _append_row(self, sheet_name: str, row: list):
        try:
            ws = self._spreadsheet.worksheet(sheet_name)
            ws.append_row(row, value_input_option="USER_ENTERED")
        except Exception as e:
            logger.error("Google Sheets write error (%s): %s", sheet_name, e)


google_sheets_service = GoogleSheetsService()
