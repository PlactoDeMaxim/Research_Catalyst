"""
Cache Service

In-memory cache with 24-hour TTL.
Cache key = hash of query + filters.
"""

import hashlib
import json
import time
from typing import Any

CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours

_cache: dict[str, tuple[float, Any]] = {}


def _make_key(query: str, **filters: Any) -> str:
    """Create a deterministic cache key from query + filters."""
    payload = json.dumps({"query": query.lower().strip(), **filters}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def get(query: str, **filters: Any) -> Any | None:
    """Retrieve a cached result if it exists and hasn't expired."""
    key = _make_key(query, **filters)
    entry = _cache.get(key)
    if entry is None:
        return None
    timestamp, value = entry
    if time.time() - timestamp > CACHE_TTL_SECONDS:
        # Expired — remove and return None
        _cache.pop(key, None)
        return None
    return value


def set(query: str, value: Any, **filters: Any) -> None:
    """Store a value in the cache."""
    key = _make_key(query, **filters)
    _cache[key] = (time.time(), value)
    _evict_expired()


def _evict_expired() -> None:
    """Remove all expired entries (lazy cleanup)."""
    now = time.time()
    expired_keys = [k for k, (ts, _) in _cache.items() if now - ts > CACHE_TTL_SECONDS]
    for k in expired_keys:
        _cache.pop(k, None)
