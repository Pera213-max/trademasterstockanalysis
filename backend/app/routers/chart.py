"""
TradeMaster Pro - Chart Data Router
====================================

Provides historical price data for charting
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging
from datetime import datetime, timedelta
from app.services.yfinance_service import get_yfinance_service
from app.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/chart",
    tags=["chart"]
)

# Initialize service
yfinance_service = get_yfinance_service()


@router.get("/{ticker}")
async def get_chart_data(
    ticker: str,
    timeframe: str = Query("1d", regex="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|max|1m|5m|15m|30m|1h|4h)$"),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Get historical chart data for a ticker

    Args:
        ticker: Stock symbol (e.g., AAPL, MSFT)
        timeframe: Chart timeframe
            - Intraday: 1m, 5m, 15m, 30m, 1h, 4h
            - Daily+: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max
        limit: Number of data points to return

    Returns:
        Historical OHLCV data formatted for charting

    Example:
        /api/chart/AAPL?timeframe=1d&limit=100
    """
    try:
        ticker = ticker.upper()

        # Map timeframe to yfinance period/interval
        period_map = {
            # Intraday timeframes (last 7 days max for intraday)
            "1m": {"period": "7d", "interval": "1m"},
            "5m": {"period": "7d", "interval": "5m"},
            "15m": {"period": "7d", "interval": "15m"},
            "30m": {"period": "7d", "interval": "30m"},
            "1h": {"period": "1mo", "interval": "1h"},
            "4h": {"period": "3mo", "interval": "1d"},  # 4h not supported, fallback to daily

            # Daily+ timeframes
            "1d": {"period": "1mo", "interval": "1d"},
            "5d": {"period": "5d", "interval": "1d"},
            "1mo": {"period": "1mo", "interval": "1d"},
            "3mo": {"period": "3mo", "interval": "1d"},
            "6mo": {"period": "6mo", "interval": "1d"},
            "1y": {"period": "1y", "interval": "1d"},
            "2y": {"period": "2y", "interval": "1d"},
            "5y": {"period": "5y", "interval": "1d"},
            "max": {"period": "max", "interval": "1d"},
        }

        # Get period and interval
        config = period_map.get(timeframe, {"period": "1mo", "interval": "1d"})
        period = config["period"]
        interval = config["interval"]

        logger.info(f"Fetching chart data for {ticker}: {period} / {interval}")

        # Fetch data from yfinance
        historical_data = yfinance_service.get_historical_data(
            ticker=ticker,
            period=period,
            interval=interval,
            allow_external=not settings.US_CACHE_ONLY
        )

        if historical_data is None or historical_data.empty:
            return {
                "success": True,
                "ticker": ticker,
                "timeframe": timeframe,
                "interval": interval,
                "period": period,
                "count": 0,
                "data": [],
                "message": "Chart cache warming"
            }

        # Format for frontend (TradingView expects specific format)
        chart_data = []
        for index, row in historical_data.iterrows():
            try:
                chart_data.append({
                    "time": int(index.timestamp()),  # Unix timestamp
                    "open": float(row.get("Open", 0)),
                    "high": float(row.get("High", 0)),
                    "low": float(row.get("Low", 0)),
                    "close": float(row.get("Close", 0)),
                    "volume": int(row.get("Volume", 0)),
                })
            except Exception as e:
                logger.warning(f"Error formatting row for {ticker}: {e}")
                continue

        # Limit to requested number of points
        chart_data = chart_data[-limit:] if len(chart_data) > limit else chart_data

        if not chart_data:
            return {
                "success": True,
                "ticker": ticker,
                "timeframe": timeframe,
                "interval": interval,
                "period": period,
                "count": 0,
                "data": [],
                "message": "Chart cache warming"
            }

        return {
            "success": True,
            "ticker": ticker,
            "timeframe": timeframe,
            "interval": interval,
            "period": period,
            "count": len(chart_data),
            "data": chart_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chart data for {ticker}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch chart data: {str(e)}"
        )
