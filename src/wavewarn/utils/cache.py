# src/wavewarn/utils/cache.py
import time
from typing import Any, Dict, Tuple, Optional

class TTLCache:
    """
    Very small in-process TTL cache for API responses.
    Not multi-process safe; good enough for a single uvicorn worker.
    """
    def __init__(self, ttl_seconds: int = 3600, max_items: int = 256):
        self.ttl = ttl_seconds
        self.max_items = max_items
        self._data: Dict[str, Tuple[float, Any]] = {}
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.evictions = 0

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        item = self._data.get(key)
        if not item:
            self.misses += 1
            return None
        ts, val = item
        if now - ts > self.ttl:
            self._data.pop(key, None)
            self.misses += 1
            return None
        self.hits += 1
        return val

    def set(self, key: str, value: Any) -> None:
        if len(self._data) >= self.max_items:
            # naive eviction: remove oldest
            oldest_key = min(self._data, key=lambda k: self._data[k][0])
            self._data.pop(oldest_key, None)
            self.evictions += 1
        self._data[key] = (time.time(), value)
        self.sets += 1

    def stats(self) -> dict:
        return {
            "ttl_s": self.ttl,
            "size": len(self._data),
            "max_items": self.max_items,
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "evictions": self.evictions,
        }

# singletons used by clients
wx_cache = TTLCache(ttl_seconds=3600, max_items=256)     # weather
aq_cache = TTLCache(ttl_seconds=3600, max_items=256)     # air (optional later)

