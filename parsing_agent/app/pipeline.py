import json
import logging
import os
from pathlib import Path

import yaml

from app.parsers.web_parser import WebParser
from app.parsers.pdf_parser import PDFParser
from app.parsers.docx_parser import DOCXParser
from app.parsers.gkproject_parser import GKProjectParser
from app.parsers.markdown_parser import MarkdownParser
from app.processors.cleaner import TextCleaner
from app.processors.chunker import TextChunker
from app.loaders.chroma_loader import ChromaLoader

logger = logging.getLogger(__name__)

PARSER_MAP = {
    "web": WebParser,
    "pdf": PDFParser,
    "docx": DOCXParser,
    "markdown": MarkdownParser,
    "gkproject": GKProjectParser,
}


class Pipeline:
    def __init__(self, sources_config: str, processing_config: str):
        with open(sources_config) as f:
            self.sources = yaml.safe_load(f)

        with open(processing_config) as f:
            self.proc_config = yaml.safe_load(f)["processing"]

        self.cleaner = TextCleaner(self.proc_config["cleaning"])
        self.chunker = TextChunker(self.proc_config["chunking"])
        self.loader = ChromaLoader(self.proc_config)

    async def run_full(self):
        logger.info("Starting full pipeline...")
        documents = await self._parse_all()
        logger.info("Parsed %d documents", len(documents))

        chunks = self._process(documents)
        logger.info("Created %d chunks", len(chunks))

        await self.loader.load(chunks)
        logger.info("Pipeline complete!")

    async def run_parse_only(self, output_dir: str):
        documents = await self._parse_all()
        chunks = self._process(documents)

        os.makedirs(output_dir, exist_ok=True)
        output_path = Path(output_dir) / "chunks.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([c.__dict__ for c in chunks], f, ensure_ascii=False, indent=2)
        logger.info("Saved %d chunks to %s", len(chunks), output_path)

    async def run_load_only(self, input_dir: str):
        input_path = Path(input_dir) / "chunks.json"
        with open(input_path, encoding="utf-8") as f:
            raw_chunks = json.load(f)

        from app.processors.chunker import Chunk
        chunks = [Chunk(**c) for c in raw_chunks]

        await self.loader.load(chunks)
        logger.info("Loaded %d chunks from %s", len(chunks), input_path)

    async def show_stats(self):
        stats = self.loader.get_stats()
        logger.info("Collection stats: %s", stats)

    async def clear_collection(self):
        self.loader.clear()
        logger.info("Collection cleared.")

    async def _parse_all(self) -> list:
        all_documents = []
        defaults = self.sources.get("settings") or {}
        for source in self.sources.get("sources", []):
            source_type = source["type"]
            parser_class = PARSER_MAP.get(source_type)
            if not parser_class:
                logger.warning("Unknown source type: %s", source_type)
                continue

            merged = {**defaults, **source}
            parser = parser_class()
            try:
                docs = await parser.parse(merged)
                all_documents.extend(docs)
                logger.info("Parsed %d documents from '%s'", len(docs), source["name"])
            except Exception as e:
                logger.error("Failed to parse '%s': %s", source["name"], e)

        return all_documents

    def _process(self, documents: list) -> list:
        all_chunks = []
        for doc in documents:
            cleaned_text = self.cleaner.clean(doc.text)
            if len(cleaned_text) < self.proc_config["cleaning"]["min_chunk_length"]:
                continue
            chunks = self.chunker.chunk(cleaned_text, doc.metadata)
            all_chunks.extend(chunks)
        return all_chunks
