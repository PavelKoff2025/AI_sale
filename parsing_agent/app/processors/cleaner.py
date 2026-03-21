import re
import html


class TextCleaner:
    def __init__(self, config: dict):
        self.config = config

    def clean(self, text: str) -> str:
        text = html.unescape(text)

        if self.config.get("remove_html", True):
            text = re.sub(r"<[^>]+>", "", text)

        if self.config.get("remove_extra_whitespace", True):
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = re.sub(r" {2,}", " ", text)

        text = text.strip()

        max_len = self.config.get("max_chunk_length", 2000)
        if len(text) > max_len * 10:
            text = text[: max_len * 10]

        return text
