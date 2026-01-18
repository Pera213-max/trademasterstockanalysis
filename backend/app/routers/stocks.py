from fastapi import APIRouter, HTTPException, Query, Request
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
import json
import os
import re
import math
import logging
from app.services.predictor import StockPredictor
from app.services.enhanced_predictor import EnhancedStockPredictor
from app.services.finnhub_service import get_finnhub_service
from app.services.yfinance_service import get_yfinance_service
from app.services.news_service import get_news_service
from app.services.stock_universe import get_stock_count
from app.services.mock_data import (
    get_mock_stock_picks,
    get_mock_hidden_gems,
    get_mock_quick_wins,
    get_mock_macro_indicators
)
from database.redis.config import get_redis_cache
from app.config.settings import settings
from app.utils.admin_auth import is_force_refresh_allowed

# Import data manager for cache-first strategy
try:
    from app.services.yfinance_data_manager import get_yfinance_data_manager
    data_manager = get_yfinance_data_manager()
except Exception:
    data_manager = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_local_cache: Dict[str, Dict[str, Any]] = {}
_TICKER_PATTERN = re.compile(r"^[A-Z]{1,5}(-[A-Z]{1,2})?$")


def _normalize_ticker(ticker: str) -> str:
    normalized = (ticker or "").strip().upper()
    if not _TICKER_PATTERN.match(normalized):
        raise HTTPException(status_code=400, detail=f"Invalid ticker: {ticker}")
    return normalized


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(",", ".")
        cleaned = re.sub(r"[^0-9eE+.-]", "", cleaned)
        if not cleaned:
            return None
        try:
            number = float(cleaned)
        except ValueError:
            return None
        return number if math.isfinite(number) else None
    return None


def _get_local_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    entry = _local_cache.get(cache_key)
    if not entry:
        return None
    if entry["expires_at"] <= datetime.now():
        _local_cache.pop(cache_key, None)
        return None
    return entry["value"]


def _set_local_cache(cache_key: str, value: Dict[str, Any], ttl_seconds: int) -> None:
    _local_cache[cache_key] = {
        "expires_at": datetime.now() + timedelta(seconds=ttl_seconds),
        "value": value
    }


US_ANALYSIS_TTL_SECONDS = int(os.getenv("US_ANALYSIS_TTL_SECONDS", "1800"))
US_ANALYSIS_STALE_TTL_SECONDS = int(os.getenv("US_ANALYSIS_STALE_TTL_SECONDS", "86400"))
US_ANALYSIS_LOCK_TTL_SECONDS = int(os.getenv("US_ANALYSIS_LOCK_TTL_SECONDS", "120"))
US_ANALYSIS_WARM_LOCK_TTL_SECONDS = int(os.getenv("US_ANALYSIS_WARM_LOCK_TTL_SECONDS", "3600"))
US_ANALYSIS_PLACEHOLDER_TTL_SECONDS = int(os.getenv("US_ANALYSIS_PLACEHOLDER_TTL_SECONDS", "60"))
US_ANALYSIS_WAIT_SECONDS = float(os.getenv("US_ANALYSIS_WAIT_SECONDS", "2.0"))
US_ANALYSIS_WAIT_INTERVAL = float(os.getenv("US_ANALYSIS_WAIT_INTERVAL", "0.1"))


def _get_cached_value(cache_key: str) -> Optional[Dict[str, Any]]:
    if redis_cache and redis_cache.is_connected():
        try:
            cached = redis_cache.get(cache_key)
            if cached:
                return cached
        except Exception:
            pass
    return _get_local_cache(cache_key)


def _set_cached_value(cache_key: str, value: Dict[str, Any], ttl_seconds: int) -> None:
    if redis_cache and redis_cache.is_connected():
        try:
            redis_cache.setex(cache_key, ttl_seconds, value)
            return
        except Exception:
            pass
    _set_local_cache(cache_key, value, ttl_seconds)


def _try_acquire_cache_lock(lock_key: str, ttl_seconds: int) -> bool:
    client = getattr(redis_cache, "redis_client", None)
    if not client:
        return True
    try:
        return bool(client.set(lock_key, "1", nx=True, ex=ttl_seconds))
    except TypeError:
        return True
    except Exception:
        return False


def _release_cache_lock(lock_key: str) -> None:
    client = getattr(redis_cache, "redis_client", None)
    if not client:
        return
    try:
        client.delete(lock_key)
    except Exception:
        return


async def _wait_for_cache_value(cache_key: str) -> Optional[Dict[str, Any]]:
    attempts = max(1, int(US_ANALYSIS_WAIT_SECONDS / US_ANALYSIS_WAIT_INTERVAL))
    for _ in range(attempts):
        await asyncio.sleep(US_ANALYSIS_WAIT_INTERVAL)
        cached = _get_cached_value(cache_key)
        if cached:
            return cached
    return None


async def _warm_analysis_cache_async(tickers: List[str]) -> None:
    """Warm analysis cache for given tickers in background."""
    try:
        logger.info(f"Background warming analysis cache for {len(tickers)} tickers")
        result = await asyncio.to_thread(warm_stock_analysis_cache, tickers, True, False)
        logger.info(f"Analysis cache warm complete: warmed={result.get('warmed', 0)}, skipped={result.get('skipped', 0)}")
    except Exception as e:
        logger.warning(f"Background analysis cache warm failed: {e}")


def _sanitize_pick_targets(picks: List[Dict[str, Any]], timeframe: str) -> None:
    if not picks:
        return
    for pick in picks:
        try:
            current = _coerce_float(pick.get("currentPrice") or pick.get("current_price"))
            target = _coerce_float(pick.get("targetPrice") or pick.get("target_price"))
            if current is None or current <= 0:
                continue
            current_price = float(current)
            target_price = float(target) if target is not None else current_price
            fundamentals = pick.get("fundamentals") if isinstance(pick.get("fundamentals"), dict) else None
            safe_target, potential = stock_predictor._apply_target_guardrails(
                current_price,
                target_price,
                fundamentals,
                timeframe
            )
            pick["currentPrice"] = float(current_price)
            pick["targetPrice"] = float(safe_target)
            pick["potentialReturn"] = float(potential)
        except (TypeError, ValueError):
            continue


def _refresh_pick_prices(picks: List[Dict[str, Any]], timeframe: str) -> None:
    """
    Refresh prices for stock picks using CACHE-FIRST strategy.

    This function uses the data manager to get cached quotes instead of
    making direct yfinance API calls, preventing rate limit crashes.
    """
    if not picks:
        return

    # Get all tickers
    tickers = [pick.get("ticker") for pick in picks if pick.get("ticker")]

    # Get cached quotes in bulk (uses Redis pipeline for efficiency)
    quotes = {}
    if data_manager:
        quotes = data_manager.get_multiple_quotes(tickers, queue_missing=True)
    else:
        # Fallback to yfinance_service with caching
        for ticker in tickers:
            try:
                quotes[ticker] = yfinance_service.get_quote(ticker, use_cache=True)
            except Exception:
                quotes[ticker] = None

    # Update pick prices with cached data
    for pick in picks:
        try:
            ticker = pick.get("ticker")
            if not ticker:
                continue

            quote = quotes.get(ticker)
            live_price = _coerce_float(quote.get("c") if quote else None)
            if live_price is None or live_price <= 0:
                # Keep existing price if no cached data available
                continue

            current_price = _coerce_float(pick.get("currentPrice") or pick.get("current_price"))
            target_price = _coerce_float(pick.get("targetPrice") or pick.get("target_price"))
            if current_price and target_price:
                scale = live_price / current_price if current_price else 1.0
                target_price = target_price * scale
            elif target_price is None:
                target_price = live_price

            fundamentals = pick.get("fundamentals") if isinstance(pick.get("fundamentals"), dict) else None
            safe_target, potential = stock_predictor._apply_target_guardrails(
                live_price,
                target_price,
                fundamentals,
                timeframe
            )

            pick["currentPrice"] = float(live_price)
            pick["targetPrice"] = float(safe_target)
            pick["potentialReturn"] = float(potential)
        except Exception:
            continue

router = APIRouter(
    prefix="/api/stocks",
    tags=["stocks"]
)

# Initialize predictors, cache and services
stock_predictor = StockPredictor()
enhanced_predictor = EnhancedStockPredictor()
redis_cache = get_redis_cache()
finnhub_service = get_finnhub_service()
yfinance_service = get_yfinance_service()
news_service = get_news_service()

# MOCK MODE - Set to True to use demo data
USE_MOCK_DATA = False  # Using Finnhub for real data


@router.get("/picks")
async def get_sector_picks(
    sector: Optional[str] = Query(None, regex="^(tech|energy|healthcare|finance|consumer)$"),
    theme: Optional[str] = Query(None, regex="^(growth|value|esg)$"),
    timeframe: str = Query("swing", regex="^(day|swing|long)$"),
    limit: int = Query(5, ge=1, le=100)  # Allow up to 100 for finding specific stocks
):
    """
    Get AI-powered stock picks filtered by sector and/or theme

    Args:
        sector: Sector filter (tech, energy, healthcare, finance, consumer) - optional
        theme: Theme filter (growth, value, esg) - optional
        timeframe: Trading timeframe (day, swing, long)
        limit: Number of picks to return (1-20)

    Returns:
        Top stock picks matching sector/theme filters with AI scores

    Examples:
        - /api/stocks/picks?sector=tech&timeframe=long - Tech stocks for long-term
        - /api/stocks/picks?theme=growth&timeframe=swing - Growth stocks for swing trading
        - /api/stocks/picks?sector=healthcare&theme=value - Value healthcare stocks
    """
    try:
        if USE_MOCK_DATA:
            raise HTTPException(
                status_code=503,
                detail="Mock data disabled. Provide live API keys instead."
            )

        # Build cache key from parameters
        cache_key = f"predictions:sector:{sector or 'all'}:{theme or 'all'}:{timeframe}:{limit}"

        # Check cache first (cached per settings TTL)
        if redis_cache and redis_cache.is_connected():
            import json
            cached_data = redis_cache.redis_client.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for sector picks: {sector}/{theme}/{timeframe}")
                result = json.loads(cached_data)
                _sanitize_pick_targets(result.get("data", []), timeframe)
                result['cached'] = True
                return result
        else:
            cached_local = _get_local_cache(cache_key)
            if cached_local:
                logger.info(f"Local cache hit for sector picks: {sector}/{theme}/{timeframe}")
                _sanitize_pick_targets(cached_local.get("data", []), timeframe)
                cached_local['cached'] = True
                return cached_local

        # Use basic predictor with sector/theme filters (enhanced predictor doesn't have this method)
        picks = stock_predictor.predict_stocks_by_sector(
            sector=sector,
            theme=theme,
            timeframe=timeframe,
            limit=limit
        )
        _sanitize_pick_targets(picks, timeframe)
        _refresh_pick_prices(picks, timeframe)

        result = {
            "success": True,
            "sector": sector or "all",
            "theme": theme or "general",
            "timeframe": timeframe,
            "count": len(picks),
            "data": picks,
            "cached": False
        }

        # Cache the results (settings TTL)
        if redis_cache and redis_cache.is_connected():
            import json
            redis_cache.redis_client.setex(cache_key, settings.CACHE_TTL_AI_PICKS, json.dumps(result))
        else:
            _set_local_cache(cache_key, result, settings.CACHE_TTL_AI_PICKS)

        # Warm analysis cache in background for sector picks
        tickers = [p.get("ticker") for p in picks[:15] if p.get("ticker")]
        if tickers:
            asyncio.create_task(_warm_analysis_cache_async(tickers))

        return result

    except Exception as e:
        logger.error(f"Error in get_sector_picks: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate sector picks: {str(e)}"
        )


@router.get("/hidden-gems")
async def get_hidden_gems(
    timeframe: str = Query("swing", regex="^(day|swing|long)$"),
    limit: int = Query(10, ge=1, le=20),
    force_refresh: bool = Query(False),
    request: Request = None
):
    """
    Get hidden gem stock picks - high potential stocks with low attention

    Hidden gems are mid/small-cap stocks with:
    - Market cap $500M - $10B
    - Revenue growth > 30%
    - Low analyst coverage
    - Strong technical indicators
    - Volume surge patterns

    These are stocks most people miss - perfect for finding opportunities before they become mainstream.

    Args:
        timeframe: Trading timeframe (day, swing, long)
        limit: Number of picks to return (1-20)

    Returns:
        Hidden gem stock picks with enhanced AI scores
    """
    try:
        if USE_MOCK_DATA:
            raise HTTPException(
                status_code=503,
                detail="Mock data disabled. Provide live API keys instead."
            )

        if force_refresh and not is_force_refresh_allowed(request):
            raise HTTPException(
                status_code=403,
                detail="force_refresh requires X-Admin-Key or Bearer admin token"
            )

        cache_key = f"predictions:hidden_gems:{timeframe}"
        effective_limit = max(limit, 10)

        if not force_refresh:
            if redis_cache and redis_cache.is_connected():
                import json
                cached_data = redis_cache.redis_client.get(cache_key)
                if cached_data:
                    logger.info(f"Cache hit for hidden gems: {timeframe}")
                    result = json.loads(cached_data)
                    cached_picks = result.get("data", [])
                    _sanitize_pick_targets(cached_picks, timeframe)
                    result['data'] = cached_picks[:limit]
                    result['count'] = len(result['data'])
                    result['cached'] = True
                    return result
            else:
                cached_local = _get_local_cache(cache_key)
                if cached_local:
                    logger.info(f"Local cache hit for hidden gems: {timeframe}")
                    cached_picks = cached_local.get("data", [])
                    _sanitize_pick_targets(cached_picks, timeframe)
                    cached_local['data'] = cached_picks[:limit]
                    cached_local['count'] = len(cached_local['data'])
                    cached_local['cached'] = True
                    return cached_local
        else:
            logger.info(f"Force refresh for hidden gems: {timeframe}")

        # Use enhanced predictor to find hidden gems
        picks = enhanced_predictor.find_hidden_gems(timeframe=timeframe, limit=effective_limit)
        _sanitize_pick_targets(picks, timeframe)
        _refresh_pick_prices(picks, timeframe)

        cache_payload = {
            "success": True,
            "category": "hidden_gems",
            "timeframe": timeframe,
            "count": len(picks),
            "data": picks,
            "cached": False
        }

        # Cache hidden gems (settings TTL)
        if redis_cache and redis_cache.is_connected():
            import json
            redis_cache.redis_client.setex(cache_key, settings.CACHE_TTL_HIDDEN_GEMS, json.dumps(cache_payload))
        else:
            _set_local_cache(cache_key, cache_payload, settings.CACHE_TTL_HIDDEN_GEMS)

        # Warm analysis cache in background for hidden gems
        tickers = [p.get("ticker") for p in picks[:15] if p.get("ticker")]
        if tickers:
            asyncio.create_task(_warm_analysis_cache_async(tickers))

        response_payload = {
            **cache_payload,
            "data": picks[:limit],
            "count": len(picks[:limit])
        }

        return response_payload

    except Exception as e:
        logger.error(f"Error in get_hidden_gems: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to find hidden gems: {str(e)}"
        )


@router.get("/quick-wins")
async def get_quick_wins(
    limit: int = Query(10, ge=1, le=20),
    force_refresh: bool = Query(False),
    request: Request = None
):
    """
    Get quick win opportunities for day trading

    Quick wins are high-volume, liquid stocks with:
    - Strong intraday momentum (last 3 days)
    - Volume surge (3x+ average)
    - High volatility (2%+)
    - Clear support/resistance levels

    Perfect for active day traders looking for fast moves.

    Args:
        limit: Number of picks to return (1-20)

    Returns:
        Quick win stock picks optimized for day trading
    """
    try:
        if USE_MOCK_DATA:
            raise HTTPException(
                status_code=503,
                detail="Mock data disabled. Provide live API keys instead."
            )

        if force_refresh and not is_force_refresh_allowed(request):
            raise HTTPException(
                status_code=403,
                detail="force_refresh requires X-Admin-Key or Bearer admin token"
            )

        cache_key = "predictions:quick_wins"
        effective_limit = max(limit, 10)

        if not force_refresh:
            if redis_cache and redis_cache.is_connected():
                import json
                cached_data = redis_cache.redis_client.get(cache_key)
                if cached_data:
                    logger.info("Cache hit for quick wins")
                    result = json.loads(cached_data)
                    cached_picks = result.get("data", [])
                    _sanitize_pick_targets(cached_picks, "day")
                    result['data'] = cached_picks[:limit]
                    result['count'] = len(result['data'])
                    result['cached'] = True
                    return result
            else:
                cached_local = _get_local_cache(cache_key)
                if cached_local:
                    logger.info("Local cache hit for quick wins")
                    cached_picks = cached_local.get("data", [])
                    _sanitize_pick_targets(cached_picks, "day")
                    cached_local['data'] = cached_picks[:limit]
                    cached_local['count'] = len(cached_local['data'])
                    cached_local['cached'] = True
                    return cached_local
        else:
            logger.info("Force refresh for quick wins")

        # Use enhanced predictor to find quick wins
        picks = enhanced_predictor.find_quick_wins(limit=effective_limit)
        _sanitize_pick_targets(picks, "day")
        _refresh_pick_prices(picks, "day")

        cache_payload = {
            "success": True,
            "category": "quick_wins",
            "timeframe": "day",
            "count": len(picks),
            "data": picks,
            "cached": False
        }

        # Cache quick wins (settings TTL)
        if picks:
            if redis_cache and redis_cache.is_connected():
                import json
                redis_cache.redis_client.setex(cache_key, settings.CACHE_TTL_QUICK_WINS, json.dumps(cache_payload))
            else:
                _set_local_cache(cache_key, cache_payload, settings.CACHE_TTL_QUICK_WINS)

            # Warm analysis cache in background for quick wins
            tickers = [p.get("ticker") for p in picks[:15] if p.get("ticker")]
            if tickers:
                asyncio.create_task(_warm_analysis_cache_async(tickers))
        else:
            logger.warning("Quick wins returned 0 picks; skipping cache update")

        response_payload = {
            **cache_payload,
            "data": picks[:limit],
            "count": len(picks[:limit])
        }

        return response_payload

    except Exception as e:
        logger.error(f"Error in get_quick_wins: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to find quick wins: {str(e)}"
        )


@router.get("/top-picks")
async def get_top_picks(
    timeframe: str = Query("swing", regex="^(day|swing|long)$"),
    limit: int = Query(10, ge=1, le=100),  # Allow up to 100 picks
    force_refresh: bool = Query(False),
    request: Request = None
):
    """
    Get AI-powered top stock picks using real technical analysis

    Args:
        timeframe: Trading timeframe (day, swing, long)
        limit: Number of picks to return (1-20)

    Returns:
        Top stock picks with AI confidence scores based on real market data
    """
    try:
        if USE_MOCK_DATA:
            raise HTTPException(
                status_code=503,
                detail="Mock data disabled. Provide live API keys instead."
            )

        if force_refresh and not is_force_refresh_allowed(request):
            raise HTTPException(
                status_code=403,
                detail="force_refresh requires X-Admin-Key or Bearer admin token"
            )

        # Check cache first
        cache_key = f"predictions:stocks:{timeframe}:{limit}"
        if not force_refresh:
            if redis_cache and redis_cache.is_connected():
                cached_data = redis_cache.get_cached_predictions(timeframe)
                if cached_data:
                    logger.info(f"Cache hit for stock predictions: {timeframe}")
                    _sanitize_pick_targets(cached_data, timeframe)
                    return {
                        "success": True,
                        "timeframe": timeframe,
                        "count": len(cached_data),
                        "data": cached_data[:limit],
                        "cached": True
                    }
            else:
                cached_local = _get_local_cache(cache_key)
                if cached_local:
                    logger.info(f"Local cache hit for stock predictions: {timeframe}")
                    _sanitize_pick_targets(cached_local.get("data", []), timeframe)
                    cached_local['cached'] = True
                    return cached_local
        else:
            logger.info(f"Force refresh for stock predictions: {timeframe}")

        # Use basic predictor for top picks (enhanced predictor doesn't have this method)
        picks = stock_predictor.predict_top_stocks(timeframe=timeframe, limit=limit)
        _sanitize_pick_targets(picks, timeframe)

        result = {
            "success": True,
            "timeframe": timeframe,
            "count": len(picks),
            "data": picks,
            "cached": False
        }

        # Cache the results (settings TTL)
        if redis_cache and redis_cache.is_connected():
            redis_cache.cache_predictions(timeframe, picks, ttl=settings.CACHE_TTL_AI_PICKS)
        else:
            _set_local_cache(cache_key, result, settings.CACHE_TTL_AI_PICKS)

        # Warm analysis cache in background for top picks
        tickers = [p.get("ticker") for p in picks[:20] if p.get("ticker")]
        if tickers:
            asyncio.create_task(_warm_analysis_cache_async(tickers))

        return result

    except Exception as e:
        logger.error(f"Error in get_top_picks: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate stock predictions: {str(e)}"
        )


@router.get("/movers")
async def get_movers():
    """
    Get top movers - gainers and losers using CACHE-FIRST strategy.

    Uses cached data to prevent yfinance rate limit crashes.

    Returns:
        Top gainers and losers for the day
    """
    try:
        # Check cache first (5 minute TTL for movers)
        cache_key = "movers:stocks"
        if redis_cache and redis_cache.is_connected():
            cached_data = redis_cache.redis_client.get(cache_key)
            if cached_data:
                import json
                logger.info("Cache hit for stock movers")
                data = json.loads(cached_data)
                data['cached'] = True
                return data
        else:
            cached_local = _get_local_cache(cache_key)
            if cached_local:
                logger.info("Local cache hit for stock movers")
                cached_local['cached'] = True
                return cached_local

        # Popular tickers to check
        tickers = [
            'NVDA', 'AMD', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
            'NFLX', 'BABA', 'COIN', 'PLTR', 'PYPL', 'SQ', 'DIS', 'UBER',
            'ABNB', 'SNAP', 'ROKU', 'SHOP', 'SPOT', 'TWLO', 'CRWD', 'NET'
        ]

        # Get all quotes in bulk from cache
        quotes = {}
        fundamentals_cache = {}

        if data_manager:
            quotes = data_manager.get_multiple_quotes(tickers, queue_missing=True)
            for ticker in tickers:
                fundamentals_cache[ticker] = data_manager.get_fundamentals(ticker, queue_if_missing=True)
        else:
            for ticker in tickers:
                try:
                    quotes[ticker] = yfinance_service.get_quote(ticker, use_cache=True)
                    fundamentals_cache[ticker] = yfinance_service.get_fundamentals(ticker, use_cache=True)
                except Exception:
                    quotes[ticker] = None
                    fundamentals_cache[ticker] = None

        movers_data = []

        for ticker in tickers:
            try:
                # Try Finnhub first, then cached yfinance
                quote = finnhub_service.get_quote(ticker)
                if not quote or quote.get('c', 0) == 0:
                    quote = quotes.get(ticker)
                if not quote or quote.get('c', 0) == 0:
                    continue

                current_price = quote.get('c', 0)
                previous_close = quote.get('pc', current_price)
                change = current_price - previous_close
                change_percent = (change / previous_close) * 100 if previous_close > 0 else 0

                # Get company profile for name
                profile = finnhub_service.get_company_profile(ticker)
                name = profile.get('name', ticker) if profile else ticker
                fundamentals = fundamentals_cache.get(ticker) or {}
                if name == ticker and fundamentals:
                    name = fundamentals.get('shortName', ticker)

                # Volume from cached quote
                volume = quote.get('v', 0)
                avg_volume = fundamentals.get('averageVolume', 0) if fundamentals else 0
                volume_ratio = (volume / avg_volume) if avg_volume else 1
                interest_score = abs(change_percent) * (1 + min(volume_ratio, 3))

                movers_data.append({
                    "ticker": ticker,
                    "name": name,
                    "price": round(float(current_price), 2),
                    "change": round(float(change), 2),
                    "changePercent": round(float(change_percent), 2),
                    "volume": int(volume) if volume else 0,
                    "type": "stock",
                    "_interestScore": float(interest_score),
                    "_volumeRatio": float(volume_ratio)
                })

            except Exception as e:
                logger.warning(f"Error fetching data for {ticker}: {e}")
                continue

        def pick_interesting(items, count):
            if not items:
                return []
            interesting = [
                item for item in items
                if abs(item.get('changePercent', 0)) >= 2.0 or item.get('_volumeRatio', 1) >= 1.8
            ]
            if interesting:
                liquid = [
                    item for item in interesting
                    if item.get('price', 0) >= 5 and item.get('volume', 0) >= 500_000
                ]
                if liquid:
                    interesting = liquid
            pool = interesting if interesting else items
            pool = sorted(pool, key=lambda x: x.get('_interestScore', 0), reverse=True)
            selected = pool[:count]
            for item in selected:
                item.pop('_interestScore', None)
                item.pop('_volumeRatio', None)
            return selected

        gainers = pick_interesting([m for m in movers_data if m['changePercent'] > 0], 5)
        losers = pick_interesting([m for m in movers_data if m['changePercent'] < 0], 5)

        result = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "data": {
                "gainers": gainers,
                "losers": losers
            },
            "cached": False
        }

        # Cache for 5 minutes
        if redis_cache and redis_cache.is_connected():
            import json
            redis_cache.redis_client.setex(cache_key, 300, json.dumps(result))
        else:
            _set_local_cache(cache_key, result, 300)

        # Warm analysis cache in background for movers
        mover_tickers = [m.get("ticker") for m in gainers + losers if m.get("ticker")]
        if mover_tickers:
            asyncio.create_task(_warm_analysis_cache_async(mover_tickers))

        return result

    except Exception as e:
        logger.error(f"Error in get_movers: {str(e)}", exc_info=True)

        # Return empty result instead of static fallback data
        # This prevents showing the same stocks every day
        return {
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "data": {
                "gainers": [],
                "losers": []
            },
            "error": "Unable to fetch movers data. Please try again later.",
            "cached": False
        }


@router.get("/{ticker}")
async def get_stock_details(ticker: str):
    """
    Get detailed stock information with real-time data

    Args:
        ticker: Stock ticker symbol

    Returns:
        Comprehensive stock data including technical analysis
    """
    try:
        ticker = _normalize_ticker(ticker)

        # Check cache first (1 minute TTL for stock details)
        if redis_cache and redis_cache.is_connected():
            cached_price = redis_cache.get_cached_prices(ticker)
            if cached_price:
                logger.info(f"Cache hit for stock details: {ticker}")
                cached_price['cached'] = True
                return {
                    "success": True,
                    "data": cached_price
                }

        # Fetch real data using Finnhub
        quote = finnhub_service.get_quote(ticker)
        if not quote or quote.get('c', 0) == 0:
            raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")

        profile = finnhub_service.get_company_profile(ticker)
        financials = finnhub_service.get_basic_financials(ticker)

        current_price = quote.get('c', 0)
        previous_close = quote.get('pc', current_price)
        change = current_price - previous_close
        change_percent = (change / previous_close) * 100 if previous_close > 0 else 0

        # Extract financial metrics
        metrics = financials.get('metric', {}) if financials else {}

        def _safe_float(value):
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        high_52 = _safe_float(metrics.get('52WeekHigh'))
        low_52 = _safe_float(metrics.get('52WeekLow'))

        if current_price:
            if high_52 is None or current_price > high_52:
                high_52 = current_price
            if low_52 is None or current_price < low_52:
                low_52 = current_price

        if high_52 is not None and low_52 is not None and high_52 < low_52:
            high_52, low_52 = max(high_52, low_52), min(high_52, low_52)

        stock_data = {
            "ticker": ticker,
            "name": profile.get('name', ticker) if profile else ticker,
            "price": round(float(current_price), 2),
            "change": round(float(change), 2),
            "changePercent": round(float(change_percent), 2),
            "volume": 0,
            "marketCap": profile.get('marketCapitalization', 0) * 1000000 if profile else None,
            "pe": metrics.get('peBasicExclExtraTTM'),
            "eps": metrics.get('epsBasicExclExtraItemsTTM'),
            "high52w": high_52,
            "low52w": low_52,
            "avgVolume": metrics.get('10DayAverageTradingVolume'),
            "sector": profile.get('finnhubIndustry') if profile else None,
            "industry": profile.get('finnhubIndustry') if profile else None,
            "description": profile.get('description') if profile else None,
            "website": profile.get('weburl') if profile else None,
            "ceo": profile.get('ceo') if profile else None,
            "employees": profile.get('employeeTotal') if profile else None,
            "technicals": {}
        }

        # Cache for 1 minute
        if redis_cache and redis_cache.is_connected():
            redis_cache.cache_prices(ticker, stock_data, ttl=60)

        return {
            "success": True,
            "data": stock_data,
            "cached": False
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stock details for {ticker}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch stock details: {str(e)}"
        )


@router.get("/{ticker}/news")
async def get_stock_news(
    ticker: str,
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(7, ge=1, le=30)
):
    """
    Get news for a specific stock

    Args:
        ticker: Stock ticker symbol
        limit: Number of news items to return
        days: Number of days to look back for news

    Returns:
        List of relevant news articles for the stock
    """
    try:
        ticker = _normalize_ticker(ticker)

        # Check cache (10 minute TTL)
        cache_key = f"stock_news_{ticker}_{days}"
        if redis_cache and redis_cache.is_connected():
            cached_news = redis_cache.get(cache_key)
            if cached_news:
                logger.info(f"Cache hit for stock news: {ticker}")
                return {
                    "success": True,
                    "ticker": ticker,
                    "count": len(cached_news[:limit]),
                    "data": cached_news[:limit],
                    "cached": True
                }
            if settings.US_CACHE_ONLY:
                empty_news: List[Dict[str, Any]] = []
                redis_cache.set(cache_key, empty_news, ex=600)
                return {
                    "success": True,
                    "ticker": ticker,
                    "count": 0,
                    "data": [],
                    "cached": True,
                    "message": "News cache warming"
                }

        # Fetch real news using news service
        # Get both newest and weighted news for comprehensive coverage
        news_data = news_service.get_stock_news_weighted(ticker, days=days)

        # Combine newest and weighted, removing duplicates
        all_news = news_data.get('newest', []) + news_data.get('weighted', [])

        # Remove duplicates by URL
        seen_urls = set()
        unique_news = []
        for article in all_news:
            url = article.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_news.append(article)

        # Sort by weight (most important first) and limit
        unique_news.sort(key=lambda x: x.get('weight', 0), reverse=True)
        news_items = unique_news[:limit]

        # Format for frontend
        formatted_news = []
        for i, article in enumerate(news_items):
            formatted_news.append({
                "id": str(i + 1),
                "ticker": article.get('ticker') or ticker,
                "headline": article.get('title', ''),
                "summary": article.get('description', ''),
                "timestamp": article.get('publishedAt', ''),
                "category": article.get('category', 'GENERAL'),
                "isHot": article.get('isHot', False),
                "impact": article.get('impact', 'LOW'),
                "url": article.get('url', ''),
                "source": article.get('source', 'Unknown'),
                "weight": article.get('weight', 0)
            })

        # Cache news (10 minute TTL)
        if redis_cache and redis_cache.is_connected():
            redis_cache.setex(cache_key, 600, formatted_news)

        logger.info(f" Fetched {len(formatted_news)} relevant news articles for {ticker}")

        return {
            "success": True,
            "ticker": ticker,
            "count": len(formatted_news),
            "data": formatted_news,
            "cached": False,
            "stats": {
                "total_articles": news_data.get('total_articles', 0),
                "avg_weight": news_data.get('avg_weight', 0),
                "categories": news_data.get('categories', {}),
                "period_days": days
            }
        }

    except Exception as e:
        logger.error(f"Error getting stock news: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch news: {str(e)}"
        )


def _empty_stock_analysis_data(ticker: str, message: str = "") -> Dict[str, Any]:
    tradeable_universe = len(getattr(enhanced_predictor, "ticker_universe", [])) or 0
    return {
        "ticker": ticker,
        "company_name": ticker,
        "sector": "Unknown",
        "industry": "Unknown",
        "quote": {
            "current_price": 0,
            "previous_close": 0,
            "change": 0,
            "change_pct": 0,
            "day_high": 0,
            "day_low": 0,
            "volume": 0,
        },
        "ai_score": None,
        "insider_trading": {
            "signal": None,
            "sentiment": "UNKNOWN",
            "net_activity": 0,
            "net_value": 0,
            "total_buy_value": 0,
            "total_sell_value": 0,
            "buys": 0,
            "sells": 0,
        },
        "short_interest": {
            "short_percent": 0,
            "days_to_cover": 0,
            "squeeze_potential": None,
            "signal": None,
        },
        "options_flow": {
            "put_call_ratio": 0,
            "unusual_activity": False,
            "signal": None,
            "flow_sentiment": "UNKNOWN",
        },
        "earnings": {
            "next_date": None,
            "days_until": None,
            "beat_streak": 0,
            "signal": None,
            "quality": None,
        },
        "fundamentals": {
            "market_cap": 0,
            "pe_ratio": 0,
            "forward_pe": 0,
            "peg_ratio": 0,
            "price_to_book": 0,
            "dividend_yield": 0,
            "profit_margin": 0,
            "revenue_growth": 0,
            "earnings_growth": 0,
            "roe": 0,
            "debt_to_equity": 0,
            "beta": 1,
            "52_week_high": 0,
            "52_week_low": 0,
        },
        "technicals": {
            "sma_20": 0,
            "sma_50": 0,
            "sma_200": 0,
            "rsi": 50,
            "trend": "Neutral",
        },
        "news": {
            "major_events": [],
            "summary": None,
            "sentiment": "neutral",
        },
        "thesis": {
            "prediction": "NEUTRAL",
            "bullish_reasons": [],
            "bearish_reasons": [],
            "primary_catalyst": message or "No cached catalyst",
            "confidence": "LOW",
        },
        "coverage": {
            "total_universe": get_stock_count(),
            "tradeable_universe": tradeable_universe,
            "as_of": datetime.now().isoformat(),
        },
    }


def _build_stock_analysis_data(ticker: str, allow_external: bool) -> Dict[str, Any]:
    from app.services.stock_news_analyzer import get_stock_news_analyzer
    from app.services.insider_trading_service import get_insider_service
    from app.services.short_interest_service import get_short_service
    from app.services.options_flow_service import get_options_service
    from app.services.earnings_service import get_earnings_service

    yfinance_svc = yfinance_service
    predictor = enhanced_predictor
    quote = yfinance_svc.get_quote(ticker, allow_external=allow_external)
    if not quote and not allow_external:
        return _empty_stock_analysis_data(ticker, "Quote not cached")
    if not quote:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")

    fundamentals = yfinance_svc.get_fundamentals(ticker, allow_external=allow_external) or {}
    historical = yfinance_svc.get_stock_data(
        ticker,
        period="6mo",
        allow_external=allow_external
    )

    ai_score = None
    try:
        stock_data = predictor.get_stock_data(ticker, allow_external=allow_external)
        if stock_data is not None and len(stock_data) >= 20:
            info = {
                'marketCap': fundamentals.get('marketCap', 0),
                'revenueGrowth': fundamentals.get('revenueGrowth', 0),
                'heldPercentInstitutions': fundamentals.get('institutionalOwnership', 0),
                'heldPercentInsiders': fundamentals.get('insiderOwnership', 0),
            }
            ai_score = predictor.calculate_enhanced_score(ticker, stock_data, info)
    except Exception as e:
        logger.warning(f"Could not calculate AI score for {ticker}: {e}")

    insider_svc = get_insider_service()
    short_svc = get_short_service()
    options_svc = get_options_service()
    earnings_svc = get_earnings_service()

    if allow_external:
        insider_data = insider_svc.get_insider_activity(ticker)
        short_data = short_svc.get_short_interest(ticker)
        options_data = options_svc.get_options_activity(ticker)
        earnings_data = earnings_svc.get_earnings_calendar(ticker)
    else:
        insider_data = insider_svc._get_default_insider_data(ticker)
        short_data = short_svc._get_default_short_data(ticker)
        options_data = options_svc._get_default_options_data(ticker)
        earnings_data = earnings_svc._get_default_earnings_data(ticker)

    major_news = []
    news_summary = None
    if allow_external:
        try:
            news_analyzer = get_stock_news_analyzer()
            major_news = news_analyzer.get_major_news(ticker, days=10)
            if major_news and len(major_news) > 0:
                logger.info(f"Found {len(major_news)} news articles for {ticker}")
            else:
                logger.warning(f"WARNING: No news found for {ticker}")
                major_news = []
            news_summary = news_analyzer.get_news_summary(ticker) if major_news else None
        except Exception as e:
            logger.warning(f"Failed to fetch news for {ticker}: {e}")
            major_news = []
            news_summary = None

    bullish_reasons = []
    bearish_reasons = []

    if ai_score and ai_score["total_score"] > 120:
        bullish_reasons.append(
            f"Strong AI score ({ai_score['total_score']}/230): {ai_score['reasoning']}"
        )

    insider_sentiment = (
        insider_data.get('insider_sentiment')
        or insider_data.get('sentiment')
        or 'UNKNOWN'
    )
    insider_net_value = insider_data.get('net_value', 0)
    insider_net_activity = insider_data.get('net_activity', 0)

    if insider_net_activity >= 3:
        bullish_reasons.append(
            f"Insider buying: Net {insider_net_activity:.0f} transactions"
        )
    elif insider_net_activity <= -3:
        bearish_reasons.append(
            f"Insider selling: Net {abs(insider_net_activity):.0f} transactions"
        )

    if short_data.get('squeeze_potential') in ['EXTREME', 'HIGH']:
        bullish_reasons.append(
            f"Short squeeze setup: {short_data.get('short_percent_float', 0):.1f}% short interest, "
            f"{short_data.get('days_to_cover', 0):.1f} days to cover"
        )

    if options_data.get('signal') == 'UNUSUAL_CALL_ACTIVITY':
        bullish_reasons.append(
            f"Unusual call buying: {options_data.get('call_volume', 0):,} calls vs "
            f"{options_data.get('put_volume', 0):,} puts (PC ratio: "
            f"{options_data.get('put_call_ratio', 0):.2f})"
        )
    elif options_data.get('signal') == 'UNUSUAL_PUT_ACTIVITY':
        bearish_reasons.append(
            f"Heavy put buying: PC ratio {options_data.get('put_call_ratio', 0):.2f}"
        )

    if earnings_data.get('signal') in ['PRE_EARNINGS_RUNUP', 'BEAT_EXPECTED']:
        days_until = earnings_data.get('days_until_earnings', 999)
        if days_until and days_until < 14:
            bullish_reasons.append(
                f"Earnings catalyst: {earnings_data.get('beat_streak', 0)} consecutive beats, "
                f"{days_until} days until report"
            )

    if major_news:
        positive_news = [n for n in major_news[:5] if n.get('sentiment') == 'positive']
        if len(positive_news) >= 3:
            news_highlights = []
            for news in positive_news[:2]:
                headline = news.get('headline', '')
                if headline:
                    news_highlights.append(f'"{headline[:80]}..."')
            bullish_reasons.append(
                f"Positive news momentum: {len(positive_news)} bullish articles including "
                f"{' and '.join(news_highlights[:2])}"
            )

    current_price = quote.get('c', 0)
    if historical is not None and len(historical) >= 50:
        sma_50 = historical['Close'].rolling(50).mean().iloc[-1]
        if current_price > sma_50 * 1.05:
            bullish_reasons.append(
                f"Strong uptrend: Price {((current_price / sma_50 - 1) * 100):.1f}% above 50-day MA"
            )

    prev_close = quote.get('pc', current_price)
    change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0

    analysis = {
        "ticker": ticker,
        "company_name": fundamentals.get('shortName', ticker) if fundamentals else ticker,
        "sector": fundamentals.get('sector', 'Unknown') if fundamentals else 'Unknown',
        "industry": fundamentals.get('industry', 'Unknown') if fundamentals else 'Unknown',
        "quote": {
            "current_price": current_price,
            "previous_close": prev_close,
            "change": current_price - prev_close,
            "change_pct": round(change_pct, 2),
            "day_high": quote.get('h', 0),
            "day_low": quote.get('l', 0),
            "volume": quote.get('v', 0),
        },
        "ai_score": ai_score if ai_score else None,
        "insider_trading": {
            "signal": insider_data.get('signal'),
            "sentiment": insider_sentiment,
            "net_activity": insider_net_activity,
            "net_value": insider_net_value,
            "total_buy_value": insider_data.get('total_buy_value', 0),
            "total_sell_value": insider_data.get('total_sell_value', 0),
            "buys": insider_data.get('insider_buys', insider_data.get('buys', 0)),
            "sells": insider_data.get('insider_sells', insider_data.get('sells', 0)),
        },
        "short_interest": {
            "short_percent": short_data.get('short_percent_float', 0),
            "days_to_cover": short_data.get('days_to_cover', 0),
            "squeeze_potential": short_data.get('squeeze_potential'),
            "signal": short_data.get('signal'),
        },
        "options_flow": {
            "put_call_ratio": options_data.get('put_call_ratio', 0),
            "unusual_activity": options_data.get('unusual_activity', False),
            "signal": options_data.get('signal'),
            "flow_sentiment": options_data.get('flow_sentiment'),
        },
        "earnings": {
            "next_date": earnings_data.get('next_earnings_date'),
            "days_until": earnings_data.get('days_until_earnings'),
            "beat_streak": earnings_data.get('beat_streak', 0),
            "signal": earnings_data.get('signal'),
            "quality": earnings_data.get('earnings_quality'),
        },
        "fundamentals": {
            "market_cap": fundamentals.get('marketCap', 0) if fundamentals else 0,
            "pe_ratio": fundamentals.get('peRatio', 0) if fundamentals else 0,
            "forward_pe": fundamentals.get('forwardPE', 0) if fundamentals else 0,
            "peg_ratio": fundamentals.get('pegRatio', 0) if fundamentals else 0,
            "price_to_book": fundamentals.get('priceToBook', 0) if fundamentals else 0,
            "dividend_yield": fundamentals.get('dividendYield', 0) if fundamentals else 0,
            "profit_margin": fundamentals.get('profitMargins', 0) if fundamentals else 0,
            "revenue_growth": fundamentals.get('revenueGrowth', 0) if fundamentals else 0,
            "earnings_growth": fundamentals.get('earningsGrowth', 0) if fundamentals else 0,
            "roe": fundamentals.get('returnOnEquity', 0) if fundamentals else 0,
            "debt_to_equity": fundamentals.get('debtToEquity', 0) if fundamentals else 0,
            "beta": fundamentals.get('beta', 1) if fundamentals else 1,
            "52_week_high": fundamentals.get('fiftyTwoWeekHigh', 0) if fundamentals else 0,
            "52_week_low": fundamentals.get('fiftyTwoWeekLow', 0) if fundamentals else 0,
        },
        "technicals": {
            "sma_20": float(historical['Close'].rolling(20).mean().iloc[-1])
            if historical is not None and len(historical) >= 20 else 0,
            "sma_50": float(historical['Close'].rolling(50).mean().iloc[-1])
            if historical is not None and len(historical) >= 50 else 0,
            "sma_200": float(historical['Close'].rolling(200).mean().iloc[-1])
            if historical is not None and len(historical) >= 200 else 0,
            "rsi": float(
                historical['Close'].pct_change().rolling(14).apply(
                    lambda x: 100 - 100 / (1 + (x[x > 0].mean() / abs(x[x < 0].mean())))
                    if len(x[x < 0]) > 0 else 50
                ).iloc[-1]
            ) if historical is not None and len(historical) >= 14 else 50,
            "trend": "Bullish"
            if current_price > (
                historical['Close'].rolling(50).mean().iloc[-1]
                if historical is not None and len(historical) >= 50 else current_price
            ) else "Bearish",
        },
        "news": {
            "major_events": major_news[:10],
            "summary": news_summary,
            "sentiment": (
                "positive" if len([n for n in major_news if n.get('sentiment') == 'positive']) > len(major_news) / 2
                else "negative" if len([n for n in major_news if n.get('sentiment') == 'negative']) > len(major_news) / 2
                else "neutral"
            ),
        },
        "thesis": {
            "prediction": (
                "BULLISH" if len(bullish_reasons) > len(bearish_reasons)
                else "BEARISH" if len(bearish_reasons) > len(bullish_reasons)
                else "NEUTRAL"
            ),
            "bullish_reasons": bullish_reasons,
            "bearish_reasons": bearish_reasons,
            "primary_catalyst": (
                bullish_reasons[0] if bullish_reasons
                else bearish_reasons[0] if bearish_reasons
                else "No clear catalyst"
            ),
            "confidence": (
                "HIGH" if abs(len(bullish_reasons) - len(bearish_reasons)) >= 3
                else "MEDIUM" if abs(len(bullish_reasons) - len(bearish_reasons)) >= 1
                else "LOW"
            ),
        },
        "coverage": {
            "total_universe": get_stock_count(),
            "tradeable_universe": len(predictor.ticker_universe),
            "as_of": datetime.now().isoformat(),
        },
    }

    return analysis


async def _refresh_stock_analysis_cache(ticker: str, cache_key: str, stale_key: str, lock_key: str) -> None:
    try:
        analysis = await asyncio.to_thread(_build_stock_analysis_data, ticker, True)
        result = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "data": analysis,
            "cached": False,
        }
        _set_cached_value(cache_key, result, US_ANALYSIS_TTL_SECONDS)
        _set_cached_value(stale_key, result, US_ANALYSIS_STALE_TTL_SECONDS)
    except Exception as exc:
        logger.error("Failed to refresh analysis cache for %s: %s", ticker, exc)
    finally:
        _release_cache_lock(lock_key)


def warm_stock_analysis_cache(
    tickers: List[str],
    allow_external: bool = True,
    force: bool = False
) -> Dict[str, int]:
    if not tickers:
        return {"warmed": 0, "skipped": 0, "failed": 0}

    lock_key = "stock_analysis:warm_lock"
    if not _try_acquire_cache_lock(lock_key, US_ANALYSIS_WARM_LOCK_TTL_SECONDS):
        logger.info("US analysis cache warm already running")
        return {"warmed": 0, "skipped": len(tickers), "failed": 0}

    warmed = 0
    skipped = 0
    failed = 0

    try:
        for raw in tickers:
            try:
                ticker = _normalize_ticker(raw)
            except HTTPException:
                failed += 1
                continue

            cache_key = f"stock_analysis:{ticker}"
            stale_key = f"{cache_key}:stale"

            if not force:
                cached = _get_cached_value(cache_key)
                if cached:
                    skipped += 1
                    continue

            try:
                analysis = _build_stock_analysis_data(ticker, allow_external=allow_external)
                result = {
                    "success": True,
                    "timestamp": datetime.now().isoformat(),
                    "data": analysis,
                    "cached": True,
                    "stale": False,
                }
                _set_cached_value(cache_key, result, US_ANALYSIS_TTL_SECONDS)
                _set_cached_value(stale_key, result, US_ANALYSIS_STALE_TTL_SECONDS)
                warmed += 1
            except Exception as exc:
                logger.warning("US analysis warm failed for %s: %s", ticker, exc)
                failed += 1
    finally:
        _release_cache_lock(lock_key)

    return {"warmed": warmed, "skipped": skipped, "failed": failed}


@router.get("/{ticker}/sentiment")
async def get_stock_sentiment(ticker: str):
    """
    Get social sentiment for a stock

    Args:
        ticker: Stock ticker symbol

    Returns:
        Sentiment analysis from social media
    """
    try:
        ticker = _normalize_ticker(ticker)

        # Check cache (5 minute TTL)
        cache_key = f"social:ticker:{ticker}"
        if redis_cache and redis_cache.is_connected():
            cached_sentiment = redis_cache.get_cached_social_data(ticker)
            if cached_sentiment:
                logger.info(f"Cache hit for stock sentiment: {ticker}")
                return {
                    "success": True,
                    "timestamp": datetime.now().isoformat(),
                    "data": cached_sentiment,
                    "cached": True
                }

        # Would integrate with social scanner service here
        sentiment_data = {
            "ticker": ticker,
            "score": 0.72,
            "label": "Bullish",
            "mentions": {
                "total": 15420,
                "reddit": 8500,
                "twitter": 5200,
                "stocktwits": 1720
            },
            "trending": {
                "last24h": 245.5,
                "last7d": 89.3
            },
            "sentiment_breakdown": {
                "very_bullish": 32,
                "bullish": 28,
                "neutral": 25,
                "bearish": 12,
                "very_bearish": 3
            }
        }

        # Cache sentiment
        if redis_cache and redis_cache.is_connected():
            redis_cache.cache_ticker_social(ticker, sentiment_data, ttl=300)

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "data": sentiment_data,
            "cached": False
        }

    except Exception as e:
        logger.error(f"Error getting stock sentiment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch sentiment: {str(e)}"
        )


@router.get("/short-opportunities")
async def get_short_opportunities(
    timeframe: str = Query("swing", regex="^(day|swing|long)$"),
    limit: int = Query(10, ge=1, le=20)
):
    """
    SHORT OPPORTUNITIES - Find stocks with high short potential
    
    DISCLAIMER: Short selling is high-risk. These are analytical signals only.
    Always use stop-losses and proper risk management.
    
    Analyzes stocks for:
    - Fundamental weakness (high P/E, declining growth, poor margins)
    - Bearish technicals (below MAs, RSI overbought, death cross)
    - Negative news sentiment and catalysts
    - Momentum reversal (recent peak, declining)
    - Distribution volume (heavy selling)
    
    Args:
        timeframe: Trading timeframe (day, swing, long)
        limit: Number of opportunities to return (1-20)
    
    Returns:
        List of short opportunity stocks with:
        - Score (0-100) - higher = better short candidate
        - Current price & downside target
        - Detailed reasoning & signals
        - Risk warnings
    """
    try:
        # Try to import short_predictor - if it fails, return friendly error
        try:
            from app.services.short_predictor import get_short_predictor
            short_predictor_available = True
        except Exception as import_error:
            logger.warning(f"Short predictor not available: {import_error}")
            short_predictor_available = False

        if not short_predictor_available:
            # Return empty result with helpful message instead of crashing
            return {
                "success": True,
                "category": "short_opportunities",
                "timeframe": timeframe,
                "count": 0,
                "data": [],
                "cached": False,
                "message": "Short picks analysis is currently being updated. This feature requires additional data processing capabilities.",
                "disclaimer": "WARNING: SHORT SELLING IS HIGH RISK. Use proper risk management and stop-losses."
            }

        cache_key = f"short_opportunities:{timeframe}:{limit}"

        # Check cache (30 min TTL)
        if redis_cache and redis_cache.is_connected():
            import json
            cached_data = redis_cache.redis_client.get(cache_key)
            if cached_data:
                logger.info("Cache hit for short opportunities")
                result = json.loads(cached_data)
                result['cached'] = True
                return result

        logger.info(f"Generating fresh short opportunities for {timeframe}")

        # Find short opportunities
        short_predictor = get_short_predictor()
        opportunities = short_predictor.find_short_opportunities(
            timeframe=timeframe,
            limit=limit
        )

        result = {
            "success": True,
            "category": "short_opportunities",
            "timeframe": timeframe,
            "count": len(opportunities),
            "data": opportunities,
            "cached": False,
            "disclaimer": "WARNING: SHORT SELLING IS HIGH RISK. Use proper risk management and stop-losses. These are analytical signals only, not financial advice."
        }

        # Cache for 30 minutes
        if redis_cache and redis_cache.is_connected():
            import json
            redis_cache.redis_client.setex(cache_key, 1800, json.dumps(result))

        return result

    except Exception as e:
        logger.error(f"Error in get_short_opportunities: {str(e)}", exc_info=True)
        # Return empty result instead of 500 error
        return {
            "success": True,
            "category": "short_opportunities",
            "timeframe": timeframe,
            "count": 0,
            "data": [],
            "cached": False,
            "message": "Short picks analysis is temporarily unavailable. Please try again later.",
            "disclaimer": "WARNING: SHORT SELLING IS HIGH RISK."
        }


@router.get("/stock/{ticker}/analysis")
async def get_stock_analysis(ticker: str):
    """
    ENHANCED STOCK ANALYSIS - Deep dive with AI reasoning

    Provides comprehensive analysis including:
    - AI prediction score with full breakdown (230 points)
    - WHY this stock will move (news-based reasoning)
    - Insider trading activity
    - Short squeeze potential
    - Options flow signals
    - Earnings momentum
    - Real news from last 10 days
    - Technical & fundamental analysis

    Args:
        ticker: Stock ticker symbol (e.g., AAPL, MSFT)

    Returns:
        Complete stock analysis with AI reasoning and real data
    """
    try:
        ticker = _normalize_ticker(ticker)
        cache_key = f"stock_analysis:{ticker}"
        stale_key = f"{cache_key}:stale"
        lock_key = f"{cache_key}:lock"

        cached = _get_cached_value(cache_key)
        if cached:
            cached["cached"] = True
            cached["stale"] = False
            return cached

        stale = _get_cached_value(stale_key)
        if stale:
            stale["cached"] = True
            stale["stale"] = True
            if not settings.US_CACHE_ONLY:
                if _try_acquire_cache_lock(lock_key, US_ANALYSIS_LOCK_TTL_SECONDS):
                    asyncio.create_task(
                        _refresh_stock_analysis_cache(ticker, cache_key, stale_key, lock_key)
                    )
            return stale

        if settings.US_CACHE_ONLY:
            analysis = _build_stock_analysis_data(ticker, allow_external=False)
            result = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "data": analysis,
                "cached": True,
                "stale": False,
            }
            _set_cached_value(cache_key, result, US_ANALYSIS_TTL_SECONDS)
            _set_cached_value(stale_key, result, US_ANALYSIS_STALE_TTL_SECONDS)
            return result

        if not _try_acquire_cache_lock(lock_key, US_ANALYSIS_LOCK_TTL_SECONDS):
            cached = await _wait_for_cache_value(cache_key)
            if cached:
                cached["cached"] = True
                return cached
            analysis = _empty_stock_analysis_data(ticker, "Analysis warming")
            result = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "data": analysis,
                "cached": True,
                "stale": True,
            }
            _set_cached_value(cache_key, result, US_ANALYSIS_PLACEHOLDER_TTL_SECONDS)
            return result

        try:
            analysis = _build_stock_analysis_data(ticker, allow_external=True)
            result = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "data": analysis,
                "cached": False,
                "stale": False,
            }
            _set_cached_value(cache_key, result, US_ANALYSIS_TTL_SECONDS)
            _set_cached_value(stale_key, result, US_ANALYSIS_STALE_TTL_SECONDS)
            return result
        finally:
            _release_cache_lock(lock_key)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_stock_analysis for {ticker}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze {ticker}: {str(e)}"
        )


# ============================================================================
# CHART DATA ENDPOINT
# ============================================================================

@router.get(
    "/chart/{ticker}",
    summary="Get Price History Chart Data",
    description="Fetch historical OHLCV data for charting"
)
async def get_chart_data(
    ticker: str,
    timeframe: str = '1d',
    limit: int = 100
):
    """
    Get historical price data for charts

    Args:
        ticker: Stock ticker symbol
        timeframe: Data timeframe - 1d (daily), 1h (hourly), 15m (15-minute)
        limit: Number of data points to return (default 100)

    Returns:
        Historical OHLCV data formatted for lightweight-charts
    """
    try:
        ticker = _normalize_ticker(ticker)

        # Map timeframes to yfinance intervals and periods
        interval_map = {
            '1d': ('1d', '1y'),    # Daily data for 1 year
            '1h': ('1h', '1mo'),   # Hourly data for 1 month
            '15m': ('15m', '5d')   # 15-minute data for 5 days
        }

        interval, period = interval_map.get(timeframe, ('1d', '1y'))

        # Get yfinance service
        yfinance_service = get_yfinance_service()

        # Fetch historical data
        historical = yfinance_service.get_historical_data(
            ticker,
            period=period,
            interval=interval,
            allow_external=not settings.US_CACHE_ONLY
        )

        if historical is None or historical.empty:
            return {
                "success": True,
                "ticker": ticker,
                "timeframe": timeframe,
                "count": 0,
                "data": [],
                "message": "Chart cache warming"
            }

        # Take only the last 'limit' rows
        historical = historical.tail(limit)

        # Convert to chart format
        chart_data = []
        for index, row in historical.iterrows():
            chart_data.append({
                "timestamp": index.isoformat(),
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close']),
                "volume": int(row['Volume'])
            })

        return {
            "success": True,
            "data": chart_data,
            "ticker": ticker,
            "timeframe": timeframe,
            "count": len(chart_data)
        }

    except Exception as e:
        logger.error(f"Error fetching chart data for {ticker}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "data": []
        }
