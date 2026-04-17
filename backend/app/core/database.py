import json
import logging
import os
from pathlib import Path

import aiosqlite

from app.core.config import settings

logger = logging.getLogger("ai_sale.database")

_DB_PATH: str | None = None
_db: aiosqlite.Connection | None = None


def _resolve_db_path() -> str:
    url = settings.database_url
    if url.startswith("sqlite"):
        path = url.split("///", 1)[-1]
    else:
        path = url
    if not os.path.isabs(path):
        base = Path(__file__).resolve().parents[3]
        path = str(base / path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


async def get_db() -> aiosqlite.Connection:
    global _db, _DB_PATH
    if _db is not None:
        return _db

    _DB_PATH = _resolve_db_path()
    logger.info("Opening SQLite database: %s", _DB_PATH)
    _db = await aiosqlite.connect(_DB_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA foreign_keys=ON")
    await _init_tables(_db)
    return _db


async def _init_tables(db: aiosqlite.Connection):
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id   TEXT PRIMARY KEY,
            messages     TEXT NOT NULL DEFAULT '[]',
            created_at   REAL NOT NULL,
            last_active  REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS leads (
            id           TEXT PRIMARY KEY,
            name         TEXT NOT NULL,
            phone        TEXT NOT NULL,
            message      TEXT NOT NULL DEFAULT '',
            source       TEXT NOT NULL DEFAULT 'chat_widget',
            session_id   TEXT,
            qualification TEXT,
            created_at   TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_last_active ON sessions(last_active);
        CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);
    """)
    await db.commit()
    logger.info("Database tables initialized")


async def close_db():
    global _db
    if _db is not None:
        await _db.close()
        _db = None
        logger.info("Database connection closed")
