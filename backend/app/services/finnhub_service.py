"""
TradeMaster Pro - Finnhub Service
===================================

Real-time stock market data using Finnhub API.
Provides quote data, company profiles, and market news.

Finnhub Free tier: 60 API calls/minute
"""

import os
import logging
import time
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque
import finnhub
from dotenv import load_dotenv
from app.config.settings import settings
from database.redis.config import get_redis_cache

load_dotenv()

logger = logging.getLogger(__name__)

class FinnhubService:
    """Finnhub API service for real-time stock data with rate limiting"""

    # Rate limit defaults (free tier: 60 calls/minute)
    RATE_LIMIT_WINDOW = 60  # seconds
    DEFAULT_PROFILE_TTL = 21600  # 6 hours
    DEFAULT_FINANCIALS_TTL = 21600  # 6 hours
    DEFAULT_TRENDS_TTL = 21600  # 6 hours
    DEFAULT_PRICE_TARGET_TTL = 21600  # 6 hours
    DEFAULT_CANDLES_TTL = 600  # 10 minutes
    DEFAULT_INSIDER_TTL = 3600  # 1 hour

    def __init__(self):
        self.api_key = os.getenv('FINNHUB_API_KEY')
        if not self.api_key:
            logger.warning("FINNHUB_API_KEY not found in environment")
            self.client = None
        else:
            self.client = finnhub.Client(api_key=self.api_key)
            logger.info("Finnhub client initialized successfully")

        self.calls_per_minute = settings.FINNHUB_CALLS_PER_MINUTE
        self.rate_limit_buffer = settings.FINNHUB_RATE_LIMIT_BUFFER
        self.rate_limit_mode = settings.FINNHUB_RATE_LIMIT_MODE.lower()
        self.redis_cache = get_redis_cache()
        self.redis_rate_limit_key = "finnhub:rate_limit_hit"
        self.local_cache: Dict[str, Dict[str, Any]] = {}

        # Track API call timestamps for per-worker rate limiting fallback
        self.call_timestamps = deque(maxlen=self.calls_per_minute)
        self.rate_limit_hit_time = None

    def _redis_connected(self) -> bool:
        return bool(self.redis_cache and self.redis_cache.is_connected())

    def _get_cache_key(self, namespace: str, symbol: Optional[str] = None, suffix: Optional[str] = None) -> str:
        parts = ["finnhub", namespace]
        if symbol:
            parts.append(symbol.upper())
        if suffix:
            parts.append(suffix)
        return ":".join(parts)

    def _get_cached(self, cache_key: str) -> Optional[Any]:
        if self._redis_connected():
            try:
                cached = self.redis_cache.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as exc:
                logger.debug("Finnhub cache get failed (%s): %s", cache_key, exc)

        entry = self.local_cache.get(cache_key)
        if entry and entry["expires_at"] > time.time():
            return entry["value"]
        if entry:
            self.local_cache.pop(cache_key, None)
        return None

    def _set_cached(self, cache_key: str, value: Any, ttl: int) -> None:
        if value is None:
            return
        if self._redis_connected():
            try:
                self.redis_cache.redis_client.setex(cache_key, ttl, json.dumps(value))
                return
            except Exception as exc:
                logger.debug("Finnhub cache set failed (%s): %s", cache_key, exc)
        self.local_cache[cache_key] = {"expires_at": time.time() + ttl, "value": value}

    def _check_rate_limit_cooldown(self) -> None:
        if not self._redis_connected():
            return
        try:
            cooldown = self.redis_cache.redis_client.ttl(self.redis_rate_limit_key)
            if cooldown and cooldown > 0:
                logger.info("Rate limit cooldown: waiting %ss...", cooldown)
                time.sleep(cooldown + 1)
        except Exception as exc:
            logger.debug("Finnhub cooldown check failed: %s", exc)

    def _wait_for_rate_limit_redis(self) -> bool:
        if not self._redis_connected():
            return False

        self._check_rate_limit_cooldown()

        now = time.time()
        window = int(now // self.RATE_LIMIT_WINDOW)
        cache_key = f"finnhub:rate:{window}"
        try:
            count = self.redis_cache.redis_client.incr(cache_key)
            if count == 1:
                self.redis_cache.redis_client.expire(cache_key, self.RATE_LIMIT_WINDOW + 2)
        except Exception as exc:
            logger.debug("Finnhub redis rate limit failed: %s", exc)
            return False

        if count >= max(1, self.calls_per_minute - self.rate_limit_buffer):
            wait_time = self.RATE_LIMIT_WINDOW - (now % self.RATE_LIMIT_WINDOW) + 1
            logger.info(
                "Approaching Finnhub rate limit (%s/%s), waiting %.1fs...",
                count,
                self.calls_per_minute,
                wait_time
            )
            time.sleep(wait_time)
            return self._wait_for_rate_limit_redis()
        return True

    def _wait_for_rate_limit(self):
        """
        Wait if we're approaching or have hit the rate limit.
        Finnhub free tier: 60 calls/minute
        """
        if self._redis_connected() and self._wait_for_rate_limit_redis():
            return

        now = time.time()

        # If we recently hit a rate limit, wait longer
        if self.rate_limit_hit_time:
            wait_time = 60 - (now - self.rate_limit_hit_time)
            if wait_time > 0:
                logger.info(f"Rate limit cooldown: waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                self.rate_limit_hit_time = None
                self.call_timestamps.clear()
                return

        # Remove old timestamps (older than 60 seconds)
        while self.call_timestamps and (now - self.call_timestamps[0]) > self.RATE_LIMIT_WINDOW:
            self.call_timestamps.popleft()

        # If we've made too many calls in the last minute, wait
        if len(self.call_timestamps) >= max(1, self.calls_per_minute - self.rate_limit_buffer):
            oldest_call = self.call_timestamps[0]
            wait_time = self.RATE_LIMIT_WINDOW - (now - oldest_call) + 1
            if wait_time > 0:
                logger.info(
                    f"Approaching rate limit ({len(self.call_timestamps)}/{self.calls_per_minute}), "
                    f"waiting {wait_time:.1f}s..."
                )
                time.sleep(wait_time)

        # Record this call
        self.call_timestamps.append(time.time())

    def _handle_api_call(self, func, *args, **kwargs):
        """
        Execute API call with rate limiting and retry logic
        """
        max_retries = 3
        retry_delay = 10  # seconds

        for attempt in range(max_retries):
            # Wait for rate limit before making call
            self._wait_for_rate_limit()

            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_str = str(e).lower()

                # Check if it's a rate limit error (429 or "api limit")
                if '429' in error_str or 'api limit' in error_str or 'rate limit' in error_str:
                    self.rate_limit_hit_time = time.time()
                    if self._redis_connected():
                        try:
                            self.redis_cache.redis_client.setex(self.redis_rate_limit_key, self.RATE_LIMIT_WINDOW, "1")
                        except Exception as exc:
                            logger.debug("Failed to set Finnhub cooldown: %s", exc)
                    wait_time = retry_delay * (attempt + 1)
                    logger.warning(f"API rate limit hit, waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(wait_time)
                    continue
                # Check for server errors (502, 503, 504) - Finnhub server issues
                elif '502' in error_str or '503' in error_str or '504' in error_str or 'bad gateway' in error_str:
                    wait_time = retry_delay * (attempt + 1)
                    logger.warning(f"Finnhub server error, waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(wait_time)
                    continue
                else:
                    # Other error, don't retry
                    raise e

        # All retries exhausted
        logger.error(f"API call failed after {max_retries} retries")
        return None

    def get_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get real-time quote for a stock

        Returns:
            {
                'c': current_price,
                'h': high_price,
                'l': low_price,
                'o': open_price,
                'pc': previous_close,
                't': timestamp
            }
        """
        if not self.client:
            logger.error("Finnhub client not initialized")
            return None

        try:
            cache_key = self._get_cache_key("quote", symbol)
            cached = self._get_cached(cache_key)
            if cached:
                return cached
            quote = self._handle_api_call(self.client.quote, symbol)
            if quote and quote.get('c', 0) > 0:
                self._set_cached(cache_key, quote, settings.CACHE_TTL_PRICES)
                return quote
            return None
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {str(e)}")
            return None

    def get_company_profile(self, symbol: str) -> Optional[Dict]:
        """
        Get company profile information

        Returns company details including market cap, industry, etc.
        """
        if not self.client:
            return None

        try:
            cache_key = self._get_cache_key("profile", symbol)
            cached = self._get_cached(cache_key)
            if cached:
                return cached
            profile = self._handle_api_call(self.client.company_profile2, symbol=symbol)
            if profile:
                self._set_cached(cache_key, profile, self.DEFAULT_PROFILE_TTL)
            return profile
        except Exception as e:
            logger.error(f"Error fetching profile for {symbol}: {str(e)}")
            return None

    def get_company_news(self, symbol: str, days: int = 7) -> List[Dict]:
        """
        Get company news from last N days

        Returns list of news articles
        """
        if not self.client:
            return []

        try:
            cache_key = self._get_cache_key("company_news", symbol, f"{days}d")
            cached = self._get_cached(cache_key)
            if isinstance(cached, list):
                return cached[:10]
            to_date = datetime.now().strftime('%Y-%m-%d')
            from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            news = self._handle_api_call(self.client.company_news, symbol, _from=from_date, to=to_date)
            if news is not None:
                self._set_cached(cache_key, news, settings.FINNHUB_COMPANY_NEWS_TTL)
            return news[:10] if news else []  # Limit to 10 most recent
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {str(e)}")
            return []

    def get_market_news(self, category: str = 'general') -> List[Dict]:
        """
        Get general market news

        Categories: general, forex, crypto, merger
        """
        if not self.client:
            return []

        try:
            cache_key = self._get_cache_key("market_news", category)
            cached = self._get_cached(cache_key)
            if isinstance(cached, list):
                return cached[:20]
            news = self._handle_api_call(self.client.general_news, category, min_id=0)
            if news is not None:
                self._set_cached(cache_key, news, settings.FINNHUB_MARKET_NEWS_TTL)
            return news[:20] if news else []
        except Exception as e:
            logger.error(f"Error fetching market news: {str(e)}")
            return []

    def get_recommendation_trends(self, symbol: str) -> List[Dict]:
        """
        Get analyst recommendation trends

        Returns buy/hold/sell recommendations over time
        """
        if not self.client:
            return []

        try:
            cache_key = self._get_cache_key("recommendation_trends", symbol)
            cached = self._get_cached(cache_key)
            if isinstance(cached, list):
                return cached
            trends = self._handle_api_call(self.client.recommendation_trends, symbol)
            if trends is not None:
                self._set_cached(cache_key, trends, self.DEFAULT_TRENDS_TTL)
            return trends if trends else []
        except Exception as e:
            logger.error(f"Error fetching recommendations for {symbol}: {str(e)}")
            return []

    def get_price_target(self, symbol: str) -> Optional[Dict]:
        """
        Get analyst price targets

        Returns target high, low, median, mean
        NOTE: This is a PREMIUM endpoint - may return 403 on free tier
        """
        if not self.client:
            return None

        try:
            cache_key = self._get_cache_key("price_target", symbol)
            cached = self._get_cached(cache_key)
            if cached:
                return cached
            target = self._handle_api_call(self.client.price_target, symbol)
            if target:
                self._set_cached(cache_key, target, self.DEFAULT_PRICE_TARGET_TTL)
            return target
        except Exception as e:
            logger.error(f"Error fetching price target for {symbol}: {str(e)}")
            return None

    def get_basic_financials(self, symbol: str) -> Optional[Dict]:
        """
        Get basic financial metrics

        Returns P/E, market cap, dividend yield, etc.
        """
        if not self.client:
            return None

        try:
            cache_key = self._get_cache_key("basic_financials", symbol)
            cached = self._get_cached(cache_key)
            if cached:
                return cached
            financials = self._handle_api_call(self.client.company_basic_financials, symbol, 'all')
            if financials:
                self._set_cached(cache_key, financials, self.DEFAULT_FINANCIALS_TTL)
            return financials
        except Exception as e:
            logger.error(f"Error fetching financials for {symbol}: {str(e)}")
            return None

    def get_stock_candles(self, symbol: str, resolution: str = 'D', days: int = 90) -> Optional[Dict]:
        """
        Get historical OHLCV candles for a stock

        NOTE: This is a PREMIUM endpoint - may return 403 on free tier

        Args:
            symbol: Stock ticker
            resolution: Candle resolution (1, 5, 15, 30, 60, D, W, M)
            days: Number of days of history

        Returns:
            Dict with o, h, l, c, v, t arrays (open, high, low, close, volume, timestamp)
        """
        if not self.client:
            return None

        try:
            cache_key = self._get_cache_key("stock_candles", symbol, f"{resolution}:{days}")
            cached = self._get_cached(cache_key)
            if cached:
                return cached
            to_time = int(time.time())
            from_time = to_time - (days * 24 * 60 * 60)

            candles = self._handle_api_call(self.client.stock_candles, symbol, resolution, from_time, to_time)

            if candles and candles.get('s') == 'ok':
                self._set_cached(cache_key, candles, self.DEFAULT_CANDLES_TTL)
                return candles
            return None
        except Exception as e:
            logger.error(f"Error fetching candles for {symbol}: {str(e)}")
            return None

    def get_insider_transactions(self, symbol: str, days: int = 90) -> List[Dict]:
        """
        Get insider transactions for a stock (if available on the plan).

        Returns list of insider transactions.
        """
        if not self.client:
            return []

        try:
            cache_key = self._get_cache_key("insider_transactions", symbol, f"{days}d")
            cached = self._get_cached(cache_key)
            if isinstance(cached, list):
                return cached
            to_date = datetime.now().strftime('%Y-%m-%d')
            from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            if not hasattr(self.client, 'stock_insider_transactions'):
                return []

            data = self._handle_api_call(
                self.client.stock_insider_transactions,
                symbol,
                _from=from_date,
                to=to_date
            )

            if not data:
                return []

            if isinstance(data, dict):
                result = data.get('data', []) or []
                self._set_cached(cache_key, result, self.DEFAULT_INSIDER_TTL)
                return result

            result = data if isinstance(data, list) else []
            self._set_cached(cache_key, result, self.DEFAULT_INSIDER_TTL)
            return result

        except Exception as e:
            logger.error(f"Error fetching insider transactions for {symbol}: {str(e)}")
            return []


# Global singleton instance
_finnhub_service = None

def get_finnhub_service() -> FinnhubService:
    """Get or create Finnhub service singleton"""
    global _finnhub_service
    if _finnhub_service is None:
        _finnhub_service = FinnhubService()
    return _finnhub_service
