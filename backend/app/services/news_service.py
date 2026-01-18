"""
TradeMaster Pro - News Service
================================

Fetches market-moving news using NewsAPI.
Filters for high-impact stories and breaking news.
Supports categorization by newest and most weighted news.
"""

import os
import logging
from typing import List, Dict, Optional, Literal
from datetime import datetime, timedelta
from newsapi import NewsApiClient
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class NewsService:
    """News API service for market news"""

    def __init__(self):
        self.api_key = os.getenv('NEWS_API_KEY')

        if not self.api_key:
            logger.warning("NEWS_API_KEY not found")
            self.client = None
        else:
            try:
                self.client = NewsApiClient(api_key=self.api_key)
                logger.info("News API client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize News API client: {str(e)}")
                self.client = None

        # High-impact keywords for "news bombs"
        self.bomb_keywords = [
            'FDA approval', 'merger', 'acquisition', 'earnings beat',
            'earnings miss', 'bankruptcy', 'IPO', 'investigation',
            'lawsuit', 'breakthrough', 'recall', 'guidance raised',
            'guidance lowered', 'buyout', 'takeover', 'default'
        ]

        # Category weights (higher = more important)
        self.category_weights = {
            'FDA_APPROVAL': 100,
            'MERGER': 95,
            'ACQUISITION': 95,
            'BANKRUPTCY': 90,
            'BUYOUT': 90,
            'TAKEOVER': 90,
            'EARNINGS_BEAT': 85,
            'EARNINGS_MISS': 85,
            'IPO': 80,
            'INVESTIGATION': 75,
            'LAWSUIT': 70,
            'RECALL': 70,
            'GUIDANCE_RAISED': 65,
            'GUIDANCE_LOWERED': 65,
            'BREAKTHROUGH': 60,
            'DEFAULT': 55,
            'ECONOMIC': 50,
            'CRYPTO': 45,
            'GENERAL': 30
        }

        # Reliable source bonus
        self.source_bonuses = {
            'Reuters': 20,
            'Bloomberg': 20,
            'Wall Street Journal': 18,
            'WSJ': 18,
            'Financial Times': 18,
            'CNBC': 15,
            'MarketWatch': 12,
            'Yahoo Finance': 10,
            'Seeking Alpha': 8,
            'Investopedia': 8
        }

    def calculate_news_weight(self, article: Dict) -> float:
        """
        Calculate weight/importance score for a news article

        Weight is based on:
        - Category importance (0-100)
        - Source reliability bonus (0-20)
        - Recency bonus (0-30)
        - Hot news bonus (0-20)

        Returns: Weight score (0-170)
        """
        weight = 0.0

        # Category weight
        category = article.get('category', 'GENERAL')
        weight += self.category_weights.get(category, 30)

        # Source bonus
        source = article.get('source', '')
        for source_name, bonus in self.source_bonuses.items():
            if source_name.lower() in source.lower():
                weight += bonus
                break

        # Recency bonus (max 30 points for articles within last hour)
        published_at = article.get('publishedAt', '')
        if published_at:
            try:
                if isinstance(published_at, str):
                    # Parse ISO format
                    pub_time = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                else:
                    pub_time = published_at

                # Make datetime naive for comparison
                if pub_time.tzinfo:
                    pub_time = pub_time.replace(tzinfo=None)

                hours_old = (datetime.now() - pub_time).total_seconds() / 3600
                if hours_old <= 1:
                    weight += 30
                elif hours_old <= 6:
                    weight += 25
                elif hours_old <= 24:
                    weight += 20
                elif hours_old <= 48:
                    weight += 10
                elif hours_old <= 168:  # 7 days
                    weight += 5
            except Exception as e:
                logger.debug(f"Error parsing date: {e}")

        # Hot news bonus
        if article.get('isHot', False):
            weight += 20

        return weight

    def _detect_category(self, title: str, description: str = '') -> str:
        """Detect news category from content"""
        text = f"{title} {description}".lower()

        category_keywords = {
            'FDA_APPROVAL': ['fda approv', 'fda clear', 'drug approv'],
            'MERGER': ['merger', 'merge with'],
            'ACQUISITION': ['acqui', 'acquire', 'acquisition'],
            'BANKRUPTCY': ['bankrupt', 'chapter 11', 'chapter 7'],
            'BUYOUT': ['buyout', 'buy out'],
            'TAKEOVER': ['takeover', 'take over', 'hostile bid'],
            'EARNINGS_BEAT': ['earnings beat', 'beat estimates', 'exceed expect', 'profit surge'],
            'EARNINGS_MISS': ['earnings miss', 'miss estimates', 'below expect', 'profit drop'],
            'IPO': ['ipo', 'initial public offering', 'going public'],
            'INVESTIGATION': ['investigation', 'probe', 'inquiry', 'sec investigat'],
            'LAWSUIT': ['lawsuit', 'sue', 'legal action', 'settlement'],
            'RECALL': ['recall', 'safety issue', 'defect'],
            'GUIDANCE_RAISED': ['guidance raised', 'raise forecast', 'raise outlook', 'upbeat guidance'],
            'GUIDANCE_LOWERED': ['guidance lower', 'cut forecast', 'lower outlook', 'warn'],
            'BREAKTHROUGH': ['breakthrough', 'revolutionary', 'game-chang'],
            'ECONOMIC': ['fed', 'interest rate', 'inflation', 'gdp', 'unemployment'],
            'CRYPTO': ['bitcoin', 'crypto', 'ethereum', 'blockchain']
        }

        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return category

        return 'GENERAL'

    def _detect_impact(self, category: str) -> str:
        """Detect impact level from category"""
        high_impact = ['FDA_APPROVAL', 'MERGER', 'ACQUISITION', 'BANKRUPTCY', 'BUYOUT', 'TAKEOVER']
        medium_impact = ['EARNINGS_BEAT', 'EARNINGS_MISS', 'IPO', 'INVESTIGATION', 'LAWSUIT',
                        'RECALL', 'GUIDANCE_RAISED', 'GUIDANCE_LOWERED', 'BREAKTHROUGH']

        if category in high_impact:
            return 'HIGH'
        elif category in medium_impact:
            return 'MEDIUM'
        return 'LOW'

    def _extract_ticker(self, title: str, description: str = '') -> Optional[str]:
        """Try to extract stock ticker from news"""
        import re
        text = f"{title} {description}"

        # Common patterns: $AAPL, (NASDAQ: AAPL), AAPL stock
        patterns = [
            r'\$([A-Z]{1,5})\b',
            r'\((?:NASDAQ|NYSE|AMEX):\s*([A-Z]{1,5})\)',
            r'\b([A-Z]{2,5})\s+(?:stock|shares|inc|corp)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def get_market_news(self, limit: int = 20) -> List[Dict]:
        """
        Get general market news

        Returns latest business/finance news
        """
        if not self.client:
            return self._get_mock_news()

        try:
            # Get top business headlines
            response = self.client.get_top_headlines(
                category='business',
                language='en',
                country='us',
                page_size=limit
            )

            if response['status'] != 'ok':
                return self._get_mock_news()

            articles = []
            for article in response.get('articles', []):
                articles.append({
                    'title': article.get('title', ''),
                    'description': article.get('description', ''),
                    'source': article.get('source', {}).get('name', 'Unknown'),
                    'url': article.get('url', ''),
                    'publishedAt': article.get('publishedAt', ''),
                    'image': article.get('urlToImage', ''),
                })

            return articles

        except Exception as e:
            logger.error(f"Error fetching market news: {str(e)}")
            return self._get_mock_news()

    def get_stock_news(self, ticker: str, days: int = 7) -> List[Dict]:
        """
        Get news for specific stock

        Args:
            ticker: Stock symbol
            days: Number of days to look back
        """
        if not self.client:
            return []

        try:
            # Calculate date range
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)

            response = self.client.get_everything(
                q=ticker,
                from_param=from_date.strftime('%Y-%m-%d'),
                to=to_date.strftime('%Y-%m-%d'),
                language='en',
                sort_by='relevancy',
                page_size=10
            )

            if response['status'] != 'ok':
                return []

            articles = []
            for article in response.get('articles', []):
                articles.append({
                    'title': article.get('title', ''),
                    'description': article.get('description', ''),
                    'source': article.get('source', {}).get('name', 'Unknown'),
                    'url': article.get('url', ''),
                    'publishedAt': article.get('publishedAt', ''),
                    'image': article.get('urlToImage', ''),
                })

            return articles

        except Exception as e:
            logger.error(f"Error fetching news for {ticker}: {str(e)}")
            return []

    def get_news_bombs(self, limit: int = 10, days: int = 1) -> List[Dict]:
        """
        Get "news bombs" - high-impact market-moving stories

        Filters for breaking news with explosive keywords AND stock relevance
        """
        if not self.client:
            return self._get_mock_bombs()

        try:
            # Search for high-impact keywords IN FINANCE/BUSINESS context
            all_bombs = []

            # Use more targeted search queries to get STOCK-RELATED news only
            finance_queries = [
                'stock acquisition OR stock merger',
                'stock earnings beat OR earnings miss',
                'FDA approval stock',
                'IPO stock market',
                'stock bankruptcy OR stock buyout'
            ]

            for query in finance_queries:
                try:
                    response = self.client.get_everything(
                        q=query,
                        from_param=(datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'),
                        language='en',
                        sort_by='publishedAt',
                        page_size=5,
                        domains='reuters.com,bloomberg.com,cnbc.com,marketwatch.com,wsj.com,finance.yahoo.com,seekingalpha.com'  # Only financial news sources
                    )

                    if response['status'] == 'ok':
                        for article in response.get('articles', []):
                            title = article.get('title', '')
                            description = article.get('description', '')

                            # Use smart category detection instead of assuming from query
                            category = self._detect_category(title, description)

                            # Extract ticker - REQUIRED for it to be a valid stock news
                            ticker = self._extract_ticker(title, description)

                            # FILTER: Only include if we found a ticker OR category is stock-related
                            if not ticker and category == 'GENERAL':
                                continue  # Skip non-stock news

                            bomb = {
                                'title': title,
                                'description': description,
                                'source': article.get('source', {}).get('name', 'Unknown'),
                                'url': article.get('url', ''),
                                'publishedAt': article.get('publishedAt', ''),
                                'image': article.get('urlToImage', ''),
                                'impact': self._detect_impact(category),
                                'category': category,
                                'isHot': True,
                                'ticker': ticker
                            }
                            bomb['weight'] = self.calculate_news_weight(bomb)
                            all_bombs.append(bomb)
                except Exception as e:
                    logger.error(f"Error searching query {query}: {str(e)}")
                    continue

            # Sort by weight (most important first)
            all_bombs.sort(key=lambda x: x['weight'], reverse=True)

            # Remove duplicates by title
            seen_titles = set()
            unique_bombs = []
            for bomb in all_bombs:
                if bomb['title'] not in seen_titles:
                    seen_titles.add(bomb['title'])
                    unique_bombs.append(bomb)

            logger.info(f"✅ Found {len(unique_bombs)} relevant stock news bombs")
            return unique_bombs[:limit]

        except Exception as e:
            logger.error(f"Error fetching news bombs: {str(e)}")
            return self._get_mock_bombs()

    def get_categorized_news(
        self,
        sort_by: Literal['newest', 'weighted'] = 'newest',
        days: int = 7,
        limit: int = 20,
        ticker: Optional[str] = None
    ) -> List[Dict]:
        """
        Get news sorted by either time (newest) or weight (most impactful)

        Args:
            sort_by: 'newest' for most recent, 'weighted' for most impactful
            days: Number of days to look back (1-7)
            limit: Maximum number of articles
            ticker: Optional stock ticker to filter by

        Returns: List of news articles with weight scores
        """
        if not self.client:
            return self._get_mock_categorized_news(sort_by, limit)

        try:
            all_news = []

            # Get news bombs (high-impact)
            bombs = self.get_news_bombs(limit=30, days=days)
            all_news.extend(bombs)

            # Get general market news
            market_news = self.get_market_news(limit=20)
            for article in market_news:
                title = article.get('title', '')
                description = article.get('description', '')
                category = self._detect_category(title, description)

                news_item = {
                    'title': title,
                    'description': description,
                    'source': article.get('source', 'Unknown'),
                    'url': article.get('url', ''),
                    'publishedAt': article.get('publishedAt', ''),
                    'image': article.get('image', ''),
                    'category': category,
                    'impact': self._detect_impact(category),
                    'isHot': False,
                    'ticker': self._extract_ticker(title, description)
                }
                news_item['weight'] = self.calculate_news_weight(news_item)
                all_news.append(news_item)

            # If ticker specified, get stock-specific news
            if ticker:
                stock_news = self.get_stock_news(ticker, days=days)
                for article in stock_news:
                    title = article.get('title', '')
                    description = article.get('description', '')
                    category = self._detect_category(title, description)

                    news_item = {
                        'title': title,
                        'description': description,
                        'source': article.get('source', 'Unknown'),
                        'url': article.get('url', ''),
                        'publishedAt': article.get('publishedAt', ''),
                        'image': article.get('image', ''),
                        'category': category,
                        'impact': self._detect_impact(category),
                        'isHot': False,
                        'ticker': ticker
                    }
                    news_item['weight'] = self.calculate_news_weight(news_item)
                    all_news.append(news_item)

            # Remove duplicates
            seen_titles = set()
            unique_news = []
            for news in all_news:
                if news['title'] not in seen_titles:
                    seen_titles.add(news['title'])
                    unique_news.append(news)

            # Filter by ticker if specified (STRICT VALIDATION)
            if ticker:
                # Get company name for better validation
                try:
                    from app.services.yfinance_service import get_yfinance_service
                    yf_service = get_yfinance_service()
                    fundamentals = yf_service.get_fundamentals(ticker)
                    company_name = fundamentals.get('shortName', '').lower() if fundamentals else ''
                except Exception as e:
                    company_name = ''
                    logger.warning(f"Could not get company name for {ticker}: {e}")

                ticker_lower = ticker.lower()
                validated_news = []

                # Sports keywords to filter out
                sports_keywords = ['nfl', 'nba', 'nhl', 'mlb', 'soccer', 'football', 'basketball',
                                 'hockey', 'baseball', 'playoff', 'super bowl', 'championship game',
                                 'world series', 'finals game', 'trade deadline', 'draft pick',
                                 'coach', 'quarterback', 'touchdown', 'goal scorer', 'player stats']

                for n in unique_news:
                    title_lower = n.get('title', '').lower()
                    desc_lower = n.get('description', '').lower()

                    # Skip if it's sports news
                    is_sports = any(keyword in title_lower or keyword in desc_lower for keyword in sports_keywords)
                    if is_sports:
                        continue

                    # Check if ticker or company name appears in meaningful context
                    ticker_match = (
                        n.get('ticker') == ticker or
                        f'${ticker_lower}' in title_lower or  # Stock ticker format like $AAPL
                        f' {ticker_lower} ' in f' {title_lower} ' or  # Ticker as separate word
                        f'({ticker_lower})' in title_lower or  # Ticker in parentheses
                        ticker_lower in title_lower.split()  # Ticker as complete word
                    )

                    company_match = False
                    if company_name and len(company_name) > 3:  # Only check if company name is meaningful
                        company_match = (
                            company_name in title_lower or
                            company_name in desc_lower
                        )

                    if ticker_match or company_match:
                        validated_news.append(n)

                unique_news = validated_news

            # Sort based on preference
            if sort_by == 'weighted':
                unique_news.sort(key=lambda x: x.get('weight', 0), reverse=True)
            else:  # newest
                unique_news.sort(key=lambda x: x.get('publishedAt', ''), reverse=True)

            return unique_news[:limit]

        except Exception as e:
            logger.error(f"Error fetching categorized news: {str(e)}")
            return self._get_mock_categorized_news(sort_by, limit)

    def get_stock_news_weighted(self, ticker: str, days: int = 7) -> Dict:
        """
        Get comprehensive news analysis for a specific stock

        Returns both newest and most weighted news, plus summary stats
        """
        news = self.get_categorized_news(
            sort_by='weighted',
            days=days,
            limit=30,
            ticker=ticker
        )

        # Calculate news metrics
        total_weight = sum(n.get('weight', 0) for n in news)
        avg_weight = total_weight / len(news) if news else 0

        # Count by category
        category_counts = {}
        for n in news:
            cat = n.get('category', 'GENERAL')
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # Sort by newest and weighted
        newest = sorted(news, key=lambda x: x.get('publishedAt', ''), reverse=True)[:10]
        weighted = sorted(news, key=lambda x: x.get('weight', 0), reverse=True)[:10]

        return {
            'ticker': ticker,
            'total_articles': len(news),
            'avg_weight': round(avg_weight, 1),
            'categories': category_counts,
            'newest': newest,
            'weighted': weighted,
            'period_days': days
        }

    def _get_mock_news(self) -> List[Dict]:
        """Mock news data"""
        return [
            {
                'title': 'Fed Signals Potential Rate Cut in 2024',
                'description': 'Federal Reserve hints at possible interest rate reductions',
                'source': 'Reuters',
                'url': 'https://reuters.com',
                'publishedAt': datetime.now().isoformat(),
                'image': None,
                'category': 'ECONOMIC',
                'impact': 'MEDIUM',
                'isHot': False,
                'ticker': None,
                'weight': 100
            },
            {
                'title': 'Tech Stocks Rally on AI Optimism',
                'description': 'Major tech companies surge on artificial intelligence growth',
                'source': 'Bloomberg',
                'url': 'https://bloomberg.com',
                'publishedAt': (datetime.now() - timedelta(hours=2)).isoformat(),
                'image': None,
                'category': 'GENERAL',
                'impact': 'LOW',
                'isHot': False,
                'ticker': None,
                'weight': 75
            }
        ]

    def _get_mock_bombs(self) -> List[Dict]:
        """Mock news bombs"""
        return [
            {
                'title': 'BREAKING: FDA Approves Major Drug Treatment',
                'description': 'Pharmaceutical breakthrough could save millions',
                'source': 'WSJ',
                'url': 'https://wsj.com',
                'publishedAt': datetime.now().isoformat(),
                'image': None,
                'impact': 'HIGH',
                'category': 'FDA_APPROVAL',
                'isHot': True,
                'ticker': None,
                'weight': 168
            },
            {
                'title': 'Major Tech Company Announces $50B Acquisition',
                'description': 'Largest acquisition in sector history to reshape industry',
                'source': 'Bloomberg',
                'url': 'https://bloomberg.com',
                'publishedAt': (datetime.now() - timedelta(hours=3)).isoformat(),
                'image': None,
                'impact': 'HIGH',
                'category': 'ACQUISITION',
                'isHot': True,
                'ticker': None,
                'weight': 160
            },
            {
                'title': 'Company Reports Earnings Beat, Stock Surges',
                'description': 'Q4 earnings exceed analyst expectations by 25%',
                'source': 'CNBC',
                'url': 'https://cnbc.com',
                'publishedAt': (datetime.now() - timedelta(hours=5)).isoformat(),
                'image': None,
                'impact': 'HIGH',
                'category': 'EARNINGS_BEAT',
                'isHot': True,
                'ticker': None,
                'weight': 145
            },
            {
                'title': 'IPO Launch: New Tech Unicorn Goes Public',
                'description': 'Highly anticipated IPO opens with strong demand',
                'source': 'MarketWatch',
                'url': 'https://marketwatch.com',
                'publishedAt': (datetime.now() - timedelta(hours=8)).isoformat(),
                'image': None,
                'impact': 'MEDIUM',
                'category': 'IPO',
                'isHot': False,
                'ticker': None,
                'weight': 127
            },
            {
                'title': 'Biotech Firm Reports Breakthrough in Cancer Research',
                'description': 'Phase 3 trials show promising results for new treatment',
                'source': 'Reuters',
                'url': 'https://reuters.com',
                'publishedAt': (datetime.now() - timedelta(hours=12)).isoformat(),
                'image': None,
                'impact': 'MEDIUM',
                'category': 'BREAKTHROUGH',
                'isHot': False,
                'ticker': None,
                'weight': 115
            },
            {
                'title': 'SEC Launches Investigation into Trading Practices',
                'description': 'Regulatory probe focuses on potential market manipulation',
                'source': 'Financial Times',
                'url': 'https://ft.com',
                'publishedAt': (datetime.now() - timedelta(days=1)).isoformat(),
                'image': None,
                'impact': 'MEDIUM',
                'category': 'INVESTIGATION',
                'isHot': False,
                'ticker': None,
                'weight': 108
            },
            {
                'title': 'Company Raises Full-Year Guidance',
                'description': 'Strong demand drives upward revision in revenue forecast',
                'source': 'Yahoo Finance',
                'url': 'https://finance.yahoo.com',
                'publishedAt': (datetime.now() - timedelta(days=2)).isoformat(),
                'image': None,
                'impact': 'MEDIUM',
                'category': 'GUIDANCE_RAISED',
                'isHot': False,
                'ticker': None,
                'weight': 90
            },
            {
                'title': 'Bitcoin Reaches New Monthly High',
                'description': 'Cryptocurrency rally continues amid institutional interest',
                'source': 'CNBC',
                'url': 'https://cnbc.com',
                'publishedAt': (datetime.now() - timedelta(days=3)).isoformat(),
                'image': None,
                'impact': 'LOW',
                'category': 'CRYPTO',
                'isHot': False,
                'ticker': None,
                'weight': 75
            }
        ]

    def _get_mock_categorized_news(self, sort_by: str, limit: int) -> List[Dict]:
        """Mock categorized news data"""
        all_news = self._get_mock_bombs() + self._get_mock_news()

        if sort_by == 'weighted':
            all_news.sort(key=lambda x: x.get('weight', 0), reverse=True)
        else:  # newest
            all_news.sort(key=lambda x: x.get('publishedAt', ''), reverse=True)

        return all_news[:limit]


# Global singleton
_news_service = None

def get_news_service() -> NewsService:
    """Get or create News service singleton"""
    global _news_service
    if _news_service is None:
        _news_service = NewsService()
    return _news_service
