"""
Portfolio Management API Endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Request
from typing import List, Optional
from pydantic import BaseModel
import logging
from datetime import datetime
import asyncio
import hashlib
import json

from app.services.portfolio_analyzer import get_portfolio_analyzer
from app.services.smart_alerts import get_smart_alerts_system
from app.utils.admin_auth import is_force_refresh_allowed
from app.services.stock_universe import get_all_stocks, SECTOR_MAPPING
from app.services.risk_management import (
    get_track_record_system,
    get_position_calculator,
    get_stop_loss_calculator
)
from app.utils.simple_cache import get_cache
from database.redis.config import get_redis_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio")

PORTFOLIO_ANALYZE_CACHE_TTL = 120
PORTFOLIO_PERF_CACHE_TTL = 300
PORTFOLIO_LOCK_TTL = 30
PORTFOLIO_WAIT_SECONDS = 2.0
PORTFOLIO_WAIT_INTERVAL = 0.1


def _normalize_holdings(holdings: List[dict]) -> List[dict]:
    normalized = []
    for holding in holdings:
        ticker = holding.get("ticker")
        if not ticker:
            continue
        normalized.append({
            "ticker": str(ticker).strip().upper(),
            "shares": int(holding.get("shares", 0) or 0),
            "avg_cost": float(holding.get("avg_cost", 0) or 0),
            "currency": holding.get("currency"),
            "market": holding.get("market"),
            "asset_type": holding.get("asset_type"),
        })
    normalized.sort(key=lambda item: item["ticker"])
    return normalized


def _hash_payload(payload: dict) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _try_acquire_lock(cache, lock_key: str, ttl: int) -> bool:
    client = getattr(cache, "redis_client", None)
    if not client or not hasattr(client, "set"):
        return True
    try:
        return bool(client.set(lock_key, "1", nx=True, ex=ttl))
    except TypeError:
        return True
    except Exception:
        return False


def _release_lock(cache, lock_key: str) -> None:
    client = getattr(cache, "redis_client", None)
    if not client:
        return
    try:
        client.delete(lock_key)
    except Exception:
        return


async def _wait_for_cached(cache, cache_key: str) -> Optional[dict]:
    attempts = max(1, int(PORTFOLIO_WAIT_SECONDS / PORTFOLIO_WAIT_INTERVAL))
    for _ in range(attempts):
        await asyncio.sleep(PORTFOLIO_WAIT_INTERVAL)
        try:
            cached = cache.get(cache_key)
        except Exception:
            cached = None
        if cached:
            return cached
    return None


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class Holding(BaseModel):
    """Single portfolio holding"""
    ticker: str
    shares: int
    avg_cost: float = 0
    currency: Optional[str] = None
    market: Optional[str] = None
    asset_type: Optional[str] = None


class PortfolioRequest(BaseModel):
    """Portfolio analysis request"""
    holdings: List[Holding]


class PortfolioPerformanceRequest(BaseModel):
    """Portfolio performance series request"""
    holdings: List[Holding]
    period: Optional[str] = "6mo"
    benchmarks: Optional[List[str]] = None


class WatchlistRequest(BaseModel):
    """Watchlist for alerts"""
    tickers: List[str]


class HistoricalPick(BaseModel):
    """Historical pick for track record"""
    ticker: str
    entry_price: float
    target_price: float
    days_held: int = 7


class TrackRecordRequest(BaseModel):
    """Track record calculation request"""
    picks: List[HistoricalPick]


class SimpleTradeRecord(BaseModel):
    """Simple trade for track record"""
    ticker: str
    return_pct: float = 0  # Alias for 'return' which is reserved in Python


class SimpleTrackRecordRequest(BaseModel):
    """Simple track record request"""
    trades: List[SimpleTradeRecord]


class PositionSizeRequest(BaseModel):
    """Position sizing request"""
    account_value: float
    risk_per_trade: float  # 1-5%
    entry_price: float
    stop_loss_price: float


class StopLossRequest(BaseModel):
    """Stop loss calculation request"""
    ticker: str
    entry_price: float
    risk_tolerance: str = 'MEDIUM'  # LOW, MEDIUM, HIGH


class SimpleStopLossRequest(BaseModel):
    """Simple stop loss calculation"""
    entry_price: float
    account_value: float
    position_size: float  # number of shares


# ============================================================================
# PORTFOLIO ENDPOINTS
# ============================================================================

@router.post("/analyze")
async def analyze_portfolio(request: PortfolioRequest):
    """
    Analyze portfolio health and get recommendations

    **Example Request:**
    ```json
    {
        "holdings": [
            {"ticker": "AAPL", "shares": 100, "avg_cost": 150.0},
            {"ticker": "MSFT", "shares": 50, "avg_cost": 300.0}
        ]
    }
    ```

    **Returns:**
    - Total portfolio value
    - Health score (0-100)
    - Risk analysis
    - Diversification metrics
    - Rebalancing recommendations
    - Alerts
    """
    try:
        logger.info(f"Analyzing portfolio with {len(request.holdings)} positions")

        analyzer = get_portfolio_analyzer()
        holdings_data = [h.dict() for h in request.holdings]
        normalized_holdings = _normalize_holdings(holdings_data)
        cache = get_redis_cache()
        cache_key = f"portfolio:analysis:{_hash_payload({'holdings': normalized_holdings})}"

        if cache and cache.is_connected():
            cached = cache.get(cache_key)
            if cached:
                cached["cached"] = True
                return cached

        if cache and cache.is_connected():
            lock_key = f"{cache_key}:lock"
            if not _try_acquire_lock(cache, lock_key, PORTFOLIO_LOCK_TTL):
                cached = await _wait_for_cached(cache, cache_key)
                if cached:
                    cached["cached"] = True
                    return cached
                warming = analyzer._empty_portfolio_response()
                warming["summary"]["status"] = "WARMING"
                warming["summary"]["message"] = (
                    "Salkun analyysi on jonossa. Yrita hetken paasta uudelleen."
                )
                return {"success": True, "data": warming}

            try:
                analysis = analyzer.analyze_portfolio(normalized_holdings)
                result = {"success": True, "data": analysis}
                cache.setex(cache_key, PORTFOLIO_ANALYZE_CACHE_TTL, result)
                return result
            finally:
                _release_lock(cache, lock_key)

        analysis = analyzer.analyze_portfolio(normalized_holdings)
        return {
            "success": True,
            "data": analysis
        }

    except Exception as e:
        logger.error(f"Error analyzing portfolio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/performance")
async def get_portfolio_performance(request: PortfolioPerformanceRequest):
    """
    Get normalized portfolio performance series vs benchmarks.

    **Example Request:**
    ```json
    {
        "holdings": [
            {"ticker": "NOKIA.HE", "shares": 100, "avg_cost": 3.5},
            {"ticker": "SPY", "shares": 5, "avg_cost": 420}
        ],
        "period": "6mo",
        "benchmarks": ["^OMXH25", "SPY"]
    }
    ```
    """
    try:
        analyzer = get_portfolio_analyzer()
        holdings_data = [h.dict() for h in request.holdings]
        normalized_holdings = _normalize_holdings(holdings_data)
        period = request.period or "6mo"
        benchmarks = request.benchmarks or ["^OMXH25", "SPY"]
        normalized_benchmarks = sorted({str(b).strip().upper() for b in benchmarks if b})
        cache = get_redis_cache()
        cache_key = f"portfolio:performance:{_hash_payload({'holdings': normalized_holdings, 'period': period, 'benchmarks': normalized_benchmarks})}"

        if cache and cache.is_connected():
            cached = cache.get(cache_key)
            if cached:
                cached["cached"] = True
                return cached

        if cache and cache.is_connected():
            lock_key = f"{cache_key}:lock"
            if not _try_acquire_lock(cache, lock_key, PORTFOLIO_LOCK_TTL):
                cached = await _wait_for_cached(cache, cache_key)
                if cached:
                    cached["cached"] = True
                    return cached
                return {
                    "success": True,
                    "data": {
                        "series": [],
                        "benchmarks": normalized_benchmarks,
                        "message": "Kehityssarja muodostuu taustalla. Yrita hetken paasta uudelleen."
                    }
                }

            try:
                result = analyzer.get_portfolio_performance_series(
                    normalized_holdings,
                    period=period,
                    benchmarks=normalized_benchmarks
                )
                response = {"success": True, "data": result}
                cache.setex(cache_key, PORTFOLIO_PERF_CACHE_TTL, response)
                return response
            finally:
                _release_lock(cache, lock_key)

        result = analyzer.get_portfolio_performance_series(
            normalized_holdings,
            period=period,
            benchmarks=normalized_benchmarks
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error generating portfolio performance series: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def get_portfolio_health(
    tickers: str = Query(..., description="Comma-separated list of tickers"),
    shares: str = Query(..., description="Comma-separated list of share counts"),
    costs: str = Query("", description="Comma-separated list of avg costs (optional)")
):
    """
    Quick portfolio health check (GET endpoint)

    **Example:**
    `/api/portfolio/health?tickers=AAPL,MSFT&shares=100,50&costs=150,300`

    **Returns:**
    - Health score
    - Risk level
    - Quick summary
    """
    try:
        ticker_list = tickers.split(',')
        shares_list = [int(s) for s in shares.split(',')]
        costs_list = [float(c) for c in costs.split(',')] if costs else [0] * len(ticker_list)

        if len(ticker_list) != len(shares_list):
            raise ValueError("Tickers and shares count mismatch")

        holdings = [
            {"ticker": t, "shares": s, "avg_cost": c}
            for t, s, c in zip(ticker_list, shares_list, costs_list)
        ]

        analyzer = get_portfolio_analyzer()
        analysis = analyzer.analyze_portfolio(holdings)

        return {
            "success": True,
            "data": {
                "health_score": analysis['health_score'],
                "risk_level": analysis['risk_score']['level'],
                "diversification_level": analysis['diversification']['level'],
                "total_value": analysis['total_value'],
                "summary": analysis['summary']
            }
        }

    except Exception as e:
        logger.error(f"Error getting portfolio health: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# ALERTS ENDPOINTS
# ============================================================================

@router.post("/alerts")
async def get_alerts(request: WatchlistRequest):
    """
    Get smart alerts for watchlist stocks

    **Example Request:**
    ```json
    {
        "tickers": ["AAPL", "MSFT", "TSLA", "NVDA"]
    }
    ```

    **Returns:**
    - Price spikes (>5%)
    - Volume spikes (>2x average)
    - Major news events
    - 52-week highs/lows
    - Technical breakouts
    """
    try:
        logger.info(f"Checking alerts for {len(request.tickers)} tickers")

        alerts_system = get_smart_alerts_system()
        alerts = alerts_system.check_alerts(request.tickers)

        return {
            "success": True,
            "data": {
                "total": len(alerts),
                "alerts": alerts
            }
        }

    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/{ticker}")
async def get_ticker_alerts(ticker: str):
    """
    Get alerts for a specific ticker

    **Example:**
    `/api/portfolio/alerts/AAPL`

    **Returns:**
    Alerts specific to the ticker
    """
    try:
        alerts_system = get_smart_alerts_system()
        alerts = alerts_system.check_alerts([ticker.upper()])

        return {
            "success": True,
            "data": {
                "ticker": ticker.upper(),
                "total": len(alerts),
                "alerts": alerts
            }
        }

    except Exception as e:
        logger.error(f"Error getting alerts for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watchlist/summary")
async def get_watchlist_summary(request: WatchlistRequest):
    """
    Get summary of alerts for entire watchlist

    **Example Request:**
    ```json
    {
        "tickers": ["AAPL", "MSFT", "TSLA", "NVDA", "GOOGL"]
    }
    ```

    **Returns:**
    - Total alerts count
    - Alerts by type (PRICE_SPIKE, VOLUME_SPIKE, NEWS_IMPACT, etc)
    - Severity breakdown
    - Recent alerts
    """
    try:
        alerts_system = get_smart_alerts_system()
        summary = alerts_system.get_watchlist_alerts(request.tickers)

        return {
            "success": True,
            "data": summary
        }

    except Exception as e:
        logger.error(f"Error getting watchlist summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/universe")
async def get_universe_alerts(
    limit: int = Query(20, ge=1, le=50),
    force_refresh: bool = Query(False),
    request: Request = None
):
    """
    Get smart alerts for the full program stock universe.

    Returns:
    - Total scanned tickers
    - Top alerts across the universe
    """
    try:
        if force_refresh and not is_force_refresh_allowed(request):
            raise HTTPException(
                status_code=403,
                detail="force_refresh requires X-Admin-Key or Bearer admin token"
            )

        cache = get_cache()
        cache_key = f"alerts:universe:{limit}"
        if not force_refresh:
            cached = cache.get(cache_key)
            if cached:
                return {"success": True, "data": cached, "cached": True}

        tickers = get_all_stocks()
        alerts_system = get_smart_alerts_system()
        alerts = alerts_system.check_alerts(
            tickers,
            limit=limit,
            include_news=False,
            max_workers=8
        )

        result = {
            "total_scanned": len(tickers),
            "total_alerts": len(alerts),
            "alerts": alerts,
            "generated_at": datetime.now().isoformat()
        }
        cache.set(cache_key, result, ttl=900)

        return {"success": True, "data": result, "cached": False}

    except Exception as e:
        logger.error(f"Error getting universe alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/universe/summary")
async def get_universe_summary():
    """
    Get summary for the full program stock universe.

    Returns:
    - Total stocks
    - Sector breakdown (counts and percentages)
    """
    try:
        tickers = get_all_stocks()
        total = len(tickers)
        sector_lookup = {}
        for sector, sector_tickers in SECTOR_MAPPING.items():
            for ticker in sector_tickers:
                if ticker not in sector_lookup:
                    sector_lookup[ticker] = sector

        sector_counts = {}
        for ticker in tickers:
            sector = sector_lookup.get(ticker, "other")
            sector_counts[sector] = sector_counts.get(sector, 0) + 1

        sector_breakdown = [
            {
                "sector": sector,
                "count": count,
                "percentage": round((count / total) * 100, 1) if total else 0
            }
            for sector, count in sorted(
                sector_counts.items(),
                key=lambda item: item[1],
                reverse=True
            )
        ]

        return {
            "success": True,
            "data": {
                "total_stocks": total,
                "sector_breakdown": sector_breakdown,
                "as_of": datetime.now().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Error getting universe summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# RISK MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/track-record")
async def get_track_record(request: TrackRecordRequest):
    """
    Calculate track record for historical picks

    **Example Request:**
    ```json
    {
        "picks": [
            {"ticker": "AAPL", "entry_price": 150.0, "target_price": 165.0, "days_held": 7},
            {"ticker": "MSFT", "entry_price": 300.0, "target_price": 320.0, "days_held": 7}
        ]
    }
    ```

    **Returns:**
    - Win rate
    - Average return
    - Best/worst picks
    - Target hit rate
    - Performance level
    """
    try:
        logger.info(f"Calculating track record for {len(request.picks)} picks")

        track_record = get_track_record_system()
        picks_data = [p.dict() for p in request.picks]
        summary = track_record.get_track_record_summary(picks_data)

        return {
            "success": True,
            "data": summary
        }

    except Exception as e:
        logger.error(f"Error calculating track record: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/position-size")
async def calculate_position_size(request: PositionSizeRequest):
    """
    Calculate optimal position size based on risk

    **Example Request:**
    ```json
    {
        "account_value": 10000,
        "risk_per_trade": 2.0,
        "entry_price": 150.0,
        "stop_loss_price": 145.0
    }
    ```

    **Returns:**
    - recommended_shares: Number of shares to buy
    - position_value: Total position value
    - risk_amount: Dollar amount at risk
    - max_loss_per_share: Maximum loss per share
    """
    try:
        calculator = get_position_calculator()
        result = calculator.calculate_position_size(
            request.account_value,
            request.risk_per_trade,
            request.entry_price,
            request.stop_loss_price
        )

        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])

        # Map to frontend expected format
        return {
            "success": True,
            "data": {
                "recommended_shares": result.get('shares', 0),
                "position_value": result.get('position_value', 0),
                "risk_amount": result.get('risk_amount', 0),
                "max_loss_per_share": result.get('risk_per_share', 0),
                "position_pct": result.get('position_pct', 0),
                "recommendation": result.get('recommendation', '')
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating position size: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop-loss")
async def calculate_stop_loss(request: StopLossRequest):
    """
    Calculate optimal stop loss level

    **Example Request:**
    ```json
    {
        "ticker": "AAPL",
        "entry_price": 150.0,
        "risk_tolerance": "MEDIUM"
    }
    ```

    **Risk Tolerance:**
    - LOW: 3% stop loss
    - MEDIUM: 5% stop loss
    - HIGH: 8% stop loss

    **Returns:**
    - Recommended stop price
    - Risk per share
    - Risk percentage
    - Method used (technical or percentage)
    """
    try:
        calculator = get_stop_loss_calculator()
        result = calculator.calculate_stop_loss(
            request.ticker.upper(),
            request.entry_price,
            request.risk_tolerance.upper()
        )

        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating stop loss: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stop-loss/{ticker}")
async def get_stop_loss(
    ticker: str,
    entry_price: float = Query(..., description="Entry price"),
    risk_tolerance: str = Query("MEDIUM", description="Risk tolerance (LOW/MEDIUM/HIGH)")
):
    """
    Quick stop loss calculation (GET endpoint)

    **Example:**
    `/api/portfolio/stop-loss/AAPL?entry_price=150&risk_tolerance=MEDIUM`

    **Returns:**
    Stop loss recommendation
    """
    try:
        calculator = get_stop_loss_calculator()
        result = calculator.calculate_stop_loss(
            ticker.upper(),
            entry_price,
            risk_tolerance.upper()
        )

        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])

        return {
            "success": True,
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating stop loss: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# SIMPLIFIED RISK MANAGEMENT ENDPOINTS (for frontend compatibility)
# ============================================================================

@router.post("/track-record-simple")
async def calculate_simple_track_record(request: SimpleTrackRecordRequest):
    """
    Calculate track record from simple trade list with returns

    **Example Request:**
    ```json
    {
        "trades": [
            {"ticker": "AAPL", "return_pct": 12.5},
            {"ticker": "MSFT", "return_pct": -3.2},
            {"ticker": "NVDA", "return_pct": 8.7}
        ]
    }
    ```

    **Returns:**
    - total_picks: Number of trades
    - winning_picks: Number of profitable trades
    - losing_picks: Number of losing trades
    - win_rate: Percentage of winning trades
    - avg_return: Average return across all trades
    - performance_level: EXCELLENT, GOOD, AVERAGE, POOR, VERY_POOR
    """
    try:
        trades = request.trades

        if not trades:
            return {
                "success": True,
                "data": {
                    "total_picks": 0,
                    "winning_picks": 0,
                    "losing_picks": 0,
                    "win_rate": 0,
                    "avg_return": 0,
                    "performance_level": "NONE"
                }
            }

        # Calculate statistics
        total_picks = len(trades)
        winning_picks = len([t for t in trades if t.return_pct > 0])
        losing_picks = len([t for t in trades if t.return_pct <= 0])

        win_rate = (winning_picks / total_picks * 100) if total_picks > 0 else 0
        avg_return = sum([t.return_pct for t in trades]) / total_picks if total_picks > 0 else 0

        # Determine performance level
        if win_rate >= 70 and avg_return >= 5:
            performance_level = "EXCELLENT"
        elif win_rate >= 60 and avg_return >= 3:
            performance_level = "GOOD"
        elif win_rate >= 50 and avg_return >= 0:
            performance_level = "AVERAGE"
        elif win_rate >= 40:
            performance_level = "POOR"
        else:
            performance_level = "VERY_POOR"

        return {
            "success": True,
            "data": {
                "total_picks": total_picks,
                "winning_picks": winning_picks,
                "losing_picks": losing_picks,
                "win_rate": round(win_rate, 1),
                "avg_return": round(avg_return, 2),
                "performance_level": performance_level
            }
        }

    except Exception as e:
        logger.error(f"Error calculating simple track record: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop-loss-simple")
async def calculate_simple_stop_loss(request: SimpleStopLossRequest):
    """
    Calculate stop loss levels based on risk percentages

    **Example Request:**
    ```json
    {
        "entry_price": 150.0,
        "account_value": 10000,
        "position_size": 100
    }
    ```

    **Returns:**
    - conservative: 8% stop loss
    - moderate: 5% stop loss
    - aggressive: 3% stop loss
    - recommendations for each level
    """
    try:
        entry_price = request.entry_price
        account_value = request.account_value
        position_size = request.position_size

        # Calculate position value
        position_value = entry_price * position_size
        position_pct = (position_value / account_value * 100) if account_value > 0 else 0

        # Calculate stop loss levels
        conservative_pct = 0.08  # 8% stop
        moderate_pct = 0.05      # 5% stop
        aggressive_pct = 0.03    # 3% stop

        conservative_price = entry_price * (1 - conservative_pct)
        moderate_price = entry_price * (1 - moderate_pct)
        aggressive_price = entry_price * (1 - aggressive_pct)

        # Calculate max loss for each level
        conservative_loss = (entry_price - conservative_price) * position_size
        moderate_loss = (entry_price - moderate_price) * position_size
        aggressive_loss = (entry_price - aggressive_price) * position_size

        # Calculate loss as % of account
        conservative_loss_pct = (conservative_loss / account_value * 100) if account_value > 0 else 0
        moderate_loss_pct = (moderate_loss / account_value * 100) if account_value > 0 else 0
        aggressive_loss_pct = (aggressive_loss / account_value * 100) if account_value > 0 else 0

        return {
            "success": True,
            "data": {
                "conservative": round(conservative_price, 2),
                "moderate": round(moderate_price, 2),
                "aggressive": round(aggressive_price, 2),
                "recommendations": {
                    "conservative": f"8% stop at ${conservative_price:.2f} (${conservative_loss:.2f} max loss, {conservative_loss_pct:.1f}% of account)",
                    "moderate": f"5% stop at ${moderate_price:.2f} (${moderate_loss:.2f} max loss, {moderate_loss_pct:.1f}% of account)",
                    "aggressive": f"3% stop at ${aggressive_price:.2f} (${aggressive_loss:.2f} max loss, {aggressive_loss_pct:.1f}% of account)"
                }
            }
        }

    except Exception as e:
        logger.error(f"Error calculating simple stop loss: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
