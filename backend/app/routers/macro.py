from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
import random
import logging
import math
from app.services.macro_analyzer import MacroAnalyzer
from app.services.yfinance_service import get_yfinance_service
from app.services.market_data_service import get_market_data_service
from database.redis.config import get_redis_cache
from app.config.settings import settings

logger = logging.getLogger(__name__)
redis_cache = get_redis_cache()

router = APIRouter(
    prefix="/api/macro",
    tags=["macro"]
)

# Initialize macro analyzer
_macro_analyzer = None

def get_macro_analyzer():
    """Get or create MacroAnalyzer singleton"""
    global _macro_analyzer
    if _macro_analyzer is None:
        _macro_analyzer = MacroAnalyzer()
    return _macro_analyzer


def _safe_float(value: Optional[float]) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


@router.get("/indicators")
async def get_macro_indicators():
    """
    Get key macroeconomic indicators (with 2-minute cache for performance)

    Returns:
        Current values of major economic indicators
    """
    try:
        # CHECK CACHE FIRST - prevents rate limits and speeds up response
        if redis_cache and redis_cache.is_connected():
            cached = redis_cache.get_cached_macro_data()
            if cached and cached.get("data"):
                logger.info("📦 Returning cached macro indicators")
                cached["cached"] = True
                return cached

        yfinance = get_yfinance_service()

        logger.info("Fetching LIVE macro data from yfinance...")

        # Get all data directly from yfinance (bypassing cache and mock data)
        # VIX - Volatility Index
        vix_quote = yfinance.get_quote("^VIX")

        # DXY - US Dollar Index
        dxy_quote = yfinance.get_quote("DX-Y.NYB")

        # S&P 500 for market context
        spx_quote = yfinance.get_quote("^GSPC")

        # NASDAQ 100 (using QQQ ETF as proxy - more reliable than ^NDX)
        ndx_quote = yfinance.get_quote("QQQ")

        # Get commodity prices from yfinance
        oil_ticker = yfinance.get_quote("CL=F")  # WTI Crude Oil
        gold_ticker = yfinance.get_quote("GC=F")  # Gold

        # Get Treasury yields from yfinance
        treasury_10y = yfinance.get_quote("^TNX")  # 10-Year Treasury

        # Build indicators list with LIVE real data (NO CACHE, NO MOCK DATA)
        indicators = []

        # 1. VIX Volatility Index - LIVE from yfinance
        if vix_quote:
            vix_current = _safe_float(vix_quote.get('c'))
            if vix_current is None:
                vix_current = _safe_float(vix_quote.get('pc'))
            if vix_current is None:
                vix_current = 0.0
            vix_prev = _safe_float(vix_quote.get('pc')) or vix_current
            vix_change = vix_current - vix_prev
            vix_change_pct = (vix_change / vix_prev * 100) if vix_prev else 0.0

            indicators.append({
                "id": "vix",
                "label": "VIX",
                "name": "CBOE Volatility Index",
                "shortName": "VIX",
                "currentValue": vix_current,
                "value": vix_current,
                "change": vix_change,
                "changePercent": vix_change_pct,
                "unit": "",
                "description": "Market volatility and fear gauge",
                "lastUpdated": datetime.now().isoformat(),
                "impact": "POSITIVE" if vix_current < 20 else "NEGATIVE"
            })
            logger.info(f"VIX: {vix_current:.2f} ({vix_change_pct:+.2f}%)")

        # 2. US Dollar Index (DXY) - LIVE from yfinance
        if dxy_quote:
            dxy_current = _safe_float(dxy_quote.get('c'))
            if dxy_current is None:
                dxy_current = _safe_float(dxy_quote.get('pc'))
            if dxy_current is None:
                dxy_current = 0.0
            dxy_prev = _safe_float(dxy_quote.get('pc')) or dxy_current
            dxy_change = dxy_current - dxy_prev
            dxy_change_pct = (dxy_change / dxy_prev * 100) if dxy_prev else 0.0

            indicators.append({
                "id": "dxy",
                "label": "DXY",
                "name": "US Dollar Index",
                "shortName": "DXY",
                "currentValue": dxy_current,
                "value": dxy_current,
                "change": dxy_change,
                "changePercent": dxy_change_pct,
                "unit": "",
                "description": "Measure of USD vs basket of currencies",
                "lastUpdated": datetime.now().isoformat(),
                "impact": "NEUTRAL" if abs(dxy_change_pct) < 1 else "NEGATIVE" if dxy_change_pct > 1 else "POSITIVE"
            })
            logger.info(f"DXY: {dxy_current:.2f} ({dxy_change_pct:+.2f}%)")

        # 3. S&P 500 - LIVE from yfinance
        if spx_quote:
            spx_current = _safe_float(spx_quote.get('c'))
            if spx_current is None:
                spx_current = _safe_float(spx_quote.get('pc'))
            if spx_current is None:
                spx_current = 0.0
            spx_prev = _safe_float(spx_quote.get('pc')) or spx_current
            spx_change = spx_current - spx_prev
            spx_change_pct = (spx_change / spx_prev * 100) if spx_prev else 0.0

            indicators.append({
                "id": "spx",
                "label": "S&P 500",
                "name": "S&P 500 Index",
                "shortName": "S&P 500",
                "currentValue": spx_current,
                "value": spx_current,
                "change": spx_change,
                "changePercent": spx_change_pct,
                "unit": "",
                "description": "Broad US equity market index",
                "lastUpdated": datetime.now().isoformat(),
                "impact": "POSITIVE" if spx_change_pct > 0 else "NEGATIVE" if spx_change_pct < 0 else "NEUTRAL"
            })
            logger.info(f"S&P 500: {spx_current:.2f} ({spx_change_pct:+.2f}%)")

        # 4. NASDAQ 100 - LIVE from yfinance
        if ndx_quote:
            ndx_current = _safe_float(ndx_quote.get('c'))
            if ndx_current is None:
                ndx_current = _safe_float(ndx_quote.get('pc'))
            if ndx_current is None:
                ndx_current = 0.0
            ndx_prev = _safe_float(ndx_quote.get('pc')) or ndx_current
            ndx_change = ndx_current - ndx_prev
            ndx_change_pct = (ndx_change / ndx_prev * 100) if ndx_prev else 0.0

            indicators.append({
                "id": "ndx",
                "label": "NASDAQ 100",
                "name": "NASDAQ 100 (QQQ)",
                "shortName": "QQQ",
                "currentValue": ndx_current,
                "value": ndx_current,
                "change": ndx_change,
                "changePercent": ndx_change_pct,
                "unit": "$",
                "description": "Top 100 tech-heavy NASDAQ companies (QQQ ETF)",
                "lastUpdated": datetime.now().isoformat(),
                "impact": "POSITIVE" if ndx_change_pct > 0 else "NEGATIVE" if ndx_change_pct < 0 else "NEUTRAL"
            })
            logger.info(f"NASDAQ 100 (QQQ): ${ndx_current:.2f} ({ndx_change_pct:+.2f}%)")

        # 5. 10-Year Treasury Yield - LIVE from yfinance (renumbered after NDX addition)
        if treasury_10y:
            t10y_current_raw = _safe_float(treasury_10y.get('c'))
            if t10y_current_raw is None:
                t10y_current_raw = _safe_float(treasury_10y.get('pc'))
            if t10y_current_raw is None:
                t10y_current_raw = 0.0
            t10y_current = t10y_current_raw / 10  # TNX is in basis points (divide by 10)
            t10y_prev_raw = _safe_float(treasury_10y.get('pc'))
            if t10y_prev_raw is None:
                t10y_prev_raw = t10y_current_raw
            t10y_prev = t10y_prev_raw / 10
            t10y_change = t10y_current - t10y_prev
            t10y_change_pct = (t10y_change / t10y_prev * 100) if t10y_prev else 0.0

            indicators.append({
                "id": "treasury-yield",
                "label": "10Y Yield",
                "name": "10-Year Treasury Yield",
                "shortName": "10Y Yield",
                "currentValue": t10y_current,
                "value": t10y_current,
                "change": t10y_change,
                "changePercent": t10y_change_pct,
                "unit": "%",
                "description": "U.S. 10-year government bond yield",
                "lastUpdated": datetime.now().isoformat(),
                "impact": "NEGATIVE" if t10y_current > 4.5 else "POSITIVE" if t10y_current < 3.5 else "NEUTRAL"
            })
            logger.info(f"10Y Treasury: {t10y_current:.2f}% ({t10y_change_pct:+.2f}%)")

        # 5. Oil Price - LIVE from yfinance
        if oil_ticker:
            oil_current = _safe_float(oil_ticker.get('c'))
            if oil_current is None:
                oil_current = _safe_float(oil_ticker.get('pc'))
            if oil_current is None:
                oil_current = 0.0
            oil_prev = _safe_float(oil_ticker.get('pc')) or oil_current
            oil_change = oil_current - oil_prev
            oil_change_pct = (oil_change / oil_prev * 100) if oil_prev else 0.0

            indicators.append({
                "id": "oil",
                "label": "Oil",
                "name": "WTI Crude Oil",
                "shortName": "Oil",
                "currentValue": oil_current,
                "value": oil_current,
                "change": oil_change,
                "changePercent": oil_change_pct,
                "unit": "$",
                "description": "West Texas Intermediate crude oil price per barrel",
                "lastUpdated": datetime.now().isoformat(),
                "impact": "NEGATIVE" if oil_change_pct > 3 else "POSITIVE" if oil_change_pct < -3 else "NEUTRAL"
            })
            logger.info(f"Oil (WTI): ${oil_current:.2f} ({oil_change_pct:+.2f}%)")

        # 6. Gold Price - LIVE from yfinance
        if gold_ticker:
            gold_current = _safe_float(gold_ticker.get('c'))
            if gold_current is None:
                gold_current = _safe_float(gold_ticker.get('pc'))
            if gold_current is None:
                gold_current = 0.0
            gold_prev = _safe_float(gold_ticker.get('pc')) or gold_current
            gold_change = gold_current - gold_prev
            gold_change_pct = (gold_change / gold_prev * 100) if gold_prev else 0.0

            indicators.append({
                "id": "gold",
                "label": "Gold",
                "name": "Gold Price",
                "shortName": "Gold",
                "currentValue": gold_current,
                "value": gold_current,
                "change": gold_change,
                "changePercent": gold_change_pct,
                "unit": "$",
                "description": "Gold spot price per troy ounce",
                "lastUpdated": datetime.now().isoformat(),
                "impact": "POSITIVE" if gold_change_pct > 2 else "NEGATIVE" if gold_change_pct < -2 else "NEUTRAL"
            })
            logger.info(f"Gold: ${gold_current:.2f} ({gold_change_pct:+.2f}%)")

        # Calculate summary
        positive = len([i for i in indicators if i["impact"] == "POSITIVE"])
        negative = len([i for i in indicators if i["impact"] == "NEGATIVE"])
        neutral = len([i for i in indicators if i["impact"] == "NEUTRAL"])

        logger.info(f"Fetched {len(indicators)} real-time macro indicators")

        payload = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "overall_sentiment": "POSITIVE" if positive > negative else "NEGATIVE" if negative > positive else "NEUTRAL"
            },
            "count": len(indicators),
            "data": indicators,
            "cached": False
        }
        if redis_cache and redis_cache.is_connected():
            redis_cache.cache_macro_data(payload, ttl=settings.CACHE_TTL_MACRO)

        return payload

    except Exception as e:
        logger.error(f"Error fetching macro indicators: {str(e)}")
        if redis_cache and redis_cache.is_connected():
            cached = redis_cache.get_cached_macro_data()
            if cached and cached.get("data"):
                cached["cached"] = True
                return cached
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-overview")
async def get_market_overview():
    """
    Get comprehensive real-time market overview (ENHANCED)

    Returns:
        - Major indices (S&P 500, NASDAQ, Dow Jones, VIX)
        - Sector performance (9 major sectors)
        - Market sentiment score (0-100)
        - Risk level and trading style recommendations
        - Market status (open/closed/pre-market/after-hours)

    Data sources: yfinance (real-time market data)
    Cache: 2 minutes TTL for optimal performance
    """
    try:
        logger.info("🔄 Fetching comprehensive market overview...")

        market_service = get_market_data_service()
        overview = market_service.get_market_overview()

        return {
            "success": True,
            "data": overview,
            "cached": False
        }

    except Exception as e:
        logger.error(f"❌ Market overview error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fed")
async def get_fed_data():
    """
    Get Federal Reserve related data

    Returns:
        Fed rates, meeting dates, policy outlook
    """

    # Calculate realistic next meeting date (FED meets ~8 times per year, roughly every 6 weeks)
    next_meeting_date = datetime.now() + timedelta(days=42)
    days_until = (next_meeting_date - datetime.now()).days

    fed_data = {
        "currentRate": {
            "value": 4.50,
            "range": "4.25-4.50",
            "lastChange": -0.25,
            "lastChangeDate": (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")
        },
        "nextMeeting": {
            "date": next_meeting_date.strftime("%Y-%m-%d"),
            "daysUntil": days_until,
            "expectedAction": "HOLD",
            "probability": {
                "cut": 25,
                "hold": 65,
                "hike": 10
            }
        },
        "upcomingMeetings": [
            {
                "date": next_meeting_date.strftime("%Y-%m-%d"),
                "type": "FOMC Meeting"
            },
            {
                "date": (next_meeting_date + timedelta(days=42)).strftime("%Y-%m-%d"),
                "type": "FOMC Meeting"
            },
            {
                "date": (next_meeting_date + timedelta(days=84)).strftime("%Y-%m-%d"),
                "type": "FOMC Meeting"
            }
        ],
        "recentStatements": [
            {
                "date": (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d"),
                "summary": "The Committee decided to lower the target range by 25 basis points",
                "sentiment": "DOVISH"
            },
            {
                "date": (datetime.now() - timedelta(days=87)).strftime("%Y-%m-%d"),
                "summary": "Committee will carefully assess incoming economic data",
                "sentiment": "NEUTRAL"
            }
        ],
        "dotPlot": {
            "2025": 4.1,
            "2026": 3.4,
            "2027": 2.9,
            "longerRun": 2.5
        },
        "balanceSheet": {
            "total": 7450000000000,
            "change": -35000000000,
            "asOfDate": datetime.now().isoformat()
        }
    }

    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "data": fed_data
    }


@router.get("/events/upcoming")
async def get_upcoming_events(
    days: int = Query(14, ge=1, le=90),
    type: Optional[str] = Query(None, regex="^(EARNINGS|FDA|FED|IPO|ECONOMIC)$")
):
    """
    Get upcoming economic and market events from REAL sources (ENHANCED)

    Args:
        days: Number of days ahead to look
        type: Filter by event type (EARNINGS, FED, IPO, ECONOMIC)

    Returns:
        List of upcoming events
        Data sources: Finnhub (earnings, IPOs), Economic calendar (key dates)
    """
    try:
        from app.services.calendar_service import get_calendar_service

        # Get calendar service
        calendar_service = get_calendar_service()

        # Get real upcoming events
        events = calendar_service.get_upcoming_events(days=days, event_type=type)

        logger.info(f"✅ Fetched {len(events)} upcoming events")

        return {
            "success": True,
            "days": days,
            "type": type or "ALL",
            "count": len(events),
            "data": events,
            "sources": ["finnhub_earnings", "finnhub_ipo", "economic_calendar"]
        }

    except Exception as e:
        logger.error(f"❌ Upcoming events error: {str(e)}")

        # Return empty result instead of static fallback
        # This prevents showing the same events every day
        return {
            "success": False,
            "error": "Unable to fetch upcoming events. Please try again later.",
            "days": days,
            "type": type or "ALL",
            "count": 0,
            "data": []
        }


@router.get("/calendar")
async def get_economic_calendar(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get economic calendar with all scheduled data releases

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        Economic calendar events
    """

    # Default to next 30 days
    if not start_date:
        start_date = datetime.now().strftime("%Y-%m-%d")
    if not end_date:
        end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    calendar_events = [
        {
            "date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
            "time": "08:30 EST",
            "event": "Initial Jobless Claims",
            "importance": "MEDIUM",
            "country": "US",
            "previous": "220K",
            "forecast": "225K",
            "actual": None
        },
        {
            "date": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
            "time": "08:30 EST",
            "event": "Consumer Price Index (CPI)",
            "importance": "HIGH",
            "country": "US",
            "previous": "3.7%",
            "forecast": "3.2%",
            "actual": None
        },
        {
            "date": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d"),
            "time": "08:30 EST",
            "event": "Non-Farm Payrolls",
            "importance": "HIGH",
            "country": "US",
            "previous": "187K",
            "forecast": "200K",
            "actual": None
        },
        {
            "date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
            "time": "14:00 EST",
            "event": "FOMC Meeting Minutes",
            "importance": "HIGH",
            "country": "US",
            "previous": None,
            "forecast": None,
            "actual": None
        },
        {
            "date": (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"),
            "time": "10:00 EST",
            "event": "Consumer Confidence",
            "importance": "MEDIUM",
            "country": "US",
            "previous": "106.1",
            "forecast": "105.0",
            "actual": None
        }
    ]

    return {
        "success": True,
        "start_date": start_date,
        "end_date": end_date,
        "count": len(calendar_events),
        "data": calendar_events
    }


@router.get("/market-sentiment")
async def get_market_sentiment():
    """
    Get overall market sentiment indicators

    Returns:
        Composite market sentiment score and components
    """

    sentiment_data = {
        "overall": {
            "score": 68,
            "label": "BULLISH",
            "trend": "IMPROVING"
        },
        "components": {
            "vix": {
                "value": 14.85,
                "signal": "LOW_FEAR",
                "weight": 20
            },
            "putCallRatio": {
                "value": 0.82,
                "signal": "BULLISH",
                "weight": 15
            },
            "advanceDecline": {
                "ratio": 1.8,
                "signal": "STRONG",
                "weight": 15
            },
            "newHighsLows": {
                "ratio": 2.5,
                "signal": "POSITIVE",
                "weight": 10
            },
            "breadth": {
                "percentAbove50MA": 68,
                "signal": "HEALTHY",
                "weight": 15
            },
            "momentum": {
                "score": 72,
                "signal": "STRONG",
                "weight": 15
            },
            "volatility": {
                "score": 65,
                "signal": "MODERATE",
                "weight": 10
            }
        },
        "sectorsStrength": [
            {"sector": "Technology", "score": 85},
            {"sector": "Communication Services", "score": 78},
            {"sector": "Consumer Discretionary", "score": 72},
            {"sector": "Financials", "score": 68},
            {"sector": "Healthcare", "score": 65},
            {"sector": "Industrials", "score": 62},
            {"sector": "Materials", "score": 58},
            {"sector": "Energy", "score": 55},
            {"sector": "Utilities", "score": 45},
            {"sector": "Real Estate", "score": 42}
        ],
        "riskAppetite": "HIGH"
    }

    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "data": sentiment_data
    }
