"""
Классификатор намерений (intent) пользователя.
Быстрая эвристика до вызова LLM — определяет категорию запроса.
Многословные фразы дают +2 балла, однословные +1.
"""

import re

INTENT_PHRASES: dict[str, list[str]] = {
    "pricing": [
        "сколько стоит", "какая цена", "какая стоимость", "расчёт стоимост",
        "расчет стоимост", "узнать цен", "узнать стоимост",
    ],
    "lead": [
        "выезд инженер", "вызвать инженер", "оставить заявк",
    ],
    "contacts": [
        "где находит", "где вы", "как доехать", "как добраться",
    ],
    "process": [
        "как работает", "как вы работ", "как происход",
    ],
}

INTENT_KEYWORDS: dict[str, list[str]] = {
    "pricing": [
        "цен", "стоимост", "стоит", "прайс", "бюджет", "смет",
        "дорого", "дёшев", "дешев", "тариф", "прейскурант",
    ],
    "services": [
        "услуг", "монтаж", "котельн", "отоплен", "водоснабж", "электри",
        "канализац", "тёплый пол", "теплый пол", "радиатор", "скважин",
        "септик", "кессон", "бойлер", "насос",
        "водоочист", "конвектор", "дымоход",
    ],
    "lead": [
        "заявк", "заказ", "вызвать", "вызовите", "записаться", "оставить",
        "перезвон", "консультац", "замер",
    ],
    "contacts": [
        "телефон", "контакт", "адрес", "позвонить", "связаться",
        "email", "почт", "офис", "местоположен",
    ],
    "process": [
        "этап", "процесс", "шаг", "порядок", "сроки",
    ],
    "guarantee": [
        "гарант", "ответственн", "страхов", "качеств", "рекламац",
    ],
    "portfolio": [
        "портфолио", "пример работ", "пример", "объект", "кейс", "проект",
        "фото работ", "отчёт", "отчет", "наши работ",
    ],
    "reviews": [
        "отзыв", "рекоменд", "довольн", "мнение",
    ],
}

PRIORITY_INTENTS = ["pricing", "lead", "contacts"]


def classify_intent(message: str) -> str:
    text = message.lower()
    scores: dict[str, int] = {}

    for intent, phrases in INTENT_PHRASES.items():
        for phrase in phrases:
            if phrase in text:
                scores[intent] = scores.get(intent, 0) + 2

    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[intent] = scores.get(intent, 0) + 1

    if not scores:
        return "general"

    max_score = max(scores.values())
    top = [k for k, v in scores.items() if v == max_score]

    if len(top) == 1:
        return top[0]

    for priority in PRIORITY_INTENTS:
        if priority in top:
            return priority

    return top[0]
