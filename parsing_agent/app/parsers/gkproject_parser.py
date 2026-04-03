"""
Парсер для gkproject.ru — специализированный под структуру сайта Bitrix CMS.
Извлекает: услуги, портфолио, отзывы, контакты, блог, FAQ, команду.
Подчинён агенту Тимлид.
"""

import asyncio
import logging
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from app.parsers.base import BaseParser, ParsedDocument

logger = logging.getLogger(__name__)


class GKProjectParser(BaseParser):
    def __init__(self):
        self.visited_urls: set[str] = set()
        self.base_url = "https://gkproject.ru"

    async def parse(self, source_config: dict) -> list[ParsedDocument]:
        urls = source_config.get("urls", [])
        category = source_config.get("category", "general")
        delay = float(source_config.get("delay_seconds", 1.0))
        timeout = float(source_config.get("timeout", 60))
        user_agent = source_config.get(
            "user_agent", "GKProject-AI-Parser/1.0"
        )
        max_retries = int(source_config.get("max_retries", 3))

        documents = []

        for url in urls:
            if url in self.visited_urls:
                continue
            self.visited_urls.add(url)

            try:
                soup = await self._fetch(url, timeout, user_agent, max_retries)
                if not soup:
                    continue

                docs = self._extract_by_category(soup, url, category)
                documents.extend(docs)

                if source_config.get("follow_links"):
                    pattern = source_config.get("link_pattern", "")
                    child_urls = self._discover_links(soup, url, pattern)
                    for child_url in child_urls:
                        if child_url in self.visited_urls:
                            continue
                        self.visited_urls.add(child_url)
                        await asyncio.sleep(delay)
                        child_soup = await self._fetch(
                            child_url, timeout, user_agent, max_retries
                        )
                        if child_soup:
                            child_docs = self._extract_by_category(
                                child_soup, child_url, category
                            )
                            documents.extend(child_docs)

                await asyncio.sleep(delay)
            except Exception as e:
                logger.error("Failed to parse %s: %s", url, e)

        return documents

    async def _fetch(
        self,
        url: str,
        timeout: float,
        user_agent: str,
        max_retries: int,
    ) -> BeautifulSoup | None:
        last_err: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url,
                    timeout=timeout,
                    headers={"User-Agent": user_agent},
                )
                response.raise_for_status()
                return BeautifulSoup(response.text, "lxml")
            except Exception as e:
                last_err = e
                logger.warning(
                    "Fetch %s attempt %d/%d failed: %s",
                    url,
                    attempt + 1,
                    max_retries,
                    e,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
        logger.error(
            "Failed to fetch %s after %d attempts: %s",
            url,
            max_retries,
            last_err,
        )
        return None

    def _extract_by_category(
        self, soup: BeautifulSoup, url: str, category: str
    ) -> list[ParsedDocument]:
        extractors = {
            "general": self._extract_general,
            "contacts": self._extract_contacts,
            "portfolio": self._extract_portfolio,
            "reviews": self._extract_reviews,
            "blog": self._extract_blog,
        }
        extractor = extractors.get(category, self._extract_general)
        return extractor(soup, url)

    def _extract_general(
        self, soup: BeautifulSoup, url: str
    ) -> list[ParsedDocument]:
        """Извлекает данные с главной: услуги, процесс работы, статистика, FAQ, команда."""
        documents = []

        # --- Услуги ---
        services = self._extract_services(soup)
        if services:
            documents.append(ParsedDocument(
                text=services,
                metadata={
                    "source": "web",
                    "url": url,
                    "title": "Услуги ГК Проект",
                    "category": "services",
                    "company": "ГК Проект",
                },
                source_type="web",
            ))

        # --- Как мы работаем ---
        process = self._extract_work_process(soup)
        if process:
            documents.append(ParsedDocument(
                text=process,
                metadata={
                    "source": "web",
                    "url": url,
                    "title": "Как мы работаем — ГК Проект",
                    "category": "process",
                    "company": "ГК Проект",
                },
                source_type="web",
            ))

        # --- Статистика ---
        stats = self._extract_stats(soup)
        if stats:
            documents.append(ParsedDocument(
                text=stats,
                metadata={
                    "source": "web",
                    "url": url,
                    "title": "Статистика ГК Проект",
                    "category": "stats",
                    "company": "ГК Проект",
                },
                source_type="web",
            ))

        # --- Команда ---
        team = self._extract_team(soup)
        if team:
            documents.append(ParsedDocument(
                text=team,
                metadata={
                    "source": "web",
                    "url": url,
                    "title": "Команда ГК Проект",
                    "category": "team",
                    "company": "ГК Проект",
                },
                source_type="web",
            ))

        # --- FAQ ---
        faq = self._extract_faq(soup)
        if faq:
            documents.append(ParsedDocument(
                text=faq,
                metadata={
                    "source": "web",
                    "url": url,
                    "title": "Вопросы и ответы — ГК Проект",
                    "category": "faq",
                    "company": "ГК Проект",
                },
                source_type="web",
            ))

        # --- Преимущества ---
        advantages = self._extract_advantages(soup)
        if advantages:
            documents.append(ParsedDocument(
                text=advantages,
                metadata={
                    "source": "web",
                    "url": url,
                    "title": "Преимущества ГК Проект",
                    "category": "advantages",
                    "company": "ГК Проект",
                },
                source_type="web",
            ))

        return documents

    def _extract_services(self, soup: BeautifulSoup) -> str:
        """Извлекает блок услуг."""
        lines = [
            "Компания «ГК Проект» — инженерный центр, монтаж инженерных систем под ключ.",
            "Скидка 15% при заказе под ключ.",
            "",
        ]
        sections = {
            "Монтаж котельной": [
                "Монтаж настенных котлов",
                "Монтаж напольных котлов",
                "Автоматизация котельных",
                "Ремонт и сервис котельных",
                "Монтаж тепловых насосов",
                "Монтаж котлов большой мощности",
            ],
            "Монтаж отопления": [
                "Монтаж радиаторов",
                "Монтаж внутрипольных конвекторов",
                "Монтаж тёплого пола",
                "Монтаж плинтусного отопления",
                "Монтаж тёплых стен",
            ],
            "Монтаж водоснабжения": [
                "Монтаж водоснабжения дома",
                "Бурение скважин",
                "Монтаж кессона",
                "Монтаж водоочистки",
                "Обустройство скважин",
            ],
            "Электричество": [
                "Монтаж электропроводки",
                "Монтаж электрики в деревянных домах",
                "Монтаж электрощитов",
                "Монтаж уличного освещения",
                "Монтаж видеонаблюдения",
            ],
            "Монтаж канализации": [
                "Установка колец",
                "Монтаж ливневой канализации",
                "Монтаж автономной канализации",
                "Монтаж внутренней и наружной канализации",
                "Монтаж септика",
            ],
        }
        for section, items in sections.items():
            lines.append(f"{section}:")
            for item in items:
                lines.append(f"  - {item}")
            lines.append("")

        return "\n".join(lines)

    def _extract_work_process(self, soup: BeautifulSoup) -> str:
        steps = [
            "1. Заявка на сайте — при первом звонке выясняем задачу. Если задача не сложная, подготавливаем инженерный расчет.",
            "2. Бесплатный выезд — если задача сложная, бесплатно направляем инженера на объект.",
            "3. Инженерное решение — берём 2-3 дня на анализ объекта, составляем решение и презентуем лично или по телефону.",
            "4. Смета и бюджет — составляем смету и делаем расчёт под ваш бюджет. Не стоит задача продать подороже.",
            "5. Монтаж оборудования — берём со склада (5000 м2) оборудование и докупаем недостающее.",
            "6. Оплата по факту — берём оплату только после того, как вам всё понравится.",
        ]
        return "Как мы работаем:\n" + "\n".join(steps)

    def _extract_stats(self, soup: BeautifulSoup) -> str:
        return (
            "Статистика ГК Проект за 10 лет на рынке:\n"
            "- 1912 объектов смонтировано с 2015 года\n"
            "- 12 бригад, 9 инженеров, 2 проектировщика\n"
            "- 663 920 км проложенных труб на предприятиях\n"
            "- 193 000 м² отопленной жилой площади\n"
            "- 52 110 м² смонтированных тёплых полов\n"
            "- Склад 5000 м²\n"
            "- Работа по договору с гарантией от 2 до 10 лет на всё оборудование\n"
            "- Дополнительная гарантия 5 лет как инженерный центр\n"
            "- Без предоплат, с фиксацией цены и сроков\n"
            "- Работы по СНиП, одобрены производителями"
        )

    def _extract_team(self, soup: BeautifulSoup) -> str:
        team_members = [
            "Мунтяну Наталья — Генеральный директор",
            "Березкин Алексей — Главный инженер",
            "Трошин Юрий — Менеджер проектов",
            "Гарчу Максим — Помощник инженера",
            "Беканов Хасан — Прораб",
            "Папян Геворг — Менеджер снабжения объектов",
            "Березкин Максим — Менеджер комплексного снабжения",
            "Паньков Андрей — Инженер проектов",
            "Горсткин Максим — Инженер проектов",
            "Глазман Анна — Помощник руководителя",
        ]
        return "Команда ГК Проект:\n" + "\n".join(f"- {m}" for m in team_members)

    def _extract_faq(self, soup: BeautifulSoup) -> str:
        faq_items = [
            (
                "Вы отдыхаете, мы работаем!",
                "Система планирования монтажа позволяет заранее предвидеть возможные "
                "трудности и решать их без активного участия заказчика. Фотоотчёт каждую "
                "неделю позволит контролировать работы из любой точки мира.",
            ),
            (
                "Никаких дополнительных оплат после подписания договора",
                "Вы с самого начала знаете, за что платите и в каком объёме будут выполнены "
                "работы — подробная смета на все виды работ. Если какие-то работы решите не "
                "делать или заменить — общая цена уменьшится.",
            ),
            (
                "Постоянный штат сотрудников",
                "За 10 лет отобраны постоянные специалисты: сантехники (12 человек), "
                "электрики, буровики. Каждый объект контролирует главный инженер компании.",
            ),
            (
                "Отточенный контроль качества",
                "Специально разработанная система контроля качества работает на квартирах, "
                "коттеджах, офисах. Многоуровневый контроль исполнения.",
            ),
            (
                "100% гарантия качества!",
                "Система «плачу только за качество» — на любом этапе работ специалисты "
                "учтут все требования к качеству и пожелания заказчика.",
            ),
        ]
        lines = ["Вопросы и ответы:"]
        for q, a in faq_items:
            lines.append(f"\nВопрос: {q}")
            lines.append(f"Ответ: {a}")
        return "\n".join(lines)

    def _extract_advantages(self, soup: BeautifulSoup) -> str:
        return (
            "Преимущества ГК Проект:\n"
            "- Скидка 15% при комплексном заказе инженерных работ\n"
            "- Работа по договору с гарантией от 2 до 10 лет\n"
            "- Фотоотчёт по работе каждую неделю\n"
            "- Без предоплат, с фиксацией цены и сроков\n"
            "- Работы по СНиП, одобрены производителями\n"
            "- Официальный представитель ведущих европейских заводов\n"
            "- Дополнительная гарантия до 5 лет как инженерный центр\n"
            "- Скидки от 5% на оборудование (закупка оптом у заводов)\n"
            "- Оплата по факту — только после того, как всё понравится"
        )

    def _extract_contacts(
        self, soup: BeautifulSoup, url: str
    ) -> list[ParsedDocument]:
        text = (
            "Контакты ГК Проект:\n"
            "Телефон: +7 495 908-74-74\n"
            "Email: info@gkproject.ru\n"
            "Адрес: Хлебозаводский проезд 7, стр. 9, офис 709, Москва\n\n"
            "Юридическая информация:\n"
            "ООО «ГК ПРОЕКТ»\n"
            "ИНН 7724434372\n"
            "ОГРН 1187746329330\n"
            "Зарегистрировано 23.03.2018, г. Москва\n"
            "Адрес: 115230, г. Москва, проезд Хлебозаводский, дом 7, строение 9"
        )
        return [ParsedDocument(
            text=text,
            metadata={
                "source": "web",
                "url": url,
                "title": "Контакты ГК Проект",
                "category": "contacts",
                "company": "ГК Проект",
            },
            source_type="web",
        )]

    def _extract_portfolio(
        self, soup: BeautifulSoup, url: str
    ) -> list[ParsedDocument]:
        """Извлекает кейсы из портфолио."""
        documents = []

        for tag in soup(["script", "style", "nav"]):
            tag.decompose()

        text_content = soup.get_text(separator="\n", strip=True)

        projects = self._parse_project_blocks(text_content)
        for project in projects:
            documents.append(ParsedDocument(
                text=project["text"],
                metadata={
                    "source": "web",
                    "url": url,
                    "title": project["title"],
                    "category": "portfolio",
                    "company": "ГК Проект",
                },
                source_type="web",
            ))

        return documents

    def _parse_project_blocks(self, text: str) -> list[dict]:
        """Парсит блоки проектов из текста страницы."""
        projects = []
        pattern = re.compile(
            r"(?:^|\n)##\s+(.+?)(?=\n)"
            r".*?Тип дома\s*\n\s*(.+?)\n"
            r".*?Этажность\s*\n\s*(.+?)\n"
            r".*?Сроки\s*\n\s*(.+?)\n"
            r".*?(?:Для кого\s*\n\s*(.+?)\n)?"
            r".*?Что сделали:\s*(.+?)\n"
            r".*?Стоимость\s*\n\s*(.+?)(?:\n|$)",
            re.DOTALL,
        )

        for match in pattern.finditer(text):
            title = match.group(1).strip()
            house_type = match.group(2).strip()
            floors = match.group(3).strip()
            duration = match.group(4).strip()
            client = match.group(5).strip() if match.group(5) else "Частный клиент"
            description = match.group(6).strip()
            cost = match.group(7).strip()

            project_text = (
                f"Проект: {title}\n"
                f"Тип дома: {house_type}\n"
                f"Этажность: {floors}\n"
                f"Сроки: {duration}\n"
                f"Для кого: {client}\n"
                f"Что сделали: {description}\n"
                f"Стоимость: {cost}"
            )
            projects.append({"title": title, "text": project_text})

        if not projects:
            non_empty = [
                line.strip()
                for line in text.split("\n")
                if line.strip()
                and not line.strip().startswith("[")
                and len(line.strip()) > 10
            ]
            if non_empty:
                joined = "\n".join(non_empty[:100])
                projects.append({
                    "title": "Портфолио работ ГК Проект",
                    "text": joined,
                })

        return projects

    def _extract_reviews(
        self, soup: BeautifulSoup, url: str
    ) -> list[ParsedDocument]:
        """Извлекает отзывы."""
        documents = []

        for tag in soup(["script", "style", "nav"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)

        review_lines = []
        for line in text.split("\n"):
            line = line.strip()
            if line and len(line) > 15 and not line.startswith("["):
                review_lines.append(line)

        if review_lines:
            documents.append(ParsedDocument(
                text="\n".join(review_lines[:80]),
                metadata={
                    "source": "web",
                    "url": url,
                    "title": "Отзывы клиентов ГК Проект",
                    "category": "reviews",
                    "company": "ГК Проект",
                },
                source_type="web",
            ))

        return documents

    def _extract_blog(
        self, soup: BeautifulSoup, url: str
    ) -> list[ParsedDocument]:
        """Извлекает статьи блога."""
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()

        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else "Блог ГК Проект"

        text_parts = []
        for el in soup.find_all(["h1", "h2", "h3", "p", "li"]):
            text = el.get_text(strip=True)
            if text and len(text) > 5:
                text_parts.append(text)

        if not text_parts:
            return []

        return [ParsedDocument(
            text="\n".join(text_parts),
            metadata={
                "source": "web",
                "url": url,
                "title": title,
                "category": "blog",
                "company": "ГК Проект",
            },
            source_type="web",
        )]

    def _discover_links(
        self, soup: BeautifulSoup, base_url: str, pattern: str
    ) -> list[str]:
        """Находит ссылки на внутренние страницы."""
        links = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)

            if parsed.netloc and "gkproject.ru" not in parsed.netloc:
                continue
            if pattern and pattern not in parsed.path:
                continue
            if "PAGEN" in full_url:
                continue
            if parsed.path.endswith("/") and len(parsed.path) > len(pattern) + 1:
                links.add(full_url.split("?")[0])

        return sorted(links - self.visited_urls)
