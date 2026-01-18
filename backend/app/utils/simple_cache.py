"""
Simple in-memory cache implementation (replaces Redis)

This cache is suitable for single-instance deployments where Redis is not available.
For multi-instance deployments or persistent cache, use Redis instead.
"""

import time
from typing import Any, Optional, Dict
import logging
import threading

logger = logging.getLogger(__name__)


class SimpleCache:
    """Thread-safe in-memory cache with TTL support"""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._cleanup_counter = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if expired/not found
        """
        with self._lock:
            if key not in self._cache:
                return None

            # Check if expired
            if key in self._timestamps:
                if time.time() > self._timestamps[key]:
                    # Expired - remove and return None
                    self.delete(key)
                    return None

            return self._cache.get(key)

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """
        Set value in cache with TTL

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default 300 = 5 minutes)
        """
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = time.time() + ttl

            # Periodically cleanup expired keys (every 100 sets)
            self._cleanup_counter += 1
            if self._cleanup_counter >= 100:
                self._cleanup_expired()
                self._cleanup_counter = 0

    def delete(self, key: str) -> None:
        """Delete key from cache"""
        with self._lock:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)

    def clear(self) -> None:
        """Clear entire cache"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
            logger.info("Cache cleared")

    def _cleanup_expired(self) -> None:
        """Remove expired keys from cache (internal, assumes lock held)"""
        current_time = time.time()
        expired_keys = [
            key for key, expiry in self._timestamps.items()
            if current_time > expiry
        ]

        for key in expired_keys:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache keys")

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        with self._lock:
            return {
                "total_keys": len(self._cache),
                "expired_keys": sum(
                    1 for expiry in self._timestamps.values()
                    if time.time() > expiry
                )
            }


# Global cache instance
_cache = SimpleCache()


def get_cache() -> SimpleCache:
    """Get global cache instance"""
    return _cache
