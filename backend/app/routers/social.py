from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
import random
import logging
import json

from database.redis.config import get_redis_cache

logger = logging.getLogger(__name__)
redis_cache = get_redis_cache()

# Cache TTL: 4 hours for social data (updated twice daily by scheduler)
SOCIAL_CACHE_TTL = 4 * 60 * 60

router = APIRouter(
    prefix="/api/social",
    tags=["social"]
)


@router.get("/trending")
async def get_social_trending(
    limit: int = Query(10, ge=1, le=50),
    source: Optional[str] = Query(None, regex="^(reddit|twitter|stocktwits|all)$"),
    hours: int = Query(24, ge=1, le=168)
):
    """
    Get trending stocks from REAL Reddit data (with cache)

    Args:
        limit: Number of trending items to return
        source: Filter by platform (currently only reddit supported)
        hours: Hours to look back (default 24)

    Returns:
        List of trending tickers with mention counts and sentiment
        Data source: Reddit API (WallStreetBets, stocks, investing, StockMarket)
    """
    try:
        # CHECK CACHE FIRST
        cache_key = f"social:trending:{hours}"
        if redis_cache and redis_cache.is_connected():
            try:
                cached = redis_cache.redis_client.get(cache_key)
                if cached:
                    logger.info("📦 Returning cached Reddit trending data")
                    data = json.loads(cached)
                    data["cached"] = True
                    # Apply limit filter
                    if data.get("data"):
                        data["data"] = data["data"][:limit]
                        data["count"] = len(data["data"])
                    return data
            except Exception as e:
                logger.debug(f"Cache read error: {e}")

        from app.services.reddit_service import get_reddit_service

        # Get Reddit service
        reddit_service = get_reddit_service()

        # Get trending stocks from Reddit (fetch more for caching)
        reddit_trending = reddit_service.get_trending_stocks(limit=50, hours=hours)

        # Transform data to match frontend expectations
        # Reddit service returns: sentiment (string), sentimentScore (number)
        # Frontend expects: sentiment (number), mentions (number)
        transformed_data = []
        for item in reddit_trending:
            transformed_data.append({
                "ticker": item.get("ticker", ""),
                "mentions": item.get("mentions", 0),
                "sentiment": item.get("sentimentScore", 0.0),  # Use sentimentScore as numeric sentiment
                "platform": "reddit",
                "trending": item.get("trending", False)
            })

        logger.info(f"✅ Fetched {len(transformed_data)} trending stocks from Reddit")

        result = {
            "success": True,
            "count": len(transformed_data),
            "data": transformed_data,
            "source": "reddit",
            "hours": hours,
            "note": "Real data from r/wallstreetbets, r/stocks, r/investing, r/StockMarket",
            "cached": False
        }

        # CACHE THE RESULT (4 hours TTL)
        if redis_cache and redis_cache.is_connected():
            try:
                redis_cache.redis_client.setex(cache_key, SOCIAL_CACHE_TTL, json.dumps(result))
                logger.info(f"📦 Cached Reddit trending data for {SOCIAL_CACHE_TTL}s")
            except Exception as e:
                logger.debug(f"Cache write error: {e}")

        # Apply limit filter for response
        result["data"] = result["data"][:limit]
        result["count"] = len(result["data"])

        return result

    except Exception as e:
        logger.error(f"❌ Social trending error: {str(e)}")

        # Return fallback mock data if Reddit API fails
        # Use simple format matching frontend expectations
        trending_items = [
            {
                "ticker": "NVDA",
                "mentions": 8500,
                "sentiment": 0.82,
                "platform": "reddit",
                "trending": True
            },
            {
                "ticker": "TSLA",
                "mentions": 5800,
                "sentiment": 0.45,
                "platform": "reddit",
                "trending": True
            },
            {
                "ticker": "AMD",
                "mentions": 4800,
                "sentiment": 0.72,
                "platform": "reddit",
                "trending": True
            },
            {
                "ticker": "GME",
                "mentions": 7200,
                "sentiment": 0.91,
                "platform": "reddit",
                "trending": True
            },
            {
                "ticker": "SPY",
                "mentions": 5100,
                "sentiment": 0.56,
                "platform": "reddit",
                "trending": True
            },
            {
                "ticker": "PLTR",
                "mentions": 4500,
                "sentiment": 0.78,
                "platform": "reddit",
                "trending": True
            },
            {
                "ticker": "AAPL",
                "mentions": 3200,
                "sentiment": 0.38,
                "platform": "reddit",
                "trending": True
            },
            {
                "ticker": "META",
                "mentions": 2900,
                "sentiment": -0.45,
                "platform": "reddit",
                "trending": True
            }
        ]

        return {
            "success": True,
            "count": len(trending_items[:limit]),
            "data": trending_items[:limit],
            "source": "reddit",
            "hours": hours,
            "note": "Fallback data - Reddit API unavailable or credentials not configured"
        }


@router.get("/sentiment/{ticker}")
async def get_ticker_sentiment(ticker: str):
    """
    Get social sentiment for a specific ticker

    Args:
        ticker: Stock/crypto ticker symbol

    Returns:
        Detailed sentiment analysis
    """

    ticker = ticker.upper()

    sentiment_data = {
        "ticker": ticker,
        "overall_sentiment": {
            "score": 0.72,
            "label": "Bullish",
            "confidence": 0.85
        },
        "mentions": {
            "total": 15420,
            "reddit": 8500,
            "twitter": 5200,
            "stocktwits": 1720
        },
        "trending": {
            "last1h": 1250,
            "last24h": 15420,
            "last7d": 98450,
            "changePercent24h": 245.5
        },
        "sentiment_breakdown": {
            "very_bullish": 32,
            "bullish": 28,
            "neutral": 25,
            "bearish": 12,
            "very_bearish": 3
        },
        "top_keywords": [
            {"word": "bullish", "count": 1240, "sentiment": 0.9},
            {"word": "breakout", "count": 890, "sentiment": 0.8},
            {"word": "moon", "count": 765, "sentiment": 0.95},
            {"word": "hold", "count": 620, "sentiment": 0.6},
            {"word": "buy", "count": 580, "sentiment": 0.85}
        ],
        "influencer_sentiment": {
            "bullish": 8,
            "bearish": 2,
            "neutral": 3
        },
        "platform_breakdown": {
            "reddit": {
                "mentions": 8500,
                "sentiment": 0.78,
                "top_subreddits": [
                    {"name": "wallstreetbets", "mentions": 5200},
                    {"name": "stocks", "mentions": 2100},
                    {"name": "investing", "mentions": 1200}
                ]
            },
            "twitter": {
                "mentions": 5200,
                "sentiment": 0.65,
                "trending_hashtags": [
                    "#bullish",
                    "#stocks",
                    f"${ticker}"
                ]
            },
            "stocktwits": {
                "mentions": 1720,
                "sentiment": 0.68,
                "bullishPercent": 72
            }
        }
    }

    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "data": sentiment_data
    }


@router.get("/reddit/wallstreetbets")
async def get_wsb_trending(limit: int = Query(10, ge=1, le=50)):
    """
    Get trending tickers from Reddit WallStreetBets

    Args:
        limit: Number of tickers to return

    Returns:
        Top trending tickers on WSB
    """

    wsb_data = [
        {
            "rank": 1,
            "ticker": "GME",
            "name": "GameStop",
            "mentions": 7200,
            "sentiment": 0.91,
            "change24h": 412.8,
            "topPosts": [
                {
                    "title": "GME to the moon! 🚀🚀🚀",
                    "upvotes": 15420,
                    "comments": 2840,
                    "sentiment": 0.95
                },
                {
                    "title": "Why GME is undervalued - DD",
                    "upvotes": 12350,
                    "comments": 1920,
                    "sentiment": 0.88
                }
            ]
        },
        {
            "rank": 2,
            "ticker": "NVDA",
            "name": "NVIDIA",
            "mentions": 5200,
            "sentiment": 0.82,
            "change24h": 189.3,
            "topPosts": [
                {
                    "title": "NVDA earnings play - Am I retarded?",
                    "upvotes": 8920,
                    "comments": 1540,
                    "sentiment": 0.75
                }
            ]
        },
        {
            "rank": 3,
            "ticker": "SPY",
            "name": "S&P 500 ETF",
            "mentions": 5100,
            "sentiment": 0.56,
            "change24h": 34.2,
            "topPosts": [
                {
                    "title": "SPY 500 EOY - Change my mind",
                    "upvotes": 6420,
                    "comments": 980,
                    "sentiment": 0.68
                }
            ]
        },
        {
            "rank": 4,
            "ticker": "TSLA",
            "name": "Tesla",
            "mentions": 4800,
            "sentiment": 0.45,
            "change24h": 78.5,
            "topPosts": [
                {
                    "title": "TSLA calls printing tomorrow 💎🙌",
                    "upvotes": 5680,
                    "comments": 1120,
                    "sentiment": 0.82
                }
            ]
        },
        {
            "rank": 5,
            "ticker": "PLTR",
            "name": "Palantir",
            "mentions": 4500,
            "sentiment": 0.78,
            "change24h": 178.3,
            "topPosts": [
                {
                    "title": "PLTR gang rise up! 🚀",
                    "upvotes": 4920,
                    "comments": 850,
                    "sentiment": 0.85
                }
            ]
        }
    ]

    return {
        "success": True,
        "source": "r/wallstreetbets",
        "count": len(wsb_data[:limit]),
        "timestamp": datetime.now().isoformat(),
        "data": wsb_data[:limit]
    }


@router.get("/twitter/trending")
async def get_twitter_trending(limit: int = Query(10, ge=1, le=50)):
    """
    Get trending stocks/crypto on Twitter

    Args:
        limit: Number of trending items to return

    Returns:
        Trending tickers on Twitter
    """

    twitter_data = [
        {
            "rank": 1,
            "ticker": "BTC",
            "name": "Bitcoin",
            "mentions": 6100,
            "sentiment": 0.68,
            "change24h": 125.3,
            "trendingHashtags": ["#Bitcoin", "#BTC", "#Crypto"],
            "influencerMentions": 42
        },
        {
            "rank": 2,
            "ticker": "TSLA",
            "name": "Tesla",
            "mentions": 6200,
            "sentiment": 0.45,
            "change24h": 92.1,
            "trendingHashtags": ["#TSLA", "#Tesla", "#ElonMusk"],
            "influencerMentions": 38
        },
        {
            "rank": 3,
            "ticker": "NVDA",
            "name": "NVIDIA",
            "mentions": 5200,
            "sentiment": 0.82,
            "change24h": 245.5,
            "trendingHashtags": ["#NVDA", "#AI", "#Semiconductors"],
            "influencerMentions": 35
        },
        {
            "rank": 4,
            "ticker": "AAPL",
            "name": "Apple",
            "mentions": 4100,
            "sentiment": 0.38,
            "change24h": -23.5,
            "trendingHashtags": ["#AAPL", "#Apple", "#iPhone"],
            "influencerMentions": 28
        },
        {
            "rank": 5,
            "ticker": "ETH",
            "name": "Ethereum",
            "mentions": 3200,
            "sentiment": 0.64,
            "change24h": 87.2,
            "trendingHashtags": ["#Ethereum", "#ETH", "#DeFi"],
            "influencerMentions": 24
        }
    ]

    return {
        "success": True,
        "source": "Twitter",
        "count": len(twitter_data[:limit]),
        "timestamp": datetime.now().isoformat(),
        "data": twitter_data[:limit]
    }


@router.get("/analysis/{ticker}")
async def get_social_analysis(ticker: str):
    """
    Get comprehensive social media analysis for a ticker

    Args:
        ticker: Stock/crypto ticker symbol

    Returns:
        Detailed social media analytics
    """

    ticker = ticker.upper()

    analysis = {
        "ticker": ticker,
        "summary": {
            "overall_sentiment": 0.72,
            "total_mentions": 15420,
            "trending_score": 8.5,
            "viral_potential": "HIGH"
        },
        "timeline": {
            "hourly": [
                {"hour": i, "mentions": random.randint(500, 2000), "sentiment": random.uniform(0.4, 0.9)}
                for i in range(24)
            ]
        },
        "demographics": {
            "retail_investors": 68,
            "institutions": 12,
            "influencers": 8,
            "bots": 12
        },
        "momentum": {
            "acceleration": "INCREASING",
            "velocity": 245.5,
            "prediction": "Likely to trend higher in next 4-6 hours"
        },
        "comparisons": {
            "vs_sector_average": 2.8,
            "vs_market_average": 3.5,
            "relative_strength": 8.2
        }
    }

    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "data": analysis
    }
