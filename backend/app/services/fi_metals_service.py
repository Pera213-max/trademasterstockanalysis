"""
Precious Metals Service
=======================

Provides data for gold and silver:
- Real-time prices
- Historical data for charts
- Key metrics (52w high/low, changes, etc.)
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

from database.redis.config import get_redis_cache
from app.config.settings import settings

logger = logging.getLogger(__name__)

CACHE_TTL_QUOTE = 300  # 5 minutes for quotes
CACHE_TTL_HISTORY = 3600  # 1 hour for history
CACHE_TTL_STALE = 86400  # 24 hours stale fallback

# Precious metals configuration
METALS = [
    {
        "symbol": "GC=F",
        "code": "GOLD",
        "name": "Kulta",
        "name_en": "Gold",
        "unit": "USD/oz",
        "description": "Kullan spot-hinta (COMEX futuurit)",
    },
    {
        "symbol": "SI=F",
        "code": "SILVER",
        "name": "Hopea",
        "name_en": "Silver",
        "unit": "USD/oz",
        "description": "Hopean spot-hinta (COMEX futuurit)",
    },
]


class FiMetalsService:
    """Service for precious metals data (gold, silver)"""

    def __init__(self):
        self.redis_cache = get_redis_cache()
        self._yfinance = None

    @property
    def yfinance(self):
        if self._yfinance is None:
            from app.services.yfinance_service import get_yfinance_service
            self._yfinance = get_yfinance_service()
        return self._yfinance

    def _get_cache(self, key: str) -> Optional[Any]:
        if self.redis_cache and self.redis_cache.is_connected():
            try:
                cached = self.redis_cache.redis_client.get(key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.debug(f"Cache read error for {key}: {e}")
        return None

    def _set_cache(self, key: str, data: Any, ttl: int):
        if self.redis_cache and self.redis_cache.is_connected():
            try:
                self.redis_cache.redis_client.setex(key, ttl, json.dumps(data))
            except Exception as e:
                logger.debug(f"Cache write error for {key}: {e}")

    def get_metals_overview(self) -> Dict[str, Any]:
        """Get overview of all precious metals with current prices."""
        cache_key = "fi:metals:overview"
        stale_key = "fi:metals:overview:stale"

        # Check cache
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        # Fetch fresh data
        metals_data = []
        for metal in METALS:
            try:
                quote = self._fetch_metal_quote(metal["symbol"])
                if quote:
                    metals_data.append({
                        **metal,
                        **quote,
                    })
            except Exception as e:
                logger.warning(f"Failed to fetch {metal['code']}: {e}")

        if not metals_data:
            # Try stale cache
            stale = self._get_cache(stale_key)
            if stale:
                logger.info("Using stale metals cache")
                return stale
            return {"metals": [], "timestamp": datetime.utcnow().isoformat()}

        result = {
            "metals": metals_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Cache results
        self._set_cache(cache_key, result, CACHE_TTL_QUOTE)
        self._set_cache(stale_key, result, CACHE_TTL_STALE)

        return result

    def get_metal_detail(self, code: str) -> Optional[Dict[str, Any]]:
        """Get detailed data for a specific metal including history."""
        code = code.upper()
        metal_config = next((m for m in METALS if m["code"] == code), None)
        if not metal_config:
            return None

        cache_key = f"fi:metals:detail:{code}"
        stale_key = f"fi:metals:detail:{code}:stale"

        # Check cache
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        # Fetch quote
        quote = self._fetch_metal_quote(metal_config["symbol"])
        if not quote:
            stale = self._get_cache(stale_key)
            if stale:
                return stale
            return None

        # Fetch history for charts
        history = self._fetch_metal_history(metal_config["symbol"], period="1y")

        result = {
            **metal_config,
            **quote,
            "history": history,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Cache results
        self._set_cache(cache_key, result, CACHE_TTL_QUOTE)
        self._set_cache(stale_key, result, CACHE_TTL_STALE)

        return result

    def get_metal_history(
        self, code: str, period: str = "1y", interval: str = "1d"
    ) -> Optional[List[Dict[str, Any]]]:
        """Get historical data for a metal."""
        code = code.upper()
        metal_config = next((m for m in METALS if m["code"] == code), None)
        if not metal_config:
            return None

        cache_key = f"fi:metals:history:{code}:{period}:{interval}"
        stale_key = f"fi:metals:history:{code}:{period}:{interval}:stale"

        # Check cache
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        # Fetch history
        history = self._fetch_metal_history(
            metal_config["symbol"], period=period, interval=interval
        )

        if not history:
            stale = self._get_cache(stale_key)
            if stale:
                return stale
            return None

        # Cache results
        self._set_cache(cache_key, history, CACHE_TTL_HISTORY)
        self._set_cache(stale_key, history, CACHE_TTL_STALE)

        return history

    def _fetch_metal_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch current quote for a metal symbol."""
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Get price from fast_info or info
            try:
                fast = ticker.fast_info
                price = getattr(fast, "last_price", None) or info.get("regularMarketPrice")
                prev_close = getattr(fast, "previous_close", None) or info.get("previousClose")
            except Exception:
                price = info.get("regularMarketPrice") or info.get("previousClose")
                prev_close = info.get("previousClose")

            if not price:
                return None

            change = (price - prev_close) if prev_close else 0
            change_pct = (change / prev_close * 100) if prev_close else 0

            return {
                "price": round(price, 2),
                "previousClose": round(prev_close, 2) if prev_close else None,
                "change": round(change, 2),
                "changePercent": round(change_pct, 2),
                "high": info.get("dayHigh") or info.get("regularMarketDayHigh"),
                "low": info.get("dayLow") or info.get("regularMarketDayLow"),
                "open": info.get("open") or info.get("regularMarketOpen"),
                "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
                "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
                "fiftyDayAverage": info.get("fiftyDayAverage"),
                "twoHundredDayAverage": info.get("twoHundredDayAverage"),
                "volume": info.get("volume") or info.get("regularMarketVolume"),
            }
        except Exception as e:
            logger.warning(f"Failed to fetch quote for {symbol}: {e}")
            return None

    def _fetch_metal_history(
        self, symbol: str, period: str = "1y", interval: str = "1d"
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetch historical data for a metal symbol."""
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)

            if hist.empty:
                return None

            result = []
            for idx, row in hist.iterrows():
                date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
                result.append({
                    "date": date_str,
                    "open": round(float(row.get("Open", 0)), 2),
                    "high": round(float(row.get("High", 0)), 2),
                    "low": round(float(row.get("Low", 0)), 2),
                    "close": round(float(row.get("Close", 0)), 2),
                    "volume": int(row.get("Volume", 0)),
                })

            return result
        except Exception as e:
            logger.warning(f"Failed to fetch history for {symbol}: {e}")
            return None

    def warm_cache(self) -> Dict[str, Any]:
        """Warm the metals cache."""
        logger.info("Warming metals cache...")
        overview = self.get_metals_overview()

        # Also warm detail caches
        for metal in METALS:
            try:
                self.get_metal_detail(metal["code"])
            except Exception as e:
                logger.debug(f"Failed to warm cache for {metal['code']}: {e}")

        return {
            "success": True,
            "metals_count": len(overview.get("metals", [])),
        }


# Singleton instance
_metals_service: Optional[FiMetalsService] = None


def get_fi_metals_service() -> FiMetalsService:
    global _metals_service
    if _metals_service is None:
        _metals_service = FiMetalsService()
    return _metals_service
