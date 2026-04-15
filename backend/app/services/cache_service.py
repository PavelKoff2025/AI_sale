import re
import threading
import time


class TTLCache:
    def __init__(self, max_items: int = 500):
        self.max_items = max_items
        self._data: dict[str, tuple[float, object]] = {}
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            row = self._data.get(key)
            if not row:
                return None
            expires_at, value = row
            if expires_at <= time.time():
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: object, ttl_seconds: int):
        if ttl_seconds <= 0:
            return
        with self._lock:
            if len(self._data) >= self.max_items:
                self._cleanup_expired()
                if len(self._data) >= self.max_items:
                    oldest_key = min(self._data.items(), key=lambda i: i[1][0])[0]
                    self._data.pop(oldest_key, None)
            self._data[key] = (time.time() + ttl_seconds, value)

    def _cleanup_expired(self):
        now = time.time()
        stale = [k for k, (expires_at, _) in self._data.items() if expires_at <= now]
        for k in stale:
            self._data.pop(k, None)


def normalize_query(text: str) -> str:
    lowered = text.lower().strip()
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered
