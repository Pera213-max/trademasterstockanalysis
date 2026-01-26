"""
TradeMaster Pro - yfinance Service
===================================

Historical stock data using yfinance with RATE LIMIT PROTECTION.

IMPORTANT: This service now uses YFinanceDataManager for:
- Distributed rate limiting across workers
- Auto-recovery from rate limit errors
- Cache-first strategy for user requests
- Background pre-fetching for 4000+ stocks

Use for:
- Historical prices (candles)
- Volume data
- Basic fundamentals
"""

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
import pandas as pd
import logging
import math
import time
import sys
import importlib
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import os
import re

_DEFAULT_CACHE_DIR = os.getenv("YFINANCE_CACHE_DIR", "/tmp/py-yfinance")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")
os.environ.setdefault("YFINANCE_CACHE_DIR", _DEFAULT_CACHE_DIR)

from .delisted_registry import add_delisted_tickers

logger = logging.getLogger(__name__)

_DELISTED_HINTS = ("delisted", "no price data found", "no data found, symbol may be delisted")
_RATE_LIMIT_HINTS = ("rate limited", "too many requests")
# Extended pattern to support Finnish tickers (e.g., FORTUM.HE, STOCKA.HE)
_TICKER_PATTERN = re.compile(r"^[A-Z0-9]{1,10}(-[A-Z]{1,2})?(\.[A-Z]{1,4})?$")
# Default timeout for yfinance calls in seconds
_YFINANCE_TIMEOUT = 15


def _with_timeout(func, timeout: int = _YFINANCE_TIMEOUT, default=None):
    """Execute a function with timeout. Returns default if timeout occurs."""
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func)
            return future.result(timeout=timeout)
    except FuturesTimeoutError:
        logger.warning(f"yfinance call timed out after {timeout}s")
        return default
    except Exception as e:
        logger.debug(f"yfinance call failed: {e}")
        return default
_SPECIAL_TICKERS = {
    "^VIX",
    "^GSPC",
    "^TNX",
    "^OMXH25",
    "^STOXX50E",
    "^GDAXI",
    "DX-Y.NYB",
    "CL=F",
    "GC=F",
    "BZ=F",
    "EURUSD=X",
    "EURSEK=X",
}


def _normalize_ticker(ticker: str) -> Optional[str]:
    if not ticker:
        return None
    normalized = str(ticker).strip().upper()
    if normalized in _SPECIAL_TICKERS:
        return normalized
    if not _TICKER_PATTERN.match(normalized):
        return None
    return normalized


def _pick_positive(*values) -> float:
    for value in values:
        try:
            candidate = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(candidate) and candidate > 0:
            return candidate
    return 0.0


def _pick_number(*values) -> float:
    for value in values:
        try:
            candidate = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(candidate):
            return candidate
    return 0.0


def _resolve_allow_external(allow_external: Optional[bool]) -> bool:
    if allow_external is not None:
        return allow_external
    return os.getenv("YFINANCE_CACHE_ONLY", "false").lower() != "true"


def _historical_list_to_df(payload: Optional[List[Dict]]) -> Optional[pd.DataFrame]:
    if not payload:
        return None
    rows = []
    index = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        date_value = item.get("date") or item.get("time")
        if not date_value:
            continue
        try:
            index.append(pd.to_datetime(date_value))
        except Exception:
            continue
        rows.append({
            "Open": _pick_number(item.get("o"), item.get("open")),
            "High": _pick_number(item.get("h"), item.get("high")),
            "Low": _pick_number(item.get("l"), item.get("low")),
            "Close": _pick_number(item.get("c"), item.get("close")),
            "Volume": int(_pick_number(item.get("v"), item.get("volume"))),
        })
    if not rows:
        return None
    df = pd.DataFrame(rows, index=index)
    if df.empty:
        return None
    return df.sort_index()


def _historical_df_to_list(df: pd.DataFrame) -> List[Dict]:
    ohlcv = []
    for idx, row in df.iterrows():
        ohlcv.append({
            "date": idx.isoformat() if hasattr(idx, "isoformat") else str(idx),
            "o": _pick_number(row.get("Open", 0)),
            "h": _pick_number(row.get("High", 0)),
            "l": _pick_number(row.get("Low", 0)),
            "c": _pick_number(row.get("Close", 0)),
            "v": int(_pick_number(row.get("Volume", 0))),
        })
    return ohlcv

if HAS_YFINANCE:
    cache_dir = os.getenv("YFINANCE_CACHE_DIR", _DEFAULT_CACHE_DIR)
    try:
        os.makedirs(cache_dir, exist_ok=True)
    except Exception as exc:
        logger.warning("Unable to ensure yfinance cache dir %s: %s", cache_dir, exc)

    try:
        if hasattr(yf, "set_tz_cache_location"):
            yf.set_tz_cache_location(cache_dir)
        elif hasattr(yf, "utils") and hasattr(yf.utils, "set_tz_cache_location"):
            yf.utils.set_tz_cache_location(cache_dir)
    except Exception as exc:
        logger.warning("Failed to set yfinance cache location: %s", exc)


def _extract_delisted_tickers(errors: Dict[str, str]) -> List[str]:
    delisted = []
    for ticker, error in errors.items():
        message = str(error).lower()
        if any(hint in message for hint in _RATE_LIMIT_HINTS):
            continue
        if any(hint in message for hint in _DELISTED_HINTS):
            delisted.append(ticker)
    return delisted


class YFinanceService:
    """
    yfinance service for historical stock data with RATE LIMIT PROTECTION.

    This service:
    - Uses cache-first strategy for all data
    - Rate limits API calls to prevent 429 errors
    - Auto-recovers from rate limits with module reload
    - Queues missing data for background fetch
    """

    # Rate limiting configuration
    CALLS_PER_MINUTE = 25
    RATE_LIMIT_WINDOW = 60
    MIN_CALL_INTERVAL = 2.5
    RATE_LIMIT_COOLDOWN = 180
    MODULE_RELOAD_COOLDOWN = 120

    def __init__(self):
        # Rate limiting state
        self._call_timestamps: deque = deque(maxlen=self.CALLS_PER_MINUTE * 2)
        self._rate_limit_hit_time: Optional[float] = None
        self._last_module_reload: Optional[float] = None
        self._last_call_time: float = 0

        # Try to get data manager for caching
        self._data_manager = None
        try:
            from .yfinance_data_manager import get_yfinance_data_manager
            self._data_manager = get_yfinance_data_manager()
        except Exception as e:
            logger.warning(f"Could not initialize data manager: {e}")

        logger.info("YFinanceService initialized with rate limiting")

    def _wait_for_rate_limit(self) -> None:
        """Wait if we're approaching rate limit - PROACTIVE protection"""
        now = time.time()

        # Check cooldown from previous rate limit hit
        if self._rate_limit_hit_time:
            cooldown_remaining = self.RATE_LIMIT_COOLDOWN - (now - self._rate_limit_hit_time)
            if cooldown_remaining > 0:
                logger.info(f"Rate limit cooldown: waiting {cooldown_remaining:.1f}s...")
                time.sleep(cooldown_remaining + 1)
                self._rate_limit_hit_time = None
                self._call_timestamps.clear()

        # Check minimum interval
        time_since_last = now - self._last_call_time
        if time_since_last < self.MIN_CALL_INTERVAL:
            sleep_time = self.MIN_CALL_INTERVAL - time_since_last
            time.sleep(sleep_time)

        # Clean old timestamps
        now = time.time()
        while self._call_timestamps and (now - self._call_timestamps[0]) > self.RATE_LIMIT_WINDOW:
            self._call_timestamps.popleft()

        # Check if approaching limit
        if len(self._call_timestamps) >= self.CALLS_PER_MINUTE - 5:
            oldest = self._call_timestamps[0]
            wait_time = self.RATE_LIMIT_WINDOW - (now - oldest) + 1
            if wait_time > 0:
                logger.info(f"Approaching rate limit ({len(self._call_timestamps)}/{self.CALLS_PER_MINUTE}), waiting {wait_time:.1f}s...")
                time.sleep(wait_time)

        # Record this call
        self._call_timestamps.append(time.time())
        self._last_call_time = time.time()

    def _handle_rate_limit_error(self, error: Exception) -> bool:
        """Handle rate limit error. Returns True if this was a rate limit error."""
        error_str = str(error).lower()
        rate_indicators = ['rate', 'limit', '429', 'too many', 'exceeded', 'throttl']

        if any(ind in error_str for ind in rate_indicators):
            self._rate_limit_hit_time = time.time()
            logger.warning(f"Rate limit hit! Activating {self.RATE_LIMIT_COOLDOWN}s cooldown...")

            # Try module reload
            self._try_module_reload()
            return True

        return False

    def _try_module_reload(self) -> bool:
        """Reload yfinance module to reset internal state"""
        now = time.time()

        if self._last_module_reload:
            elapsed = now - self._last_module_reload
            if elapsed < self.MODULE_RELOAD_COOLDOWN:
                return False

        try:
            if 'yfinance' in sys.modules:
                importlib.reload(sys.modules['yfinance'])
                self._last_module_reload = now
                logger.info("yfinance module reloaded successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to reload yfinance: {e}")

        return False

    def _execute_with_retry(self, func, *args, max_retries: int = 3, **kwargs):
        """Execute function with rate limiting and retry logic"""
        last_error = None

        for attempt in range(max_retries):
            self._wait_for_rate_limit()

            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e

                if self._handle_rate_limit_error(e):
                    # Rate limit - wait longer for next retry
                    wait_time = (attempt + 1) * 30
                    logger.warning(f"Rate limit error, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue

                # Check for transient server errors
                error_str = str(e).lower()
                if any(x in error_str for x in ['502', '503', '504', 'timeout', 'connection']):
                    wait_time = (attempt + 1) * 10
                    logger.warning(f"Server error, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                    continue

                # Non-retryable error
                raise

        # All retries failed
        if last_error:
            logger.error(f"All retries failed: {last_error}")
        return None

    def get_stock_data(
        self,
        ticker: str,
        period: str = "3mo",
        allow_external: Optional[bool] = None
    ) -> Optional[pd.DataFrame]:
        """
        Get historical OHLCV data for a stock

        Args:
            ticker: Stock ticker symbol
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)

        Returns:
            DataFrame with Open, High, Low, Close, Volume
        """
        try:
            normalized = _normalize_ticker(ticker)
            if not normalized:
                logger.debug("Skipping invalid ticker for yfinance stock data: %s", ticker)
                return None

            allow_fetch = _resolve_allow_external(allow_external)
            if self._data_manager:
                cached = self._data_manager.get_historical(
                    normalized,
                    period=period,
                    queue_if_missing=allow_fetch
                )
                cached_df = _historical_list_to_df(cached)
                if cached_df is not None and not cached_df.empty:
                    return cached_df
                if not allow_fetch:
                    return None
            elif not allow_fetch:
                return None

            stock = yf.Ticker(normalized)
            # Use timeout to prevent hanging on slow tickers
            data = _with_timeout(lambda: stock.history(period=period), timeout=_YFINANCE_TIMEOUT, default=None)

            if data is None or data.empty:
                logger.debug(f"No data found for {ticker}")
                return None

            # Rename columns to match our format
            data = data.rename(columns={
                'Open': 'Open',
                'High': 'High',
                'Low': 'Low',
                'Close': 'Close',
                'Volume': 'Volume'
            })

            # Keep only OHLCV columns
            data = data[['Open', 'High', 'Low', 'Close', 'Volume']]

            if self._data_manager:
                self._data_manager.set_cached_data(
                    normalized,
                    "historical",
                    _historical_df_to_list(data),
                    period=period
                )

            return data

        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {str(e)}")
            return None

    def get_quote(
        self,
        ticker: str,
        use_cache: bool = True,
        allow_external: Optional[bool] = None
    ) -> Optional[Dict]:
        """
        Get current quote for a stock.

        Uses cache-first strategy to prevent rate limits.
        If use_cache=True and data_manager is available, will try cache first.

        Returns:
            Dict with current price, previous close, etc.
        """
        normalized = _normalize_ticker(ticker)
        if not normalized:
            logger.debug("Skipping invalid ticker for yfinance quote: %s", ticker)
            return None

        allow_fetch = _resolve_allow_external(allow_external)

        # Try cache first if available
        if use_cache and self._data_manager:
            cached = self._data_manager.get_quote(normalized, queue_if_missing=allow_fetch)
            if cached:
                return cached
            if not allow_fetch:
                return None
        elif not allow_fetch:
            return None

        # Rate limited API call
        try:
            self._wait_for_rate_limit()

            stock = yf.Ticker(normalized)
            info = {}
            fast_info = {}
            try:
                # Use timeout to prevent hanging on slow tickers
                info = _with_timeout(lambda: stock.info, timeout=_YFINANCE_TIMEOUT, default={}) or {}
            except Exception as exc:
                if self._handle_rate_limit_error(exc):
                    return self._data_manager.get_quote(normalized) if self._data_manager else None
                logger.debug("Failed to read yfinance info for %s: %s", normalized, exc)
                info = {}
            try:
                fast_info = _with_timeout(lambda: getattr(stock, "fast_info", None), timeout=5, default={}) or {}
            except Exception as exc:
                logger.debug("Failed to read yfinance fast_info for %s: %s", normalized, exc)
                fast_info = {}

            current_price = _pick_positive(
                info.get('currentPrice'),
                info.get('regularMarketPrice'),
                fast_info.get('last_price'),
                fast_info.get('regular_market_price')
            )
            previous_close = _pick_positive(
                info.get('previousClose'),
                info.get('regularMarketPreviousClose'),
                fast_info.get('previous_close')
            )
            day_high = _pick_positive(
                info.get('dayHigh'),
                info.get('regularMarketDayHigh'),
                fast_info.get('day_high')
            )
            day_low = _pick_positive(
                info.get('dayLow'),
                info.get('regularMarketDayLow'),
                fast_info.get('day_low')
            )
            open_price = _pick_positive(
                info.get('open'),
                info.get('regularMarketOpen'),
                fast_info.get('open')
            )
            volume = _pick_number(
                info.get('volume'),
                info.get('regularMarketVolume'),
                fast_info.get('last_volume'),
                fast_info.get('volume')
            )

            if not current_price:
                # Use timeout to prevent hanging
                history = _with_timeout(lambda: stock.history(period="5d"), timeout=10, default=None)
                if history is not None and not history.empty:
                    current_price = float(history['Close'].iloc[-1])
                    if len(history) > 1:
                        previous_close = float(history['Close'].iloc[-2])
                    else:
                        previous_close = current_price
                    day_high = float(history['High'].iloc[-1]) if 'High' in history else current_price
                    day_low = float(history['Low'].iloc[-1]) if 'Low' in history else current_price
                    open_price = float(history['Open'].iloc[-1]) if 'Open' in history else current_price
                    volume = float(history['Volume'].iloc[-1]) if 'Volume' in history else 0.0

            if not current_price:
                return None

            if not previous_close:
                previous_close = current_price
            if not day_high:
                day_high = current_price
            if not day_low:
                day_low = current_price
            if not open_price:
                open_price = current_price

            quote = {
                'c': current_price,
                'pc': previous_close,
                'h': day_high,
                'l': day_low,
                'o': open_price,
                'v': volume
            }

            # Cache the result
            if self._data_manager:
                self._data_manager.set_cached_data(normalized, "quote", quote)

            return quote

        except Exception as e:
            if self._handle_rate_limit_error(e):
                # Return cached data if available after rate limit
                if self._data_manager:
                    return self._data_manager.get_quote(normalized, queue_if_missing=False)
            logger.error(f"Error fetching quote for {ticker}: {str(e)}")
            return None

    def _normalize_52_week_range(self, ticker: str, stock: "yf.Ticker", info: Dict) -> Dict[str, float]:
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 0)) or 0
        high_52 = info.get('fiftyTwoWeekHigh', 0) or 0
        low_52 = info.get('fiftyTwoWeekLow', 0) or 0

        if current_price and (
            not high_52
            or not low_52
            or current_price > high_52 * 1.02
            or current_price < low_52 * 0.98
        ):
            try:
                # Use timeout to prevent hanging
                history = _with_timeout(lambda: stock.history(period="1y"), timeout=10, default=None)
                if history is not None and not history.empty:
                    hist_high = float(history['High'].max())
                    hist_low = float(history['Low'].min())
                    if hist_high:
                        high_52 = max(high_52, hist_high)
                    if hist_low:
                        low_52 = hist_low if not low_52 else min(low_52, hist_low)
            except Exception as exc:
                logger.warning(f"52-week range fallback failed for {ticker}: {exc}")

        if current_price:
            if not high_52 or current_price > high_52:
                high_52 = current_price
            if not low_52 or current_price < low_52:
                low_52 = current_price

        if high_52 and low_52 and high_52 < low_52:
            high_52, low_52 = max(high_52, low_52), min(high_52, low_52)

        return {
            'high': high_52,
            'low': low_52
        }

    def get_fundamentals(
        self,
        ticker: str,
        use_cache: bool = True,
        allow_external: Optional[bool] = None
    ) -> Optional[Dict]:
        """
        Get fundamental data for a stock.

        Uses cache-first strategy to prevent rate limits.

        Returns:
            Dict with P/E, market cap, etc.
        """
        normalized = _normalize_ticker(ticker)
        if not normalized:
            logger.debug("Skipping invalid ticker for yfinance fundamentals: %s", ticker)
            return None

        allow_fetch = _resolve_allow_external(allow_external)

        # Try cache first if available
        if use_cache and self._data_manager:
            cached = self._data_manager.get_fundamentals(normalized, queue_if_missing=allow_fetch)
            if cached:
                return cached
            if not allow_fetch:
                return None
        elif not allow_fetch:
            return None

        try:
            self._wait_for_rate_limit()

            stock = yf.Ticker(normalized)
            # Use timeout to prevent hanging on slow tickers
            info = _with_timeout(lambda: stock.info, timeout=_YFINANCE_TIMEOUT, default=None)

            if not info:
                logger.debug(f"No info available for {ticker} (timeout or no data)")
                return None

            range_52w = self._normalize_52_week_range(ticker, stock, info)

            # Get EV, EBITDA and calculate EV/EBIT
            # yfinance provides enterpriseToEbitda directly which is very similar to EV/EBIT
            enterprise_value = info.get('enterpriseValue', 0) or 0
            ebitda = info.get('ebitda', 0) or 0
            ev_ebitda = info.get('enterpriseToEbitda', None)  # Directly from yfinance

            # EBIT: try 'ebit' first, then 'operatingIncome', then estimate from EBITDA
            ebit = info.get('ebit') or info.get('operatingIncome') or 0
            if not ebit and ebitda > 0:
                # Estimate EBIT from EBITDA (EBIT ≈ 85% of EBITDA for typical companies)
                ebit = ebitda * 0.85

            # Calculate EV/EBIT
            ev_ebit = None
            if enterprise_value and enterprise_value > 0 and ebit and ebit > 0:
                ev_ebit = round(enterprise_value / ebit, 2)
            elif ev_ebitda:
                # If we have EV/EBITDA, estimate EV/EBIT (EV/EBIT ≈ EV/EBITDA * 1.18)
                ev_ebit = round(ev_ebitda * 1.18, 2)

            # ROIC calculation
            # ROIC = NOPAT / Invested Capital
            roic = None
            operating_income = info.get('operatingIncome') or info.get('ebit') or 0
            if not operating_income and ebitda > 0:
                operating_income = ebitda * 0.85  # Estimate operating income from EBITDA

            # Get balance sheet items for invested capital
            total_debt = info.get('totalDebt', 0) or 0
            total_equity = info.get('totalStockholderEquity') or info.get('bookValue', 0) or 0
            total_cash = info.get('totalCash', 0) or 0
            market_cap = info.get('marketCap', 0) or 0

            # Method 1: Invested Capital = Equity + Debt - Excess Cash
            invested_capital = total_equity + total_debt - (total_cash * 0.5)

            # Method 2: Fallback - use market cap + debt - cash as proxy
            if invested_capital <= 0 and market_cap > 0:
                invested_capital = market_cap + total_debt - total_cash

            # Method 3: Fallback to Total Assets - Current Liabilities
            if invested_capital <= 0:
                total_assets = info.get('totalAssets', 0) or 0
                current_liabilities = info.get('totalCurrentLiabilities', 0) or 0
                invested_capital = total_assets - current_liabilities

            if operating_income and operating_income > 0 and invested_capital and invested_capital > 0:
                nopat = operating_income * 0.80  # Assume 20% tax rate
                roic = round(nopat / invested_capital, 4)

            # Fallback: use ROE as proxy for ROIC if calculation failed
            if roic is None:
                roe = info.get('returnOnEquity', 0)
                if roe and roe > 0:
                    # ROE is typically higher than ROIC, adjust down slightly
                    roic = round(roe * 0.85, 4)

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
                'returnOnAssets': info.get('returnOnAssets', 0),
                'roic': roic,
                'debtToEquity': info.get('debtToEquity', 0),
                'currentRatio': info.get('currentRatio', 0),
                'beta': info.get('beta', 1),
                'fiftyTwoWeekHigh': range_52w['high'],
                'fiftyTwoWeekLow': range_52w['low'],
                'averageVolume': info.get('averageVolume', 0),
                'shortPercentOfFloat': info.get('shortPercentOfFloat', 0),
                'shortRatio': info.get('shortRatio', 0),
                'sharesFloat': info.get('floatShares', info.get('sharesFloat', 0)),
                'sharesOutstanding': info.get('sharesOutstanding', 0),
                'shortName': info.get('shortName', ticker),
                'currency': info.get('currency'),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'institutionalOwnership': info.get('heldPercentInstitutions', 0),
                'insiderOwnership': info.get('heldPercentInsiders', 0),
                'enterpriseValue': enterprise_value,
                'ebitda': ebitda,
                'ebit': ebit,
                'evEbitda': ev_ebitda,
                'evEbit': ev_ebit
            }

            # Cache the result
            if self._data_manager:
                self._data_manager.set_cached_data(normalized, "fundamentals", fundamentals)

            return fundamentals

        except Exception as e:
            if self._handle_rate_limit_error(e):
                if self._data_manager:
                    return self._data_manager.get_fundamentals(normalized, queue_if_missing=False)
            logger.error(f"Error fetching fundamentals for {ticker}: {str(e)}")
            return None

    def get_multiple_stocks(
        self,
        tickers: List[str],
        period: str = "3mo",
        chunk_size: int = 20,  # Reduced from 50 for better rate limiting
        pause_seconds: float = 5.0,  # Increased pause
        max_retries: int = 5,  # More retries
        allow_external: Optional[bool] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Get historical data for multiple stocks at once (faster than individual calls).

        Uses rate limiting and auto-recovery from rate limit errors.

        Args:
            tickers: List of ticker symbols
            period: Data period
            chunk_size: Tickers per batch (default 20, reduced for rate limiting)
            pause_seconds: Pause between batches (default 5s)
            max_retries: Max retries per batch (default 5)

        Returns:
            Dict mapping ticker to DataFrame
        """
        if not tickers:
            return {}

        valid_tickers = []
        for ticker in tickers:
            normalized = _normalize_ticker(ticker)
            if normalized:
                valid_tickers.append(normalized)
            else:
                logger.debug("Skipping invalid ticker in batch: %s", ticker)

        if not valid_tickers:
            return {}

        allow_fetch = _resolve_allow_external(allow_external)
        result: Dict[str, pd.DataFrame] = {}
        fetch_tickers = list(valid_tickers)

        if self._data_manager:
            fetch_tickers = []
            for ticker in valid_tickers:
                cached = self._data_manager.get_historical(
                    ticker,
                    period=period,
                    queue_if_missing=allow_fetch
                )
                cached_df = _historical_list_to_df(cached)
                if cached_df is not None and not cached_df.empty:
                    result[ticker] = cached_df
                else:
                    fetch_tickers.append(ticker)

        if not fetch_tickers or not allow_fetch:
            return result

        for start in range(0, len(fetch_tickers), chunk_size):
            chunk = fetch_tickers[start:start + chunk_size]
            attempt = 0

            while attempt <= max_retries:
                # Wait for rate limit before each batch
                self._wait_for_rate_limit()

                try:
                    data = yf.download(
                        chunk,
                        period=period,
                        group_by='ticker',
                        progress=False,
                        auto_adjust=True,
                        threads=False
                    )

                    if data is None or data.empty:
                        raise RuntimeError("Empty batch response from yfinance")

                    try:
                        import yfinance.shared as yf_shared
                        errors = getattr(yf_shared, "_ERRORS", {}) or {}
                        delisted_candidates = _extract_delisted_tickers(errors)
                        if delisted_candidates:
                            added = add_delisted_tickers(delisted_candidates)
                            if added:
                                logger.info("Registered %s delisted tickers from yfinance errors", added)
                    except Exception:
                        pass

                    for ticker in chunk:
                        try:
                            ticker_data = data if len(chunk) == 1 else data[ticker]
                            if ticker_data is not None and not ticker_data.empty:
                                ticker_data = ticker_data[['Open', 'High', 'Low', 'Close', 'Volume']]
                                result[ticker] = ticker_data
                                if self._data_manager:
                                    self._data_manager.set_cached_data(
                                        ticker,
                                        "historical",
                                        _historical_df_to_list(ticker_data),
                                        period=period
                                    )
                        except Exception:
                            continue

                    break

                except Exception as e:
                    if self._handle_rate_limit_error(e):
                        # Exponential backoff: 30s, 60s, 90s, 120s, 150s
                        wait_time = (attempt + 1) * 30
                        logger.warning(f"Rate limited. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                        time.sleep(wait_time)
                        attempt += 1
                        continue

                    # Check for other transient errors
                    error_str = str(e).lower()
                    if any(x in error_str for x in ['502', '503', '504', 'timeout', 'connection']):
                        wait_time = (attempt + 1) * 10
                        logger.warning(f"Server error. Waiting {wait_time}s before retry: {e}")
                        time.sleep(wait_time)
                        attempt += 1
                        continue

                    logger.error(f"Error fetching batch data: {e}")
                    break

            # Log progress
            completed = min(start + chunk_size, len(valid_tickers))
            logger.debug(f"Batch progress: {completed}/{len(valid_tickers)} tickers")

            # Pause between batches
            time.sleep(pause_seconds)

        return result

    def get_historical_data(
        self,
        ticker: str,
        period: str = "1mo",
        interval: str = "1d",
        allow_external: Optional[bool] = None
    ) -> Optional[pd.DataFrame]:
        """
        Get historical OHLCV data for a ticker with configurable period/interval.

        Uses rate limiting and auto-recovery from rate limit errors.
        Returns None on failure or empty data.
        """
        normalized = _normalize_ticker(ticker)
        if not normalized:
            logger.debug("Skipping invalid ticker for historical data: %s", ticker)
            return None

        allow_fetch = _resolve_allow_external(allow_external)
        if interval == "1d" and self._data_manager:
            cached = self._data_manager.get_historical(
                normalized,
                period=period,
                queue_if_missing=allow_fetch
            )
            cached_df = _historical_list_to_df(cached)
            if cached_df is not None and not cached_df.empty:
                return cached_df
            if not allow_fetch:
                return None
        elif not allow_fetch:
            return None

        # Wait for rate limit before API call
        self._wait_for_rate_limit()

        try:
            # Use timeout to prevent hanging on slow tickers
            df = _with_timeout(
                lambda: yf.download(
                    normalized,
                    period=period,
                    interval=interval,
                    progress=False,
                    auto_adjust=False,
                    threads=False,
                ),
                timeout=_YFINANCE_TIMEOUT,
                default=None
            )

            if df is None or df.empty:
                logger.warning(f"No historical data for {ticker} ({period}/{interval})")
                return None

            # Handle MultiIndex columns from yfinance (e.g., ('Close', 'TICKER'))
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Ensure expected columns exist and return only OHLCV
            columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            missing = [c for c in columns if c not in df.columns]
            if missing:
                logger.warning(f"Historical data for {ticker} missing columns: {missing}")
                return None

            df = df[columns]
            if self._data_manager and interval == "1d":
                self._data_manager.set_cached_data(
                    normalized,
                    "historical",
                    _historical_df_to_list(df),
                    period=period
                )
            return df

        except Exception as e:
            if self._handle_rate_limit_error(e):
                # Wait and retry once
                time.sleep(60)
                self._wait_for_rate_limit()
                try:
                    df = _with_timeout(
                        lambda: yf.download(normalized, period=period, interval=interval, progress=False, threads=False),
                        timeout=_YFINANCE_TIMEOUT,
                        default=None
                    )
                    if df is not None and not df.empty:
                        # Handle MultiIndex columns
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = df.columns.get_level_values(0)
                        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
                        if self._data_manager and interval == "1d":
                            self._data_manager.set_cached_data(
                                normalized,
                                "historical",
                                _historical_df_to_list(df),
                                period=period
                            )
                        return df
                except Exception:
                    pass
            logger.error(f"Error fetching historical data for {ticker}: {str(e)}")
            return None


# Global singleton instance
_yfinance_service = None


def get_yfinance_service() -> YFinanceService:
    """Get or create yfinance service singleton"""
    global _yfinance_service
    if _yfinance_service is None:
        _yfinance_service = YFinanceService()
    return _yfinance_service
