"""
TradeMaster Pro - Finland (Nasdaq Helsinki) API Router
=======================================================

API endpoints for Finnish stocks from Nasdaq Helsinki.
All prices are in EUR.

Endpoints:
- GET /api/fi/universe - List of all Finnish tickers
- GET /api/fi/quote/{ticker} - Current quote
- GET /api/fi/history/{ticker} - Historical OHLCV data
- GET /api/fi/analysis/{ticker} - Comprehensive analysis
- GET /api/fi/rank - Top ranked Finnish stocks
- GET /api/fi/movers - Top gainers and losers
- GET /api/fi/sectors - Sector breakdown
"""

from fastapi import APIRouter, HTTPException, Query, Request
from typing import Optional
import logging

from app.services.fi_data import get_fi_data_service
from app.services.fi_event_service import get_fi_event_service
from app.services.fi_insight_service import get_fi_insight_service
from app.services.fi_macro_service import get_fi_macro_service
from app.services.fi_metals_service import get_fi_metals_service
from app.utils.admin_auth import is_force_refresh_allowed

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/fi",
    tags=["finland"]
)


@router.get("/universe")
async def get_universe():
    """
    Get the complete Finnish stock universe (Nasdaq Helsinki)

    Returns:
        Complete list of Finnish stocks with metadata
    """
    try:
        fi_service = get_fi_data_service()
        universe = fi_service.get_universe()

        return {
            "success": True,
            "exchange": universe["exchange"],
            "currency": universe["currency"],
            "country": universe["country"],
            "totalCount": universe["total_count"],
            "sectors": universe["sectors"],
            "blueChips": universe["blue_chips"],
            "stocks": universe["stocks"]
        }

    except Exception as e:
        logger.error(f"Error getting Finnish universe: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quote/{ticker}")
async def get_quote(ticker: str):
    """
    Get current quote for a Finnish stock

    Args:
        ticker: Stock ticker (e.g., NOKIA or NOKIA.HE)

    Returns:
        Current price and daily change data
    """
    try:
        fi_service = get_fi_data_service()
        quote = fi_service.get_quote(ticker)

        if not quote:
            raise HTTPException(
                status_code=404,
                detail=f"Quote not found for {ticker}"
            )

        return {
            "success": True,
            "data": quote
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quote for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{ticker}")
async def get_history(
    ticker: str,
    range: str = Query("1y", regex="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|max)$"),
    interval: str = Query("1d", regex="^(1d|1wk|1mo)$")
):
    """
    Get historical OHLCV data for a Finnish stock

    Args:
        ticker: Stock ticker (e.g., NOKIA or NOKIA.HE)
        range: Time range (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)
        interval: Data interval (1d, 1wk, 1mo)

    Returns:
        List of OHLCV data points
    """
    try:
        fi_service = get_fi_data_service()
        history = fi_service.get_history(ticker, range=range, interval=interval)

        if not history:
            return {
                "success": True,
                "ticker": ticker,
                "range": range,
                "interval": interval,
                "count": 0,
                "data": []
            }

        return {
            "success": True,
            "ticker": ticker,
            "range": range,
            "interval": interval,
            "count": len(history),
            "data": history
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting history for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/{ticker}")
async def get_analysis(ticker: str):
    """
    Get comprehensive analysis for a Finnish stock

    Args:
        ticker: Stock ticker (e.g., NOKIA or NOKIA.HE)

    Returns:
        Full analysis including:
        - Profile (name, sector, exchange)
        - Current quote
        - Fundamentals (P/E, margins, growth)
        - Risk metrics (volatility, drawdown)
        - Score (0-100) with breakdown
    """
    try:
        fi_service = get_fi_data_service()
        analysis = fi_service.get_analysis(ticker)

        if not analysis:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis not found for {ticker}"
            )

        return {
            "success": True,
            "data": analysis
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rank")
async def get_rankings(
    limit: int = Query(50, ge=1, le=100)
):
    """
    Get top-ranked Finnish stocks by AI score

    Args:
        limit: Maximum number of stocks to return (1-100)

    Returns:
        List of top stocks sorted by score
    """
    try:
        fi_service = get_fi_data_service()
        rankings = fi_service.get_rankings(limit=limit)

        return {
            "success": True,
            "count": len(rankings),
            "data": rankings
        }

    except Exception as e:
        logger.error(f"Error getting rankings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/movers")
async def get_movers(
    limit: int = Query(10, ge=1, le=20)
):
    """
    Get top gainers and losers for Finnish stocks

    Args:
        limit: Number of stocks per category (1-20)

    Returns:
        Top gainers and losers
    """
    try:
        fi_service = get_fi_data_service()
        movers = fi_service.get_movers(limit=limit)

        return {
            "success": True,
            "gainers": movers["gainers"],
            "losers": movers["losers"]
        }

    except Exception as e:
        logger.error(f"Error getting movers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/momentum")
async def get_weekly_momentum(
    limit: int = Query(10, ge=1, le=20)
):
    """
    Get weekly momentum data for Finnish stocks.

    Returns:
    - Weekly gainers (best 5-day performers)
    - Weekly losers (worst 5-day performers)
    - Unusual volume (stocks with volume > 2x average)
    - RSI signals (overbought/oversold stocks)

    Args:
        limit: Number of stocks per category (1-20)
    """
    try:
        fi_service = get_fi_data_service()
        momentum = fi_service.get_weekly_momentum(limit=limit)

        return {
            "success": True,
            **momentum
        }

    except Exception as e:
        logger.error(f"Error getting momentum: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/potential")
async def get_potential(
    timeframe: str = Query("short", regex="^(short|medium|long)$", description="Timeframe: short, medium, or long"),
    limit: int = Query(10, ge=1, le=50, description="Number of stocks to return")
):
    """
    Get stocks with highest potential based on timeframe.

    Timeframes:
    - short: Days to weeks (momentum, news, technicals)
    - medium: Weeks to months (growth, value catalyst)
    - long: Months to years (deep value, quality, dividends)

    Returns:
        Top potential stocks with scores and reasons
    """
    try:
        fi_service = get_fi_data_service()
        result = fi_service.get_potential_picks(timeframe=timeframe, limit=limit)

        return {
            "success": True,
            "timeframe": result["timeframe"],
            "total": result["total"],
            "data": result["stocks"]
        }

    except Exception as e:
        logger.error(f"Error getting potential stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors")
async def get_sectors():
    """
    Get sector breakdown for Finnish stocks

    Returns:
        List of sectors with stock counts
    """
    try:
        fi_service = get_fi_data_service()
        sectors = fi_service.get_sectors_summary()

        return {
            "success": True,
            "data": sectors
        }

    except Exception as e:
        logger.error(f"Error getting sectors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/macro")
async def get_macro_indicators():
    """
    Get Finnish and Eurozone macro indicators

    Returns:
        Macro indicators including:
        - OMXH25 (Helsinki 25)
        - Euro Stoxx 50
        - DAX
        - VIX
        - EUR/USD, EUR/SEK
        - Gold, Oil
        - Interest rates
    """
    try:
        macro_service = get_fi_macro_service()
        indicators = macro_service.get_macro_indicators()

        return {
            "success": True,
            "data": indicators
        }

    except Exception as e:
        logger.error(f"Error getting macro indicators: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/macro/{code}/history")
async def get_macro_history(
    code: str,
    period: str = Query("1y", regex="^(1mo|3mo|6mo|1y|2y|5y)$"),
    interval: str = Query("1d", regex="^(1d|1wk|1mo)$")
):
    """
    Get historical data for a macro indicator

    Args:
        code: Indicator code (OMXH25, VIX, EUR/USD, etc.)
        period: Time period (1mo, 3mo, 6mo, 1y, 2y, 5y)
        interval: Data interval (1d, 1wk, 1mo)

    Returns:
        Historical OHLCV data for the indicator
    """
    try:
        macro_service = get_fi_macro_service()
        result = macro_service.get_indicator_history(code, period, interval)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"History not found for indicator: {code}"
            )

        return {
            "success": True,
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting macro history for {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metals")
async def get_metals_overview():
    """
    Get precious metals overview (gold, silver)

    Returns:
        List of metals with current prices and key metrics
    """
    try:
        metals_service = get_fi_metals_service()
        result = metals_service.get_metals_overview()

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Error getting metals overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metals/{code}")
async def get_metal_detail(code: str):
    """
    Get detailed data for a specific metal including history

    Args:
        code: Metal code (GOLD or SILVER)

    Returns:
        Metal details with price, metrics, and 1-year history
    """
    try:
        metals_service = get_fi_metals_service()
        result = metals_service.get_metal_detail(code)

        if not result:
            raise HTTPException(status_code=404, detail=f"Metal {code} not found")

        return {
            "success": True,
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metal detail for {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metals/{code}/history")
async def get_metal_history(
    code: str,
    period: str = Query("1y", description="Time period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y"),
    interval: str = Query("1d", description="Data interval: 1m, 5m, 15m, 1h, 1d, 1wk, 1mo")
):
    """
    Get historical data for a metal

    Args:
        code: Metal code (GOLD or SILVER)
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y)
        interval: Data interval (1m, 5m, 15m, 1h, 1d, 1wk, 1mo)

    Returns:
        Historical OHLCV data for charts
    """
    try:
        metals_service = get_fi_metals_service()
        result = metals_service.get_metal_history(code, period=period, interval=interval)

        if not result:
            raise HTTPException(status_code=404, detail=f"Metal history for {code} not found")

        return {
            "success": True,
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metal history for {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock/{ticker}")
async def get_stock_info(ticker: str):
    """
    Get basic stock info from our database

    Args:
        ticker: Stock ticker

    Returns:
        Basic stock information (name, sector)
    """
    try:
        fi_service = get_fi_data_service()
        info = fi_service.get_stock_info(ticker)

        if not info:
            raise HTTPException(
                status_code=404,
                detail=f"Stock not found: {ticker}"
            )

        return {
            "success": True,
            "data": info
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stock info for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/technicals/{ticker}")
async def get_technicals(ticker: str):
    """
    Get technical analysis for a Finnish stock.

    Returns:
    - RSI (Relative Strength Index) - 14 period
    - MACD (Moving Average Convergence Divergence) - 12/26/9
    - Bollinger Bands - 20 period, 2 std
    - Simple Moving Averages - 20, 50, 200
    - Buy/Sell signals and summary

    Example: /api/fi/technicals/NOKIA.HE
    """
    try:
        fi_service = get_fi_data_service()

        # Normalize ticker
        ticker = ticker.upper()
        if not ticker.endswith(".HE"):
            ticker = f"{ticker}.HE"

        # Get history (need at least 200 days for SMA200)
        history = fi_service.get_history(ticker, range="1y", interval="1d")

        if not history or len(history) < 30:
            raise HTTPException(
                status_code=404,
                detail=f"Insufficient history data for {ticker}. Need at least 30 days."
            )

        # Compute technical indicators
        technicals = fi_service.compute_technicals(history)

        # Get basic stock info
        stock_info = fi_service.get_stock_info(ticker)

        return {
            "success": True,
            "data": {
                "ticker": ticker,
                "name": stock_info.get("name") if stock_info else ticker.replace(".HE", ""),
                "sector": stock_info.get("sector") if stock_info else "Unknown",
                **technicals
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting technicals for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screener")
async def screen_stocks(
    # Filters
    sector: Optional[str] = Query(None, description="Filter by sector"),
    market: Optional[str] = Query(None, description="Filter by market (Main/First North)"),
    min_dividend_yield: Optional[float] = Query(None, ge=0, description="Minimum dividend yield %"),
    max_pe: Optional[float] = Query(None, ge=0, description="Maximum P/E ratio"),
    min_pe: Optional[float] = Query(None, ge=0, description="Minimum P/E ratio"),
    max_volatility: Optional[float] = Query(None, ge=0, description="Maximum volatility %"),
    min_return_12m: Optional[float] = Query(None, description="Minimum 12-month return %"),
    min_return_3m: Optional[float] = Query(None, description="Minimum 3-month return %"),
    min_market_cap: Optional[float] = Query(None, ge=0, description="Minimum market cap (EUR)"),
    risk_level: Optional[str] = Query(None, description="Risk level (LOW/MEDIUM/HIGH)"),
    # Sorting
    sort_by: str = Query("score", description="Sort by: score, dividend_yield, pe, return_12m, return_3m, volatility, market_cap"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order: asc or desc"),
    # Pagination
    limit: int = Query(50, ge=1, le=188, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    Screen Finnish stocks by multiple criteria

    Preset filters:
    - High Dividend: min_dividend_yield=3, sort_by=dividend_yield
    - Value Stocks: max_pe=15, min_dividend_yield=2
    - Growth: min_return_12m=20, sort_by=return_12m
    - Low Risk: max_volatility=25, risk_level=LOW
    - Momentum: min_return_3m=10, sort_by=return_3m

    Returns:
        List of stocks matching criteria
    """
    try:
        fi_service = get_fi_data_service()

        filters = {
            "sector": sector,
            "market": market,
            "min_dividend_yield": min_dividend_yield,
            "max_pe": max_pe,
            "min_pe": min_pe,
            "max_volatility": max_volatility,
            "min_return_12m": min_return_12m,
            "min_return_3m": min_return_3m,
            "min_market_cap": min_market_cap,
            "risk_level": risk_level
        }

        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}

        results = fi_service.screen_stocks(
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset
        )

        return {
            "success": True,
            "filters_applied": filters,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "total_matches": results["total"],
            "returned": len(results["stocks"]),
            "offset": offset,
            "data": results["stocks"]
        }

    except Exception as e:
        logger.error(f"Error screening stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events")
async def get_fi_events(
    ticker: Optional[str] = Query(None, description="Ticker symbol (e.g., NOKIA or NOKIA.HE)"),
    types: Optional[str] = Query(None, description="Comma-separated event types (PRESS_RELEASE,INSIDER_TRANSACTION,NEWS,SHORT_POSITION)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    include_analysis: bool = Query(True, description="Include LLM analysis if available"),
):
    """
    Get latest Finnish disclosure/news events (press releases, insider transactions, short positions).
    """
    try:
        event_service = get_fi_event_service()
        event_types = [t.strip().upper() for t in types.split(",")] if types else None
        events = event_service.get_events(
            ticker=ticker,
            limit=limit,
            offset=offset,
            event_types=event_types,
            include_analysis=include_analysis,
        )
        return {
            "success": True,
            "count": len(events),
            "data": events,
        }
    except Exception as e:
        logger.error(f"Error getting FI events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/significant")
async def get_fi_significant_events(
    days: int = Query(7, ge=1, le=30, description="Number of days to look back"),
    limit: int = Query(10, ge=1, le=50),
):
    """
    Get significant Finnish disclosure/news events for the dashboard.
    Filters out generic market notices (turbo warrants, fixing info, etc.)
    and returns only company-specific news with high impact.
    """
    try:
        event_service = get_fi_event_service()
        events = event_service.get_significant_events(days=days, limit=limit)
        return {
            "success": True,
            "count": len(events),
            "data": events,
        }
    except Exception as e:
        logger.error(f"Error getting FI significant events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events/refresh")
async def refresh_fi_events(
    request: Request,
    analyze_new: bool = Query(True, description="Analyze new events with LLM"),
    limit: int = Query(50, ge=1, le=200),
    include_shorts: bool = Query(True, description="Ingest FIVA short positions"),
    include_company_news: bool = Query(True, description="Ingest Nasdaq company news per issuer"),
    include_rss: bool = Query(False, description="Ingest Nasdaq RSS disclosures"),
    include_yfinance: bool = Query(False, description="Ingest yfinance news for a ticker"),
    ticker: Optional[str] = Query(None, description="Ticker for yfinance news ingestion"),
):
    """
    Force refresh FI events (admin-only via x-admin-key or Bearer token).
    """
    if not is_force_refresh_allowed(request):
        raise HTTPException(status_code=403, detail="Admin key required")

    try:
        event_service = get_fi_event_service()
        disclosures = 0
        if include_company_news:
            disclosures += event_service.ingest_nasdaq_company_news_bulk(
                analyze_new=analyze_new,
                limit=limit,
            )
        if include_rss:
            disclosures += event_service.ingest_nasdaq_rss(analyze_new=analyze_new, limit=limit)
        shorts = event_service.ingest_fiva_short_positions(analyze_new=analyze_new) if include_shorts else 0
        yfinance_count = 0
        if include_yfinance and ticker:
            yfinance_count = event_service.ingest_yfinance_news_for_ticker(ticker, limit=10)

        return {
            "success": True,
            "disclosures_added": disclosures,
            "shorts_added": shorts,
            "yfinance_added": yfinance_count,
        }
    except Exception as e:
        logger.error(f"Error refreshing FI events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights")
async def get_fi_insights(
    ticker: str = Query(..., description="Ticker symbol"),
    insight_type: str = Query("FUNDAMENTALS", description="Insight type (FUNDAMENTALS)"),
):
    """
    Get latest AI insight for a Finnish stock.
    """
    try:
        insight_service = get_fi_insight_service()
        insight = insight_service.get_latest_insight(ticker.upper(), insight_type=insight_type.upper())
        return {
            "success": True,
            "data": insight,
        }
    except Exception as e:
        logger.error(f"Error getting FI insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/insights/refresh")
async def refresh_fi_insights(
    request: Request,
    ticker: Optional[str] = Query(None, description="Ticker symbol (optional)"),
):
    """
    Force refresh FI fundamental insights (admin-only).
    """
    if not is_force_refresh_allowed(request):
        raise HTTPException(status_code=403, detail="Admin key required")

    try:
        insight_service = get_fi_insight_service()
        if ticker:
            created = 1 if insight_service.generate_for_ticker(ticker) else 0
        else:
            from app.services.fi_data import get_fi_data_service

            fi_service = get_fi_data_service()
            created = insight_service.generate_fundamental_insights(fi_service.get_all_tickers())

        return {"success": True, "created": created}
    except Exception as e:
        logger.error(f"Error refreshing FI insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ir-headlines/{ticker}")
async def get_ir_headlines(
    ticker: str,
    limit: int = Query(5, ge=1, le=10),
):
    """
    Get latest headlines from company IR page.

    Args:
        ticker: Stock ticker (e.g., NOKIA or NOKIA.HE)
        limit: Max number of headlines (1-10)

    Returns:
        List of headlines with titles and URLs
    """
    try:
        event_service = get_fi_event_service()
        headlines = event_service.fetch_ir_headlines(ticker, limit=limit)

        return {
            "success": True,
            "ticker": ticker,
            "count": len(headlines),
            "data": headlines,
        }
    except Exception as e:
        logger.error(f"Error fetching IR headlines for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# FI Portfolio Analyzer (cache-based, no external API calls)
# ============================================================

from pydantic import BaseModel
from typing import List
import numpy as np


class PortfolioHolding(BaseModel):
    ticker: str
    shares: float
    avgCost: Optional[float] = None


class PortfolioRequest(BaseModel):
    holdings: List[PortfolioHolding]


@router.post("/portfolio/analyze")
async def analyze_fi_portfolio(request: PortfolioRequest):
    """
    Analyze a Finnish stock portfolio using cached data.
    No external API calls - uses only pre-cached data from cache warming.

    Args:
        holdings: List of {ticker: str, shares: float, avgCost: float (optional)}

    Returns:
        Portfolio analysis including:
        - Total value and gain/loss
        - Sector allocation
        - Risk metrics (beta, volatility)
        - Top holdings
        - Diversification score
    """
    try:
        fi_service = get_fi_data_service()
        holdings = request.holdings

        if not holdings:
            return {
                "success": True,
                "data": {
                    "totalValue": 0,
                    "positions": [],
                    "sectors": [],
                    "metrics": {},
                    "recommendations": []
                }
            }

        positions = []
        total_value = 0
        total_cost = 0
        sector_values = {}
        portfolio_beta = 0
        weighted_dividend_yield = 0

        for holding in holdings:
            ticker = holding.ticker.upper()
            if not ticker.endswith(".HE"):
                ticker = f"{ticker}.HE"

            shares = holding.shares
            avg_cost = holding.avgCost or 0

            # Get cached quote (no external API call)
            quote = fi_service.get_quote(ticker)
            if not quote:
                continue

            current_price = quote.get("price", 0)
            if current_price <= 0:
                continue

            current_value = current_price * shares
            cost_basis = avg_cost * shares if avg_cost > 0 else 0
            gain_loss = current_value - cost_basis if cost_basis > 0 else 0
            gain_loss_pct = (gain_loss / cost_basis * 100) if cost_basis > 0 else 0

            # Get cached fundamentals (no external API call)
            fundamentals = fi_service.get_fundamentals(ticker)
            sector = fundamentals.get("sector", "Unknown") if fundamentals else "Unknown"
            beta = fundamentals.get("beta", 1) if fundamentals else 1
            dividend_yield = fundamentals.get("dividendYield", 0) if fundamentals else 0
            name = fundamentals.get("name", ticker) if fundamentals else ticker

            # dividendYield from yfinance is already a decimal (e.g., 0.0486 = 4.86%)
            div_yield_pct = (dividend_yield or 0) * 100 if dividend_yield and dividend_yield < 1 else (dividend_yield or 0)

            position = {
                "ticker": ticker.replace(".HE", ""),
                "name": name,
                "shares": shares,
                "currentPrice": round(current_price, 2),
                "currentValue": round(current_value, 2),
                "avgCost": round(avg_cost, 2) if avg_cost > 0 else None,
                "costBasis": round(cost_basis, 2) if cost_basis > 0 else None,
                "gainLoss": round(gain_loss, 2) if cost_basis > 0 else None,
                "gainLossPct": round(gain_loss_pct, 2) if cost_basis > 0 else None,
                "sector": sector,
                "beta": beta,
                "dividendYield": round(div_yield_pct, 2),
                "weight": 0  # Calculate after total
            }

            positions.append(position)
            total_value += current_value
            total_cost += cost_basis

            # Track sector allocation
            if sector not in sector_values:
                sector_values[sector] = 0
            sector_values[sector] += current_value

        if not positions:
            return {
                "success": True,
                "data": {
                    "totalValue": 0,
                    "positions": [],
                    "sectors": [],
                    "metrics": {},
                    "recommendations": ["Ei löytynyt osakkeita välimuistista. Tarkista tickerit."]
                }
            }

        # Calculate weights and portfolio metrics
        for position in positions:
            weight = position["currentValue"] / total_value if total_value > 0 else 0
            position["weight"] = round(weight * 100, 2)

            # Weighted metrics
            beta = position.get("beta") or 1
            portfolio_beta += weight * beta
            # dividendYield in position is already in percentage (e.g., 4.86)
            weighted_dividend_yield += weight * (position.get("dividendYield") or 0)

        # Sort positions by value
        positions.sort(key=lambda x: x["currentValue"], reverse=True)

        # Sector allocation
        sectors = []
        for sector, value in sorted(sector_values.items(), key=lambda x: x[1], reverse=True):
            sectors.append({
                "sector": sector,
                "value": round(value, 2),
                "weight": round(value / total_value * 100, 2) if total_value > 0 else 0
            })

        # Diversification score (0-100)
        # Based on: number of positions, sector spread, concentration
        n_positions = len(positions)
        n_sectors = len([s for s in sectors if s["weight"] > 5])  # Sectors with >5% weight
        top_3_weight = sum(p["weight"] for p in positions[:3])

        position_score = min(30, n_positions * 3)  # Max 30 for 10+ positions
        sector_score = min(30, n_sectors * 6)  # Max 30 for 5+ sectors
        concentration_score = max(0, 40 - top_3_weight * 0.5)  # Lower concentration = higher score

        diversification_score = round(position_score + sector_score + concentration_score)

        # Risk level based on beta
        if portfolio_beta < 0.8:
            risk_level = "LOW"
        elif portfolio_beta < 1.2:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        # Total gain/loss
        total_gain_loss = total_value - total_cost if total_cost > 0 else None
        total_gain_loss_pct = (total_gain_loss / total_cost * 100) if total_cost > 0 else None

        # Recommendations
        recommendations = []
        if n_positions < 5:
            recommendations.append("Harkitse hajauttamista useampaan osakkeeseen (vähintään 5-10 osaketta).")
        if n_sectors < 3:
            recommendations.append("Salkku on keskittynyt vain muutamaan toimialaan. Harkitse toimialahajauttamista.")
        if top_3_weight > 60:
            recommendations.append(f"Kolme suurinta positiota muodostavat {top_3_weight:.0f}% salkusta. Harkitse painojen tasaamista.")
        if portfolio_beta > 1.3:
            recommendations.append("Salkun beta on korkea. Harkitse matalamman riskin osakkeita.")
        if weighted_dividend_yield < 2:
            recommendations.append("Salkun osinkotuotto on matala. Harkitse osinko-osakkeita kassavirran parantamiseksi.")

        if not recommendations:
            recommendations.append("Salkku vaikuttaa hyvin hajautetulta!")

        # Benchmark comparison (OMXH25 reference values)
        # These are approximate typical values for OMXH25
        omxh25_beta = 1.0  # By definition, market beta is 1
        omxh25_dividend_yield = 4.5  # Typical OMXH25 dividend yield ~4-5%
        omxh25_ytd_return = 8.0  # Placeholder - would need real data

        benchmark = {
            "name": "OMXH25",
            "beta": omxh25_beta,
            "dividendYield": omxh25_dividend_yield,
            "comparison": {
                "betaDiff": round(portfolio_beta - omxh25_beta, 2),
                "betaLabel": "Matalampi riski" if portfolio_beta < omxh25_beta else ("Korkeampi riski" if portfolio_beta > omxh25_beta else "Sama kuin indeksi"),
                "dividendDiff": round(weighted_dividend_yield - omxh25_dividend_yield, 2),
                "dividendLabel": "Korkeampi osinko" if weighted_dividend_yield > omxh25_dividend_yield else ("Matalampi osinko" if weighted_dividend_yield < omxh25_dividend_yield else "Sama kuin indeksi"),
            }
        }

        return {
            "success": True,
            "data": {
                "totalValue": round(total_value, 2),
                "totalCost": round(total_cost, 2) if total_cost > 0 else None,
                "totalGainLoss": round(total_gain_loss, 2) if total_gain_loss is not None else None,
                "totalGainLossPct": round(total_gain_loss_pct, 2) if total_gain_loss_pct is not None else None,
                "positions": positions,
                "sectors": sectors,
                "metrics": {
                    "beta": round(portfolio_beta, 2),
                    "dividendYield": round(weighted_dividend_yield, 2),
                    "diversificationScore": diversification_score,
                    "riskLevel": risk_level,
                    "positionCount": n_positions,
                    "sectorCount": n_sectors
                },
                "benchmark": benchmark,
                "recommendations": recommendations
            }
        }

    except Exception as e:
        logger.error(f"Error analyzing FI portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))
