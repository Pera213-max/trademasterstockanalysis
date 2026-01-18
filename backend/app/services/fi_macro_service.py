"""
Finnish Macro Indicators Service
================================

Provides macro economic indicators for Finland and the Eurozone:
- OMXH25 (Helsinki 25 index)
- EUR/USD exchange rate
- Euro Stoxx 50
- VIX (market fear index)
- ECB interest rate info
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.redis.config import get_redis_cache
from app.config.settings import settings

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutes
STALE_CACHE_TTL = 86400  # 24 hours for stale data

# Macro indicator symbols
MACRO_INDICATORS = [
    {"symbol": "^OMXH25", "code": "OMXH25", "name": "Helsinki 25", "category": "indices"},
    {"symbol": "^STOXX50E", "code": "STOXX50", "name": "Euro Stoxx 50", "category": "indices"},
    {"symbol": "^GDAXI", "code": "DAX", "name": "DAX 40", "category": "indices"},
    {"symbol": "^VIX", "code": "VIX", "name": "Volatiliteetti-indeksi", "category": "indices"},
    {"symbol": "EURUSD=X", "code": "EUR/USD", "name": "Euro / Dollari", "category": "currencies"},
    {"symbol": "EURSEK=X", "code": "EUR/SEK", "name": "Euro / Kruunu", "category": "currencies"},
    {"symbol": "GC=F", "code": "KULTA", "name": "Kulta (USD/oz)", "category": "currencies"},
    {"symbol": "BZ=F", "code": "ÖLJY", "name": "Brent-öljy (USD)", "category": "currencies"},
    {"symbol": "^TNX", "code": "US10Y", "name": "USA 10v korko", "category": "rates"},
]


class FiMacroService:
    """Service for Finnish and Eurozone macro indicators"""

    def __init__(self):
        self.redis_cache = get_redis_cache()
        self._yfinance = None

    @property
    def yfinance(self):
        if self._yfinance is None:
            from app.services.yfinance_service import get_yfinance_service
            self._yfinance = get_yfinance_service()
        return self._yfinance

    def get_macro_indicators(self, allow_external: Optional[bool] = None) -> Dict[str, Any]:
        """
        Get Finnish and Eurozone macro indicators.

        Macro indicators always try to fetch fresh data if cache is empty,
        regardless of FI_CACHE_ONLY setting (these are just a few symbols).
        """
        cache_key = "fi:macro_indicators"
        stale_key = "fi:macro_indicators:stale"

        # Check fresh cache first
        if self.redis_cache and self.redis_cache.is_connected():
            try:
                cached = self.redis_cache.redis_client.get(cache_key)
                if cached:
                    logger.debug("FI macro: cache hit")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"FI macro cache read error: {e}")

        # For macro indicators, always try to fetch if no fresh cache
        # (they're just ~10 symbols, not the full 4000+ stock universe)
        logger.info("FI macro: no fresh cache, fetching indicators...")

        # Fetch fresh data
        indicators = self._fetch_all_indicators()

        # Cache result
        if self.redis_cache and self.redis_cache.is_connected():
            try:
                data_json = json.dumps(indicators)
                self.redis_cache.redis_client.setex(cache_key, CACHE_TTL, data_json)
                self.redis_cache.redis_client.setex(stale_key, STALE_CACHE_TTL, data_json)
                logger.info(f"FI macro: cached {len(indicators['indices'])} indices, {len(indicators['currencies'])} currencies, {len(indicators['rates'])} rates")
            except Exception as e:
                logger.warning(f"FI macro cache write error: {e}")

        return indicators

    def _fetch_all_indicators(self) -> Dict[str, Any]:
        """Fetch all macro indicators from yfinance"""
        indicators = {
            "indices": [],
            "currencies": [],
            "rates": [],
            "timestamp": datetime.now().isoformat()
        }

        for indicator_config in MACRO_INDICATORS:
            try:
                indicator = self._get_indicator(
                    indicator_config["symbol"],
                    indicator_config["code"],
                    indicator_config["name"]
                )
                if indicator:
                    indicators[indicator_config["category"]].append(indicator)
                    logger.debug(f"FI macro: got {indicator_config['code']} = {indicator.get('price')}")
                else:
                    logger.warning(f"FI macro: failed to get {indicator_config['code']} ({indicator_config['symbol']})")
            except Exception as e:
                logger.warning(f"FI macro: error getting {indicator_config['code']}: {e}")

        return indicators

    def _get_indicator(self, symbol: str, code: str, name: str) -> Optional[Dict[str, Any]]:
        """Get a single indicator quote - always allows external fetch"""
        try:
            # Always allow external fetch for macro indicators
            logger.info(f"FI macro: fetching {symbol}...")
            quote = self.yfinance.get_quote(symbol, use_cache=True, allow_external=True)
            logger.info(f"FI macro: quote for {symbol} = {quote}")
            if not quote:
                logger.warning(f"FI macro: no quote returned for {symbol}")
                return None

            # yfinance returns: {'c': price, 'pc': previous_close, 'h': high, 'l': low, 'o': open, 'v': volume}
            price = quote.get("c")
            prev_close = quote.get("pc")

            if not price:
                logger.warning(f"FI macro: no price in quote for {symbol}: {quote}")
                return None

            # Calculate change and changePercent
            change = None
            change_pct = None
            if price and prev_close:
                change = round(price - prev_close, 4)
                change_pct = round((change / prev_close) * 100, 2) if prev_close else None

            return {
                "code": code,
                "name": name,
                "symbol": symbol,
                "price": price,
                "change": change,
                "changePercent": change_pct,
                "previousClose": prev_close,
            }
        except Exception as e:
            logger.warning(f"FI macro: failed to get indicator {symbol}: {e}")
            return None

    def warm_cache(self) -> Dict[str, int]:
        """
        Warm the macro indicators cache.
        Called by background scheduler to keep cache fresh.
        """
        logger.info("FI macro: warming cache...")
        try:
            indicators = self._fetch_all_indicators()

            total = (
                len(indicators.get("indices", [])) +
                len(indicators.get("currencies", [])) +
                len(indicators.get("rates", []))
            )

            # Cache result
            if self.redis_cache and self.redis_cache.is_connected():
                cache_key = "fi:macro_indicators"
                stale_key = "fi:macro_indicators:stale"
                data_json = json.dumps(indicators)
                self.redis_cache.redis_client.setex(cache_key, CACHE_TTL, data_json)
                self.redis_cache.redis_client.setex(stale_key, STALE_CACHE_TTL, data_json)

            logger.info(f"FI macro: warmed cache with {total} indicators")
            return {"success": True, "count": total}
        except Exception as e:
            logger.error(f"FI macro: cache warm failed: {e}")
            return {"success": False, "count": 0, "error": str(e)}


# Singleton
_service: Optional[FiMacroService] = None


def get_fi_macro_service() -> FiMacroService:
    global _service
    if _service is None:
        _service = FiMacroService()
    return _service
