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

КРИТИЧЕСКИ ВАЖНО:
- Учитывай ТОЛЬКО то, что ЯВНО сказал или подтвердил КЛИЕНТ (роль «Клиент» в тексте ниже).
- НЕ приписывай клиенту факты из ответов консультанта, примерам из базы знаний и гипотетическим фразам («если у вас дом…»).
- Если клиент пишет, что дома ещё нет, только планирует стройку, «просто интересуюсь», стройка осенью/в будущем — warm_contour = "no" или "unknown", НИКОГДА "yes".
- warm_contour = "yes" ТОЛЬКО если клиент прямо сказал, что коробка/дом уже есть, стройка на стадии отделки/готов, можно монтировать инженерку.

Параметры:
1. warm_contour — построен ли «тёплый контур» (коробка дома готова под инженерные системы)
2. budget_ok — готов ли обсуждать бюджет на инженерные системы от ~1,8 млн руб. (yes только если клиент явно готов к такому порядку сумм или уже обсуждал бюджет)
3. meeting_ready — готов ли к встрече/выезду в ближайшие 5 рабочих дней (yes только если явно согласился на скорую встречу)

Для каждого параметра:
- status: "yes" | "no" | "unknown"
- detail: одно короткое предложение на русском, строго по фактам из реплик КЛИЕНТА

lead_temperature (пересчитай по правилу, не выдумывай):
- "hot" — ровно три параметра со status "yes"
- "warm" — ровно два параметра со status "yes"
- "cold" — ноль или один параметр со status "yes" (или если клиент на ранней стадии без дома)

summary: 1–2 предложения, без противоречий с полями выше; только потребность клиента по его словам.

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
            result = self._sanitize_qualification(result, history)
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

    def _client_text(self, history: list[dict]) -> str:
        parts = []
        for msg in history[-20:]:
            if msg.get("role") == "user":
                parts.append(str(msg.get("content", "")))
        return " ".join(parts).lower()

    def _sanitize_qualification(self, result: dict, history: list[dict]) -> dict:
        """Исправляет типичные галлюцинации LLM: «тёплый контур» при отсутствии дома у клиента."""
        client = self._client_text(history)
        if not client.strip():
            return result

        no_house_markers = (
            "дома нет",
            "нет дома",
            "дома ещё нет",
            "ещё нет дома",
            "еще нет дома",
            "дома пока нет",
            "просто интересуюсь",
            "только интересуюсь",
            "планирую стройку",
            "стройка к осени",
            "пока только собираю",
            "пока только",
            "будущего дома",
            "дом ещё не",
            "дом еще не",
            "нет ещё дома",
        )
        has_no_house_hint = any(m in client for m in no_house_markers)

        wc = result.get("warm_contour") or {}
        if wc.get("status") == "yes" and has_no_house_hint:
            result["warm_contour"] = {
                "status": "no",
                "detail": "Клиент указывал, что дома ещё нет или стройка только в планах — тёплый контур не готов.",
            }
            logger.info("Qualification sanitize: warm_contour yes→no (client has no house / early stage)")
            summ = (result.get("summary") or "").lower()
            if any(w in summ for w in ("коробк", "тёпл", "тепл", "готов", "уже есть")):
                result["summary"] = (
                    "Клиент интересуется инженерными системами; по его словам дома ещё нет "
                    "или стройка только планируется — нужна консультация по срокам и этапам."
                )

        return result

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
