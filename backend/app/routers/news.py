"""
TradeMaster Pro - News API Router
==================================

API endpoints for news categorization and weighting.
Provides both newest and most impactful news.

NEWS IS CACHED for 4 hours to prevent API rate limits.
Scheduler refreshes news twice daily.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Literal
from datetime import datetime
import json
import logging

from ..services.news_service import get_news_service
from ..services.enhanced_news_service import get_enhanced_news_service
from database.redis.config import get_redis_cache

logger = logging.getLogger(__name__)
redis_cache = get_redis_cache()

# Cache TTL: 4 hours for news (refreshed twice daily by scheduler)
NEWS_CACHE_TTL = 4 * 60 * 60

router = APIRouter(
    prefix="/api/news",
    tags=["news"]
)


@router.get("/bombs")
async def get_news_bombs(
    limit: int = Query(20, ge=1, le=50),
    days: int = Query(7, ge=1, le=7)
):
    """
    Get high-impact "news bombs" - market-moving stories

    Args:
        limit: Maximum number of articles to return
        days: Number of days to look back (default 7 for better coverage)

    Returns:
        List of high-impact news articles with weight scores from last 7 days
    """
    try:
        news_service = get_news_service()
        bombs = news_service.get_news_bombs(limit=limit, days=days)

        # Transform to API response format
        articles = []
        for bomb in bombs:
            articles.append({
                'id': str(hash(bomb.get('title', ''))),
                'ticker': bomb.get('ticker'),
                'headline': bomb.get('title', ''),
                'summary': bomb.get('description', ''),
                'timestamp': bomb.get('publishedAt', ''),
                'category': bomb.get('category', 'GENERAL'),
                'isHot': bomb.get('isHot', False),
                'impact': bomb.get('impact', 'LOW'),
                'url': bomb.get('url', ''),
                'source': bomb.get('source', 'Unknown'),
                'weight': bomb.get('weight', 0)
            })

        return {
            'success': True,
            'count': len(articles),
            'data': articles,
            'cached': False
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categorized")
async def get_categorized_news(
    sort_by: Literal['newest', 'weighted'] = Query('newest'),
    days: int = Query(7, ge=1, le=7),
    limit: int = Query(20, ge=1, le=50),
    ticker: Optional[str] = Query(None)
):
    """
    Get news sorted by time (newest) or importance (weighted)

    Args:
        sort_by: 'newest' for most recent, 'weighted' for most impactful
        days: Number of days to look back (1-7)
        limit: Maximum number of articles
        ticker: Optional stock ticker to filter by

    Returns:
        List of news articles sorted by preference
    """
    try:
        news_service = get_news_service()
        news = news_service.get_categorized_news(
            sort_by=sort_by,
            days=days,
            limit=limit,
            ticker=ticker
        )

        # Transform to API response format
        articles = []
        for item in news:
            articles.append({
                'id': str(hash(item.get('title', ''))),
                'ticker': item.get('ticker'),
                'headline': item.get('title', ''),
                'summary': item.get('description', ''),
                'timestamp': item.get('publishedAt', ''),
                'category': item.get('category', 'GENERAL'),
                'isHot': item.get('isHot', False),
                'impact': item.get('impact', 'LOW'),
                'url': item.get('url', ''),
                'source': item.get('source', 'Unknown'),
                'weight': item.get('weight', 0)
            })

        return {
            'success': True,
            'sort_by': sort_by,
            'days': days,
            'count': len(articles),
            'data': articles,
            'cached': False
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/newest")
async def get_newest_news(
    days: int = Query(7, ge=1, le=7),
    limit: int = Query(10, ge=1, le=30)
):
    """
    Get newest news articles from multiple sources (CACHED)

    Uses yfinance, Finnhub, and NewsAPI for comprehensive coverage.
    Cached for 4 hours to prevent rate limits.
    """
    try:
        # CHECK CACHE FIRST
        cache_key = f"news:newest:{days}"
        if redis_cache and redis_cache.is_connected():
            try:
                cached = redis_cache.redis_client.get(cache_key)
                if cached:
                    logger.info("📦 Returning cached newest news")
                    data = json.loads(cached)
                    data["cached"] = True
                    # Apply limit
                    if data.get("data"):
                        data["data"] = data["data"][:limit]
                        data["count"] = len(data["data"])
                    return data
            except Exception as e:
                logger.debug(f"Cache read error: {e}")

        # Use enhanced news service
        enhanced_service = get_enhanced_news_service()
        news = enhanced_service.get_aggregated_news(days=days, limit=50)  # Fetch more for cache

        # Sort by time (newest first)
        news.sort(key=lambda x: x.get('publishedAt', ''), reverse=True)

        # Transform to API response format
        articles = []
        for item in news:
            articles.append({
                'id': str(hash(item.get('title', ''))),
                'ticker': item.get('ticker'),
                'headline': item.get('title', ''),
                'summary': item.get('description', ''),
                'timestamp': item.get('publishedAt', ''),
                'category': item.get('category', 'GENERAL'),
                'isHot': item.get('isHot', False),
                'impact': item.get('impact', 'LOW'),
                'url': item.get('url', ''),
                'source': item.get('source', 'Unknown'),
                'weight': item.get('weight', 0)
            })

        result = {
            'success': True,
            'sort_by': 'newest',
            'count': len(articles),
            'data': articles,
            'sources': ['yfinance', 'finnhub', 'newsapi'],
            'cached': False
        }

        # CACHE THE RESULT
        if redis_cache and redis_cache.is_connected():
            try:
                redis_cache.redis_client.setex(cache_key, NEWS_CACHE_TTL, json.dumps(result))
                logger.info(f"📦 Cached newest news for {NEWS_CACHE_TTL}s")
            except Exception as e:
                logger.debug(f"Cache write error: {e}")

        # Apply limit for response
        result["data"] = result["data"][:limit]
        result["count"] = len(result["data"])

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weighted")
async def get_weighted_news(
    days: int = Query(7, ge=1, le=7),
    limit: int = Query(10, ge=1, le=30)
):
    """
    Get most impactful/weighted news articles (ENHANCED)

    Returns news sorted by importance score from multiple sources
    """
    try:
        # Use enhanced news service
        enhanced_service = get_enhanced_news_service()
        news = enhanced_service.get_aggregated_news(days=days, limit=limit)

        # Already sorted by weight in the service, but ensure descending order
        news.sort(key=lambda x: x.get('weight', 0), reverse=True)

        # Transform to API response format
        articles = []
        for item in news:
            articles.append({
                'id': str(hash(item.get('title', ''))),
                'ticker': item.get('ticker'),
                'headline': item.get('title', ''),
                'summary': item.get('description', ''),
                'timestamp': item.get('publishedAt', ''),
                'category': item.get('category', 'GENERAL'),
                'isHot': item.get('isHot', False),
                'impact': item.get('impact', 'LOW'),
                'url': item.get('url', ''),
                'source': item.get('source', 'Unknown'),
                'weight': item.get('weight', 0)
            })

        return {
            'success': True,
            'sort_by': 'weighted',
            'count': len(articles),
            'data': articles,
            'sources': ['yfinance', 'finnhub', 'newsapi'],
            'avg_weight': sum(a['weight'] for a in articles) / len(articles) if articles else 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock/{ticker}")
async def get_stock_news_analysis(
    ticker: str,
    days: int = Query(7, ge=1, le=7)
):
    """
    Get comprehensive news analysis for a specific stock

    Returns both newest and most weighted news, plus summary statistics

    Args:
        ticker: Stock symbol
        days: Number of days to look back

    Returns:
        Object with newest, weighted news and stats
    """
    try:
        news_service = get_news_service()
        analysis = news_service.get_stock_news_weighted(
            ticker=ticker.upper(),
            days=days
        )

        # Transform news items to API format
        def transform_news(items):
            return [{
                'id': str(hash(item.get('title', ''))),
                'ticker': item.get('ticker'),
                'headline': item.get('title', ''),
                'summary': item.get('description', ''),
                'timestamp': item.get('publishedAt', ''),
                'category': item.get('category', 'GENERAL'),
                'isHot': item.get('isHot', False),
                'impact': item.get('impact', 'LOW'),
                'url': item.get('url', ''),
                'source': item.get('source', 'Unknown'),
                'weight': item.get('weight', 0)
            } for item in items]

        return {
            'success': True,
            'data': {
                'ticker': analysis['ticker'],
                'period_days': analysis['period_days'],
                'total_articles': analysis['total_articles'],
                'avg_weight': analysis['avg_weight'],
                'categories': analysis['categories'],
                'newest': transform_news(analysis['newest']),
                'weighted': transform_news(analysis['weighted'])
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
