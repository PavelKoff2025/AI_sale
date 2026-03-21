import time
from app.core.config import settings


class SessionService:
    """In-memory session storage. Replace with Redis for production."""

    def __init__(self):
        self._sessions: dict[str, dict] = {}

    def get_history(self, session_id: str) -> list[dict]:
        session = self._sessions.get(session_id)
        if not session:
            return []
        session["last_active"] = time.time()
        return session["messages"][-settings.session_max_messages :]

    def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "messages": [],
                "created_at": time.time(),
                "last_active": time.time(),
            }
        self._sessions[session_id]["messages"].append(
            {"role": role, "content": content}
        )
        self._sessions[session_id]["last_active"] = time.time()
        self._cleanup_expired()

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
