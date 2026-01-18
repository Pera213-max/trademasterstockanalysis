"""
Redis Cache Configuration for TradeMaster Pro

Provides caching functionality for prices, predictions, social data, and more.
Uses Redis with connection pooling and comprehensive error handling.
"""

import json
import logging
from typing import Optional, Dict, List, Any, Union
from datetime import datetime, timedelta
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis cache manager for TradeMaster Pro

    Features:
    - Price caching with TTL
    - AI predictions caching
    - Social media data caching
    - Pattern-based cache invalidation
    - Connection pooling
    - Automatic serialization/deserialization
    """

    def __init__(self, host: str = "localhost", port: int = 6379,
                 db: int = 0, password: Optional[str] = None,
                 decode_responses: bool = True, max_connections: int = 50):
        """
        Initialize Redis cache connection

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (if required)
            decode_responses: Decode responses to strings
            max_connections: Maximum connections in pool
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.redis_client = None
        self.connection_pool = None

        # Initialize connection
        try:
            import redis

            # Create connection pool for better performance
            self.connection_pool = redis.ConnectionPool(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=decode_responses,
                max_connections=max_connections,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )

            # Create Redis client
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)

            # Test connection
            self.redis_client.ping()
            logger.info(f"Redis connected successfully to {host}:{port}/{db}")

        except ImportError:
            logger.error("redis-py library not installed. Install with: pip install redis")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
        except Exception as e:
            logger.error(f"Redis initialization error: {e}")

    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if not self.redis_client:
            return False

        try:
            self.redis_client.ping()
            return True
        except Exception:
            return False

    # ========================================================================
    # PRICE CACHING
    # ========================================================================

    def cache_prices(self, ticker: str, data: Dict, ttl: int = 60) -> bool:
        """
        Cache price data for a ticker

        Args:
            ticker: Ticker symbol
            data: Price data dict
            ttl: Time to live in seconds (default: 60s)

        Returns:
            True if cached successfully, False otherwise
        """
        if not self.is_connected():
            logger.warning("Redis not connected, skipping price cache")
            return False

        try:
            key = f"price:{ticker.upper()}"

            # Add timestamp to data
            data['cached_at'] = datetime.now().isoformat()

            # Serialize and cache
            serialized = json.dumps(data)
            self.redis_client.setex(key, ttl, serialized)

            logger.debug(f"Cached prices for {ticker} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Error caching prices for {ticker}: {e}")
            return False

    def get_cached_prices(self, ticker: str) -> Optional[Dict]:
        """
        Get cached price data for a ticker

        Args:
            ticker: Ticker symbol

        Returns:
            Price data dict if found, None otherwise
        """
        if not self.is_connected():
            return None

        try:
            key = f"price:{ticker.upper()}"
            cached_data = self.redis_client.get(key)

            if cached_data:
                logger.debug(f"Cache hit for prices: {ticker}")
                return json.loads(cached_data)
            else:
                logger.debug(f"Cache miss for prices: {ticker}")
                return None

        except Exception as e:
            logger.error(f"Error getting cached prices for {ticker}: {e}")
            return None

    def cache_ohlcv(self, ticker: str, timeframe: str, data: List[Dict], ttl: int = 300) -> bool:
        """
        Cache OHLCV (candlestick) data

        Args:
            ticker: Ticker symbol
            timeframe: Timeframe (1m, 5m, 1h, 1d, etc.)
            data: List of OHLCV candles
            ttl: Time to live in seconds (default: 300s)

        Returns:
            True if cached successfully
        """
        if not self.is_connected():
            return False

        try:
            key = f"ohlcv:{ticker.upper()}:{timeframe}"

            cache_data = {
                'data': data,
                'cached_at': datetime.now().isoformat()
            }

            serialized = json.dumps(cache_data)
            self.redis_client.setex(key, ttl, serialized)

            logger.debug(f"Cached OHLCV for {ticker} ({timeframe})")
            return True

        except Exception as e:
            logger.error(f"Error caching OHLCV: {e}")
            return False

    def get_cached_ohlcv(self, ticker: str, timeframe: str) -> Optional[List[Dict]]:
        """Get cached OHLCV data"""
        if not self.is_connected():
            return None

        try:
            key = f"ohlcv:{ticker.upper()}:{timeframe}"
            cached_data = self.redis_client.get(key)

            if cached_data:
                parsed = json.loads(cached_data)
                return parsed.get('data')
            return None

        except Exception as e:
            logger.error(f"Error getting cached OHLCV: {e}")
            return None

    # ========================================================================
    # AI PREDICTIONS CACHING
    # ========================================================================

    def cache_predictions(self, timeframe: str = "swing", data: List[Dict] = None,
                         ttl: int = 3600) -> bool:
        """
        Cache AI predictions

        Args:
            timeframe: Prediction timeframe (day, swing, long)
            data: List of prediction dicts
            ttl: Time to live in seconds (default: 3600s = 1 hour)

        Returns:
            True if cached successfully
        """
        if not self.is_connected():
            logger.warning("Redis not connected, skipping predictions cache")
            return False

        try:
            key = f"predictions:{timeframe}"

            cache_data = {
                'predictions': data or [],
                'cached_at': datetime.now().isoformat(),
                'count': len(data) if data else 0
            }

            serialized = json.dumps(cache_data)
            self.redis_client.setex(key, ttl, serialized)

            logger.debug(f"Cached {len(data) if data else 0} predictions for {timeframe} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Error caching predictions: {e}")
            return False

    def get_cached_predictions(self, timeframe: str = "swing") -> Optional[List[Dict]]:
        """
        Get cached AI predictions

        Args:
            timeframe: Prediction timeframe

        Returns:
            List of predictions if found, None otherwise
        """
        if not self.is_connected():
            return None

        try:
            key = f"predictions:{timeframe}"
            cached_data = self.redis_client.get(key)

            if cached_data:
                parsed = json.loads(cached_data)
                logger.debug(f"Cache hit for predictions: {timeframe} ({parsed.get('count', 0)} items)")
                return parsed.get('predictions')
            else:
                logger.debug(f"Cache miss for predictions: {timeframe}")
                return None

        except Exception as e:
            logger.error(f"Error getting cached predictions: {e}")
            return None

    def cache_ticker_prediction(self, ticker: str, prediction: Dict, ttl: int = 3600) -> bool:
        """
        Cache prediction for specific ticker

        Args:
            ticker: Ticker symbol
            prediction: Prediction data
            ttl: Time to live in seconds

        Returns:
            True if cached successfully
        """
        if not self.is_connected():
            return False

        try:
            key = f"prediction:{ticker.upper()}"

            prediction['cached_at'] = datetime.now().isoformat()
            serialized = json.dumps(prediction)
            self.redis_client.setex(key, ttl, serialized)

            return True

        except Exception as e:
            logger.error(f"Error caching ticker prediction: {e}")
            return False

    # ========================================================================
    # SOCIAL DATA CACHING
    # ========================================================================

    def cache_social_data(self, platform: str = "all", data: Union[List[Dict], Dict] = None,
                         ttl: int = 300) -> bool:
        """
        Cache social media trending data

        Args:
            platform: Social platform (reddit, twitter, stocktwits, all)
            data: Social data (list or dict)
            ttl: Time to live in seconds (default: 300s = 5 minutes)

        Returns:
            True if cached successfully
        """
        if not self.is_connected():
            logger.warning("Redis not connected, skipping social data cache")
            return False

        try:
            key = f"social:{platform}"

            cache_data = {
                'data': data or [],
                'cached_at': datetime.now().isoformat(),
                'platform': platform
            }

            serialized = json.dumps(cache_data)
            self.redis_client.setex(key, ttl, serialized)

            logger.debug(f"Cached social data for {platform} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Error caching social data: {e}")
            return False

    def get_cached_social_data(self, platform: str = "all") -> Optional[Union[List[Dict], Dict]]:
        """
        Get cached social media data

        Args:
            platform: Social platform

        Returns:
            Social data if found, None otherwise
        """
        if not self.is_connected():
            return None

        try:
            key = f"social:{platform}"
            cached_data = self.redis_client.get(key)

            if cached_data:
                parsed = json.loads(cached_data)
                logger.debug(f"Cache hit for social: {platform}")
                return parsed.get('data')
            else:
                logger.debug(f"Cache miss for social: {platform}")
                return None

        except Exception as e:
            logger.error(f"Error getting cached social data: {e}")
            return None

    def cache_ticker_social(self, ticker: str, social_data: Dict, ttl: int = 300) -> bool:
        """Cache social sentiment for specific ticker"""
        if not self.is_connected():
            return False

        try:
            key = f"social:ticker:{ticker.upper()}"

            social_data['cached_at'] = datetime.now().isoformat()
            serialized = json.dumps(social_data)
            self.redis_client.setex(key, ttl, serialized)

            return True

        except Exception as e:
            logger.error(f"Error caching ticker social data: {e}")
            return False

    # ========================================================================
    # NEWS CACHING
    # ========================================================================

    def cache_news(self, ticker: Optional[str] = None, news_data: List[Dict] = None,
                   ttl: int = 600) -> bool:
        """
        Cache news articles

        Args:
            ticker: Ticker symbol (None for general news)
            news_data: List of news articles
            ttl: Time to live in seconds (default: 600s = 10 minutes)

        Returns:
            True if cached successfully
        """
        if not self.is_connected():
            return False

        try:
            if ticker:
                key = f"news:ticker:{ticker.upper()}"
            else:
                key = "news:general"

            cache_data = {
                'news': news_data or [],
                'cached_at': datetime.now().isoformat(),
                'count': len(news_data) if news_data else 0
            }

            serialized = json.dumps(cache_data)
            self.redis_client.setex(key, ttl, serialized)

            return True

        except Exception as e:
            logger.error(f"Error caching news: {e}")
            return False

    def get_cached_news(self, ticker: Optional[str] = None) -> Optional[List[Dict]]:
        """Get cached news articles"""
        if not self.is_connected():
            return None

        try:
            if ticker:
                key = f"news:ticker:{ticker.upper()}"
            else:
                key = "news:general"

            cached_data = self.redis_client.get(key)

            if cached_data:
                parsed = json.loads(cached_data)
                return parsed.get('news')
            return None

        except Exception as e:
            logger.error(f"Error getting cached news: {e}")
            return None

    # ========================================================================
    # MACRO DATA CACHING
    # ========================================================================

    def cache_macro_data(self, macro_data: Dict, ttl: int = 3600) -> bool:
        """
        Cache macro economic indicators

        Args:
            macro_data: Macro indicators dict
            ttl: Time to live in seconds (default: 3600s = 1 hour)

        Returns:
            True if cached successfully
        """
        if not self.is_connected():
            return False

        try:
            key = "macro:indicators"

            macro_data['cached_at'] = datetime.now().isoformat()
            serialized = json.dumps(macro_data)
            self.redis_client.setex(key, ttl, serialized)

            logger.debug(f"Cached macro data (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Error caching macro data: {e}")
            return False

    def get_cached_macro_data(self) -> Optional[Dict]:
        """Get cached macro data"""
        if not self.is_connected():
            return None

        try:
            key = "macro:indicators"
            cached_data = self.redis_client.get(key)

            if cached_data:
                logger.debug("Cache hit for macro data")
                return json.loads(cached_data)
            return None

        except Exception as e:
            logger.error(f"Error getting cached macro data: {e}")
            return None

    # ========================================================================
    # CACHE INVALIDATION
    # ========================================================================

    def invalidate_cache(self, pattern: str) -> int:
        """
        Invalidate (delete) cache keys matching pattern

        Args:
            pattern: Redis key pattern (supports wildcards *)
                     Examples: "price:*", "predictions:*", "*NVDA*"

        Returns:
            Number of keys deleted
        """
        if not self.is_connected():
            logger.warning("Redis not connected, cannot invalidate cache")
            return 0

        try:
            # Find all keys matching pattern
            keys = self.redis_client.keys(pattern)

            if not keys:
                logger.debug(f"No keys found matching pattern: {pattern}")
                return 0

            # Delete all matching keys
            deleted = self.redis_client.delete(*keys)

            logger.info(f"Invalidated {deleted} cache keys matching: {pattern}")
            return deleted

        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return 0

    def invalidate_ticker_cache(self, ticker: str) -> int:
        """
        Invalidate all cache for specific ticker

        Args:
            ticker: Ticker symbol

        Returns:
            Number of keys deleted
        """
        pattern = f"*{ticker.upper()}*"
        return self.invalidate_cache(pattern)

    def invalidate_all_prices(self) -> int:
        """Invalidate all price cache"""
        return self.invalidate_cache("price:*")

    def invalidate_all_predictions(self) -> int:
        """Invalidate all prediction cache"""
        return self.invalidate_cache("predictions:*")

    def invalidate_all_social(self) -> int:
        """Invalidate all social data cache"""
        return self.invalidate_cache("social:*")

    def clear_all_cache(self) -> bool:
        """
        Clear ALL cache (use with caution!)

        Returns:
            True if successful
        """
        if not self.is_connected():
            return False

        try:
            self.redis_client.flushdb()
            logger.warning("Cleared ALL cache from Redis database")
            return True

        except Exception as e:
            logger.error(f"Error clearing all cache: {e}")
            return False

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def get_ttl(self, key: str) -> int:
        """
        Get remaining TTL for a key

        Args:
            key: Redis key

        Returns:
            Remaining TTL in seconds, -1 if no expiry, -2 if key doesn't exist
        """
        if not self.is_connected():
            return -2

        try:
            return self.redis_client.ttl(key)
        except Exception as e:
            logger.error(f"Error getting TTL: {e}")
            return -2

    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics

        Returns:
            Dict with cache stats
        """
        if not self.is_connected():
            return {'connected': False}

        try:
            info = self.redis_client.info()

            stats = {
                'connected': True,
                'used_memory_human': info.get('used_memory_human'),
                'used_memory_peak_human': info.get('used_memory_peak_human'),
                'connected_clients': info.get('connected_clients'),
                'total_commands_processed': info.get('total_commands_processed'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'uptime_in_days': info.get('uptime_in_days'),
            }

            # Calculate hit rate
            hits = stats['keyspace_hits']
            misses = stats['keyspace_misses']
            total = hits + misses

            if total > 0:
                stats['hit_rate'] = round((hits / total) * 100, 2)
            else:
                stats['hit_rate'] = 0.0

            return stats

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'connected': False, 'error': str(e)}

    def get_all_keys(self, pattern: str = "*") -> List[str]:
        """
        Get all keys matching pattern

        Args:
            pattern: Key pattern (default: all keys)

        Returns:
            List of keys
        """
        if not self.is_connected():
            return []

        try:
            return self.redis_client.keys(pattern)
        except Exception as e:
            logger.error(f"Error getting keys: {e}")
            return []

    def close(self):
        """Close Redis connection"""
        if self.connection_pool:
            self.connection_pool.disconnect()
            logger.info("Redis connection closed")


# ============================================================================
# GLOBAL REDIS INSTANCE
# ============================================================================

# Create global cache instance (can be imported by other modules)
_redis_cache: Optional[RedisCache] = None


def get_redis_cache(host: str = None, port: int = None, **kwargs) -> Optional[RedisCache]:
    """
    Get or create global Redis cache instance

    Args:
        host: Redis host (uses env var REDIS_HOST if not provided)
        port: Redis port (uses env var REDIS_PORT if not provided)
        **kwargs: Additional RedisCache arguments

    Returns:
        RedisCache instance or None
    """
    global _redis_cache

    if _redis_cache is None:
        # Get config from environment variables
        redis_host = host or os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(port or os.getenv('REDIS_PORT', 6379))
        redis_password = os.getenv('REDIS_PASSWORD')
        redis_db = int(os.getenv('REDIS_DB', 0))
        try:
            redis_max_connections = int(os.getenv('REDIS_MAX_CONNECTIONS', '200'))
        except ValueError:
            redis_max_connections = 200
        if "max_connections" not in kwargs:
            kwargs["max_connections"] = redis_max_connections

        _redis_cache = RedisCache(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            db=redis_db,
            **kwargs
        )

    return _redis_cache


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("=== Redis Cache Configuration ===\n")

    # Initialize cache
    cache = RedisCache(host='localhost', port=6379)

    if not cache.is_connected():
        print("Redis not connected. Make sure Redis server is running.")
        exit(1)

    # Test 1: Cache prices
    print("1. Testing price caching...")
    price_data = {
        'ticker': 'NVDA',
        'price': 498.50,
        'change': 12.35,
        'change_percent': 2.54,
        'volume': 45200000
    }
    cache.cache_prices('NVDA', price_data, ttl=60)

    cached = cache.get_cached_prices('NVDA')
    print(f"Cached prices: {cached}")

    # Test 2: Cache predictions
    print("\n2. Testing predictions caching...")
    predictions = [
        {'ticker': 'NVDA', 'score': 94, 'target': 575},
        {'ticker': 'AAPL', 'score': 88, 'target': 195}
    ]
    cache.cache_predictions('swing', predictions, ttl=3600)

    cached_pred = cache.get_cached_predictions('swing')
    print(f"Cached predictions: {len(cached_pred)} items")

    # Test 3: Cache social data
    print("\n3. Testing social data caching...")
    social_data = [
        {'ticker': 'NVDA', 'mentions': 245, 'sentiment': 0.72},
        {'ticker': 'TSLA', 'mentions': 189, 'sentiment': 0.45}
    ]
    cache.cache_social_data('reddit', social_data, ttl=300)

    cached_social = cache.get_cached_social_data('reddit')
    print(f"Cached social: {len(cached_social)} items")

    # Test 4: Cache stats
    print("\n4. Cache statistics:")
    stats = cache.get_cache_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Test 5: Cache invalidation
    print("\n5. Testing cache invalidation...")
    print(f"Keys before: {len(cache.get_all_keys())}")
    deleted = cache.invalidate_cache("price:*")
    print(f"Deleted {deleted} price keys")
    print(f"Keys after: {len(cache.get_all_keys())}")

    print("\n=== Redis Cache Tests Complete ===")
