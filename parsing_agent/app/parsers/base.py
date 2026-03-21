from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ParsedDocument:
    text: str
    metadata: dict = field(default_factory=dict)
    source_type: str = ""


class BaseParser(ABC):
    @abstractmethod
    async def parse(self, source_config: dict) -> list[ParsedDocument]:
        pass
