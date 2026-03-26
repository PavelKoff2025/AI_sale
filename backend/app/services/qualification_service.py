"""
Сервис квалификации лидов.

Анализирует историю переписки с клиентом и извлекает 3 параметра:
  1. Тёплый контур (построена ли коробка дома)
  2. Бюджет (готов ли обсуждать от 1,8 млн)
  3. Готовность к встрече (в ближайшие 5 рабочих дней)
"""

import json
import logging

from app.services.llm_provider import llm_provider

logger = logging.getLogger(__name__)

QUALIFICATION_PROMPT = """\
Проанализируй диалог между AI-консультантом и потенциальным клиентом.
Извлеки параметры квалификации. Отвечай СТРОГО в формате JSON без пояснений.

Параметры:
1. warm_contour — есть ли у клиента построенный «тёплый контур» дома (коробка, крыша, окна)
2. budget_ok — готов ли обсуждать бюджет на инженерные системы от 1,8 млн руб.
3. meeting_ready — готов ли к встрече (онлайн/офлайн) в ближайшие 5 рабочих дней

Для каждого параметра укажи:
- status: "yes" | "no" | "unknown" (unknown — если в диалоге не обсуждалось)
- detail: краткое пояснение (1 предложение) на русском

Также определи:
- lead_temperature: "hot" (все 3 = yes), "warm" (2 из 3 = yes), "cold" (1 или 0 = yes)
- summary: краткое резюме потребности клиента (1-2 предложения) на русском

Формат ответа (только JSON):
{
  "warm_contour": {"status": "...", "detail": "..."},
  "budget_ok": {"status": "...", "detail": "..."},
  "meeting_ready": {"status": "...", "detail": "..."},
  "lead_temperature": "...",
  "summary": "..."
}
"""

DEFAULT_QUALIFICATION = {
    "warm_contour": {"status": "unknown", "detail": "Не обсуждалось в диалоге"},
    "budget_ok": {"status": "unknown", "detail": "Не обсуждалось в диалоге"},
    "meeting_ready": {"status": "unknown", "detail": "Не обсуждалось в диалоге"},
    "lead_temperature": "cold",
    "summary": "Клиент оставил заявку без предварительного диалога",
}


class QualificationService:
    async def analyze(self, history: list[dict]) -> dict:
        if not history:
            return dict(DEFAULT_QUALIFICATION)

        conversation_text = self._format_history(history)

        try:
            response = await llm_provider.chat(
                messages=[
                    {"role": "system", "content": QUALIFICATION_PROMPT},
                    {"role": "user", "content": conversation_text},
                ],
                temperature=0.1,
                max_tokens=500,
            )

            result = self._parse_response(response.content)
            yes_count = sum(
                1
                for key in ("warm_contour", "budget_ok", "meeting_ready")
                if result.get(key, {}).get("status") == "yes"
            )
            if "lead_temperature" not in result or result["lead_temperature"] not in (
                "hot",
                "warm",
                "cold",
            ):
                result["lead_temperature"] = (
                    "hot" if yes_count == 3 else "warm" if yes_count == 2 else "cold"
                )

            logger.info(
                "Qualification: %s (yes=%d/3)", result["lead_temperature"], yes_count
            )
            return result

        except Exception as e:
            logger.error("Qualification analysis failed: %s", e)
            return dict(DEFAULT_QUALIFICATION)

    def _format_history(self, history: list[dict]) -> str:
        lines = []
        for msg in history[-20:]:
            role = "Клиент" if msg["role"] == "user" else "Консультант"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    def _parse_response(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
            else:
                raise

        for key in ("warm_contour", "budget_ok", "meeting_ready"):
            if key not in data or not isinstance(data[key], dict):
                data[key] = {"status": "unknown", "detail": "Не удалось определить"}

        return data


qualification_service = QualificationService()
