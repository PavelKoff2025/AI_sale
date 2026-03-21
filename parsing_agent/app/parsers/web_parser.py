import asyncio
import logging
import time

import requests
from bs4 import BeautifulSoup

from app.parsers.base import BaseParser, ParsedDocument

logger = logging.getLogger(__name__)


class WebParser(BaseParser):
    async def parse(self, source_config: dict) -> list[ParsedDocument]:
        urls = source_config.get("urls", [])
        delay = source_config.get("delay_seconds", 1.5)
        documents = []

        for url in urls:
            try:
                doc = await self._parse_url(url)
                if doc:
                    documents.append(doc)
                await asyncio.sleep(delay)
            except Exception as e:
                logger.error("Failed to parse %s: %s", url, e)

        return documents

    async def _parse_url(self, url: str) -> ParsedDocument | None:
        response = requests.get(url, timeout=30, headers={
            "User-Agent": "AI-Sale-Parser/1.0 (compatible bot)",
        })
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else url

        text_parts = []
        for element in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "td"]):
            text = element.get_text(strip=True)
            if text:
                text_parts.append(text)

        full_text = "\n".join(text_parts)
        if not full_text.strip():
            return None

        return ParsedDocument(
            text=full_text,
            metadata={
                "source": "web",
                "url": url,
                "title": title,
            },
            source_type="web",
        )
