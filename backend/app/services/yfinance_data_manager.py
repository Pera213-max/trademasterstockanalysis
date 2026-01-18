"""
TradeMaster Pro - yfinance Data Manager
========================================

Centralized data management for yfinance with:
- Background pre-caching for 4000+ stocks
- Rate limit protection with auto-recovery
- Redis-backed distributed caching
- Priority queue for user requests
- No backend crashes from rate limits

Strategy:
1. User requests ONLY return cached data
2. If not cached -> return "loading" and queue for background fetch
3. Background worker continuously pre-fetches and refreshes data
4. Rate limits are handled gracefully with exponential backoff
"""

import os
import sys
import time
import json
import random
import logging
import threading
import importlib
import asyncio
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class FetchPriority(Enum):
    """Priority levels for data fetch queue"""
    CRITICAL = 1    # User is actively viewing
    HIGH = 2        # User request, not cached
    NORMAL = 3      # Regular refresh
    LOW = 4         # Background pre-fetch


@dataclass(order=True)
class FetchRequest:
    """Request for data fetch with priority"""
    priority: int
    ticker: str = field(compare=False)
    data_type: str = field(compare=False)  # 'quote', 'fundamentals', 'historical'
    requested_at: float = field(default_factory=time.time, compare=False)
    period: str = field(default="3mo", compare=False)


class YFinanceDataManager:
    """
    Centralized manager for all yfinance data with rate limiting and caching.

    This class ensures:
    1. Users NEVER wait for yfinance API calls - always get cached data
    2. Background worker handles all API calls with rate limiting
    3. Rate limits don't crash the backend
    4. 4000+ stocks are pre-cached and refreshed regularly
    """

    # Rate limit configuration (conservative for Yahoo Finance)
    CALLS_PER_MINUTE = 25  # Conservative - Yahoo seems to allow ~30-50
    RATE_LIMIT_WINDOW = 60
    MIN_CALL_INTERVAL = 2.5  # Minimum seconds between calls

    # Cooldown after rate limit hit
    RATE_LIMIT_COOLDOWN = 180  # 3 minutes cooldown after rate limit
    MODULE_RELOAD_COOLDOWN = 120  # 2 minutes between module reloads

    # Cache TTLs (seconds)
    CACHE_TTL_QUOTE = 120  # 2 minutes for quotes
    CACHE_TTL_FUNDAMENTALS = 3600  # 1 hour for fundamentals
    CACHE_TTL_HISTORICAL = 1800  # 30 minutes for historical

    # Batch settings
    BATCH_SIZE = 20  # Tickers per batch for yf.download
    BATCH_PAUSE = 5  # Seconds between batches

    def __init__(self, redis_cache=None):
        """Initialize data manager"""
        self.redis_cache = redis_cache
        self._lock = threading.Lock()

        # Rate limiting state
        self.call_timestamps: deque = deque(maxlen=self.CALLS_PER_MINUTE * 2)
        self.rate_limit_hit_time: Optional[float] = None
        self.last_module_reload: Optional[float] = None
        self.last_call_time: float = 0

        # Fetch queue
        self.fetch_queue: List[FetchRequest] = []
        self.queue_lock = threading.Lock()
        self.processing_tickers: Set[str] = set()

        # Stats
        self.stats = {
            "total_calls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "rate_limit_hits": 0,
            "queue_additions": 0,
            "successful_fetches": 0,
            "failed_fetches": 0,
            "module_reloads": 0,
        }

        # Worker state
        self._worker_running = False
        self._worker_thread: Optional[threading.Thread] = None

        logger.info("YFinanceDataManager initialized")

    def _redis_connected(self) -> bool:
        """Check if Redis is available"""
        if not self.redis_cache:
            return False
        try:
            return self.redis_cache.is_connected()
        except Exception:
            return False

    def _get_redis_client(self):
        """Get Redis client for direct operations"""
        if self._redis_connected():
            return self.redis_cache.redis_client
        return None

    # =========================================================================
    # CACHE METHODS
    # =========================================================================

    def _get_cache_key(self, ticker: str, data_type: str, period: str = "") -> str:
        """Generate cache key"""
        if period:
            return f"yf:{data_type}:{ticker.upper()}:{period}"
        return f"yf:{data_type}:{ticker.upper()}"

    def get_cached_data(self, ticker: str, data_type: str, period: str = "") -> Optional[Dict]:
        """Get data from cache"""
        key = self._get_cache_key(ticker, data_type, period)
        redis = self._get_redis_client()

        if redis:
            try:
                data = redis.get(key)
                if data:
                    self.stats["cache_hits"] += 1
                    return json.loads(data)
            except Exception as e:
                logger.debug(f"Redis get error for {key}: {e}")

        self.stats["cache_misses"] += 1
        return None

    def set_cached_data(self, ticker: str, data_type: str, data: Any,
                        period: str = "", ttl: int = None) -> bool:
        """Store data in cache"""
        if data is None:
            return False

        key = self._get_cache_key(ticker, data_type, period)
        redis = self._get_redis_client()

        if not ttl:
            ttl_map = {
                "quote": self.CACHE_TTL_QUOTE,
                "fundamentals": self.CACHE_TTL_FUNDAMENTALS,
                "historical": self.CACHE_TTL_HISTORICAL,
            }
            ttl = ttl_map.get(data_type, self.CACHE_TTL_QUOTE)

        if redis:
            try:
                redis.setex(key, ttl, json.dumps(data))
                return True
            except Exception as e:
                logger.debug(f"Redis set error for {key}: {e}")

        return False

    def get_multiple_cached_quotes(self, tickers: List[str]) -> Dict[str, Optional[Dict]]:
        """Get multiple quotes from cache efficiently"""
        results = {}
        redis = self._get_redis_client()

        if redis:
            try:
                pipeline = redis.pipeline()
                keys = [self._get_cache_key(t, "quote") for t in tickers]
                for key in keys:
                    pipeline.get(key)
                values = pipeline.execute()

                for ticker, value in zip(tickers, values):
                    if value:
                        results[ticker] = json.loads(value)
                        self.stats["cache_hits"] += 1
                    else:
                        results[ticker] = None
                        self.stats["cache_misses"] += 1
            except Exception as e:
                logger.debug(f"Redis pipeline error: {e}")
                for ticker in tickers:
                    results[ticker] = None
        else:
            for ticker in tickers:
                results[ticker] = None

        return results

    # =========================================================================
    # RATE LIMITING
    # =========================================================================

    def _check_rate_limit(self) -> float:
        """
        Check rate limit and return wait time needed.
        Returns 0 if we can proceed, otherwise seconds to wait.
        """
        now = time.time()

        # Check cooldown from previous rate limit hit
        if self.rate_limit_hit_time:
            cooldown_remaining = self.RATE_LIMIT_COOLDOWN - (now - self.rate_limit_hit_time)
            if cooldown_remaining > 0:
                return cooldown_remaining
            self.rate_limit_hit_time = None
            self.call_timestamps.clear()

        # Check minimum interval between calls
        time_since_last = now - self.last_call_time
        if time_since_last < self.MIN_CALL_INTERVAL:
            return self.MIN_CALL_INTERVAL - time_since_last

        # Check Redis-based distributed rate limiting
        redis = self._get_redis_client()
        if redis:
            try:
                window = int(now // self.RATE_LIMIT_WINDOW)
                count_key = f"yf:rate:{window}"
                cooldown_key = "yf:rate_limit_cooldown"

                # Check global cooldown
                cooldown_ttl = redis.ttl(cooldown_key)
                if cooldown_ttl and cooldown_ttl > 0:
                    return float(cooldown_ttl)

                # Check call count
                count = redis.get(count_key)
                count = int(count) if count else 0

                if count >= self.CALLS_PER_MINUTE - 5:  # Buffer of 5
                    wait_time = self.RATE_LIMIT_WINDOW - (now % self.RATE_LIMIT_WINDOW)
                    return wait_time + 1

            except Exception as e:
                logger.debug(f"Redis rate limit check error: {e}")

        # Local rate limiting fallback
        while self.call_timestamps and (now - self.call_timestamps[0]) > self.RATE_LIMIT_WINDOW:
            self.call_timestamps.popleft()

        if len(self.call_timestamps) >= self.CALLS_PER_MINUTE - 5:
            oldest = self.call_timestamps[0]
            return self.RATE_LIMIT_WINDOW - (now - oldest) + 1

        return 0

    def _record_call(self):
        """Record that we made an API call"""
        now = time.time()
        self.last_call_time = now
        self.call_timestamps.append(now)
        self.stats["total_calls"] += 1

        # Update Redis counter
        redis = self._get_redis_client()
        if redis:
            try:
                window = int(now // self.RATE_LIMIT_WINDOW)
                key = f"yf:rate:{window}"
                count = redis.incr(key)
                if count == 1:
                    redis.expire(key, self.RATE_LIMIT_WINDOW + 5)
            except Exception:
                pass

    def _handle_rate_limit_hit(self):
        """Handle rate limit error"""
        self.stats["rate_limit_hits"] += 1
        self.rate_limit_hit_time = time.time()

        # Set global cooldown in Redis
        redis = self._get_redis_client()
        if redis:
            try:
                redis.setex("yf:rate_limit_cooldown", self.RATE_LIMIT_COOLDOWN, "1")
            except Exception:
                pass

        logger.warning(
            f"yfinance rate limit hit (total: {self.stats['rate_limit_hits']}). "
            f"Cooldown for {self.RATE_LIMIT_COOLDOWN}s"
        )

        # Try module reload on first hit
        self._try_module_reload()

    def _try_module_reload(self) -> bool:
        """Try to reload yfinance module to reset internal state"""
        now = time.time()

        if self.last_module_reload:
            elapsed = now - self.last_module_reload
            if elapsed < self.MODULE_RELOAD_COOLDOWN:
                return False

        try:
            if 'yfinance' in sys.modules:
                importlib.reload(sys.modules['yfinance'])
                self.stats["module_reloads"] += 1
                self.last_module_reload = now
                logger.info(f"yfinance module reloaded (total: {self.stats['module_reloads']})")
                return True
        except Exception as e:
            logger.error(f"Failed to reload yfinance: {e}")

        return False

    # =========================================================================
    # DATA FETCHING
    # =========================================================================

    def _fetch_quote(self, ticker: str) -> Optional[Dict]:
        """Fetch quote from yfinance with rate limiting"""
        # Wait for rate limit
        wait_time = self._check_rate_limit()
        if wait_time > 0:
            time.sleep(wait_time)

        try:
            import yfinance as yf
            self._record_call()

            stock = yf.Ticker(ticker)
            info = {}
            fast_info = {}

            try:
                info = stock.info or {}
            except Exception:
                pass

            try:
                fast_info = getattr(stock, "fast_info", None) or {}
            except Exception:
                pass

            def pick_positive(*vals):
                for v in vals:
                    try:
                        f = float(v)
                        if f > 0:
                            return f
                    except (TypeError, ValueError):
                        pass
                return 0.0

            current = pick_positive(
                info.get('currentPrice'),
                info.get('regularMarketPrice'),
                fast_info.get('last_price')
            )

            if not current:
                # Fallback to history
                history = stock.history(period="5d")
                if history is not None and not history.empty:
                    current = float(history['Close'].iloc[-1])

            if not current:
                return None

            quote = {
                'c': current,
                'pc': pick_positive(info.get('previousClose'), info.get('regularMarketPreviousClose')),
                'h': pick_positive(info.get('dayHigh'), info.get('regularMarketDayHigh')),
                'l': pick_positive(info.get('dayLow'), info.get('regularMarketDayLow')),
                'o': pick_positive(info.get('open'), info.get('regularMarketOpen')),
                'v': pick_positive(info.get('volume'), info.get('regularMarketVolume')),
            }

            self.set_cached_data(ticker, "quote", quote)
            self.stats["successful_fetches"] += 1
            return quote

        except Exception as e:
            error_str = str(e).lower()
            if any(x in error_str for x in ['rate', 'limit', '429', 'too many']):
                self._handle_rate_limit_hit()
            else:
                logger.debug(f"Quote fetch error for {ticker}: {e}")
            self.stats["failed_fetches"] += 1
            return None

    def _fetch_fundamentals(self, ticker: str) -> Optional[Dict]:
        """Fetch fundamentals from yfinance with rate limiting"""
        wait_time = self._check_rate_limit()
        if wait_time > 0:
            time.sleep(wait_time)

        try:
            import yfinance as yf
            self._record_call()

            stock = yf.Ticker(ticker)
            info = stock.info

            if not info:
                return None

            fundamentals = {
                'marketCap': info.get('marketCap', 0),
                'peRatio': info.get('trailingPE', info.get('forwardPE', 0)),
                'forwardPE': info.get('forwardPE', 0),
                'pegRatio': info.get('pegRatio', 0),
                'priceToBook': info.get('priceToBook', 0),
                'dividendYield': info.get('dividendYield', 0),
                'profitMargins': info.get('profitMargins', 0),
                'revenueGrowth': info.get('revenueGrowth', 0),
                'earningsGrowth': info.get('earningsGrowth', 0),
                'returnOnEquity': info.get('returnOnEquity', 0),
                'debtToEquity': info.get('debtToEquity', 0),
                'currentRatio': info.get('currentRatio', 0),
                'beta': info.get('beta', 1),
                'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh', 0),
                'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow', 0),
                'averageVolume': info.get('averageVolume', 0),
                'shortName': info.get('shortName', ticker),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
            }

            self.set_cached_data(ticker, "fundamentals", fundamentals)
            self.stats["successful_fetches"] += 1
            return fundamentals

        except Exception as e:
            error_str = str(e).lower()
            if any(x in error_str for x in ['rate', 'limit', '429', 'too many']):
                self._handle_rate_limit_hit()
            else:
                logger.debug(f"Fundamentals fetch error for {ticker}: {e}")
            self.stats["failed_fetches"] += 1
            return None

    def _fetch_historical_batch(self, tickers: List[str], period: str = "3mo") -> Dict[str, Any]:
        """Fetch historical data for multiple tickers in batch"""
        results = {}

        wait_time = self._check_rate_limit()
        if wait_time > 0:
            time.sleep(wait_time)

        try:
            import yfinance as yf
            self._record_call()

            data = yf.download(
                tickers,
                period=period,
                group_by='ticker',
                progress=False,
                auto_adjust=True,
                threads=False
            )

            if data is None or data.empty:
                return results

            for ticker in tickers:
                try:
                    ticker_data = data if len(tickers) == 1 else data[ticker]
                    if ticker_data is not None and not ticker_data.empty:
                        # Convert to serializable format
                        ohlcv = []
                        for idx, row in ticker_data.iterrows():
                            ohlcv.append({
                                'date': idx.isoformat(),
                                'o': float(row['Open']),
                                'h': float(row['High']),
                                'l': float(row['Low']),
                                'c': float(row['Close']),
                                'v': int(row['Volume']),
                            })
                        results[ticker] = ohlcv
                        self.set_cached_data(ticker, "historical", ohlcv, period=period)
                        self.stats["successful_fetches"] += 1
                except Exception:
                    continue

            return results

        except Exception as e:
            error_str = str(e).lower()
            if any(x in error_str for x in ['rate', 'limit', '429', 'too many']):
                self._handle_rate_limit_hit()
            else:
                logger.debug(f"Batch historical fetch error: {e}")
            self.stats["failed_fetches"] += 1
            return results

    # =========================================================================
    # PUBLIC API - Cache-first for users
    # =========================================================================

    def get_quote(self, ticker: str, queue_if_missing: bool = True) -> Optional[Dict]:
        """
        Get quote for ticker - returns cached data or queues for fetch.

        This is the method user-facing endpoints should call.
        It NEVER blocks on API calls - always returns immediately.
        """
        ticker = ticker.upper()

        # Try cache first
        cached = self.get_cached_data(ticker, "quote")
        if cached:
            return cached

        # Queue for background fetch if requested
        if queue_if_missing:
            self.queue_fetch(ticker, "quote", FetchPriority.HIGH)

        return None

    def get_fundamentals(self, ticker: str, queue_if_missing: bool = True) -> Optional[Dict]:
        """Get fundamentals - cache-first with optional queue"""
        ticker = ticker.upper()

        cached = self.get_cached_data(ticker, "fundamentals")
        if cached:
            return cached

        if queue_if_missing:
            self.queue_fetch(ticker, "fundamentals", FetchPriority.HIGH)

        return None

    def get_historical(self, ticker: str, period: str = "3mo",
                       queue_if_missing: bool = True) -> Optional[List]:
        """Get historical data - cache-first with optional queue"""
        ticker = ticker.upper()

        cached = self.get_cached_data(ticker, "historical", period)
        if cached:
            return cached

        if queue_if_missing:
            self.queue_fetch(ticker, "historical", FetchPriority.HIGH, period=period)

        return None

    def get_multiple_quotes(self, tickers: List[str],
                           queue_missing: bool = True) -> Dict[str, Optional[Dict]]:
        """Get multiple quotes - returns cached data, queues missing ones"""
        tickers = [t.upper() for t in tickers]
        results = self.get_multiple_cached_quotes(tickers)

        if queue_missing:
            missing = [t for t, v in results.items() if v is None]
            for ticker in missing:
                self.queue_fetch(ticker, "quote", FetchPriority.NORMAL)

        return results

    # =========================================================================
    # FETCH QUEUE
    # =========================================================================

    def queue_fetch(self, ticker: str, data_type: str,
                    priority: FetchPriority = FetchPriority.NORMAL,
                    period: str = "3mo"):
        """Add fetch request to queue"""
        ticker = ticker.upper()

        with self.queue_lock:
            # Don't queue if already processing or in queue
            if ticker in self.processing_tickers:
                return

            # Check if already in queue
            for req in self.fetch_queue:
                if req.ticker == ticker and req.data_type == data_type:
                    # Update priority if new one is higher
                    if priority.value < req.priority:
                        req.priority = priority.value
                    return

            request = FetchRequest(
                priority=priority.value,
                ticker=ticker,
                data_type=data_type,
                period=period
            )
            self.fetch_queue.append(request)
            self.fetch_queue.sort(key=lambda x: (x.priority, x.requested_at))
            self.stats["queue_additions"] += 1

    def queue_bulk_prefetch(self, tickers: List[str], data_types: List[str] = None):
        """Queue multiple tickers for background pre-fetch"""
        if data_types is None:
            data_types = ["quote", "fundamentals"]

        for ticker in tickers:
            for dt in data_types:
                self.queue_fetch(ticker, dt, FetchPriority.LOW)

    def get_queue_stats(self) -> Dict:
        """Get queue statistics"""
        with self.queue_lock:
            return {
                "queue_size": len(self.fetch_queue),
                "processing_count": len(self.processing_tickers),
                "stats": self.stats.copy(),
            }

    # =========================================================================
    # BACKGROUND WORKER
    # =========================================================================

    def start_worker(self):
        """Start background fetch worker"""
        if self._worker_running:
            return

        self._worker_running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        logger.info("YFinanceDataManager worker started")

    def stop_worker(self):
        """Stop background fetch worker"""
        self._worker_running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        logger.info("YFinanceDataManager worker stopped")

    def _worker_loop(self):
        """Background worker loop - processes fetch queue"""
        while self._worker_running:
            try:
                # Get next request from queue
                request = None
                with self.queue_lock:
                    if self.fetch_queue:
                        request = self.fetch_queue.pop(0)
                        self.processing_tickers.add(request.ticker)

                if request:
                    self._process_request(request)
                    with self.queue_lock:
                        self.processing_tickers.discard(request.ticker)
                else:
                    # No work, sleep briefly
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Worker error: {e}")
                time.sleep(5)

    def _process_request(self, request: FetchRequest):
        """Process a single fetch request"""
        try:
            if request.data_type == "quote":
                self._fetch_quote(request.ticker)
            elif request.data_type == "fundamentals":
                self._fetch_fundamentals(request.ticker)
            elif request.data_type == "historical":
                # For historical, try to batch
                self._fetch_historical_batch([request.ticker], request.period)
        except Exception as e:
            logger.debug(f"Request processing error for {request.ticker}: {e}")

    def process_batch_prefetch(self, tickers: List[str]):
        """
        Process batch pre-fetch for multiple tickers.
        Called by scheduler for regular data refresh.
        """
        logger.info(f"Starting batch pre-fetch for {len(tickers)} tickers")

        # Fetch quotes in batches
        for i in range(0, len(tickers), self.BATCH_SIZE):
            if not self._worker_running and not threading.current_thread() == threading.main_thread():
                break

            batch = tickers[i:i + self.BATCH_SIZE]

            # Fetch historical data in batch (most efficient)
            self._fetch_historical_batch(batch, "3mo")

            # Fetch quotes individually (no batch API for quotes)
            for ticker in batch:
                wait = self._check_rate_limit()
                if wait > 0:
                    logger.info(f"Rate limit pause: waiting {wait:.1f}s...")
                    time.sleep(wait)

                self._fetch_quote(ticker)

            # Pause between batches
            time.sleep(self.BATCH_PAUSE)

            # Log progress
            progress = min(i + self.BATCH_SIZE, len(tickers))
            logger.info(f"Pre-fetch progress: {progress}/{len(tickers)} tickers")

        logger.info(f"Batch pre-fetch complete. Stats: {self.stats}")


# Global singleton
_data_manager: Optional[YFinanceDataManager] = None


def get_yfinance_data_manager(redis_cache=None) -> YFinanceDataManager:
    """Get or create global yfinance data manager"""
    global _data_manager

    if _data_manager is None:
        if redis_cache is None:
            try:
                from database.redis.config import get_redis_cache
                redis_cache = get_redis_cache()
            except Exception:
                pass

        _data_manager = YFinanceDataManager(redis_cache)

    return _data_manager
