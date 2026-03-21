import logging
from pathlib import Path

from PyPDF2 import PdfReader

from app.parsers.base import BaseParser, ParsedDocument

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    async def parse(self, source_config: dict) -> list[ParsedDocument]:
        file_path = source_config.get("path", "")
        if not Path(file_path).exists():
            logger.error("PDF file not found: %s", file_path)
            return []

        reader = PdfReader(file_path)
        documents = []

        full_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                full_text.append(text)

        if full_text:
            documents.append(ParsedDocument(
                text="\n\n".join(full_text),
                metadata={
                    "source": "pdf",
                    "file": Path(file_path).name,
                    "title": source_config.get("name", Path(file_path).stem),
                    "total_pages": len(reader.pages),
                },
                source_type="pdf",
            ))

        return documents
