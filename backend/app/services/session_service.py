import asyncio
import json
import logging
import time

from app.core.config import settings

logger = logging.getLogger("ai_sale.sessions")


class SessionService:
    """Session storage with SQLite persistence and in-memory cache.

    Hot sessions live in memory for fast access; SQLite provides durability
    across restarts. On startup, recent sessions are loaded from the DB.
    """

    def __init__(self):
        self._sessions: dict[str, dict] = {}
        self._lock = asyncio.Lock()
        self._db = None
        self._initialized = False

    async def initialize(self):
        if self._initialized:
            return
        from app.core.database import get_db
        self._db = await get_db()
        cutoff = time.time() - settings.session_ttl_seconds
        async with self._db.execute(
            "SELECT session_id, messages, created_at, last_active "
            "FROM sessions WHERE last_active > ?",
            (cutoff,),
        ) as cursor:
            rows = await cursor.fetchall()
        for row in rows:
            self._sessions[row["session_id"]] = {
                "messages": json.loads(row["messages"]),
                "created_at": row["created_at"],
                "last_active": row["last_active"],
            }
        logger.info("Loaded %d active sessions from DB", len(rows))
        self._initialized = True

    def get_history(self, session_id: str) -> list[dict]:
        session = self._sessions.get(session_id)
        if not session:
            return []
        session["last_active"] = time.time()
        return session["messages"][-settings.session_max_messages:]

    async def add_message(self, session_id: str, role: str, content: str):
        now = time.time()
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "messages": [],
                "created_at": now,
                "last_active": now,
            }
        session = self._sessions[session_id]
        session["messages"].append({"role": role, "content": content})
        session["last_active"] = now

        if self._db:
            await self._persist_session(session_id, session)

        self._cleanup_expired()

    async def _persist_session(self, session_id: str, session: dict):
        try:
            await self._db.execute(
                "INSERT INTO sessions (session_id, messages, created_at, last_active) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET messages=?, last_active=?",
                (
                    session_id,
                    json.dumps(session["messages"], ensure_ascii=False),
                    session["created_at"],
                    session["last_active"],
                    json.dumps(session["messages"], ensure_ascii=False),
                    session["last_active"],
                ),
            )
            await self._db.commit()
        except Exception as e:
            logger.error("Failed to persist session %s: %s", session_id, e)

    def active_sessions_count(self) -> int:
        self._cleanup_expired()
        return len(self._sessions)

    def get_all_sessions(self) -> dict[str, dict]:
        self._cleanup_expired()
        return self._sessions

    def _cleanup_expired(self):
        now = time.time()
        expired = [
            sid
            for sid, session in self._sessions.items()
            if now - session["last_active"] > settings.session_ttl_seconds
        ]
        for sid in expired:
            del self._sessions[sid]


session_service = SessionService()
