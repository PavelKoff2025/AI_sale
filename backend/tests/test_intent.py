"""Tests for intent classification service."""

import pytest

from app.services.intent_service import classify_intent


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Сколько стоит монтаж котельной?", "pricing"),
        ("какая цена на отопление", "pricing"),
        ("прайс на услуги", "pricing"),
        ("бюджет на водоснабжение", "pricing"),
    ],
)
def test_pricing_intent(message: str, expected: str):
    assert classify_intent(message) == expected


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Какие у вас услуги?", "services"),
        ("Монтаж котельной делаете?", "services"),
        ("Нужно отопление в дом", "services"),
        ("Водоснабжение частного дома", "services"),
        ("электрика в доме", "services"),
        ("Установите тёплый пол", "services"),
        ("септик для дачи", "services"),
    ],
)
def test_services_intent(message: str, expected: str):
    assert classify_intent(message) == expected


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Хочу оставить заявку", "lead"),
        ("Вызовите инженера на объект", "lead"),
        ("Запишите меня на консультацию", "lead"),
        ("Нужен замер", "lead"),
    ],
)
def test_lead_intent(message: str, expected: str):
    assert classify_intent(message) == expected


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Ваш телефон?", "contacts"),
        ("Как с вами связаться?", "contacts"),
        ("Где вы находитесь?", "contacts"),
        ("Какой у вас адрес?", "contacts"),
    ],
)
def test_contacts_intent(message: str, expected: str):
    assert classify_intent(message) == expected


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Как вы работаете?", "process"),
        ("Какие этапы работ?", "process"),
        ("Какой порядок работы?", "process"),
    ],
)
def test_process_intent(message: str, expected: str):
    assert classify_intent(message) == expected


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Какие гарантии?", "guarantee"),
        ("Есть ли гарантия на работы?", "guarantee"),
    ],
)
def test_guarantee_intent(message: str, expected: str):
    assert classify_intent(message) == expected


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Покажите примеры работ", "portfolio"),
        ("Есть портфолио?", "portfolio"),
        ("Фото ваших объектов", "portfolio"),
    ],
)
def test_portfolio_intent(message: str, expected: str):
    assert classify_intent(message) == expected


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Есть отзывы клиентов?", "reviews"),
        ("Какие отзывы о вашей работе?", "reviews"),
    ],
)
def test_reviews_intent(message: str, expected: str):
    assert classify_intent(message) == expected


def test_general_intent():
    assert classify_intent("Привет") == "general"
    assert classify_intent("Добрый день") == "general"
    assert classify_intent("Какая погода?") == "general"


def test_pricing_priority_over_services():
    """When both pricing and services keywords match, pricing wins (priority)."""
    result = classify_intent("Сколько стоит монтаж котельной?")
    assert result == "pricing"
