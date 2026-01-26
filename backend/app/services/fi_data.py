"""
TradeMaster Pro - Finland (Nasdaq Helsinki) Data Service
=========================================================

Provides data and analysis for Finnish stocks (Nasdaq Helsinki).
Uses yfinance for price data and fundamentals.

All Finnish stocks use .HE suffix (e.g., NOKIA.HE, KNEBV.HE)
"""

import json
import logging
import math
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from database.redis.config import get_redis_cache
from app.config.settings import settings
from app.services.fi_ticker_lookup import get_nasdaq_news_url

logger = logging.getLogger(__name__)

# Cache TTLs - LONG durations, auto-refresh handles updates
CACHE_TTL_QUOTE = 240  # 4 minutes (ensure expiry before 5-min auto-refresh)
CACHE_TTL_HISTORY = 1800  # 30 minutes (updates during day)
CACHE_TTL_FUNDAMENTALS = 86400  # 24 hours for fundamentals (stable data)
CACHE_TTL_RANKINGS = 3600  # 1 hour for rankings
CACHE_TTL_QUICK_DATA = 3600  # 1 hour for quick data (refreshed every 15 min)
CACHE_TTL_HISTORY_STALE = 604800  # 7 days fallback for history
CACHE_TTL_MOVERS = 600  # 10 minutes for movers
CACHE_TTL_QUICK_DATA_STALE = 86400  # 24 hours fallback for quick data
CACHE_TTL_RANKINGS_STALE = 86400  # 24 hours fallback for rankings
CACHE_TTL_MOVERS_STALE = 3600  # 1 hour fallback for movers
CACHE_TTL_MOMENTUM = 3600  # 1 hour for weekly momentum
CACHE_TTL_MOMENTUM_STALE = 86400  # 24 hours fallback for momentum
CACHE_TTL_CACHE_READY = 86400  # 24 hours cache readiness flag
CACHE_TTL_ANALYSIS = 3600  # 1 hour for analysis results
CACHE_TTL_ANALYSIS_STALE = 86400  # 24 hours fallback for analysis results


class FiDataService:
    """Service for Finland (Nasdaq Helsinki) stock data"""

    def __init__(self):
        self.redis_cache = get_redis_cache()
        self._tickers_data = None
        self._cache_warming = False
        self._local_cache = {}
        self._local_cache_ts = {}
        self._local_locks = {}
        self._thread_local = threading.local()
        self._load_tickers()

        # Lazy import yfinance service
        self._yfinance = None

        logger.info(f"FiDataService initialized with {len(self.get_all_tickers())} tickers")

    def _is_valid_history(self, history: list) -> bool:
        """Check if history data is valid (not all zeros)"""
        if not history or len(history) < 5:
            return False
        # Check first 10 entries - if ANY has non-zero close, data is valid
        # This is more lenient to handle sparse data or different formats
        valid_count = 0
        for h in history[:10]:
            close = h.get('close', 0)
            if close is not None and close != 0:
                valid_count += 1
        # At least 3 entries should have valid data
        return valid_count >= 3

    def warm_cache_async(self):
        """Start background cache warming - call this after startup"""
        lock_key = "fi:cache_warming_lock"
        if self.redis_cache and self.redis_cache.is_connected():
            try:
                lock_acquired = self.redis_cache.redis_client.set(
                    lock_key, "1", nx=True, ex=900
                )
                if not lock_acquired:
                    logger.info("Cache warming already in progress by another worker")
                    return
            except Exception as e:
                logger.warning(f"Failed to check cache warming lock: {e}")
                return

        if self._cache_warming:
            logger.info("Cache warming already in progress locally")
            return

        def _warm():
            self._run_cache_warm(lock_key)

        thread = threading.Thread(target=_warm, daemon=True)
        thread.start()

    def warm_cache_blocking(self) -> bool:
        """Warm caches synchronously (blocks until done)."""
        lock_key = "fi:cache_warming_lock"
        if self.redis_cache and self.redis_cache.is_connected():
            try:
                lock_acquired = self.redis_cache.redis_client.set(
                    lock_key, "1", nx=True, ex=900
                )
                if not lock_acquired:
                    logger.info("Cache warming already in progress by another worker")
                    return False
            except Exception as e:
                logger.warning(f"Failed to check cache warming lock: {e}")
                return False

        if self._cache_warming:
            logger.info("Cache warming already in progress locally")
            return False

        self._run_cache_warm(lock_key)
        return True

    def _set_cache_ready(self):
        if self.redis_cache and self.redis_cache.is_connected():
            try:
                self.redis_cache.redis_client.setex(
                    "fi:cache_ready", CACHE_TTL_CACHE_READY, datetime.now().isoformat()
                )
            except Exception:
                pass

    @contextmanager
    def _external_fetch_allowed(self):
        previous = getattr(self._thread_local, "allow_external_fetch", None)
        self._thread_local.allow_external_fetch = True
        try:
            yield
        finally:
            if previous is None:
                if hasattr(self._thread_local, "allow_external_fetch"):
                    delattr(self._thread_local, "allow_external_fetch")
            else:
                self._thread_local.allow_external_fetch = previous

    def _can_fetch_external(self) -> bool:
        allowed = getattr(self._thread_local, "allow_external_fetch", None)
        if allowed is None:
            return not settings.FI_CACHE_ONLY
        return bool(allowed)

    def _run_cache_warm(self, lock_key: str):
        import time
        self._cache_warming = True
        try:
            with self._external_fetch_allowed():
                all_tickers = self.get_all_tickers()
                logger.info(f"=== Starting Finnish stocks cache warming for {len(all_tickers)} stocks ===")
                logger.info("This may take 5-10 minutes on first run...")

                logger.info("Step 1/6: Warming quotes cache...")
                quotes_ok = 0
                for i, ticker in enumerate(all_tickers):
                    try:
                        quote = self.get_quote(ticker)
                        if quote and quote.get("price", 0) > 0:
                            quotes_ok += 1
                        if (i + 1) % 5 == 0:
                            time.sleep(0.5)
                        if (i + 1) % 30 == 0:
                            logger.info(f"Quotes: {i + 1}/{len(all_tickers)} ({quotes_ok} OK)")
                    except Exception as e:
                        logger.debug(f"Quote failed for {ticker}: {e}")
                logger.info(f"Step 1/6: Quotes done ({quotes_ok}/{len(all_tickers)} OK)")

                logger.info("Step 2/6: Warming fundamentals cache...")
                funds_ok = 0
                for i, ticker in enumerate(all_tickers):
                    try:
                        fund = self.get_fundamentals(ticker)
                        if fund and (fund.get("peRatio") or fund.get("marketCap")):
                            funds_ok += 1
                        if (i + 1) % 5 == 0:
                            time.sleep(0.5)
                        if (i + 1) % 30 == 0:
                            logger.info(f"Fundamentals: {i + 1}/{len(all_tickers)} ({funds_ok} OK)")
                    except Exception as e:
                        logger.debug(f"Fundamentals failed for {ticker}: {e}")
                logger.info(f"Step 2/6: Fundamentals done ({funds_ok}/{len(all_tickers)} OK)")

                logger.info("Step 3/6: Warming history cache (1y)...")
                hist_ok = 0
                hist_fixed = 0
                for i, ticker in enumerate(all_tickers):
                    try:
                        # First check if existing cache has invalid data (zeros)
                        hist = self.get_history(ticker, range="1y", interval="1d")
                        if hist and not self._is_valid_history(hist):
                            # Cached data is invalid - delete and refetch
                            cache_key = self._get_cache_key("history:1y:1d", ticker)
                            stale_key = f"{cache_key}:stale"
                            self._delete_cached(cache_key)
                            self._delete_cached(stale_key)
                            # Also clear yfinance data manager cache
                            if self.yfinance._data_manager:
                                try:
                                    self.yfinance._data_manager.invalidate(ticker, "historical")
                                except Exception:
                                    pass
                            # Refetch from source
                            hist = self._fetch_history_from_source(ticker, "1y", "1d")
                            if hist and self._is_valid_history(hist):
                                self._set_cached_json(cache_key, hist, CACHE_TTL_HISTORY, local_ttl=CACHE_TTL_HISTORY)
                                self._set_cached_json(stale_key, hist, CACHE_TTL_HISTORY_STALE, local_ttl=CACHE_TTL_HISTORY_STALE)
                                hist_fixed += 1
                        if hist and self._is_valid_history(hist) and len(hist) >= 100:
                            hist_ok += 1
                        if (i + 1) % 5 == 0:
                            time.sleep(0.3)
                        if (i + 1) % 30 == 0:
                            logger.info(f"History: {i + 1}/{len(all_tickers)} ({hist_ok} OK, {hist_fixed} fixed)")
                    except Exception as e:
                        logger.debug(f"History failed for {ticker}: {e}")
                logger.info(f"Step 3/6: History done ({hist_ok}/{len(all_tickers)} OK, {hist_fixed} fixed)")

                logger.info("Step 4/6: Building quick data cache...")
                results = self._build_all_quick_data()
                self._set_cached_json("fi:all_quick_data", results, CACHE_TTL_QUICK_DATA, local_ttl=CACHE_TTL_QUICK_DATA)
                self._set_cached_json("fi:all_quick_data:stale", results, CACHE_TTL_QUICK_DATA_STALE, local_ttl=CACHE_TTL_QUICK_DATA_STALE)
                logger.info("Step 4/6: Quick data cache built")

                logger.info("Step 5/6: Building movers and rankings...")
                movers = self._build_movers()
                self._set_cached_json("fi:movers", movers, CACHE_TTL_MOVERS, local_ttl=CACHE_TTL_MOVERS)
                self._set_cached_json("fi:movers:stale", movers, CACHE_TTL_MOVERS_STALE, local_ttl=CACHE_TTL_MOVERS_STALE)
                rankings = self._build_rankings()
                self._set_cached_json("fi:rankings", rankings, CACHE_TTL_RANKINGS, local_ttl=CACHE_TTL_RANKINGS)
                self._set_cached_json("fi:rankings:stale", rankings, CACHE_TTL_RANKINGS_STALE, local_ttl=CACHE_TTL_RANKINGS_STALE)
                logger.info("Step 5/6: Movers and rankings built")

                logger.info("Step 6/6: Warming analysis cache...")
                analysis_ok = 0
                for i, ticker in enumerate(all_tickers):
                    try:
                        analysis = self.get_analysis(ticker)
                        if analysis:
                            analysis_ok += 1
                        if (i + 1) % 5 == 0:
                            time.sleep(0.2)
                        if (i + 1) % 30 == 0:
                            logger.info(f"Analysis: {i + 1}/{len(all_tickers)} ({analysis_ok} OK)")
                    except Exception as e:
                        logger.debug(f"Analysis failed for {ticker}: {e}")
                logger.info(f"Step 6/6: Analysis done ({analysis_ok}/{len(all_tickers)} OK)")

                logger.info("=== Finnish stocks cache warming COMPLETE! ===")
                logger.info(
                    "Summary: %s quotes, %s fundamentals, %s histories, %s analyses",
                    quotes_ok,
                    funds_ok,
                    hist_ok,
                    analysis_ok
                )
                self._set_cache_ready()

                self._schedule_cache_refresh()

        except Exception as e:
            logger.error(f"Cache warming error: {e}")
        finally:
            self._cache_warming = False
            if self.redis_cache and self.redis_cache.is_connected():
                try:
                    self.redis_cache.redis_client.delete(lock_key)
                except Exception:
                    pass

    def _schedule_cache_refresh(self):
        """Schedule automatic cache refresh every 5 minutes for quotes/movers"""
        import threading

        def _refresh():
            import time
            while True:
                # Wait 5 minutes between refreshes (faster for movers/gainers/losers)
                time.sleep(300)

                lock_key = "fi:cache_refresh_lock"
                if self.redis_cache and self.redis_cache.is_connected():
                    try:
                        lock_acquired = self.redis_cache.redis_client.set(
                            lock_key, "1", nx=True, ex=300
                        )
                        if not lock_acquired:
                            continue
                    except:
                        continue

                try:
                    logger.info("Auto-refreshing Finnish stocks cache (quotes only)...")
                    with self._external_fetch_allowed():
                        movers = self._build_movers()
                        self._set_cached_json("fi:movers", movers, CACHE_TTL_MOVERS, local_ttl=CACHE_TTL_MOVERS)
                        self._set_cached_json("fi:movers:stale", movers, CACHE_TTL_MOVERS_STALE, local_ttl=CACHE_TTL_MOVERS_STALE)
                        logger.info("Cache refresh: movers done")

                        time.sleep(2)
                        quick = self._build_all_quick_data()
                        self._set_cached_json("fi:all_quick_data", quick, CACHE_TTL_QUICK_DATA, local_ttl=CACHE_TTL_QUICK_DATA)
                        self._set_cached_json("fi:all_quick_data:stale", quick, CACHE_TTL_QUICK_DATA_STALE, local_ttl=CACHE_TTL_QUICK_DATA_STALE)
                        rankings = self._build_rankings()
                        self._set_cached_json("fi:rankings", rankings, CACHE_TTL_RANKINGS, local_ttl=CACHE_TTL_RANKINGS)
                        self._set_cached_json("fi:rankings:stale", rankings, CACHE_TTL_RANKINGS_STALE, local_ttl=CACHE_TTL_RANKINGS_STALE)
                        logger.info("Cache refresh: quick data done")
                        self._set_cache_ready()

                except Exception as e:
                    logger.error(f"Cache refresh error: {e}")
                finally:
                    if self.redis_cache and self.redis_cache.is_connected():
                        try:
                            self.redis_cache.redis_client.delete(lock_key)
                        except:
                            pass

        thread = threading.Thread(target=_refresh, daemon=True)
        thread.start()
        logger.info("Cache auto-refresh scheduled (every 5 minutes)")

    def _get_local_cache(self, key: str, max_age: int):
        import time
        ts = self._local_cache_ts.get(key)
        if not ts:
            return None
        if (time.time() - ts) <= max_age:
            return self._local_cache.get(key)
        return None

    def _slice_history_for_range(self, history: List[Dict[str, Any]], range: str, interval: str) -> List[Dict[str, Any]]:
        if not history or interval != "1d":
            return history
        size_map = {
            "1d": 1,
            "5d": 5,
            "1mo": 21,
            "3mo": 63,
            "6mo": 126,
            "1y": 252
        }
        size = size_map.get(range)
        if not size:
            return history
        return history[-size:]

    def _set_local_cache(self, key: str, value: Any):
        import time
        self._local_cache[key] = value
        self._local_cache_ts[key] = time.time()

    def _get_cached_json(self, key: str, local_ttl: Optional[int] = None):
        if self.redis_cache and self.redis_cache.is_connected():
            try:
                cached = self.redis_cache.redis_client.get(key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass
        if local_ttl:
            return self._get_local_cache(key, local_ttl)
        return None

    def _set_cached_json(self, key: str, value: Any, ttl: int, local_ttl: Optional[int] = None):
        if self.redis_cache and self.redis_cache.is_connected():
            try:
                self.redis_cache.redis_client.setex(key, ttl, json.dumps(value))
            except Exception:
                pass
        if local_ttl:
            self._set_local_cache(key, value)

    def _delete_cached(self, key: str):
        """Delete a cached key from both Redis and local cache"""
        if self.redis_cache and self.redis_cache.is_connected():
            try:
                self.redis_cache.redis_client.delete(key)
            except Exception:
                pass
        if key in self._local_cache:
            del self._local_cache[key]
        if key in self._local_cache_ts:
            del self._local_cache_ts[key]

    def _try_acquire_lock(self, key: str, ttl: int) -> bool:
        import time
        if self.redis_cache and self.redis_cache.is_connected():
            try:
                return bool(self.redis_cache.redis_client.set(key, "1", nx=True, ex=ttl))
            except Exception:
                return False
        expires_at = self._local_locks.get(key)
        now = time.time()
        if not expires_at or expires_at <= now:
            self._local_locks[key] = now + ttl
            return True
        return False

    def _release_lock(self, key: str):
        if self.redis_cache and self.redis_cache.is_connected():
            try:
                self.redis_cache.redis_client.delete(key)
            except Exception:
                pass
        if key in self._local_locks:
            self._local_locks.pop(key, None)

    def _wait_for_cache(self, cache_key: str, stale_key: Optional[str], wait_seconds: int, local_ttl: Optional[int] = None):
        import time
        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            cached = self._get_cached_json(cache_key, local_ttl=local_ttl)
            if cached:
                return cached
            time.sleep(0.25)
        if stale_key:
            return self._get_cached_json(stale_key, local_ttl=local_ttl)
        return None

    def _refresh_cache_in_background(
        self,
        builder,
        cache_key: str,
        stale_key: Optional[str],
        ttl: int,
        stale_ttl: Optional[int],
        lock_key: str
    ):
        import threading
        import time as time_module

        def _task():
            try:
                is_history = "history:" in cache_key
                max_retries = 3 if is_history else 1
                retry_delay = 5  # seconds between retries

                for attempt in range(max_retries):
                    try:
                        data = builder()
                        # Validate history data before caching
                        if is_history and data and not self._is_valid_history(data):
                            if attempt < max_retries - 1:
                                logger.debug(f"Background refresh got invalid data for {cache_key}, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                                time_module.sleep(retry_delay)
                                continue
                            else:
                                logger.warning(f"Background refresh got invalid data for {cache_key} after {max_retries} attempts, not caching")
                                return
                        # Data is valid, cache it
                        self._set_cached_json(cache_key, data, ttl, local_ttl=ttl)
                        if stale_key and stale_ttl:
                            self._set_cached_json(stale_key, data, stale_ttl, local_ttl=stale_ttl)
                        return  # Success, exit retry loop
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logger.debug(f"Background refresh failed for {cache_key}, retrying: {e}")
                            time_module.sleep(retry_delay)
                        else:
                            raise
            except Exception as e:
                logger.error(f"Background cache refresh failed for {cache_key}: {e}")
            finally:
                self._release_lock(lock_key)

        thread = threading.Thread(target=_task, daemon=True)
        thread.start()

    @property
    def yfinance(self):
        if self._yfinance is None:
            from app.services.yfinance_service import get_yfinance_service
            self._yfinance = get_yfinance_service()
        return self._yfinance

    def _load_tickers(self):
        """Load Finnish tickers from JSON file"""
        try:
            tickers_path = Path(__file__).parent.parent / "data" / "fi_tickers.json"
            with open(tickers_path, "r", encoding="utf-8") as f:
                self._tickers_data = json.load(f)
            logger.info(f"Loaded {len(self._tickers_data.get('stocks', []))} Finnish tickers")
        except Exception as e:
            logger.error(f"Failed to load Finnish tickers: {e}")
            self._tickers_data = {"stocks": [], "metadata": {}, "sectors": {}, "blue_chips": []}

    def get_universe(self) -> Dict[str, Any]:
        """Get the complete Finnish stock universe"""
        stocks = []
        for stock in self._tickers_data.get("stocks", []):
            enriched = dict(stock)
            enriched["newsUrl"] = get_nasdaq_news_url(enriched.get("ticker", ""))
            stocks.append(enriched)

        return {
            "exchange": "Nasdaq Helsinki",
            "currency": "EUR",
            "country": "Finland",
            "total_count": len(self._tickers_data.get("stocks", [])),
            "sectors": self._tickers_data.get("sectors", {}),
            "stocks": stocks,
            "blue_chips": self._tickers_data.get("blue_chips", [])
        }

    def get_all_tickers(self) -> List[str]:
        """Get list of all Finnish tickers"""
        return [
            s["ticker"]
            for s in self._tickers_data.get("stocks", [])
            if not s.get("yfinance_disabled") and not s.get("disabled")
        ]

    def get_stock_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get basic info for a ticker from our database"""
        ticker = self._normalize_ticker(ticker)
        for stock in self._tickers_data.get("stocks", []):
            if stock["ticker"] == ticker:
                enriched = dict(stock)
                enriched["newsUrl"] = get_nasdaq_news_url(ticker)
                return enriched
        return None

    def _normalize_ticker(self, ticker: str) -> str:
        """Normalize ticker to include .HE suffix if missing"""
        ticker = ticker.upper().strip()
        if not ticker.endswith(".HE"):
            ticker = f"{ticker}.HE"
        return ticker

    def _get_cache_key(self, prefix: str, ticker: str) -> str:
        """Generate cache key for Finnish data"""
        return f"fi:{prefix}:{ticker}"

    def _get_cached_fundamentals(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Return cached fundamentals only (no yfinance fetch)."""
        cache_key = self._get_cache_key("fundamentals", ticker)
        if self.redis_cache and self.redis_cache.is_connected():
            try:
                cached = self.redis_cache.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.debug(f"Cache read error (fundamentals): {e}")
        return None

    @staticmethod
    def _to_percent(value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        try:
            num = float(value)
        except (TypeError, ValueError):
            return None
        if abs(num) <= 1:
            return num * 100
        return num

    def get_sector_benchmarks(
        self,
        ticker: str,
        fundamentals: Optional[Dict[str, Any]],
        stock_info: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        sector = (stock_info or {}).get("sector") or (fundamentals or {}).get("sector")
        if not sector:
            return None

        sector_key = sector.lower()
        sector_tickers = [
            s["ticker"]
            for s in self._tickers_data.get("stocks", [])
            if (s.get("sector") or "").lower() == sector_key
        ]
        if not sector_tickers:
            return None

        metrics = {
            "peRatio": [],
            "priceToBook": [],
            "dividendYield": [],
            "profitMargins": [],
            "returnOnEquity": [],
            "debtToEquity": [],
        }
        sample_tickers: set[str] = set()

        for t in sector_tickers:
            if t == ticker and fundamentals:
                fund = fundamentals
            else:
                fund = self._get_cached_fundamentals(t)
            if not fund:
                continue

            sample_tickers.add(t)
            pe = self._safe_float(fund.get("peRatio"))
            pb = self._safe_float(fund.get("priceToBook"))
            div = self._to_percent(fund.get("dividendYield"))
            margin = self._to_percent(fund.get("profitMargins"))
            roe = self._to_percent(fund.get("returnOnEquity"))
            debt = self._safe_float(fund.get("debtToEquity"))

            if pe is not None and pe > 0:
                metrics["peRatio"].append(pe)
            if pb is not None and pb > 0:
                metrics["priceToBook"].append(pb)
            if div is not None and div >= 0:
                metrics["dividendYield"].append(float(div))
            if margin is not None:
                metrics["profitMargins"].append(float(margin))
            if roe is not None:
                metrics["returnOnEquity"].append(float(roe))
            if debt is not None and debt >= 0:
                metrics["debtToEquity"].append(debt)

        if len(sample_tickers) < 3:
            return None

        def _median(values: List[float]) -> Optional[float]:
            if not values:
                return None
            return float(np.median(values))

        medians = {key: _median(values) for key, values in metrics.items()}

        values = {
            "peRatio": fundamentals.get("peRatio") if fundamentals else None,
            "priceToBook": fundamentals.get("priceToBook") if fundamentals else None,
            "dividendYield": self._to_percent(fundamentals.get("dividendYield") if fundamentals else None),
            "profitMargins": self._to_percent(fundamentals.get("profitMargins") if fundamentals else None),
            "returnOnEquity": self._to_percent(fundamentals.get("returnOnEquity") if fundamentals else None),
            "debtToEquity": fundamentals.get("debtToEquity") if fundamentals else None,
        }

        return {
            "sector": sector,
            "sampleCount": len(sample_tickers),
            "medians": medians,
            "values": values,
        }

    def get_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get current quote for a Finnish stock"""
        ticker = self._normalize_ticker(ticker)
        cache_key = self._get_cache_key("quote", ticker)

        # Check cache
        if self.redis_cache and self.redis_cache.is_connected():
            try:
                cached = self.redis_cache.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.debug(f"Cache read error: {e}")

        if not self._can_fetch_external():
            return None

        # Fetch from yfinance - pass allow_external=True to bypass YFINANCE_CACHE_ONLY
        try:
            quote = self.yfinance.get_quote(ticker, allow_external=True)
            if quote:
                price = quote.get("c", 0)
                prev_close = quote.get("pc", 0)
                # Calculate change and changePercent
                change = price - prev_close if price and prev_close else 0
                change_pct = (change / prev_close * 100) if prev_close and prev_close != 0 else 0

                result = {
                    "ticker": ticker,
                    "price": price,
                    "change": round(change, 4),
                    "changePercent": round(change_pct, 2),
                    "previousClose": prev_close,
                    "high": quote.get("h", 0),
                    "low": quote.get("l", 0),
                    "open": quote.get("o", 0),
                    "currency": "EUR",
                    "exchange": "Nasdaq Helsinki",
                    "timestamp": datetime.now().isoformat()
                }

                # Cache the result
                if self.redis_cache and self.redis_cache.is_connected():
                    try:
                        self.redis_cache.redis_client.setex(
                            cache_key, CACHE_TTL_QUOTE, json.dumps(result)
                        )
                    except Exception as e:
                        logger.debug(f"Cache write error: {e}")

                return result
            
            # Fallback to Inderes if yfinance fails
            try:
                from app.services.inderes_service import get_inderes_service
                inderes = get_inderes_service()
                quote = inderes.get_stock_data(ticker)
                if quote:
                    logger.info(f"Fetched {ticker} from Inderes fallback")
                    # Cache the result
                    if self.redis_cache and self.redis_cache.is_connected():
                        try:
                            self.redis_cache.redis_client.setex(
                                cache_key, CACHE_TTL_QUOTE, json.dumps(quote)
                            )
                        except Exception as e:
                            logger.debug(f"Cache write error: {e}")
                    return quote
            except Exception as e:
                logger.debug(f"Inderes fallback failed for {ticker}: {e}")

        except Exception as e:
            logger.error(f"Failed to get quote for {ticker}: {e}")

        return None

    def get_history(
        self,
        ticker: str,
        range: str = "1y",
        interval: str = "1d"
    ) -> Optional[List[Dict[str, Any]]]:
        """Get historical OHLCV data for a Finnish stock"""
        ticker = self._normalize_ticker(ticker)
        cache_key = self._get_cache_key(f"history:{range}:{interval}", ticker)
        stale_key = f"{cache_key}:stale"
        lock_key = f"{cache_key}:lock"

        cached = self._get_cached_json(cache_key, local_ttl=CACHE_TTL_HISTORY)
        if cached is not None:
            # Validate cached data - if all zeros, delete and fetch fresh
            if self._is_valid_history(cached):
                return cached
            else:
                logger.warning(f"Invalid history cache for {ticker} (all zeros), clearing")
                self._delete_cached(cache_key)
                self._delete_cached(stale_key)

        if interval == "1d":
            fallback_ranges = {
                "1y": ["2y", "5y", "max"],
                "6mo": ["1y", "2y"],
                "3mo": ["1y", "2y"],
                "1mo": ["1y"],
                "5d": ["1mo", "3mo", "1y"],
                "1d": ["5d", "1mo", "3mo", "1y"]
            }
            for fallback_range in fallback_ranges.get(range, []):
                fallback_key = self._get_cache_key(f"history:{fallback_range}:{interval}", ticker)
                fallback_cached = self._get_cached_json(fallback_key, local_ttl=CACHE_TTL_HISTORY)
                if fallback_cached and self._is_valid_history(fallback_cached):
                    sliced = self._slice_history_for_range(fallback_cached, range, interval)
                    self._set_cached_json(cache_key, sliced, CACHE_TTL_HISTORY, local_ttl=CACHE_TTL_HISTORY)
                    self._set_cached_json(stale_key, sliced, CACHE_TTL_HISTORY_STALE, local_ttl=CACHE_TTL_HISTORY_STALE)
                    return sliced

        stale = self._get_cached_json(stale_key, local_ttl=CACHE_TTL_HISTORY_STALE)
        if stale is not None:
            # Validate stale data - if all zeros, don't use it
            if self._is_valid_history(stale):
                if self._try_acquire_lock(lock_key, 300):
                    self._refresh_cache_in_background(
                        lambda: self._fetch_history_from_source(ticker, range, interval),
                        cache_key,
                        stale_key,
                        CACHE_TTL_HISTORY,
                        CACHE_TTL_HISTORY_STALE,
                        lock_key
                    )
                return stale
            else:
                logger.warning(f"Invalid stale history cache for {ticker} (all zeros), clearing")
                self._delete_cached(stale_key)

        if not self._can_fetch_external():
            return None

        if not self._try_acquire_lock(lock_key, 300):
            waited = self._wait_for_cache(cache_key, stale_key, wait_seconds=6, local_ttl=CACHE_TTL_HISTORY)
            if waited is not None:
                return waited
            return None

        try:
            result = self._fetch_history_from_source(ticker, range, interval)
            # Only cache valid data (not all zeros)
            if result and self._is_valid_history(result):
                self._set_cached_json(cache_key, result, CACHE_TTL_HISTORY, local_ttl=CACHE_TTL_HISTORY)
                self._set_cached_json(stale_key, result, CACHE_TTL_HISTORY_STALE, local_ttl=CACHE_TTL_HISTORY_STALE)
            elif result:
                logger.warning(f"Fetched invalid history for {ticker} (all zeros), not caching")
            return result
        finally:
            self._release_lock(lock_key)

    def _fetch_history_from_source(
        self,
        ticker: str,
        range: str,
        interval: str
    ) -> Optional[List[Dict[str, Any]]]:
        if not self._can_fetch_external():
            return None
        period_map = {
            "1d": "1d",
            "5d": "5d",
            "1mo": "1mo",
            "3mo": "3mo",
            "6mo": "6mo",
            "1y": "1y",
            "2y": "2y",
            "5y": "5y",
            "max": "max"
        }
        period = period_map.get(range, "1y")

        try:
            # Pass allow_external=True to bypass YFINANCE_CACHE_ONLY
            data = self.yfinance.get_historical_data(ticker, period=period, interval=interval, allow_external=True)
            if data is None or data.empty:
                return None

            # Handle multi-index columns from yfinance (e.g., ('Close', 'BITTI.HE'))
            if isinstance(data.columns, pd.MultiIndex):
                # Flatten to just the first level (Open, High, Low, Close, Volume)
                data.columns = data.columns.get_level_values(0)

            result = []

            def safe_float(val, default=0.0):
                try:
                    if hasattr(val, 'item'):
                        val = val.item()
                    if pd.isna(val):
                        return default
                    return float(val)
                except Exception:
                    return default

            def safe_int(val, default=0):
                try:
                    if hasattr(val, 'item'):
                        val = val.item()
                    if pd.isna(val):
                        return default
                    return int(val)
                except Exception:
                    return default

            for idx, row in data.iterrows():
                # Access columns directly - they should be flattened now
                r_open = row.get("Open", row.get("open", 0))
                r_high = row.get("High", row.get("high", 0))
                r_low = row.get("Low", row.get("low", 0))
                r_close = row.get("Close", row.get("close", 0))
                r_vol = row.get("Volume", row.get("volume", 0))

                close_val = safe_float(r_close)

                result.append({
                    "date": idx.strftime("%Y-%m-%d") if hasattr(idx, 'strftime') else str(idx),
                    "open": safe_float(r_open),
                    "high": safe_float(r_high),
                    "low": safe_float(r_low),
                    "close": close_val,
                    "volume": safe_int(r_vol)
                })

            return result
        except Exception as e:
            logger.error(f"Failed to get history for {ticker}: {e}")
            return None

    def get_fundamentals(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get fundamental data for a Finnish stock"""
        ticker = self._normalize_ticker(ticker)
        cache_key = self._get_cache_key("fundamentals", ticker)

        # Check cache
        if self.redis_cache and self.redis_cache.is_connected():
            try:
                cached = self.redis_cache.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.debug(f"Cache read error: {e}")

        if not self._can_fetch_external():
            return None

        try:
            # Pass allow_external=True to bypass YFINANCE_CACHE_ONLY when we're allowed to fetch
            fundamentals = self.yfinance.get_fundamentals(ticker, allow_external=True)

            if not fundamentals:
                return None

            # Get stock info from our database
            stock_info = self.get_stock_info(ticker)

            result = {
                "ticker": ticker,
                "name": fundamentals.get("shortName") or (stock_info["name"] if stock_info else ticker),
                "sector": fundamentals.get("sector") or (stock_info["sector"] if stock_info else "Unknown"),
                "industry": fundamentals.get("industry", "Unknown"),
                "exchange": "Nasdaq Helsinki",
                "currency": "EUR",
                "marketCap": fundamentals.get("marketCap", 0),
                "peRatio": fundamentals.get("peRatio", None),
                "forwardPE": fundamentals.get("forwardPE", None),
                "pegRatio": fundamentals.get("pegRatio", None),
                "priceToBook": fundamentals.get("priceToBook", None),
                "dividendYield": fundamentals.get("dividendYield", None),
                "profitMargins": fundamentals.get("profitMargins", None),
                "revenueGrowth": fundamentals.get("revenueGrowth", None),
                "earningsGrowth": fundamentals.get("earningsGrowth", None),
                "returnOnEquity": fundamentals.get("returnOnEquity", None),
                "returnOnAssets": fundamentals.get("returnOnAssets", None),
                "roic": fundamentals.get("roic", None),
                "debtToEquity": fundamentals.get("debtToEquity", None),
                "beta": fundamentals.get("beta", None),
                "fiftyTwoWeekHigh": fundamentals.get("fiftyTwoWeekHigh", None),
                "fiftyTwoWeekLow": fundamentals.get("fiftyTwoWeekLow", None),
                "averageVolume": fundamentals.get("averageVolume", None),
                "enterpriseValue": fundamentals.get("enterpriseValue", None),
                "ebit": fundamentals.get("ebit", None),
                "evEbit": fundamentals.get("evEbit", None),
                "timestamp": datetime.now().isoformat()
            }

            # Cache the result
            if self.redis_cache and self.redis_cache.is_connected():
                try:
                    self.redis_cache.redis_client.setex(
                        cache_key, CACHE_TTL_FUNDAMENTALS, json.dumps(result)
                    )
                except Exception as e:
                    logger.debug(f"Cache write error: {e}")

            return result
        except Exception as e:
            logger.error(f"Failed to get fundamentals for {ticker}: {e}")

        return None

    def compute_metrics(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute risk/return metrics from historical data"""
        if not history or len(history) < 20:
            return {
                "volatility": None,
                "maxDrawdown": None,
                "sharpeRatio": None,
                "return3m": None,
                "return12m": None
            }

        try:
            # Convert to DataFrame
            df = pd.DataFrame(history)
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df = df.dropna(subset=["close"])

            if len(df) < 20:
                return {
                    "volatility": None,
                    "maxDrawdown": None,
                    "sharpeRatio": None,
                    "return3m": None,
                    "return12m": None
                }

            # Calculate returns
            df["returns"] = df["close"].pct_change()

            # Annualized volatility
            volatility = df["returns"].std() * np.sqrt(252)

            # Maximum drawdown
            df["cummax"] = df["close"].cummax()
            df["drawdown"] = (df["close"] - df["cummax"]) / df["cummax"]
            max_drawdown = df["drawdown"].min()

            # Sharpe ratio (assuming risk-free rate of 3%)
            avg_return = df["returns"].mean() * 252
            sharpe_ratio = (avg_return - 0.03) / volatility if volatility > 0 else 0

            # Returns - use available data, not fixed lookback
            return_3m = None
            return_12m = None

            if len(df) >= 60:  # ~3 months of trading days
                lookback_3m = min(63, len(df) - 1)
                start_price_3m = df["close"].iloc[-lookback_3m]
                if start_price_3m and start_price_3m > 0:
                    return_3m = (df["close"].iloc[-1] / start_price_3m - 1) * 100
            
            if len(df) >= 230:  # ~11+ months of trading days (relax from 252)
                lookback_12m = min(252, len(df) - 1)
                start_price_12m = df["close"].iloc[-lookback_12m]
                if start_price_12m and start_price_12m > 0:
                    return_12m = (df["close"].iloc[-1] / start_price_12m - 1) * 100

            return {
                "volatility": round(volatility * 100, 2) if not math.isnan(volatility) else None,
                "maxDrawdown": round(max_drawdown * 100, 2) if not math.isnan(max_drawdown) else None,
                "sharpeRatio": round(sharpe_ratio, 2) if not math.isnan(sharpe_ratio) else None,
                "return3m": round(return_3m, 2) if return_3m is not None and not math.isnan(return_3m) else None,
                "return12m": round(return_12m, 2) if return_12m is not None and not math.isnan(return_12m) else None
            }
        except Exception as e:
            logger.error(f"Failed to compute metrics: {e}")
            return {
                "volatility": None,
                "maxDrawdown": None,
                "sharpeRatio": None,
                "return3m": None,
                "return12m": None
            }

    def compute_technicals(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute technical analysis indicators from historical data.

        Returns RSI, MACD, Bollinger Bands, SMAs and signal interpretations.
        """
        if not history or len(history) < 30:
            return {
                "rsi": None,
                "macd": None,
                "bollinger": None,
                "sma": None,
                "signals": [],
                "summary": None
            }

        try:
            # Convert to DataFrame
            df = pd.DataFrame(history)
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df = df.dropna(subset=["close"])

            if len(df) < 30:
                return {
                    "rsi": None,
                    "macd": None,
                    "bollinger": None,
                    "sma": None,
                    "signals": [],
                    "summary": None
                }

            close = df["close"]
            current_price = float(close.iloc[-1])
            signals = []

            # === RSI (14-period) ===
            rsi_period = 14
            rsi_value = None
            rsi_signal = None
            if len(close) >= rsi_period + 1:
                delta = close.diff()
                gain = delta.where(delta > 0, 0).rolling(window=rsi_period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                rsi_value = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None

                if rsi_value is not None:
                    if rsi_value < 30:
                        rsi_signal = "YLIMYYTY"
                        signals.append({"type": "RSI", "signal": "BUY", "text": f"RSI {rsi_value:.1f} - Ylimyyty, mahdollinen ostopaikka"})
                    elif rsi_value > 70:
                        rsi_signal = "YLIOSTETTU"
                        signals.append({"type": "RSI", "signal": "SELL", "text": f"RSI {rsi_value:.1f} - Yliostettu, varovaisuutta"})
                    elif 40 <= rsi_value <= 60:
                        rsi_signal = "NEUTRAALI"
                    elif rsi_value < 40:
                        rsi_signal = "HEIKKO"
                    else:
                        rsi_signal = "VAHVA"

            # === MACD (12, 26, 9) ===
            macd_value = None
            macd_signal_line = None
            macd_histogram = None
            macd_signal = None
            if len(close) >= 35:
                ema_12 = close.ewm(span=12, adjust=False).mean()
                ema_26 = close.ewm(span=26, adjust=False).mean()
                macd_line = ema_12 - ema_26
                signal_line = macd_line.ewm(span=9, adjust=False).mean()
                histogram = macd_line - signal_line

                macd_value = float(macd_line.iloc[-1]) if not pd.isna(macd_line.iloc[-1]) else None
                macd_signal_line = float(signal_line.iloc[-1]) if not pd.isna(signal_line.iloc[-1]) else None
                macd_histogram = float(histogram.iloc[-1]) if not pd.isna(histogram.iloc[-1]) else None

                if macd_value is not None and macd_signal_line is not None:
                    prev_macd = float(macd_line.iloc[-2]) if len(macd_line) > 1 else macd_value
                    prev_signal = float(signal_line.iloc[-2]) if len(signal_line) > 1 else macd_signal_line

                    # Check for crossover
                    if prev_macd <= prev_signal and macd_value > macd_signal_line:
                        macd_signal = "BULLISH_CROSSOVER"
                        signals.append({"type": "MACD", "signal": "BUY", "text": "MACD ylitti signaalilinjan - Ostosignaali"})
                    elif prev_macd >= prev_signal and macd_value < macd_signal_line:
                        macd_signal = "BEARISH_CROSSOVER"
                        signals.append({"type": "MACD", "signal": "SELL", "text": "MACD alitti signaalilinjan - Myyntisignaali"})
                    elif macd_value > macd_signal_line:
                        macd_signal = "BULLISH"
                    else:
                        macd_signal = "BEARISH"

            # === Bollinger Bands (20-period, 2 std) ===
            bb_period = 20
            bb_upper = None
            bb_middle = None
            bb_lower = None
            bb_position = None
            bb_signal = None
            if len(close) >= bb_period:
                sma_20 = close.rolling(window=bb_period).mean()
                std_20 = close.rolling(window=bb_period).std()

                bb_middle = float(sma_20.iloc[-1]) if not pd.isna(sma_20.iloc[-1]) else None
                bb_upper = float(sma_20.iloc[-1] + 2 * std_20.iloc[-1]) if bb_middle else None
                bb_lower = float(sma_20.iloc[-1] - 2 * std_20.iloc[-1]) if bb_middle else None

                if bb_upper and bb_lower and bb_middle:
                    bb_width = bb_upper - bb_lower
                    bb_position = (current_price - bb_lower) / bb_width * 100 if bb_width > 0 else 50

                    if current_price <= bb_lower:
                        bb_signal = "LOWER_BAND"
                        signals.append({"type": "BB", "signal": "BUY", "text": "Hinta alemmalla Bollinger-nauhalla - Mahdollinen pohja"})
                    elif current_price >= bb_upper:
                        bb_signal = "UPPER_BAND"
                        signals.append({"type": "BB", "signal": "SELL", "text": "Hinta ylemmällä Bollinger-nauhalla - Mahdollinen huippu"})
                    elif current_price > bb_middle:
                        bb_signal = "ABOVE_MIDDLE"
                    else:
                        bb_signal = "BELOW_MIDDLE"

            # === Simple Moving Averages ===
            sma_20_val = None
            sma_50_val = None
            sma_200_val = None
            trend = None

            if len(close) >= 20:
                sma_20_val = float(close.rolling(20).mean().iloc[-1])
            if len(close) >= 50:
                sma_50_val = float(close.rolling(50).mean().iloc[-1])
            if len(close) >= 200:
                sma_200_val = float(close.rolling(200).mean().iloc[-1])

            # Determine trend
            if sma_20_val and sma_50_val and sma_200_val:
                if current_price > sma_20_val > sma_50_val > sma_200_val:
                    trend = "VAHVA_NOUSU"
                    signals.append({"type": "TREND", "signal": "BUY", "text": "Vahva nousutrendi - Kaikki MA:t nousevassa järjestyksessä"})
                elif current_price < sma_20_val < sma_50_val < sma_200_val:
                    trend = "VAHVA_LASKU"
                    signals.append({"type": "TREND", "signal": "SELL", "text": "Vahva laskutrendi - Kaikki MA:t laskevassa järjestyksessä"})
                elif current_price > sma_200_val:
                    trend = "NOUSU"
                else:
                    trend = "LASKU"
            elif sma_50_val:
                if current_price > sma_50_val:
                    trend = "NOUSU"
                else:
                    trend = "LASKU"

            # === Summary ===
            buy_signals = len([s for s in signals if s["signal"] == "BUY"])
            sell_signals = len([s for s in signals if s["signal"] == "SELL"])

            if buy_signals > sell_signals and buy_signals >= 2:
                summary = {"verdict": "OSTA", "text": "Useita ostosignaaleja - Tekninen kuva positiivinen"}
            elif sell_signals > buy_signals and sell_signals >= 2:
                summary = {"verdict": "MYY", "text": "Useita myyntisignaaleja - Tekninen kuva negatiivinen"}
            elif buy_signals > 0:
                summary = {"verdict": "PIDÄ/OSTA", "text": "Lievästi positiivinen tekninen kuva"}
            elif sell_signals > 0:
                summary = {"verdict": "PIDÄ/MYY", "text": "Lievästi negatiivinen tekninen kuva"}
            else:
                summary = {"verdict": "NEUTRAALI", "text": "Ei selkeitä signaaleja - Odota parempia merkkejä"}

            return {
                "rsi": {
                    "value": round(rsi_value, 1) if rsi_value else None,
                    "signal": rsi_signal,
                    "period": rsi_period
                },
                "macd": {
                    "value": round(macd_value, 4) if macd_value else None,
                    "signal_line": round(macd_signal_line, 4) if macd_signal_line else None,
                    "histogram": round(macd_histogram, 4) if macd_histogram else None,
                    "signal": macd_signal
                },
                "bollinger": {
                    "upper": round(bb_upper, 2) if bb_upper else None,
                    "middle": round(bb_middle, 2) if bb_middle else None,
                    "lower": round(bb_lower, 2) if bb_lower else None,
                    "position": round(bb_position, 1) if bb_position else None,
                    "signal": bb_signal,
                    "period": bb_period
                },
                "sma": {
                    "sma20": round(sma_20_val, 2) if sma_20_val else None,
                    "sma50": round(sma_50_val, 2) if sma_50_val else None,
                    "sma200": round(sma_200_val, 2) if sma_200_val else None,
                    "trend": trend
                },
                "price": round(current_price, 2),
                "signals": signals,
                "summary": summary
            }

        except Exception as e:
            logger.error(f"Failed to compute technicals: {e}")
            return {
                "rsi": None,
                "macd": None,
                "bollinger": None,
                "sma": None,
                "signals": [],
                "summary": None
            }

    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert a value to float, returning None if not possible."""
        if value is None:
            return None
        try:
            result = float(value)
            if math.isnan(result) or math.isinf(result):
                return None
            return result
        except (ValueError, TypeError):
            return None

    def compute_score(
        self,
        metrics: Dict[str, Any],
        fundamentals: Optional[Dict[str, Any]],
        news_summary: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Compute a score (0-100) for a Finnish stock.

        Scoring breakdown:
        - Momentum (35 points): 3m and 12m returns
        - Risk (25 points): volatility and max drawdown
        - Fundamentals (30 points): P/E, profit margins, growth
        - News (10 points): LLM-analyzed news sentiment
        """
        score_components = {
            "momentum": 0,
            "risk": 0,
            "fundamentals": 0,
            "news": 0
        }
        explanations = []

        # Momentum score (35 points, was 40)
        momentum_score = 17  # Neutral baseline (was 20)

        return_3m = self._safe_float(metrics.get("return3m"))
        return_12m = self._safe_float(metrics.get("return12m"))

        if return_3m is not None:
            if return_3m > 20:
                momentum_score += 10
                explanations.append("Vahva 3kk tuotto (>20%)")
            elif return_3m > 10:
                momentum_score += 7
                explanations.append("Hyvä 3kk tuotto (>10%)")
            elif return_3m > 0:
                momentum_score += 3
            elif return_3m < -10:
                momentum_score -= 5
                explanations.append("Heikko 3kk tuotto (<-10%)")

        if return_12m is not None:
            if return_12m > 30:
                momentum_score += 10
                explanations.append("Erinomainen 12kk tuotto (>30%)")
            elif return_12m > 15:
                momentum_score += 7
                explanations.append("Hyvä 12kk tuotto (>15%)")
            elif return_12m > 0:
                momentum_score += 3
            elif return_12m < -20:
                momentum_score -= 5

        score_components["momentum"] = min(35, max(0, momentum_score))

        # Risk score (25 points, was 30)
        risk_score = 12  # Neutral baseline (was 15)

        volatility = self._safe_float(metrics.get("volatility"))
        max_drawdown = self._safe_float(metrics.get("maxDrawdown"))

        if volatility is not None:
            if volatility < 20:
                risk_score += 8
                explanations.append("Matala volatiliteetti")
            elif volatility < 30:
                risk_score += 4
            elif volatility > 50:
                risk_score -= 5
                explanations.append("Korkea volatiliteetti")

        if max_drawdown is not None:
            if max_drawdown > -15:
                risk_score += 7
                explanations.append("Pieni maksimi laskutrendi")
            elif max_drawdown > -30:
                risk_score += 3
            elif max_drawdown < -50:
                risk_score -= 5

        score_components["risk"] = min(25, max(0, risk_score))

        # Fundamentals score (30 points)
        fund_score = 15  # Neutral baseline

        if fundamentals:
            pe = self._safe_float(fundamentals.get("peRatio"))
            profit_margin = self._safe_float(fundamentals.get("profitMargins"))
            revenue_growth = self._safe_float(fundamentals.get("revenueGrowth"))
            roe = self._safe_float(fundamentals.get("returnOnEquity"))

            # P/E ratio scoring
            if pe is not None and pe > 0:
                if 5 <= pe <= 15:
                    fund_score += 5
                    explanations.append("Houkutteleva P/E-luku")
                elif 15 < pe <= 25:
                    fund_score += 3
                elif pe > 40:
                    fund_score -= 3

            # Profit margin scoring
            if profit_margin is not None:
                margin_pct = profit_margin * 100
                if margin_pct > 15:
                    fund_score += 5
                    explanations.append("Korkea voittomarginaali")
                elif margin_pct > 8:
                    fund_score += 3
                elif margin_pct < 0:
                    fund_score -= 3

            # Revenue growth scoring
            if revenue_growth is not None:
                growth_pct = revenue_growth * 100
                if growth_pct > 20:
                    fund_score += 5
                    explanations.append("Vahva liikevaihdon kasvu")
                elif growth_pct > 10:
                    fund_score += 3
                elif growth_pct < -10:
                    fund_score -= 3

        score_components["fundamentals"] = min(30, max(0, fund_score))

        # News sentiment score (10 points)
        news_score = 5  # Neutral baseline

        if news_summary:
            positive = news_summary.get("positive", 0)
            negative = news_summary.get("negative", 0)
            total = news_summary.get("total", 0)

            if total > 0:
                # Calculate net sentiment ratio
                net_sentiment = (positive - negative) / total

                if net_sentiment > 0.3:
                    news_score += 5
                    explanations.append(f"Positiivinen uutisvirta ({positive} positiivista)")
                elif net_sentiment > 0.1:
                    news_score += 3
                elif net_sentiment < -0.3:
                    news_score -= 3
                    explanations.append(f"Negatiivinen uutisvirta ({negative} negatiivista)")
                elif net_sentiment < -0.1:
                    news_score -= 2

                # Bonus for recent news activity
                if total >= 5:
                    news_score += 1  # Active news coverage

        score_components["news"] = min(10, max(0, news_score))

        # Total score
        total_score = sum(score_components.values())

        # Determine risk level based on actual risk metrics (volatility & drawdown)
        # Re-use already converted values or convert again
        vol_for_risk = self._safe_float(metrics.get("volatility"))
        dd_for_risk = self._safe_float(metrics.get("maxDrawdown"))

        risk_points = 0
        if vol_for_risk is not None:
            if vol_for_risk > 45:
                risk_points += 2
            elif vol_for_risk > 35:
                risk_points += 1
            elif vol_for_risk < 20:
                risk_points -= 1

        if dd_for_risk is not None:
            if dd_for_risk < -40:
                risk_points += 2
            elif dd_for_risk < -25:
                risk_points += 1
            elif dd_for_risk > -15:
                risk_points -= 1

        # Also consider fundamentals for risk
        if fundamentals:
            debt = self._safe_float(fundamentals.get("debtToEquity"))
            if debt is not None and debt > 150:
                risk_points += 1
            beta = self._safe_float(fundamentals.get("beta"))
            if beta is not None and beta > 1.5:
                risk_points += 1
            elif beta is not None and beta < 0.8:
                risk_points -= 1

        if risk_points >= 2:
            risk_level = "HIGH"
        elif risk_points <= -1:
            risk_level = "LOW"
        else:
            risk_level = "MEDIUM"

        return {
            "score": total_score,
            "components": score_components,
            "riskLevel": risk_level,
            "explanations": explanations[:5]  # Top 5 explanations
        }

    def _refresh_rank_from_rankings(self, analysis: Dict[str, Any], ticker: str) -> Dict[str, Any]:
        """Refresh rankPosition and rankTotal from current rankings"""
        try:
            rankings = self.get_rankings(limit=500)
            rank_total = len(rankings)
            rank_position = None
            normalized = ticker.upper()
            for idx, item in enumerate(rankings):
                if (item.get("ticker") or "").upper() == normalized:
                    rank_position = idx + 1
                    break
            analysis["rankPosition"] = rank_position
            analysis["rankTotal"] = rank_total
        except Exception as e:
            logger.debug(f"Failed to refresh rank for {ticker}: {e}")
        return analysis

    def get_analysis(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive analysis for a Finnish stock (cached)."""
        ticker = self._normalize_ticker(ticker)
        cache_key = self._get_cache_key("analysis", ticker)
        stale_key = f"{cache_key}:stale"
        lock_key = f"{cache_key}:lock"

        cached = self._get_cached_json(cache_key, local_ttl=CACHE_TTL_ANALYSIS)
        if cached is not None:
            # Always refresh rank from current rankings to ensure consistency
            return self._refresh_rank_from_rankings(cached.copy(), ticker)

        stale = self._get_cached_json(stale_key, local_ttl=CACHE_TTL_ANALYSIS_STALE)
        if stale is not None:
            if self._try_acquire_lock(lock_key, 300) and self._can_fetch_external():
                self._refresh_cache_in_background(
                    lambda: self._build_analysis(ticker),
                    cache_key,
                    stale_key,
                    CACHE_TTL_ANALYSIS,
                    CACHE_TTL_ANALYSIS_STALE,
                    lock_key
                )
            # Always refresh rank from current rankings to ensure consistency
            return self._refresh_rank_from_rankings(stale.copy(), ticker)

        if not self._can_fetch_external():
            result = self._build_analysis(ticker)
            if result:
                self._set_cached_json(cache_key, result, CACHE_TTL_ANALYSIS, local_ttl=CACHE_TTL_ANALYSIS)
                self._set_cached_json(stale_key, result, CACHE_TTL_ANALYSIS_STALE, local_ttl=CACHE_TTL_ANALYSIS_STALE)
            return result

        if not self._try_acquire_lock(lock_key, 300):
            waited = self._wait_for_cache(cache_key, stale_key, wait_seconds=6, local_ttl=CACHE_TTL_ANALYSIS)
            if waited is not None:
                return waited
            return None

        try:
            result = self._build_analysis(ticker)
            if result:
                self._set_cached_json(cache_key, result, CACHE_TTL_ANALYSIS, local_ttl=CACHE_TTL_ANALYSIS)
                self._set_cached_json(stale_key, result, CACHE_TTL_ANALYSIS_STALE, local_ttl=CACHE_TTL_ANALYSIS_STALE)
            return result
        finally:
            self._release_lock(lock_key)

    def _build_analysis(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive analysis for a Finnish stock"""
        ticker = self._normalize_ticker(ticker)

        # Get all data
        quote = self.get_quote(ticker)
        # Use 2y to ensure 252+ trading days for return12m calculation, fallback to 1y
        history = self.get_history(ticker, range="2y", interval="1d")
        if not history or len(history) < 50:
            history = self.get_history(ticker, range="1y", interval="1d")
        fundamentals = self.get_fundamentals(ticker)
        stock_info = self.get_stock_info(ticker)

        # Allow analysis fallback for tickers in our universe even if live data is missing
        if not quote and not history and not fundamentals and not stock_info:
            return None

        # Fetch news events first (needed for scoring)
        news_events = []
        event_summary = None
        try:
            from app.services.fi_event_service import get_fi_event_service
            event_service = get_fi_event_service()
            news_events = event_service.get_events(ticker=ticker, limit=10, include_analysis=True)
            # De-duplicate by source URL or title/date to avoid repeated items in UI
            if news_events:
                seen = set()
                deduped = []
                for event in news_events:
                    key = (event.get("source_url") or "").strip().lower()
                    if not key:
                        title = (event.get("title") or "").strip().lower()
                        published = (event.get("published_at") or "")[:10]
                        key = f"{title}|{published}"
                    if key in seen:
                        continue
                    seen.add(key)
                    deduped.append(event)
                news_events = deduped[:6]
            event_summary = event_service.get_event_summary(ticker)
        except Exception as e:
            logger.debug(f"Failed to load FI news events for {ticker}: {e}")

        allow_on_demand_news = settings.FI_NEWS_ON_DEMAND and self._can_fetch_external()

        # On-demand refresh if no events found
        if not news_events and allow_on_demand_news:
            try:
                from app.services.fi_event_service import get_fi_event_service
                event_service = get_fi_event_service()
                event_service.ingest_nasdaq_company_news_for_ticker(ticker, analyze_new=True, limit=6)
                event_service.ingest_ir_headlines_for_ticker(ticker, limit=5, analyze_new=True)
                # Fallback to yfinance news if still empty
                event_service.ingest_yfinance_news_for_ticker(ticker, limit=6)
                news_events = event_service.get_events(ticker=ticker, limit=6, include_analysis=True)
                event_summary = event_service.get_event_summary(ticker)
            except Exception as e:
                logger.debug(f"Failed to refresh FI news events for {ticker}: {e}")

        news_page_url = get_nasdaq_news_url(ticker)

        # Compute metrics and score (now includes news sentiment)
        metrics = self.compute_metrics(history) if history else {}
        score_data = self.compute_score(metrics, fundamentals, news_summary=event_summary)

        fundamental_insight = None
        try:
            from app.services.fi_insight_service import get_fi_insight_service
            insight_service = get_fi_insight_service()
            fundamental_insight = insight_service.get_latest_insight(ticker, insight_type="FUNDAMENTALS")
        except Exception as e:
            logger.debug(f"Failed to load FI fundamental insight for {ticker}: {e}")

        sector_benchmarks = self.get_sector_benchmarks(ticker, fundamentals, stock_info)

        rank_position = None
        rank_total = None
        try:
            rankings = self.get_rankings(limit=500)
            rank_total = len(rankings)
            normalized = ticker.upper()
            for idx, item in enumerate(rankings):
                if (item.get("ticker") or "").upper() == normalized:
                    rank_position = idx + 1
                    break
        except Exception as e:
            logger.debug(f"Failed to compute rank for {ticker}: {e}")

        return {
            "ticker": ticker,
            "name": (fundamentals.get("name") if fundamentals else None) or
                    (stock_info.get("name") if stock_info else ticker.replace(".HE", "")),
            "sector": (fundamentals.get("sector") if fundamentals else None) or
                      (stock_info.get("sector") if stock_info else "Unknown"),
            "exchange": "Nasdaq Helsinki",
            "currency": "EUR",
            "quote": quote,
            "fundamentals": fundamentals,
            "metrics": metrics,
            "score": score_data["score"],
            "scoreComponents": score_data["components"],
            "riskLevel": score_data["riskLevel"],
            "explanations": score_data["explanations"],
            "newsEvents": news_events,
            "eventSummary": event_summary,
            "newsPageUrl": news_page_url,
            "irUrl": stock_info.get("ir_url") if stock_info else None,
            "irNewsUrl": stock_info.get("ir_news_url") if stock_info else None,
            "sectorBenchmarks": sector_benchmarks,
            "fundamentalInsight": fundamental_insight,
            "rankPosition": rank_position,
            "rankTotal": rank_total,
            "timestamp": datetime.now().isoformat()
        }

    def _build_rankings(self) -> List[Dict[str, Any]]:
        # Use quick data for speed
        all_data = self.get_all_quick_data()

        def safe_num(val, default=0):
            if val is None:
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        rankings = []
        for stock in all_data:
            score = 40.0
            price_value = safe_num(stock.get("price"), 0)
            if price_value <= 0:
                rankings.append({
                    **stock,
                    "score": 0,
                    "riskLevel": "HIGH"
                })
                continue

            return_3m = safe_num(stock.get("return3m"), None)
            return_12m = safe_num(stock.get("return12m"), None)

            if return_3m is not None:
                if return_3m > 0:
                    score += min(15, return_3m * 0.5)
                else:
                    score += max(-10, return_3m * 0.5)

            if return_12m is not None:
                if return_12m > 0:
                    score += min(15, return_12m * 0.3)
                else:
                    score += max(-10, return_12m * 0.33)

            volatility = safe_num(stock.get("volatility"), None)
            if volatility is not None:
                if volatility < 20:
                    score += 5
                elif volatility < 30:
                    score += 2
                elif volatility > 50:
                    score -= 8
                elif volatility > 40:
                    score -= 4

            div_yield = safe_num(stock.get("dividendYield"), 0)
            if div_yield > 0:
                score += min(8, div_yield * 1.33)

            pe = safe_num(stock.get("peRatio"), 0)
            if pe > 0:
                if pe < 10:
                    score += 10
                elif pe < 20:
                    # Scale from 10 to 5 points for PE 10-20
                    score += 10 - (pe - 10) * 0.5
                elif pe < 35:
                    # Scale from 5 to 0 points for PE 20-35
                    score += 5 - (pe - 20) * 0.33
                else:
                    # Penalty for PE > 35
                    score -= min(8, (pe - 35) * 0.2)

            # Market cap - continuous scale bonus (prefer larger, more liquid)
            mcap = safe_num(stock.get("marketCap"), 0)
            if mcap > 0:
                # Log scale: 1M = 0 points, 100M = 2 points, 1B = 3 points, 10B = 4 points
                log_mcap = math.log10(max(mcap, 1e6))
                score += min(5, max(0, (log_mcap - 6) * 1.25))

            # Today's change - small weight
            change = safe_num(stock.get("change"), 0)
            score += max(-2, min(2, change * 0.5))

            # Risk level based on beta and volatility
            beta = safe_num(stock.get("beta"), None)
            if beta is not None and volatility is not None:
                if beta < 0.8 and volatility < 30:
                    risk_level = "LOW"
                elif beta > 1.3 or volatility > 45:
                    risk_level = "HIGH"
                else:
                    risk_level = "MEDIUM"
            elif beta is not None:
                if beta < 0.8:
                    risk_level = "LOW"
                elif beta > 1.3:
                    risk_level = "HIGH"
                else:
                    risk_level = "MEDIUM"
            else:
                risk_level = "MEDIUM"

            # Align risk level with the same scoring logic used in full analysis when possible
            try:
                quick_metrics = {
                    "return3m": stock.get("return3m"),
                    "return12m": stock.get("return12m"),
                    "volatility": stock.get("volatility"),
                    "maxDrawdown": stock.get("maxDrawdown"),
                }
                quick_fundamentals = {
                    "peRatio": stock.get("peRatio"),
                    "profitMargins": stock.get("profitMargins"),
                    "revenueGrowth": stock.get("revenueGrowth"),
                    "returnOnEquity": stock.get("returnOnEquity"),
                    "debtToEquity": stock.get("debtToEquity"),
                    "beta": stock.get("beta"),
                }
                risk_level = self.compute_score(quick_metrics, quick_fundamentals).get("riskLevel", risk_level)
            except Exception:
                pass

            rankings.append({
                **stock,
                "score": round(min(100, max(0, score)), 1),
                "riskLevel": risk_level
            })

        # Sort by score (ensure it's a number)
        rankings.sort(key=lambda x: float(x.get("score", 0) or 0), reverse=True)

        def _sanitize_value(value):
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                return None
            return value

        def _sanitize_stock(stock):
            return {k: _sanitize_value(v) for k, v in stock.items()}

        rankings = [_sanitize_stock(s) for s in rankings]

        return rankings

    def get_rankings(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get top-ranked Finnish stocks - uses quick data for speed"""
        cache_key = "fi:rankings"
        stale_key = "fi:rankings:stale"
        lock_key = "fi:rankings:lock"

        def _sanitize(items):
            def _sanitize_value(value):
                if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                    return None
                return value

            return [{k: _sanitize_value(v) for k, v in stock.items()} for stock in items]

        cached = self._get_cached_json(cache_key, local_ttl=CACHE_TTL_RANKINGS)
        if cached is not None:
            return _sanitize(cached)[:limit]

        stale = self._get_cached_json(stale_key, local_ttl=CACHE_TTL_RANKINGS_STALE)
        if stale is not None:
            if self._try_acquire_lock(lock_key, 180):
                self._refresh_cache_in_background(
                    self._build_rankings,
                    cache_key,
                    stale_key,
                    CACHE_TTL_RANKINGS,
                    CACHE_TTL_RANKINGS_STALE,
                    lock_key
                )
            return _sanitize(stale)[:limit]

        if self._try_acquire_lock(lock_key, 300):
            try:
                rankings = self._build_rankings()
                self._set_cached_json(cache_key, rankings, CACHE_TTL_RANKINGS, local_ttl=CACHE_TTL_RANKINGS)
                self._set_cached_json(stale_key, rankings, CACHE_TTL_RANKINGS_STALE, local_ttl=CACHE_TTL_RANKINGS_STALE)
                return rankings[:limit]
            finally:
                self._release_lock(lock_key)

        waited = self._wait_for_cache(cache_key, stale_key, wait_seconds=6, local_ttl=CACHE_TTL_RANKINGS)
        if waited is not None:
            return _sanitize(waited)[:limit]
        return []

    def get_potential_picks(self, timeframe: str = "short", limit: int = 10) -> Dict[str, Any]:
        """
        Get stocks with highest potential based on timeframe.

        Timeframes:
        - short: Days to weeks (momentum, news, volume)
        - medium: Weeks to months (growth, value catalyst, sector momentum)
        - long: Months to years (undervaluation, quality, dividend growth)
        """
        cache_key = f"fi:potential:{timeframe}"
        stale_key = f"{cache_key}:stale"

        cached = self._get_cached_json(cache_key, local_ttl=1800)  # 30 min cache
        if cached is not None:
            return {
                "timeframe": timeframe,
                "stocks": cached[:limit],
                "total": len(cached)
            }

        all_data = self.get_all_quick_data()

        def safe_num(val, default=None):
            if val is None:
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        potential_stocks = []

        for stock in all_data:
            price = safe_num(stock.get("price"), 0)
            if price <= 0:
                continue

            ticker = stock.get("ticker", "")
            potential_score = 0.0
            reasons = []

            # Get metrics
            return_3m = safe_num(stock.get("return3m"))
            return_12m = safe_num(stock.get("return12m"))
            volatility = safe_num(stock.get("volatility"))
            pe = safe_num(stock.get("peRatio"))
            pb = safe_num(stock.get("pbRatio"))
            div_yield = safe_num(stock.get("dividendYield"), 0)
            roe = safe_num(stock.get("returnOnEquity"))
            revenue_growth = safe_num(stock.get("revenueGrowth"))
            profit_margins = safe_num(stock.get("profitMargins"))
            debt_equity = safe_num(stock.get("debtToEquity"))
            beta = safe_num(stock.get("beta"))
            mcap = safe_num(stock.get("marketCap"), 0)
            change = safe_num(stock.get("change"), 0)

            if timeframe == "short":
                # SHORT-TERM: Momentum + Recent performance + Volume signals

                # Strong recent momentum (60% weight)
                if return_3m is not None:
                    if return_3m > 15:
                        potential_score += 25
                        reasons.append("Vahva 3kk momentum (+15%)")
                    elif return_3m > 5:
                        potential_score += 15
                        reasons.append("Positiivinen 3kk momentum")
                    elif return_3m < -15:
                        potential_score -= 15

                # Today's momentum
                if change > 3:
                    potential_score += 10
                    reasons.append(f"Tänään +{change:.1f}%")
                elif change > 1:
                    potential_score += 5

                # Reversal potential (oversold bounce)
                if return_3m is not None and return_3m < -20 and return_12m is not None and return_12m > -10:
                    potential_score += 15
                    reasons.append("Ylimyyty, käännepotentiaali")

                # Low volatility = safer short-term (15% weight)
                if volatility is not None and volatility < 25:
                    potential_score += 8
                    reasons.append("Matala volatiliteetti")

                # Reasonable valuation helps
                if pe is not None and 5 < pe < 20:
                    potential_score += 5

                # Market cap liquidity
                if mcap > 500_000_000:
                    potential_score += 5

            elif timeframe == "medium":
                # MEDIUM-TERM: Growth + Value catalyst + Sector momentum

                # Growth indicators (40% weight)
                if revenue_growth is not None and revenue_growth > 0.1:
                    potential_score += 20
                    reasons.append(f"Liikevaihdon kasvu +{revenue_growth*100:.0f}%")
                elif revenue_growth is not None and revenue_growth > 0.05:
                    potential_score += 10
                    reasons.append("Maltillinen kasvu")

                if roe is not None and roe > 0.15:
                    potential_score += 15
                    reasons.append(f"Korkea ROE {roe*100:.0f}%")
                elif roe is not None and roe > 0.10:
                    potential_score += 8

                # Value with catalyst (35% weight)
                if pe is not None and pe > 0:
                    if pe < 12:
                        potential_score += 15
                        reasons.append(f"Edullinen P/E {pe:.1f}")
                    elif pe < 18:
                        potential_score += 8

                if pb is not None and pb < 1.5:
                    potential_score += 10
                    reasons.append(f"Alhainen P/B {pb:.2f}")

                # Momentum confirmation (25% weight)
                if return_3m is not None and return_3m > 0:
                    potential_score += min(10, return_3m * 0.5)
                if return_12m is not None and return_12m > 10:
                    potential_score += 8
                    reasons.append("Positiivinen 12kk trendi")

                # Profitability
                if profit_margins is not None and profit_margins > 0.1:
                    potential_score += 5

            else:  # long
                # LONG-TERM: Deep value + Quality + Dividend growth

                # Deep value (45% weight)
                if pe is not None and pe > 0:
                    if pe < 10:
                        potential_score += 25
                        reasons.append(f"Merkittävä aliarvostus P/E {pe:.1f}")
                    elif pe < 15:
                        potential_score += 15
                        reasons.append(f"Kohtuullinen P/E {pe:.1f}")

                if pb is not None:
                    if pb < 1.0:
                        potential_score += 15
                        reasons.append(f"Alle tasearvon P/B {pb:.2f}")
                    elif pb < 1.5:
                        potential_score += 8

                # Quality metrics (35% weight)
                if roe is not None and roe > 0.12:
                    potential_score += 12
                    reasons.append(f"Vahva kannattavuus ROE {roe*100:.0f}%")

                if debt_equity is not None and debt_equity < 50:
                    potential_score += 10
                    reasons.append("Matala velkaantuminen")
                elif debt_equity is not None and debt_equity > 150:
                    potential_score -= 10

                if profit_margins is not None and profit_margins > 0.1:
                    potential_score += 8

                # Dividend potential (20% weight)
                if div_yield > 4:
                    potential_score += 12
                    reasons.append(f"Korkea osinko {div_yield:.1f}%")
                elif div_yield > 2:
                    potential_score += 6
                    reasons.append(f"Vakaa osinko {div_yield:.1f}%")

                # Stable beta for long-term
                if beta is not None and beta < 1.0:
                    potential_score += 5

                # Long-term track record
                if return_12m is not None and return_12m > 0:
                    potential_score += 5

            # Only include stocks with meaningful potential
            if potential_score > 15:
                potential_stocks.append({
                    "ticker": ticker,
                    "name": stock.get("name", ticker),
                    "sector": stock.get("sector", ""),
                    "price": price,
                    "change": change,
                    "potentialScore": round(potential_score, 1),
                    "reasons": reasons[:4],  # Top 4 reasons
                    "peRatio": pe,
                    "pbRatio": pb,
                    "dividendYield": div_yield,
                    "return3m": return_3m,
                    "return12m": return_12m,
                    "roe": roe,
                    "revenueGrowth": revenue_growth,
                    "riskLevel": stock.get("riskLevel", "MEDIUM")
                })

        # Sort by potential score
        potential_stocks.sort(key=lambda x: x["potentialScore"], reverse=True)

        # Cache result
        self._set_cached_json(cache_key, potential_stocks, 1800, local_ttl=1800)
        self._set_cached_json(stale_key, potential_stocks, 7200, local_ttl=7200)

        return {
            "timeframe": timeframe,
            "stocks": potential_stocks[:limit],
            "total": len(potential_stocks)
        }

    def _build_movers(self) -> Dict[str, List[Dict[str, Any]]]:
        tickers = self.get_all_tickers()
        movers = []
        import time

        for i, ticker in enumerate(tickers):
            try:
                quote = self.get_quote(ticker)
                if quote and quote.get("price") and quote.get("price") > 0:
                    stock_info = self.get_stock_info(ticker)
                    change_pct = quote.get("changePercent", 0) or 0
                    movers.append({
                        "ticker": ticker,
                        "name": stock_info.get("name") if stock_info else ticker,
                        "price": quote.get("price", 0),
                        "change": quote.get("change", 0),
                        "changePercent": change_pct
                    })
                if (i + 1) % 5 == 0:
                    time.sleep(0.5)
            except Exception as e:
                logger.debug(f"Failed to get quote for {ticker}: {e}")
                continue

        movers.sort(key=lambda x: x["changePercent"], reverse=True)
        return {
            "gainers": movers,
            "losers": movers[::-1]
        }

    def get_movers(self, limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """Get top gainers and losers for Finnish stocks"""
        cache_key = "fi:movers"
        stale_key = "fi:movers:stale"
        lock_key = "fi:movers:lock"

        def _slice(result):
            if not result:
                return {"gainers": [], "losers": []}
            return {
                "gainers": (result.get("gainers") or [])[:limit],
                "losers": (result.get("losers") or [])[:limit]
            }

        cached = self._get_cached_json(cache_key, local_ttl=CACHE_TTL_MOVERS)
        if cached is not None:
            return _slice(cached)

        stale = self._get_cached_json(stale_key, local_ttl=CACHE_TTL_MOVERS_STALE)
        if stale is not None:
            if self._try_acquire_lock(lock_key, 180):
                self._refresh_cache_in_background(
                    self._build_movers,
                    cache_key,
                    stale_key,
                    CACHE_TTL_MOVERS,
                    CACHE_TTL_MOVERS_STALE,
                    lock_key
                )
            return _slice(stale)

        if self._try_acquire_lock(lock_key, 300):
            try:
                result = self._build_movers()
                self._set_cached_json(cache_key, result, CACHE_TTL_MOVERS, local_ttl=CACHE_TTL_MOVERS)
                self._set_cached_json(stale_key, result, CACHE_TTL_MOVERS_STALE, local_ttl=CACHE_TTL_MOVERS_STALE)
                return _slice(result)
            finally:
                self._release_lock(lock_key)

        waited = self._wait_for_cache(cache_key, stale_key, wait_seconds=6, local_ttl=CACHE_TTL_MOVERS)
        if waited is not None:
            return _slice(waited)
        return {"gainers": [], "losers": []}

    def get_sectors_summary(self) -> List[Dict[str, Any]]:
        """Get summary of stocks by sector"""
        sectors = self._tickers_data.get("sectors", {})
        return [
            {"sector": sector, "count": count}
            for sector, count in sorted(sectors.items(), key=lambda x: -x[1])
        ]

    def get_quick_stock_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get quick stock data (quote + basic fundamentals + returns) - faster than full analysis"""
        cache_key = self._get_cache_key("quick", ticker)

        # Check cache
        if self.redis_cache and self.redis_cache.is_connected():
            try:
                cached = self.redis_cache.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except:
                pass

        stock_info = self.get_stock_info(ticker)
        quote = self.get_quote(ticker)
        
        # If quote is missing, we use defaults but CONTINUE to get fundamentals
        if not quote:
            quote = {
                "price": 0,
                "change": 0,
                "changePercent": 0
            }

        # Try to get fundamentals from cache only (don't fetch if not cached)
        fundamentals = None
        if self.redis_cache and self.redis_cache.is_connected():
            try:
                # First try direct fundamentals cache
                fund_cache_key = self._get_cache_key("fundamentals", ticker)
                cached_fund = self.redis_cache.redis_client.get(fund_cache_key)
                if cached_fund:
                    fundamentals = json.loads(cached_fund)
                else:
                    # Fall back to analysis cache which contains fundamentals
                    analysis_cache_key = self._get_cache_key("analysis", ticker)
                    cached_analysis = self.redis_cache.redis_client.get(analysis_cache_key)
                    if cached_analysis:
                        analysis_data = json.loads(cached_analysis)
                        fundamentals = analysis_data.get("fundamentals")
            except:
                pass

        # If not in cache, try to fetch (if allowed) - FIX for missing P/E and P/B
        if not fundamentals and self._can_fetch_external():
            fundamentals = self.get_fundamentals(ticker)

        # Try to get history from cache to compute returns/volatility (don't fetch if not cached)
        # Check 2y history first (for 12m returns), then fall back to 1y
        # Also check stale keys which have longer TTL (7 days)
        return_3m = None
        return_12m = None
        volatility = None
        max_drawdown = None
        history_data = None
        try:
            # Try 2y first, then 1y - check both main and stale cache
            for range_key in ["2y:1d", "1y:1d"]:
                history_cache_key = self._get_cache_key(f"history:{range_key}", ticker)
                history_stale_key = f"{history_cache_key}:stale"
                # Use _get_cached_json which checks local cache first, then Redis
                history_data = self._get_cached_json(history_cache_key, local_ttl=CACHE_TTL_HISTORY)
                if not history_data:
                    # Fall back to stale cache (longer TTL)
                    history_data = self._get_cached_json(history_stale_key, local_ttl=CACHE_TTL_HISTORY_STALE)
                if history_data:
                    break

            if history_data and len(history_data) >= 20:
                metrics = self.compute_metrics(history_data)
                return_3m = metrics.get("return3m")
                return_12m = metrics.get("return12m")
                volatility = metrics.get("volatility")
                max_drawdown = metrics.get("maxDrawdown")
        except Exception as e:
            logger.debug(f"Failed to compute returns from cache for {ticker}: {e}")

        # Get dividend yield - yfinance returns it as decimal (0.0176 = 1.76%)
        div_yield = 0
        if fundamentals:
            raw_div = fundamentals.get("dividendYield", 0) or 0
            raw_div = self._safe_float(raw_div) or 0
            # Convert to percentage - yfinance returns as decimal (0.0176 for 1.76%)
            # If value > 1, it's already a percentage, don't multiply
            if raw_div > 0:
                div_yield = raw_div * 100 if raw_div < 1 else raw_div
                # Cap at 20% - higher values are likely data errors
                if div_yield > 20:
                    div_yield = 0  # Treat as missing data

        price_value = self._safe_float(quote.get("price")) or 0
        change_pct = self._safe_float(quote.get("changePercent")) or 0
        pe_ratio = self._safe_float(fundamentals.get("peRatio") if fundamentals else None)
        pb_ratio = self._safe_float(fundamentals.get("priceToBook") if fundamentals else None)
        market_cap = self._safe_float(fundamentals.get("marketCap") if fundamentals else None) or 0
        beta = self._safe_float(fundamentals.get("beta") if fundamentals else None)
        profit_margin = self._safe_float(fundamentals.get("profitMargins") if fundamentals else None)
        revenue_growth = self._safe_float(fundamentals.get("revenueGrowth") if fundamentals else None)
        roe = self._safe_float(fundamentals.get("returnOnEquity") if fundamentals else None)
        debt_to_equity = self._safe_float(fundamentals.get("debtToEquity") if fundamentals else None)

        # Calculate dividend amount in EUR (annual dividend per share)
        dividend_amount = None
        if div_yield > 0 and price_value > 0:
            dividend_amount = round(price_value * div_yield / 100, 2)

        result = {
            "ticker": ticker,
            "name": stock_info.get("name") if stock_info else ticker,
            "sector": stock_info.get("sector") if stock_info else "Unknown",
            "market": stock_info.get("market", "Main") if stock_info else "Main",
            "price": price_value,
            "change": change_pct,
            "peRatio": pe_ratio,
            "pbRatio": pb_ratio,
            "dividendYield": round(div_yield, 2) if div_yield else 0,
            "dividendAmount": dividend_amount,
            "marketCap": market_cap,
            "beta": beta,
            "profitMargins": profit_margin,
            "revenueGrowth": revenue_growth,
            "returnOnEquity": roe,
            "debtToEquity": debt_to_equity,
            "return3m": self._safe_float(return_3m),
            "return12m": self._safe_float(return_12m),
            "volatility": self._safe_float(volatility),
            "maxDrawdown": self._safe_float(max_drawdown),
        }

        # Cache for 2 minutes
        if self.redis_cache and self.redis_cache.is_connected():
            try:
                self.redis_cache.redis_client.setex(cache_key, 120, json.dumps(result))
            except:
                pass

        return result

    def _build_all_quick_data(self) -> List[Dict[str, Any]]:
        tickers = self.get_all_tickers()
        results = []
        import time

        for i, ticker in enumerate(tickers):
            try:
                data = self.get_quick_stock_data(ticker)
                if data:
                    results.append(data)
                if (i + 1) % 5 == 0:
                    time.sleep(0.3)
            except Exception as e:
                logger.debug(f"Failed to get quick data for {ticker}: {e}")
                continue

        return results

    def get_all_quick_data(self) -> List[Dict[str, Any]]:
        """Get quick data for ALL stocks - uses batch caching with stampede protection"""
        cache_key = "fi:all_quick_data"
        stale_key = "fi:all_quick_data:stale"
        lock_key = "fi:all_quick_data:lock"

        cached = self._get_cached_json(cache_key, local_ttl=CACHE_TTL_QUICK_DATA)
        if cached is not None:
            return cached

        stale = self._get_cached_json(stale_key, local_ttl=CACHE_TTL_QUICK_DATA_STALE)
        if stale is not None:
            if self._try_acquire_lock(lock_key, 300):
                self._refresh_cache_in_background(
                    self._build_all_quick_data,
                    cache_key,
                    stale_key,
                    CACHE_TTL_QUICK_DATA,
                    CACHE_TTL_QUICK_DATA_STALE,
                    lock_key
                )
            return stale

        if self._try_acquire_lock(lock_key, 900):
            try:
                results = self._build_all_quick_data()
                self._set_cached_json(cache_key, results, CACHE_TTL_QUICK_DATA, local_ttl=CACHE_TTL_QUICK_DATA)
                self._set_cached_json(stale_key, results, CACHE_TTL_QUICK_DATA_STALE, local_ttl=CACHE_TTL_QUICK_DATA_STALE)
                return results
            finally:
                self._release_lock(lock_key)

        waited = self._wait_for_cache(cache_key, stale_key, wait_seconds=8, local_ttl=CACHE_TTL_QUICK_DATA)
        if waited is not None:
            return waited
        return []

    def screen_stocks(
        self,
        filters: Dict[str, Any],
        sort_by: str = "score",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Screen stocks by multiple criteria - uses rankings for scores
        """
        cache_key = f"fi:screener:{hash(str(sorted(filters.items())))}:{sort_by}:{sort_order}"

        # Check cache
        if self.redis_cache and self.redis_cache.is_connected():
            try:
                cached = self.redis_cache.redis_client.get(cache_key)
                if cached:
                    data = json.loads(cached)

                    def _sanitize_value(value):
                        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                            return None
                        return value

                    def _sanitize_stock(stock):
                        return {k: _sanitize_value(v) for k, v in stock.items()}

                    stocks = [_sanitize_stock(s) for s in data.get("stocks", [])]
                    return {
                        "total": data.get("total", 0),
                        "stocks": stocks[offset:offset + limit]
                    }
            except:
                pass

        # Use rankings which already has scores and riskLevel
        all_stocks = self.get_rankings(200)

        # Apply filters
        filtered = all_stocks
        for key, value in filters.items():
            if key == "sector" and value:
                filtered = [s for s in filtered if s.get("sector", "").lower() == value.lower()]
            elif key == "market" and value:
                filtered = [s for s in filtered if s.get("market", "").lower() == value.lower()]
            elif key == "min_dividend_yield" and value is not None:
                filtered = [s for s in filtered if (s.get("dividendYield") or 0) >= value]
            elif key == "max_pe" and value is not None:
                filtered = [s for s in filtered if s.get("peRatio") and 0 < s.get("peRatio") <= value]
            elif key == "min_pe" and value is not None:
                filtered = [s for s in filtered if s.get("peRatio") and s.get("peRatio") >= value]
            elif key == "min_market_cap" and value is not None:
                filtered = [s for s in filtered if (s.get("marketCap") or 0) >= value]
            elif key == "max_volatility" and value is not None:
                # Volatility filter - use beta as proxy (beta > 1.5 = high volatility)
                filtered = [s for s in filtered if s.get("beta") and s.get("beta") <= value / 20]
            elif key == "min_return_12m" and value is not None:
                filtered = [s for s in filtered if s.get("return12m") and s.get("return12m") >= value]
            elif key == "min_return_3m" and value is not None:
                filtered = [s for s in filtered if s.get("return3m") and s.get("return3m") >= value]
            elif key == "risk_level" and value:
                filtered = [s for s in filtered if s.get("riskLevel", "").upper() == value.upper()]

        # Sort
        sort_key_map = {
            "score": "score",
            "dividend_yield": "dividendYield",
            "dividend_amount": "dividendAmount",
            "pe": "peRatio",
            "pb": "pbRatio",
            "market_cap": "marketCap",
            "change": "change",
            "return_3m": "return3m",
            "return_12m": "return12m",
            "volatility": "volatility",
            "beta": "beta",
            "roe": "returnOnEquity",
        }
        sort_field = sort_key_map.get(sort_by, "score")
        reverse = sort_order == "desc"

        # For P/E and volatility, lower is usually better when sorted "desc"
        if sort_by in ["pe", "volatility"] and sort_order == "desc":
            reverse = False

        def safe_num(val, default=0):
            if val is None:
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        def sort_key(x):
            val = safe_num(x.get(sort_field), None)
            if val is None:
                return float('-inf') if reverse else float('inf')
            return val

        filtered.sort(key=sort_key, reverse=reverse)

        def _sanitize_value(value):
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                return None
            return value

        def _sanitize_stock(stock):
            return {k: _sanitize_value(v) for k, v in stock.items()}

        filtered = [_sanitize_stock(s) for s in filtered]

        total = len(filtered)

        # Cache for 5 minutes
        if self.redis_cache and self.redis_cache.is_connected():
            try:
                self.redis_cache.redis_client.setex(
                    cache_key, 300, json.dumps({"total": total, "stocks": filtered})
                )
            except:
                pass

        return {
            "total": total,
            "stocks": filtered[offset:offset + limit]
        }


    def get_weekly_momentum(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get weekly momentum data for Finnish stocks.

        Returns:
        - Weekly gainers (best 5-day performers)
        - Weekly losers (worst 5-day performers)
        - Unusual volume (stocks with volume > 2x average)
        - RSI signals (overbought/oversold stocks)
        """
        cache_key = "fi:weekly_momentum"
        stale_key = "fi:weekly_momentum:stale"
        lock_key = "fi:weekly_momentum:lock"

        def _slice(result):
            if not result:
                return {
                    "weekly_gainers": [],
                    "weekly_losers": [],
                    "unusual_volume": [],
                    "overbought": [],
                    "oversold": [],
                    "updated_at": None
                }
            return {
                "weekly_gainers": (result.get("weekly_gainers") or [])[:limit],
                "weekly_losers": (result.get("weekly_losers") or [])[:limit],
                "unusual_volume": (result.get("unusual_volume") or [])[:limit],
                "overbought": (result.get("overbought") or [])[:5],
                "oversold": (result.get("oversold") or [])[:5],
                "updated_at": result.get("updated_at")
            }

        cached = self._get_cached_json(cache_key, local_ttl=CACHE_TTL_MOMENTUM)
        if cached is not None:
            return _slice(cached)

        stale = self._get_cached_json(stale_key, local_ttl=CACHE_TTL_MOMENTUM_STALE)
        if stale is not None:
            if self._try_acquire_lock(lock_key, 300):
                self._refresh_cache_in_background(
                    self._build_weekly_momentum,
                    cache_key,
                    stale_key,
                    CACHE_TTL_MOMENTUM,
                    CACHE_TTL_MOMENTUM_STALE,
                    lock_key
                )
            return _slice(stale)

        if self._try_acquire_lock(lock_key, 600):
            try:
                result = self._build_weekly_momentum()
                self._set_cached_json(cache_key, result, CACHE_TTL_MOMENTUM, local_ttl=CACHE_TTL_MOMENTUM)
                self._set_cached_json(stale_key, result, CACHE_TTL_MOMENTUM_STALE, local_ttl=CACHE_TTL_MOMENTUM_STALE)
                return _slice(result)
            finally:
                self._release_lock(lock_key)

        waited = self._wait_for_cache(cache_key, stale_key, wait_seconds=10, local_ttl=CACHE_TTL_MOMENTUM)
        if waited is not None:
            return _slice(waited)

        return {
            "weekly_gainers": [],
            "weekly_losers": [],
            "unusual_volume": [],
            "overbought": [],
            "oversold": [],
            "updated_at": None
        }

    def _build_weekly_momentum(self) -> Dict[str, Any]:
        """Build weekly momentum data for all Finnish stocks"""
        from datetime import datetime
        import time

        tickers = self.get_all_tickers()
        weekly_data = []
        unusual_volume = []
        overbought = []
        oversold = []

        # Allow external fetch for momentum build (needed when FI_CACHE_ONLY=True)
        with self._external_fetch_allowed():
            for i, ticker in enumerate(tickers):
                try:
                    # Get 3 months of daily history (enough for RSI 14 + volume analysis)
                    # Using single API call per stock to avoid rate limits
                    history = self.get_history(ticker, range="3mo", interval="1d")
                    if not history or len(history) < 15:
                        continue

                    stock_info = self.get_stock_info(ticker)
                    name = stock_info.get("name") if stock_info else ticker

                    # Calculate weekly return (5 trading days)
                    current_price = history[-1].get("close", 0)
                    week_ago_price = history[-6].get("close", 0) if len(history) >= 6 else history[0].get("close", 0)

                    if week_ago_price and week_ago_price > 0:
                        weekly_return = ((current_price - week_ago_price) / week_ago_price) * 100
                    else:
                        weekly_return = 0

                    # Calculate average volume and current volume
                    volumes = [h.get("volume", 0) for h in history if h.get("volume")]
                    avg_volume = sum(volumes[:-1]) / len(volumes[:-1]) if len(volumes) > 1 else 0
                    current_volume = history[-1].get("volume", 0)
                    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0

                    # Calculate RSI 14 (standard 14-period RSI on daily data)
                    # Using 3 months of data for more stable calculation
                    rsi = None
                    if len(history) >= 15:
                        closes = pd.Series([h.get("close", 0) for h in history])
                        delta = closes.diff()
                        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss
                        rsi_series = 100 - (100 / (1 + rs))
                        rsi = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else None

                    stock_data = {
                        "ticker": ticker,
                        "name": name,
                        "price": round(current_price, 2),
                        "weeklyReturn": round(weekly_return, 2),
                        "volume": current_volume,
                        "avgVolume": int(avg_volume),
                        "volumeRatio": round(volume_ratio, 2),
                        "rsi": round(rsi, 1) if rsi else None
                    }

                    weekly_data.append(stock_data)

                    # Check for unusual volume (> 2x average)
                    if volume_ratio >= 2.0:
                        unusual_volume.append(stock_data)

                    # Check for RSI signals
                    if rsi:
                        if rsi >= 70:
                            overbought.append(stock_data)
                        elif rsi <= 30:
                            oversold.append(stock_data)

                    # Rate limiting
                    if (i + 1) % 10 == 0:
                        time.sleep(0.3)

                except Exception as e:
                    logger.debug(f"Failed to get momentum for {ticker}: {e}")
                    continue

        # Sort by weekly return
        weekly_data.sort(key=lambda x: x["weeklyReturn"], reverse=True)
        unusual_volume.sort(key=lambda x: x["volumeRatio"], reverse=True)
        overbought.sort(key=lambda x: x.get("rsi", 0), reverse=True)
        oversold.sort(key=lambda x: x.get("rsi", 100))

        return {
            "weekly_gainers": weekly_data,
            "weekly_losers": weekly_data[::-1],
            "unusual_volume": unusual_volume,
            "overbought": overbought,
            "oversold": oversold,
            "updated_at": datetime.utcnow().isoformat()
        }


# Singleton instance
_fi_data_service = None


def get_fi_data_service() -> FiDataService:
    """Get singleton instance of FiDataService"""
    global _fi_data_service
    if _fi_data_service is None:
        _fi_data_service = FiDataService()
    return _fi_data_service
