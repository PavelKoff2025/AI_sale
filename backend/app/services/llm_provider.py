"""
Абстракция LLM-провайдера с поддержкой OpenAI и GigaChat.

Режимы (LLM_PROVIDER):
  auto     — пробует OpenAI, при ошибке переключается на GigaChat
  openai   — только OpenAI
  gigachat — только GigaChat
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_CONCURRENT_LLM = 10
_llm_semaphore = asyncio.Semaphore(MAX_CONCURRENT_LLM)


@dataclass
class LLMResponse:
    content: str
    tokens_used: int
    provider: str


class BaseLLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AsyncGenerator[str, None]:
        ...

    @abstractmethod
    async def get_embedding(self, text: str) -> list[float]:
        ...


class OpenAIProvider(BaseLLMProvider):
    name = "openai"

    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.embedding_model = settings.openai_embedding_model
        logger.info("OpenAI provider initialized (model=%s)", self.model)

    async def chat(self, messages, temperature=0.7, max_tokens=1000) -> LLMResponse:
        async with _llm_semaphore:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return LLMResponse(
                content=response.choices[0].message.content,
                tokens_used=response.usage.total_tokens if response.usage else 0,
                provider=self.name,
            )

    async def chat_stream(self, messages, temperature=0.7, max_tokens=1000):
        async with _llm_semaphore:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content

    async def get_embedding(self, text: str) -> list[float]:
        async with _llm_semaphore:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )
            return response.data[0].embedding


class GigaChatProvider(BaseLLMProvider):
    name = "gigachat"

    def __init__(self):
        from gigachat import GigaChat
        from gigachat.models import Chat, Messages, MessagesRole
        self._GigaChat = GigaChat
        self._Chat = Chat
        self._Messages = Messages
        self._MessagesRole = MessagesRole

        self._client_kwargs = {
            "credentials": settings.gigachat_credentials,
            "model": settings.gigachat_model,
            "scope": settings.gigachat_scope,
            "verify_ssl_certs": settings.gigachat_verify_ssl,
            "timeout": 60.0,
            "max_retries": 2,
        }
        logger.info(
            "GigaChat provider initialized (model=%s, scope=%s)",
            settings.gigachat_model,
            settings.gigachat_scope,
        )

    def _build_chat(self, messages: list[dict], temperature: float, max_tokens: int):
        role_map = {
            "system": self._MessagesRole.SYSTEM,
            "user": self._MessagesRole.USER,
            "assistant": self._MessagesRole.ASSISTANT,
        }
        gc_messages = [
            self._Messages(
                role=role_map.get(m["role"], self._MessagesRole.USER),
                content=m["content"],
            )
            for m in messages
        ]
        return self._Chat(
            messages=gc_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def chat(self, messages, temperature=0.7, max_tokens=1000) -> LLMResponse:
        chat_obj = self._build_chat(messages, temperature, max_tokens)
        async with self._GigaChat(**self._client_kwargs) as client:
            response = await client.achat(chat_obj)
        content = response.choices[0].message.content
        tokens_used = (
            response.usage.total_tokens if response.usage else 0
        )
        return LLMResponse(
            content=content,
            tokens_used=tokens_used,
            provider=self.name,
        )

    async def chat_stream(self, messages, temperature=0.7, max_tokens=1000):
        chat_obj = self._build_chat(messages, temperature, max_tokens)
        async with self._GigaChat(**self._client_kwargs) as client:
            async for chunk in client.astream(chat_obj):
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content

    async def get_embedding(self, text: str) -> list[float]:
        async with self._GigaChat(**self._client_kwargs) as client:
            response = await client.aembeddings(texts=[text])
        return response.data[0].embedding


class AutoProvider(BaseLLMProvider):
    """Пробует primary провайдер, при ошибке переключается на fallback."""

    name = "auto"

    def __init__(self, primary: BaseLLMProvider, fallback: BaseLLMProvider):
        self.primary = primary
        self.fallback = fallback
        self._active = primary
        logger.info(
            "Auto provider: primary=%s, fallback=%s",
            primary.name,
            fallback.name,
        )

    @property
    def active_provider_name(self) -> str:
        return self._active.name

    async def chat(self, messages, temperature=0.7, max_tokens=1000) -> LLMResponse:
        async with _llm_semaphore:
            try:
                result = await self.primary.chat(messages, temperature, max_tokens)
                self._active = self.primary
                return result
            except Exception as e:
                logger.warning(
                    "Primary LLM (%s) failed: %s. Switching to %s",
                    self.primary.name, str(e)[:120], self.fallback.name,
                )
                self._active = self.fallback
                return await self.fallback.chat(messages, temperature, max_tokens)

    async def chat_stream(self, messages, temperature=0.7, max_tokens=1000):
        async with _llm_semaphore:
            try:
                chunks_buffer = []
                async for chunk in self.primary.chat_stream(messages, temperature, max_tokens):
                    chunks_buffer.append(chunk)
                    yield chunk
                self._active = self.primary
                return
            except Exception as e:
                logger.warning(
                    "Primary LLM stream (%s) failed after %d chunks: %s. Switching to %s",
                    self.primary.name, len(chunks_buffer), str(e)[:120], self.fallback.name,
                )

            self._active = self.fallback
            async for chunk in self.fallback.chat_stream(messages, temperature, max_tokens):
                yield chunk

    async def get_embedding(self, text: str) -> list[float]:
        async with _llm_semaphore:
            try:
                return await self.primary.get_embedding(text)
            except Exception as e:
                logger.warning(
                    "Primary embeddings (%s) failed: %s. Trying %s",
                    self.primary.name, str(e)[:120], self.fallback.name,
                )
                return await self.fallback.get_embedding(text)


def create_llm_provider() -> BaseLLMProvider:
    provider_type = settings.llm_provider.lower()

    if provider_type == "openai":
        return OpenAIProvider()

    if provider_type == "gigachat":
        return GigaChatProvider()

    if provider_type == "auto":
        providers = []
        if settings.openai_api_key:
            providers.append(OpenAIProvider())
        if settings.gigachat_credentials:
            providers.append(GigaChatProvider())

        if len(providers) == 2:
            return AutoProvider(primary=providers[0], fallback=providers[1])
        if len(providers) == 1:
            return providers[0]
        raise ValueError("LLM_PROVIDER=auto, but no API keys configured (OPENAI_API_KEY / GIGACHAT_CREDENTIALS)")

    raise ValueError(f"Unknown LLM_PROVIDER: {provider_type}. Use: auto, openai, gigachat")


llm_provider = create_llm_provider()
