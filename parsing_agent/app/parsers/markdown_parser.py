import logging
from pathlib import Path

from app.parsers.base import BaseParser, ParsedDocument

logger = logging.getLogger(__name__)


class MarkdownParser(BaseParser):
    async def parse(self, source_config: dict) -> list[ParsedDocument]:
        file_path = source_config.get("path", "")
        path = Path(file_path)
        if not path.is_file():
            logger.error("Markdown file not found: %s", file_path)
            return []

        try:
            text = path.read_text(encoding="utf-8")
        except OSError as e:
            logger.error("Cannot read markdown %s: %s", file_path, e)
            return []

        text = text.strip()
        if not text:
            return []

        category = source_config.get("category", "markdown")
        company = source_config.get("company_name", "")

        meta = {
            "source": "markdown",
            "file": path.name,
            "title": source_config.get("name", path.stem),
            "category": category,
        }
        if company:
            meta["company"] = company

        return [
            ParsedDocument(
                text=text,
                metadata=meta,
                source_type="markdown",
            )
        ]
