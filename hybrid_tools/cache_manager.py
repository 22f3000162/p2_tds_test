"""
Cache manager for storing rendered HTML and other expensive operations.
Thread-safe LRU cache with TTL support.
"""

import time
import hashlib
from typing import Optional, Any, Dict
from collections import OrderedDict
import threading


class CacheManager:
    """
    Thread-safe LRU cache with TTL support.

    Features:
    - LRU eviction when size limit reached
    - TTL (time-to-live) for cache entries
    - Lazy cleanup of expired entries
    - Content-based hashing for keys
    """

    def __init__(self, max_size: int = 100, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = threading.Lock()

        print(f"[CACHE] Initialized (max_size={max_size}, ttl={default_ttl}s)")

    # --------------------------------------------------
    # INTERNAL HELPERS
    # --------------------------------------------------
    def _generate_key(self, url: str, **kwargs) -> str:
        parts = [url]
        for k, v in sorted(kwargs.items()):
            parts.append(f"{k}={v}")

        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def _cleanup_expired(self):
        now = time.time()
        expired_keys = [
            k for k, v in self._cache.items()
            if v["expires_at"] <= now
        ]
        for k in expired_keys:
            del self._cache[k]

        if expired_keys:
            print(f"[CACHE] Cleaned {len(expired_keys)} expired entries")

    # --------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------
    def get(self, url: str, **kwargs) -> Optional[Any]:
        key = self._generate_key(url, **kwargs)

        with self._lock:
            self._cleanup_expired()

            entry = self._cache.get(key)
            if not entry:
                return None

            self._cache.move_to_end(key)
            print(f"[CACHE] ✓ Hit: {url[:60]}...")
            return entry["value"]

    def set(self, url: str, value: Any, ttl: Optional[int] = None, **kwargs):
        key = self._generate_key(url, **kwargs)
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl

        with self._lock:
            self._cleanup_expired()

            # Evict only if inserting a NEW key and at capacity
            if key not in self._cache and len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                print("[CACHE] Evicted LRU entry")

            self._cache[key] = {
                "value": value,
                "created_at": time.time(),
                "expires_at": expires_at,
            }
            self._cache.move_to_end(key)

            print(f"[CACHE] ✓ Stored: {url[:60]}... (ttl={ttl}s)")

    def delete(self, url: str, **kwargs) -> bool:
        """Explicitly delete a cache entry."""
        key = self._generate_key(url, **kwargs)
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                print(f"[CACHE] Deleted: {url[:60]}...")
                return True
        return False

    def clear(self):
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            print(f"[CACHE] Cleared {count} entries")

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            self._cleanup_expired()

            if not self._cache:
                return {
                    "size": 0,
                    "max_size": self.max_size,
                    "oldest_age": 0,
                    "newest_age": 0,
                }

            now = time.time()
            oldest = next(iter(self._cache.values()))
            newest = next(reversed(self._cache.values()))

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "oldest_age": int(now - oldest["created_at"]),
                "newest_age": int(now - newest["created_at"]),
            }


# --------------------------------------------------
# GLOBAL HTML CACHE
# --------------------------------------------------
_html_cache: Optional[CacheManager] = None


def get_html_cache() -> CacheManager:
    global _html_cache

    if _html_cache is None:
        _html_cache = CacheManager(max_size=100, default_ttl=3600)

    return _html_cache
