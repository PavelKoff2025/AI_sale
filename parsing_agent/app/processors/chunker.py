import hashlib
from dataclasses import dataclass, field

from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)
    chunk_id: str = ""

    def __post_init__(self):
        if not self.chunk_id:
            self.chunk_id = hashlib.md5(self.text.encode()).hexdigest()[:12]


class TextChunker:
    def __init__(self, config: dict):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.get("chunk_size", 500),
            chunk_overlap=config.get("chunk_overlap", 50),
            separators=config.get("separators", ["\n\n", "\n", ". ", " "]),
        )

    def chunk(self, text: str, metadata: dict) -> list[Chunk]:
        splits = self.splitter.split_text(text)
        chunks = []
        for i, split_text in enumerate(splits):
            chunk_metadata = {
                **metadata,
                "chunk_index": i,
                "total_chunks": len(splits),
            }
            chunks.append(Chunk(text=split_text, metadata=chunk_metadata))
        return chunks
