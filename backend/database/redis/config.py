"""
Redis cache configuration stub

This module provides a simple in-memory cache fallback
when Redis is not available.
"""

import os
import json
import logging
from typing import Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SimpleCache:
    """Simple in-memory cache as Redis fallback"""

    def __init__(self):
        self._cache = {}
        self._expiry = {}
        # For compatibility with Redis client interface
        self.redis_client = self

    def is_connected(self) -> bool:
        """Check if cache is available (always True for in-memory)"""
        return True

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self._cache:
            if key in self._expiry and datetime.now() > self._expiry[key]:
                del self._cache[key]
                del self._expiry[key]
                return None
            return self._cache[key]
        return None

    def set(self, key: str, value: Any, ex: int = 3600) -> bool:
        """Set value in cache with expiry in seconds"""
        self._cache[key] = value
        self._expiry[key] = datetime.now() + timedelta(seconds=ex)
        return True

    def setex(self, key: str, ttl: int, value: Any) -> bool:
        """Set value with expiry (Redis-compatible interface)"""
        return self.set(key, value, ex=ttl)

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if key in self._cache:
            del self._cache[key]
            if key in self._expiry:
                del self._expiry[key]
            return True
        return False

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        return self.get(key) is not None

    # Specialized cache methods for stocks router compatibility
    def get_cached_predictions(self, timeframe: str) -> Optional[Any]:
        """Get cached stock predictions"""
        return self.get(f"predictions:{timeframe}")

    def cache_predictions(self, timeframe: str, data: Any, ttl: int = 3600) -> bool:
        """Cache stock predictions"""
        return self.set(f"predictions:{timeframe}", data, ex=ttl)

    def get_cached_prices(self, ticker: str) -> Optional[Any]:
        """Get cached stock prices"""
        return self.get(f"prices:{ticker}")

    def cache_prices(self, ticker: str, data: Any, ttl: int = 60) -> bool:
        """Cache stock prices"""
        return self.set(f"prices:{ticker}", data, ex=ttl)

    def get_cached_news(self, ticker: str) -> Optional[Any]:
        """Get cached news for ticker"""
        return self.get(f"news:{ticker}")

    def cache_news(self, ticker: str, data: Any, ttl: int = 600) -> bool:
        """Cache news for ticker"""
        return self.set(f"news:{ticker}", data, ex=ttl)

    def get_cached_social_data(self, ticker: str) -> Optional[Any]:
        """Get cached social data for ticker"""
        return self.get(f"social:{ticker}")

    def cache_ticker_social(self, ticker: str, data: Any, ttl: int = 300) -> bool:
        """Cache social data for ticker"""
        return self.set(f"social:{ticker}", data, ex=ttl)

    def get_cached_macro_data(self) -> Optional[Any]:
        """Get cached macro indicators"""
        return self.get("macro:indicators")

    def cache_macro_data(self, data: Any, ttl: int = 3600) -> bool:
        """Cache macro indicators"""
        return self.set("macro:indicators", data, ex=ttl)


def _serialize_cache_value(value: Any) -> Any:
    if isinstance(value, (bytes, str)):
        return value
    return json.dumps(value)


def _deserialize_cache_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


class RedisCache:
    """Redis-backed cache with SimpleCache-compatible interface."""

    def __init__(self, redis_client):
        self.redis_client = redis_client

    def is_connected(self) -> bool:
        try:
            return bool(self.redis_client.ping())
        except Exception:
            return False

    def get(self, key: str) -> Optional[Any]:
        return _deserialize_cache_value(self.redis_client.get(key))

    def set(self, key: str, value: Any, ex: int = 3600) -> bool:
        payload = _serialize_cache_value(value)
        return bool(self.redis_client.setex(key, ex, payload))

    def setex(self, key: str, ttl: int, value: Any) -> bool:
        payload = _serialize_cache_value(value)
        return bool(self.redis_client.setex(key, ttl, payload))

    def delete(self, key: str) -> bool:
        return bool(self.redis_client.delete(key))

    def exists(self, key: str) -> bool:
        return bool(self.redis_client.exists(key))

    def get_cached_predictions(self, timeframe: str) -> Optional[Any]:
        return self.get(f"predictions:{timeframe}")

    def cache_predictions(self, timeframe: str, data: Any, ttl: int = 3600) -> bool:
        return self.set(f"predictions:{timeframe}", data, ex=ttl)

    def get_cached_prices(self, ticker: str) -> Optional[Any]:
        return self.get(f"prices:{ticker}")

    def cache_prices(self, ticker: str, data: Any, ttl: int = 60) -> bool:
        return self.set(f"prices:{ticker}", data, ex=ttl)

    def get_cached_news(self, ticker: str) -> Optional[Any]:
        return self.get(f"news:{ticker}")

    def cache_news(self, ticker: str, data: Any, ttl: int = 600) -> bool:
        return self.set(f"news:{ticker}", data, ex=ttl)

    def get_cached_social_data(self, ticker: str) -> Optional[Any]:
        return self.get(f"social:{ticker}")

    def cache_ticker_social(self, ticker: str, data: Any, ttl: int = 300) -> bool:
        return self.set(f"social:{ticker}", data, ex=ttl)

    def get_cached_macro_data(self) -> Optional[Any]:
        return self.get("macro:indicators")

    def cache_macro_data(self, data: Any, ttl: int = 3600) -> bool:
        return self.set("macro:indicators", data, ex=ttl)


# Global cache instance
_cache_instance = None


def get_redis_cache() -> Optional[SimpleCache]:
    """Get Redis cache instance or fallback to SimpleCache."""
    global _cache_instance

    if _cache_instance is None:
        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            try:
                import redis
                try:
                    max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "200"))
                except ValueError:
                    max_connections = 200
                client = redis.Redis.from_url(
                    redis_url,
                    decode_responses=False,
                    max_connections=max_connections,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True,
                )
                client.ping()
                _cache_instance = RedisCache(client)
                logger.info("Connected to Redis cache")
                return _cache_instance
            except Exception as exc:
                logger.warning("Redis unavailable, using SimpleCache fallback: %s", exc)

        _cache_instance = SimpleCache()
        logger.info("Using in-memory cache (SimpleCache)")

    return _cache_instance
