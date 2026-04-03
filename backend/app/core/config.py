from pathlib import Path

from pydantic_settings import BaseSettings

_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    # LLM Provider: "auto" | "openai" | "gigachat"
    llm_provider: str = "auto"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    # Голос (Whisper + TTS) — тот же API key
    openai_tts_model: str = "tts-1"
    openai_tts_voice: str = "nova"

    # GigaChat (Sber)
    gigachat_credentials: str = ""
    gigachat_model: str = "GigaChat"
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_verify_ssl: bool = False

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_collection: str = "ai_sale_knowledge"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8080
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    log_level: str = "INFO"

    # Company
    company_name: str = "Your Company"
    company_description: str = "AI Sales Assistant"
    # Путь к файлу шаблона внутри контейнера (UTF-8). Обязательные плейсхолдеры: {company_name}, {rag_context}
    # Пример: /app/docs/SYSTEM_PROMPT.md при томе ./docs:/app/docs в docker-compose
    system_prompt_path: str = ""

    # RAG
    rag_top_k: int = 12
    rag_score_threshold: float = 0.22
    # Если после порога пусто — добираем чанки с score >= этого значения (снижает «промахи» по Азбуке и т.п.)
    rag_fallback_min_score: float = 0.12

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_enabled: bool = True

    # Session
    session_max_messages: int = 20
    session_ttl_seconds: int = 1800

    # Google Sheets
    google_sheets_enabled: bool = False
    google_sheets_credentials_file: str = ""
    google_sheets_spreadsheet_id: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    model_config = {
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
