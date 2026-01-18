"""
Enhanced News Service - Multiple Sources
==========================================

Combines news from:
1. yfinance - Real-time stock-specific news
2. Finnhub - Breaking market news
3. NewsAPI - General financial news

Caches results and provides weighted scoring.
"""

import os
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import yfinance as yf
import finnhub
from newsapi import NewsApiClient
from dotenv import load_dotenv
import hashlib
import json
import time

from app.config.settings import settings
from database.redis.config import get_redis_cache

load_dotenv()

logger = logging.getLogger(__name__)


class EnhancedNewsService:
    """Enhanced news service using multiple sources"""

    def __init__(self):
        # Initialize API clients
        self.news_api_key = os.getenv('NEWS_API_KEY')
        self.finnhub_api_key = os.getenv('FINNHUB_API_KEY')

        self.news_client = None
        self.finnhub_client = None

        # Initialize NewsAPI
        if self.news_api_key:
            try:
                self.news_client = NewsApiClient(api_key=self.news_api_key)
                logger.info("✅ NewsAPI initialized")
            except Exception as e:
                logger.error(f"NewsAPI init failed: {e}")

        # Initialize Finnhub
        if self.finnhub_api_key:
            try:
                self.finnhub_client = finnhub.Client(api_key=self.finnhub_api_key)
                logger.info("✅ Finnhub initialized")
            except Exception as e:
                logger.error(f"Finnhub init failed: {e}")

        # Cache for news articles
        self.news_cache = {}
        self.cache_timestamp = {}
        self.cache_ttl = settings.FINNHUB_MARKET_NEWS_TTL
        self.redis_cache = get_redis_cache()

        # Category weights
        self.category_weights = {
            'FDA_APPROVAL': 100,
            'MERGER': 95,
            'ACQUISITION': 95,
            'BANKRUPTCY': 90,
            'EARNINGS_BEAT': 85,
            'EARNINGS_MISS': 85,
            'IPO': 80,
            'INVESTIGATION': 75,
            'LAWSUIT': 70,
            'BREAKTHROUGH': 65,
            'GUIDANCE_RAISED': 60,
            'GUIDANCE_LOWERED': 60,
            'ECONOMIC': 50,
            'GENERAL': 30
        }

        # Source bonuses
        self.source_bonuses = {
            'Reuters': 20,
            'Bloomberg': 20,
            'Wall Street Journal': 18,
            'CNBC': 15,
            'MarketWatch': 12,
            'Yahoo Finance': 10
        }

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache is still valid"""
        if cache_key not in self.cache_timestamp:
            return False
        age = (datetime.now() - self.cache_timestamp[cache_key]).total_seconds()
        return age < self.cache_ttl

    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict]]:
        """Get from cache if valid"""
        if self._is_cache_valid(cache_key):
            return self.news_cache.get(cache_key)
        return None

    def _save_to_cache(self, cache_key: str, data: List[Dict]):
        """Save to cache"""
        self.news_cache[cache_key] = data
        self.cache_timestamp[cache_key] = datetime.now()

    def _get_from_redis(self, cache_key: str) -> Optional[List[Dict]]:
        if not self.redis_cache or not self.redis_cache.is_connected():
            return None
        try:
            cached_data = self.redis_cache.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as exc:
            logger.debug("Failed to read cached aggregated news: %s", exc)
        return None

    def _save_to_redis(self, cache_key: str, data: List[Dict]) -> None:
        if not self.redis_cache or not self.redis_cache.is_connected():
            return
        try:
            self.redis_cache.redis_client.setex(cache_key, self.cache_ttl, json.dumps(data))
        except Exception as exc:
            logger.debug("Failed to cache aggregated news: %s", exc)

    def _acquire_lock(self, lock_key: str) -> bool:
        if not self.redis_cache or not self.redis_cache.is_connected():
            return True
        try:
            return bool(
                self.redis_cache.redis_client.set(
                    lock_key,
                    "1",
                    nx=True,
                    ex=settings.FINNHUB_NEWS_LOCK_TTL
                )
            )
        except Exception as exc:
            logger.debug("Failed to acquire aggregated news lock: %s", exc)
            return True

    def _release_lock(self, lock_key: str) -> None:
        if not self.redis_cache or not self.redis_cache.is_connected():
            return
        try:
            self.redis_cache.redis_client.delete(lock_key)
        except Exception as exc:
            logger.debug("Failed to release aggregated news lock: %s", exc)

    def get_stock_news_yfinance(self, ticker: str, limit: int = 10) -> List[Dict]:
        """Get news for a specific stock from yfinance"""
        try:
            stock = yf.Ticker(ticker)
            news = stock.news

            articles = []
            for item in news[:limit]:
                # Handle new yfinance format where data is nested under 'content'
                content = item.get('content', item)  # Fallback to item itself for old format

                # Extract title and summary from nested structure
                title = content.get('title', '') or item.get('title', '')
                summary = content.get('summary', '') or content.get('description', '') or item.get('summary', '')

                # Extract URL - try multiple possible locations
                url = (content.get('canonicalUrl', {}).get('url', '') or
                       content.get('clickThroughUrl', {}).get('url', '') or
                       item.get('link', ''))

                # Extract publish time
                pub_date = content.get('pubDate', '') or content.get('displayTime', '')
                if pub_date:
                    published_at = pub_date
                elif item.get('providerPublishTime'):
                    published_at = datetime.fromtimestamp(item.get('providerPublishTime', 0)).isoformat()
                else:
                    published_at = datetime.now().isoformat()

                # Extract publisher
                provider = content.get('provider', {})
                source = provider.get('displayName', '') or item.get('publisher', 'Yahoo Finance')

                article = {
                    'title': title,
                    'description': summary,
                    'url': url,
                    'publishedAt': published_at,
                    'source': source,
                    'ticker': ticker,
                    'category': self._detect_category(title, summary),
                    'isHot': False,
                    'weight': 0
                }

                # Skip items with no title
                if not title:
                    continue

                # Detect impact
                article['impact'] = self._detect_impact(article['category'])

                # Calculate weight
                article['weight'] = self.calculate_news_weight(article)

                articles.append(article)

            return articles

        except Exception as e:
            logger.error(f"Error fetching yfinance news for {ticker}: {e}")
            return []

    def get_market_news_finnhub(self, category: str = 'general', limit: int = 20) -> List[Dict]:
        """Get market news from Finnhub"""
        if not self.finnhub_client:
            return []

        try:
            # Finnhub market news
            news = self.finnhub_client.general_news(category, min_id=0)

            articles = []
            for item in news[:limit]:
                article = {
                    'title': item.get('headline', ''),
                    'description': item.get('summary', ''),
                    'url': item.get('url', ''),
                    'publishedAt': datetime.fromtimestamp(item.get('datetime', 0)).isoformat(),
                    'source': item.get('source', 'Finnhub'),
                    'ticker': None,
                    'category': self._detect_category(item.get('headline', ''), item.get('summary', '')),
                    'isHot': False,
                    'weight': 0
                }

                # Detect impact
                article['impact'] = self._detect_impact(article['category'])

                # Calculate weight
                article['weight'] = self.calculate_news_weight(article)

                articles.append(article)

            return articles

        except Exception as e:
            logger.error(f"Error fetching Finnhub news: {e}")
            return []

    def get_aggregated_news(self, days: int = 7, limit: int = 20) -> List[Dict]:
        """
        Get aggregated news from all sources (FIXED: Now respects days parameter!)

        Combines yfinance, Finnhub, and NewsAPI for comprehensive coverage

        CRITICAL FIX: Filters news by date range - now returns news from last {days} days
        """
        cache_key = f"aggregated_news_{days}_{limit}"

        # Check in-memory cache
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.info(f"📦 Returning cached aggregated news ({len(cached)} articles)")
            return cached

        # Check shared Redis cache
        redis_cached = self._get_from_redis(cache_key)
        if redis_cached:
            self._save_to_cache(cache_key, redis_cached)
            logger.info("Returning Redis cached aggregated news (%s articles)", len(redis_cached))
            return redis_cached

        lock_key = f"{cache_key}:lock"
        if not self._acquire_lock(lock_key):
            for _ in range(3):
                time.sleep(0.5)
                redis_cached = self._get_from_redis(cache_key)
                if redis_cached:
                    self._save_to_cache(cache_key, redis_cached)
                    logger.info(
                        "Returning Redis cached aggregated news after wait (%s articles)",
                        len(redis_cached)
                    )
                    return redis_cached
            logger.info("Aggregated news lock busy; returning empty list")
            return []

        all_news = []

        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days)
        logger.info(f"🗓️ Fetching news from {cutoff_date.strftime('%Y-%m-%d')} onwards ({days} days)")

        # 1. Get Finnhub market news (FIXED: Now filters by date)
        try:
            finnhub_news = self.get_market_news_finnhub('general', limit=50)  # Get more to filter

            # FILTER by date
            filtered_finnhub = []
            for article in finnhub_news:
                try:
                    pub_time = datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00'))
                    if pub_time.tzinfo:
                        pub_time = pub_time.replace(tzinfo=None)

                    if pub_time >= cutoff_date:
                        filtered_finnhub.append(article)
                except Exception as e:
                    continue  # Skip articles with bad dates

            all_news.extend(filtered_finnhub)
            logger.info(f"✅ Finnhub: {len(filtered_finnhub)}/{len(finnhub_news)} articles within {days} days")
        except Exception as e:
            logger.error(f"Finnhub error: {e}")

        # 2. Get yfinance news for top tickers (FIXED: Now filters by date)
        top_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AMD', 'PLTR', 'COIN']
        yf_count = 0
        for ticker in top_tickers:  # All tickers for better coverage
            try:
                ticker_news = self.get_stock_news_yfinance(ticker, limit=5)

                # FILTER by date
                filtered_yf = []
                for article in ticker_news:
                    try:
                        pub_time = datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00'))
                        if pub_time.tzinfo:
                            pub_time = pub_time.replace(tzinfo=None)

                        if pub_time >= cutoff_date:
                            filtered_yf.append(article)
                    except Exception as e:
                        continue

                all_news.extend(filtered_yf)
                yf_count += len(filtered_yf)
            except Exception as e:
                logger.debug(f"yfinance error for {ticker}: {e}")

        logger.info(f"✅ yfinance: {yf_count} articles within {days} days")

        # 3. Get NewsAPI general financial news
        if self.news_client:
            try:
                # NewsAPI requires YYYY-MM-DD format (not ISO with time)
                from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                response = self.news_client.get_everything(
                    q='stock OR earnings OR market OR IPO OR merger',
                    language='en',
                    sort_by='publishedAt',
                    page_size=15,
                    from_param=from_date
                )

                for item in response.get('articles', []):
                    article = {
                        'title': item.get('title', ''),
                        'description': item.get('description', ''),
                        'url': item.get('url', ''),
                        'publishedAt': item.get('publishedAt', ''),
                        'source': item.get('source', {}).get('name', 'Unknown'),
                        'ticker': self._extract_ticker(item.get('title', ''), item.get('description', '')),
                        'category': self._detect_category(item.get('title', ''), item.get('description', '')),
                        'isHot': False,
                        'weight': 0
                    }

                    article['impact'] = self._detect_impact(article['category'])
                    article['weight'] = self.calculate_news_weight(article)
                    all_news.append(article)

                logger.info(f"✅ NewsAPI: {len(response.get('articles', []))} articles")
            except Exception as e:
                logger.error(f"NewsAPI error: {e}")

        # Remove duplicates based on title similarity
        unique_news = self._remove_duplicates(all_news)

        # Sort by weight
        unique_news.sort(key=lambda x: x['weight'], reverse=True)

        # Filter out vague/low-signal articles
        unique_news = [n for n in unique_news if self._is_relevant_article(n)]

        # FILTER: Prioritize HIGH/MEDIUM impact news only
        # This ensures we show REAL market-moving news, not just general economic articles
        high_impact_news = [n for n in unique_news if n.get('impact') in ['HIGH', 'MEDIUM']]
        low_impact_news = [
            n for n in unique_news
            if n.get('impact') == 'LOW' and (n.get('ticker') or n.get('weight', 0) >= 90)
        ]

        logger.info(f"📊 News breakdown: {len(high_impact_news)} HIGH/MEDIUM impact, {len(low_impact_news)} LOW impact")

        # Take HIGH/MEDIUM impact first, then LOW impact as filler if needed
        if len(high_impact_news) >= limit:
            result = high_impact_news[:limit]
            logger.info(f"✅ Using only HIGH/MEDIUM impact news ({len(result)} articles)")
        else:
            # Not enough high-impact news, add LOW impact as filler
            result = high_impact_news + low_impact_news[:limit - len(high_impact_news)]
            logger.info(f"⚠️ Mixed impact: {len(high_impact_news)} HIGH/MEDIUM + {len(result) - len(high_impact_news)} LOW impact")

        # Save to cache
        self._save_to_cache(cache_key, result)
        self._save_to_redis(cache_key, result)
        self._release_lock(lock_key)

        logger.info(f"📰 Total aggregated news: {len(result)} unique articles")
        return result

    def _remove_duplicates(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles based on title"""
        seen_titles = set()
        unique = []

        for article in articles:
            title_hash = hashlib.md5(article['title'].lower().encode()).hexdigest()
            if title_hash not in seen_titles:
                seen_titles.add(title_hash)
                unique.append(article)

        return unique

    def _is_relevant_article(self, article: Dict) -> bool:
        title = (article.get('title') or '').strip()
        if len(title) < 12:
            return False

        description = (article.get('description') or '').strip()
        impact = article.get('impact', 'LOW')
        if not description and impact == 'LOW':
            return False

        category = article.get('category', 'GENERAL')
        ticker = article.get('ticker')
        weight = article.get('weight', 0) or 0

        if impact == 'LOW' and not ticker and category in {'GENERAL', 'ECONOMIC', 'CRYPTO'}:
            return False

        if weight < 60 and not ticker:
            return False

        return True

    def calculate_news_weight(self, article: Dict) -> float:
        """
        Calculate weight score for news article (ENHANCED)

        Weight = Category (0-100) + Source (0-20) + Recency (0-30) + High Impact Bonus (0-50)
        Max weight = ~200 points
        """
        weight = 0.0

        # Category weight (biggest factor)
        category = article.get('category', 'GENERAL')
        base_category_weight = self.category_weights.get(category, 30)
        weight += base_category_weight

        # HIGH IMPACT BONUS (NEW): Extra points for market-moving categories
        high_impact_categories = [
            'FDA_APPROVAL',      # +50: Massive stock movers
            'MERGER',            # +45: Huge price movements
            'ACQUISITION',       # +45: Major deals
            'BANKRUPTCY',        # +40: Devastating news
            'EARNINGS_BEAT',     # +35: Strong signals
            'EARNINGS_MISS',     # +35: Warning signs
            'BUYOUT',            # +40: Premium prices
            'TAKEOVER',          # +40: Hostile or friendly
            'IPO',               # +30: New listings
            'INVESTIGATION',     # +25: Regulatory risk
            'LAWSUIT',           # +20: Legal risk
            'GUIDANCE_RAISED',   # +25: Growth acceleration
            'GUIDANCE_LOWERED',  # +25: Growth deceleration
            'BREAKTHROUGH'       # +30: Innovation
        ]

        impact_bonuses = {
            'FDA_APPROVAL': 50,
            'MERGER': 45,
            'ACQUISITION': 45,
            'BANKRUPTCY': 40,
            'BUYOUT': 40,
            'TAKEOVER': 40,
            'EARNINGS_BEAT': 35,
            'EARNINGS_MISS': 35,
            'BREAKTHROUGH': 30,
            'IPO': 30,
            'GUIDANCE_RAISED': 25,
            'GUIDANCE_LOWERED': 25,
            'INVESTIGATION': 25,
            'LAWSUIT': 20
        }

        if category in impact_bonuses:
            weight += impact_bonuses[category]
            logger.debug(f"🎯 HIGH IMPACT: {category} +{impact_bonuses[category]} points")

        # Source bonus (premium sources = more reliable)
        source = article.get('source', '')
        for source_name, bonus in self.source_bonuses.items():
            if source_name.lower() in source.lower():
                weight += bonus
                break

        # Recency bonus (breaking news = more important)
        published_at = article.get('publishedAt', '')
        if published_at:
            try:
                if isinstance(published_at, str):
                    pub_time = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                else:
                    pub_time = published_at

                if pub_time.tzinfo:
                    pub_time = pub_time.replace(tzinfo=None)

                hours_old = (datetime.now() - pub_time).total_seconds() / 3600
                if hours_old <= 1:
                    weight += 30  # Breaking news
                elif hours_old <= 6:
                    weight += 25
                elif hours_old <= 24:
                    weight += 20
                elif hours_old <= 48:
                    weight += 10
                elif hours_old <= 168:  # 7 days
                    weight += 5
            except Exception as e:
                logger.debug(f"Date parse error: {e}")

        # Hot news bonus (flagged as important)
        if article.get('isHot', False):
            weight += 20

        return weight

    def _detect_category(self, title: str, description: str = '') -> str:
        """
        Detect news category (ENHANCED with better keyword matching)

        Now detects 15+ high-impact categories with multiple keywords each
        """
        text = f"{title} {description}".lower()

        # Enhanced category keywords with better coverage
        category_keywords = {
            'FDA_APPROVAL': [
                'fda approv', 'fda clear', 'drug approv', 'fda granted',
                'fda authorize', 'regulatory approval', 'drug cleared'
            ],
            'MERGER': [
                'merger', 'merge with', 'merging with', 'merger agreement',
                'combination of', 'combining with'
            ],
            'ACQUISITION': [
                'acqui', 'acquire', 'acquisition', 'acquired by', 'acquiring',
                'to acquire', 'buyout', 'buys out', 'purchased by'
            ],
            'BANKRUPTCY': [
                'bankrupt', 'chapter 11', 'chapter 7', 'insolvency',
                'filing for bankruptcy', 'bankruptcy protection'
            ],
            'BUYOUT': [
                'buyout', 'bought out', 'taking private', 'lbo',
                'leveraged buyout', 'management buyout'
            ],
            'TAKEOVER': [
                'takeover', 'hostile takeover', 'take over', 'takeover bid',
                'acquisition offer', 'tender offer'
            ],
            'EARNINGS_BEAT': [
                'earnings beat', 'beat estimates', 'exceed expect', 'topped estimates',
                'surpass forecast', 'better than expected earnings', 'earnings surprise'
            ],
            'EARNINGS_MISS': [
                'earnings miss', 'miss estimates', 'below expect', 'fell short',
                'disappointed', 'lower than expected', 'earnings shortfall'
            ],
            'IPO': [
                'ipo', 'initial public offering', 'going public', 'public debut',
                'stock debut', 'first day of trading', 'newly listed'
            ],
            'INVESTIGATION': [
                'investigation', 'probe', 'sec investigat', 'under investigation',
                'doj probe', 'federal investigation', 'regulatory probe'
            ],
            'LAWSUIT': [
                'lawsuit', 'sue', 'legal action', 'sued', 'suing', 'litigation',
                'class action', 'legal battle', 'court case'
            ],
            'RECALL': [
                'recall', 'product recall', 'recalling', 'safety recall',
                'voluntary recall', 'recalled product'
            ],
            'BREAKTHROUGH': [
                'breakthrough', 'revolutionary', 'game-changing', 'paradigm shift',
                'major advance', 'scientific breakthrough', 'innovation'
            ],
            'GUIDANCE_RAISED': [
                'guidance raised', 'raise forecast', 'raise outlook', 'upgraded guidance',
                'increased forecast', 'boosted outlook', 'raised guidance'
            ],
            'GUIDANCE_LOWERED': [
                'guidance lower', 'cut forecast', 'lower outlook', 'downgraded guidance',
                'reduced forecast', 'lowered guidance', 'cut outlook'
            ],
            'BREAKOUT': [
                'breakout', 'all-time high', 'record high', 'new high',
                'breaking out', 'technical breakout'
            ],
            'ECONOMIC': [
                'fed', 'interest rate', 'inflation', 'gdp', 'federal reserve',
                'monetary policy', 'rate hike', 'rate cut', 'employment',
                'jobs report', 'cpi', 'consumer price'
            ],
            'CRYPTO': [
                'bitcoin', 'ethereum', 'crypto', 'cryptocurrency', 'blockchain',
                'btc', 'eth', 'digital currency', 'crypto market'
            ]
        }

        # Check each category (order matters - most specific first)
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return category

        return 'GENERAL'

    def _detect_impact(self, category: str) -> str:
        """
        Detect impact level (ENHANCED)

        HIGH = Immediate major stock price movement (5-30%+)
        MEDIUM = Significant price movement (2-10%)
        LOW = Minor or gradual impact (<2%)
        """
        high_impact = [
            'FDA_APPROVAL',       # Often +20-50% moves
            'MERGER',             # Often +15-40% moves
            'ACQUISITION',        # Often +15-40% moves
            'BANKRUPTCY',         # Often -50-90% moves
            'BUYOUT',             # Often +20-50% moves (premium)
            'TAKEOVER'            # Often +15-40% moves
        ]

        medium_impact = [
            'EARNINGS_BEAT',      # +2-10% typical
            'EARNINGS_MISS',      # -2-10% typical
            'IPO',                # Varies widely
            'INVESTIGATION',      # -5-20% typical
            'LAWSUIT',            # -3-15% typical
            'RECALL',             # -5-20% typical
            'BREAKTHROUGH',       # +5-15% typical
            'GUIDANCE_RAISED',    # +3-10% typical
            'GUIDANCE_LOWERED',   # -3-10% typical
            'BREAKOUT'            # Technical signal
        ]

        if category in high_impact:
            return 'HIGH'
        elif category in medium_impact:
            return 'MEDIUM'
        return 'LOW'

    def _extract_ticker(self, title: str, description: str = '') -> Optional[str]:
        """Extract stock ticker from text"""
        import re
        text = f"{title} {description}"

        patterns = [
            r'\$([A-Z]{1,5})\b',
            r'\((?:NASDAQ|NYSE|AMEX):\s*([A-Z]{1,5})\)',
            r'\b([A-Z]{2,5})\s+(?:stock|shares)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None


# Singleton instance
_enhanced_news_service = None

def get_enhanced_news_service() -> EnhancedNewsService:
    """Get singleton instance of enhanced news service"""
    global _enhanced_news_service
    if _enhanced_news_service is None:
        _enhanced_news_service = EnhancedNewsService()
    return _enhanced_news_service
