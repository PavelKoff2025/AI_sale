"""
Сервис отправки уведомлений о новых заявках в Telegram.
Использует Telegram Bot API через httpx (async).
"""

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramService:
    def __init__(self):
        self.token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self.enabled = settings.telegram_enabled and bool(self.token) and bool(self.chat_id)

        if not self.enabled:
            logger.warning(
                "Telegram notifications disabled — "
                "set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env"
            )

    async def send_lead_notification(self, lead: dict) -> bool:
        if not self.enabled:
            return False

        text = self._format_lead_message(lead)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    TELEGRAM_API.format(token=self.token),
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                )

            if response.status_code == 200:
                logger.info("Telegram notification sent for lead %s", lead.get("id", "?"))
                return True

            logger.error(
                "Telegram API error %s: %s",
                response.status_code,
                response.text[:200],
            )
            return False

        except httpx.TimeoutException:
            logger.error("Telegram API timeout for lead %s", lead.get("id", "?"))
            return False
        except Exception as e:
            logger.error("Telegram send failed: %s", e)
            return False

    def _format_lead_message(self, lead: dict) -> str:
        name = lead.get("name", "—")
        phone = lead.get("phone", "—")
        message = lead.get("message", "")
        source = lead.get("source", "chat_widget")
        created = lead.get("created_at", "")
        lead_id = lead.get("id", "")

        lines = [
            "🔔 <b>Новая заявка с сайта!</b>",
            "",
            f"👤 <b>Имя:</b> {name}",
            f"📞 <b>Телефон:</b> {phone}",
        ]

        if message:
            lines.append(f"💬 <b>Сообщение:</b> {message}")

        lines.extend([
            "",
            f"📎 Источник: {source}",
            f"🕐 {created}",
            f"🆔 {lead_id}",
        ])

        return "\n".join(lines)

    async def send_test_message(self) -> bool:
        """Отправка тестового сообщения для проверки настроек."""
        if not self.enabled:
            return False

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    TELEGRAM_API.format(token=self.token),
                    json={
                        "chat_id": self.chat_id,
                        "text": "✅ AI-агент «ГК Проект» подключён! Уведомления о заявках будут приходить сюда.",
                        "parse_mode": "HTML",
                    },
                )
            return response.status_code == 200
        except Exception as e:
            logger.error("Telegram test message failed: %s", e)
            return False


telegram_service = TelegramService()
