"""
Social Scanner Service for TradeMaster Pro

Scans social media platforms (Reddit, Twitter, StockTwits) for trending stock mentions
and sentiment analysis.
"""

import re
import logging
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedditScanner:
    """
    Scanner for Reddit stock discussions (r/wallstreetbets, r/stocks)

    Uses PRAW (Python Reddit API Wrapper) to fetch posts and comments,
    extract stock tickers, and analyze sentiment.
    """

    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None,
                 user_agent: Optional[str] = None):
        """
        Initialize Reddit scanner

        Args:
            client_id: Reddit API client ID
            client_secret: Reddit API client secret
            user_agent: Reddit API user agent
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent or "TradeMasterPro/1.0"
        self.reddit = None
        self.rate_limit_delay = 1.0  # 1 second delay between requests (60 req/min)
        self.last_request_time = 0

        # Initialize Reddit connection if credentials provided
        if client_id and client_secret:
            try:
                import praw
                self.reddit = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent=self.user_agent
                )
                logger.info("Reddit API initialized successfully")
            except ImportError:
                logger.warning("praw library not installed. Install with: pip install praw")
            except Exception as e:
                logger.error(f"Failed to initialize Reddit API: {e}")

        # Ticker regex patterns
        # Matches $AAPL or standalone AAPL (2-5 uppercase letters)
        self.ticker_pattern = re.compile(r'\$([A-Z]{1,5})\b|\b([A-Z]{2,5})\b')

        # Common words to exclude (not tickers)
        self.excluded_words = {
            'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS',
            'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM', 'HIS', 'HOW', 'ITS', 'MAY',
            'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WHO', 'BOY', 'DID', 'ITS', 'LET', 'PUT',
            'SAY', 'SHE', 'TOO', 'USE', 'USD', 'USA', 'CEO', 'CFO', 'CTO', 'IPO', 'ETF',
            'WSB', 'DD', 'YOLO', 'FD', 'IMO', 'ATH', 'ATL', 'EOD', 'AH', 'PM', 'PT',
            'TA', 'FA', 'IV', 'YTD', 'EPS', 'ER', 'SEC', 'Fed', 'GDP', 'CPI', 'API',
            'EDIT', 'TLDR', 'ELI5', 'LOL', 'WTF', 'OMG', 'BTW', 'IMO', 'FOMO', 'HODL'
        }

        # Sentiment word lists
        self.positive_words = {
            'bullish', 'bull', 'moon', 'rocket', 'gain', 'gains', 'profit', 'up', 'high',
            'buy', 'long', 'calls', 'breakout', 'rally', 'surge', 'soar', 'climb', 'strong',
            'good', 'great', 'excellent', 'amazing', 'awesome', 'love', 'like', 'positive',
            'growth', 'opportunity', 'undervalued', 'cheap', 'winner', 'winning', 'tendies',
            'diamond', 'hands', 'hold', 'hodl', 'pump', 'lambo', 'squeeze'
        }

        self.negative_words = {
            'bearish', 'bear', 'crash', 'drop', 'loss', 'losses', 'down', 'low', 'sell',
            'short', 'puts', 'breakdown', 'dump', 'plunge', 'fall', 'decline', 'weak',
            'bad', 'terrible', 'awful', 'worst', 'hate', 'dislike', 'negative', 'overvalued',
            'expensive', 'loser', 'losing', 'rekt', 'bag', 'bagholder', 'trap', 'rug',
            'scam', 'fraud', 'bankruptcy', 'delisted'
        }

    def _rate_limit(self):
        """Apply rate limiting between API requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()

    def _extract_tickers(self, text: str) -> List[str]:
        """
        Extract stock tickers from text

        Args:
            text: Text to search for tickers

        Returns:
            List of ticker symbols found
        """
        if not text:
            return []

        tickers = []
        matches = self.ticker_pattern.findall(text.upper())

        for match in matches:
            # match is a tuple ($TICKER, TICKER), one will be empty
            ticker = match[0] or match[1]

            # Skip excluded words and single letters
            if ticker and len(ticker) >= 2 and ticker not in self.excluded_words:
                tickers.append(ticker)

        return tickers

    def _calculate_sentiment(self, text: str) -> float:
        """
        Calculate sentiment score for text

        Args:
            text: Text to analyze

        Returns:
            Sentiment score between -1.0 (very negative) and 1.0 (very positive)
        """
        if not text:
            return 0.0

        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)

        positive_count = sum(1 for word in words if word in self.positive_words)
        negative_count = sum(1 for word in words if word in self.negative_words)

        total = positive_count + negative_count
        if total == 0:
            return 0.0

        # Calculate score: (positive - negative) / total
        sentiment = (positive_count - negative_count) / total
        return round(sentiment, 3)

    def scan_wallstreetbets(self, limit: int = 100, time_filter: str = "day") -> List[Dict]:
        """
        Scan r/wallstreetbets for stock mentions and sentiment

        Args:
            limit: Number of posts to scan (max 100)
            time_filter: Time filter (hour, day, week, month, year, all)

        Returns:
            List of dicts with ticker, mentions, sentiment_score, posts
        """
        return self._scan_subreddit("wallstreetbets", limit, time_filter)

    def scan_stocks_subreddit(self, limit: int = 100, time_filter: str = "day") -> List[Dict]:
        """
        Scan r/stocks for stock mentions and sentiment

        Args:
            limit: Number of posts to scan (max 100)
            time_filter: Time filter (hour, day, week, month, year, all)

        Returns:
            List of dicts with ticker, mentions, sentiment_score, posts
        """
        return self._scan_subreddit("stocks", limit, time_filter)

    def _scan_subreddit(self, subreddit_name: str, limit: int = 100,
                       time_filter: str = "day") -> List[Dict]:
        """
        Scan a subreddit for stock mentions and sentiment

        Args:
            subreddit_name: Name of subreddit to scan
            limit: Number of posts to scan
            time_filter: Time filter for posts

        Returns:
            List of dicts with ticker, mentions, sentiment_score, posts
        """
        if not self.reddit:
            logger.warning("Reddit API not initialized. Using mock data.")
            return self._get_mock_data(subreddit_name)

        try:
            subreddit = self.reddit.subreddit(subreddit_name)

            # Track ticker mentions and sentiments
            ticker_data = defaultdict(lambda: {
                'mentions': 0,
                'sentiment_scores': [],
                'post_titles': []
            })

            # Scan top posts
            logger.info(f"Scanning r/{subreddit_name} top {limit} posts from {time_filter}...")

            for post in subreddit.top(time_filter=time_filter, limit=limit):
                self._rate_limit()

                # Extract tickers from title and selftext
                text = f"{post.title} {post.selftext}"
                tickers = self._extract_tickers(text)

                if not tickers:
                    continue

                # Calculate sentiment
                sentiment = self._calculate_sentiment(text)

                # Update ticker data
                for ticker in set(tickers):  # Use set to count each ticker once per post
                    ticker_data[ticker]['mentions'] += 1
                    ticker_data[ticker]['sentiment_scores'].append(sentiment)
                    ticker_data[ticker]['post_titles'].append(post.title[:100])

            # Compile results
            results = []
            for ticker, data in ticker_data.items():
                # Calculate average sentiment
                avg_sentiment = sum(data['sentiment_scores']) / len(data['sentiment_scores'])

                results.append({
                    'ticker': ticker,
                    'mentions': data['mentions'],
                    'sentiment_score': round(avg_sentiment, 3),
                    'sentiment_label': self._get_sentiment_label(avg_sentiment),
                    'posts': data['post_titles'][:5],  # Top 5 post titles
                    'subreddit': subreddit_name,
                    'scanned_at': datetime.now().isoformat()
                })

            # Sort by mentions (descending)
            results.sort(key=lambda x: x['mentions'], reverse=True)

            logger.info(f"Found {len(results)} tickers in r/{subreddit_name}")
            return results

        except Exception as e:
            logger.error(f"Error scanning r/{subreddit_name}: {e}")
            return self._get_mock_data(subreddit_name)

    def _get_sentiment_label(self, score: float) -> str:
        """Convert sentiment score to label"""
        if score >= 0.5:
            return "Very Bullish"
        elif score >= 0.2:
            return "Bullish"
        elif score <= -0.5:
            return "Very Bearish"
        elif score <= -0.2:
            return "Bearish"
        else:
            return "Neutral"

    def _get_mock_data(self, subreddit_name: str) -> List[Dict]:
        """Return mock data when Reddit API is not available"""
        mock_data = {
            'wallstreetbets': [
                {
                    'ticker': 'NVDA',
                    'mentions': 245,
                    'sentiment_score': 0.72,
                    'sentiment_label': 'Very Bullish',
                    'posts': [
                        'NVDA to the moon! 🚀',
                        'All in on NVDA calls',
                        'NVDA earnings play - who\'s with me?'
                    ],
                    'subreddit': 'wallstreetbets',
                    'scanned_at': datetime.now().isoformat()
                },
                {
                    'ticker': 'TSLA',
                    'mentions': 189,
                    'sentiment_score': 0.45,
                    'sentiment_label': 'Bullish',
                    'posts': [
                        'TSLA oversold bounce incoming',
                        'Elon tweet pump incoming',
                        'TSLA $300 EOY?'
                    ],
                    'subreddit': 'wallstreetbets',
                    'scanned_at': datetime.now().isoformat()
                },
                {
                    'ticker': 'AMD',
                    'mentions': 156,
                    'sentiment_score': 0.38,
                    'sentiment_label': 'Bullish',
                    'posts': [
                        'AMD new chips looking strong',
                        'AMD vs NVDA - which to buy?',
                        'AMD earnings DD inside'
                    ],
                    'subreddit': 'wallstreetbets',
                    'scanned_at': datetime.now().isoformat()
                }
            ],
            'stocks': [
                {
                    'ticker': 'AAPL',
                    'mentions': 178,
                    'sentiment_score': 0.52,
                    'sentiment_label': 'Very Bullish',
                    'posts': [
                        'Apple Vision Pro sales exceeding expectations',
                        'AAPL dividend increase announced',
                        'Why AAPL is a solid long-term hold'
                    ],
                    'subreddit': 'stocks',
                    'scanned_at': datetime.now().isoformat()
                },
                {
                    'ticker': 'MSFT',
                    'mentions': 142,
                    'sentiment_score': 0.61,
                    'sentiment_label': 'Very Bullish',
                    'posts': [
                        'Microsoft Azure growth is impressive',
                        'MSFT AI strategy paying off',
                        'Long-term investment: MSFT analysis'
                    ],
                    'subreddit': 'stocks',
                    'scanned_at': datetime.now().isoformat()
                },
                {
                    'ticker': 'GOOGL',
                    'mentions': 98,
                    'sentiment_score': 0.28,
                    'sentiment_label': 'Bullish',
                    'posts': [
                        'Google Cloud competing with AWS',
                        'GOOGL undervalued compared to peers',
                        'Alphabet buyback program analysis'
                    ],
                    'subreddit': 'stocks',
                    'scanned_at': datetime.now().isoformat()
                }
            ]
        }

        return mock_data.get(subreddit_name, [])


class TwitterScanner:
    """
    Scanner for Twitter/X stock discussions

    NOTE: Twitter API v2 is paid (minimum $100/month as of 2024).
    This is a placeholder implementation that can be activated with API credentials.
    """

    def __init__(self, bearer_token: Optional[str] = None):
        """
        Initialize Twitter scanner

        Args:
            bearer_token: Twitter API v2 bearer token
        """
        self.bearer_token = bearer_token
        self.api_available = False

        if bearer_token:
            try:
                import tweepy
                self.client = tweepy.Client(bearer_token=bearer_token)
                self.api_available = True
                logger.info("Twitter API initialized successfully")
            except ImportError:
                logger.warning("tweepy library not installed. Install with: pip install tweepy")
            except Exception as e:
                logger.error(f"Failed to initialize Twitter API: {e}")

    def scan_trending_stocks(self, limit: int = 100) -> List[Dict]:
        """
        Scan Twitter for trending stock mentions

        Args:
            limit: Number of tweets to analyze

        Returns:
            List of dicts with ticker, mentions, sentiment_score
        """
        if not self.api_available:
            logger.warning("Twitter API not available. Using mock data.")
            return self._get_mock_data()

        # TODO: Implement Twitter API scanning when credentials are available
        # Search for tweets with cashtags ($AAPL) or stock-related hashtags
        # Use tweepy.Client.search_recent_tweets()

        return self._get_mock_data()

    def _get_mock_data(self) -> List[Dict]:
        """Return mock Twitter data"""
        return [
            {
                'ticker': 'NVDA',
                'mentions': 1842,
                'sentiment_score': 0.68,
                'sentiment_label': 'Very Bullish',
                'platform': 'twitter',
                'scanned_at': datetime.now().isoformat()
            },
            {
                'ticker': 'TSLA',
                'mentions': 1623,
                'sentiment_score': 0.42,
                'sentiment_label': 'Bullish',
                'platform': 'twitter',
                'scanned_at': datetime.now().isoformat()
            },
            {
                'ticker': 'AAPL',
                'mentions': 1204,
                'sentiment_score': 0.55,
                'sentiment_label': 'Very Bullish',
                'platform': 'twitter',
                'scanned_at': datetime.now().isoformat()
            }
        ]


class StockTwitsScanner:
    """
    Scanner for StockTwits stock discussions

    StockTwits has a free API with rate limits (200 requests/hour).
    """

    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize StockTwits scanner

        Args:
            access_token: StockTwits API access token (optional for some endpoints)
        """
        self.access_token = access_token
        self.base_url = "https://api.stocktwits.com/api/2"
        self.rate_limit_delay = 18  # ~200 requests/hour = 3600/200 = 18 seconds
        self.last_request_time = 0

    def _rate_limit(self):
        """Apply rate limiting between API requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()

    def get_trending_stocks(self, limit: int = 30) -> List[Dict]:
        """
        Get trending stocks from StockTwits

        Args:
            limit: Number of trending stocks to return

        Returns:
            List of dicts with ticker, mentions, sentiment_score
        """
        try:
            import requests

            self._rate_limit()

            # StockTwits trending endpoint (no auth required)
            url = f"{self.base_url}/trending/symbols.json"

            headers = {}
            if self.access_token:
                headers['Authorization'] = f'Bearer {self.access_token}'

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                symbols = data.get('symbols', [])

                results = []
                for i, symbol in enumerate(symbols[:limit], 1):
                    ticker = symbol.get('symbol', '')
                    title = symbol.get('title', '')

                    results.append({
                        'rank': i,
                        'ticker': ticker,
                        'name': title,
                        'mentions': None,  # Not provided by trending endpoint
                        'sentiment_score': None,  # Would need to fetch streams
                        'platform': 'stocktwits',
                        'scanned_at': datetime.now().isoformat()
                    })

                logger.info(f"Found {len(results)} trending stocks on StockTwits")
                return results
            else:
                logger.warning(f"StockTwits API error: {response.status_code}")
                return self._get_mock_data()

        except ImportError:
            logger.warning("requests library not installed")
            return self._get_mock_data()
        except Exception as e:
            logger.error(f"Error fetching StockTwits data: {e}")
            return self._get_mock_data()

    def get_ticker_sentiment(self, ticker: str, limit: int = 30) -> Dict:
        """
        Get sentiment for a specific ticker from StockTwits

        Args:
            ticker: Stock ticker symbol
            limit: Number of messages to analyze

        Returns:
            Dict with ticker, sentiment breakdown, and recent messages
        """
        try:
            import requests

            self._rate_limit()

            # StockTwits streams endpoint
            url = f"{self.base_url}/streams/symbol/{ticker}.json"
            params = {'limit': limit}

            headers = {}
            if self.access_token:
                headers['Authorization'] = f'Bearer {self.access_token}'

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                messages = data.get('messages', [])

                # Count sentiment
                bullish_count = 0
                bearish_count = 0

                for msg in messages:
                    entities = msg.get('entities', {})
                    sentiment = entities.get('sentiment', {})

                    if sentiment.get('basic') == 'Bullish':
                        bullish_count += 1
                    elif sentiment.get('basic') == 'Bearish':
                        bearish_count += 1

                total = bullish_count + bearish_count
                sentiment_score = 0.0

                if total > 0:
                    sentiment_score = (bullish_count - bearish_count) / total

                return {
                    'ticker': ticker,
                    'total_messages': len(messages),
                    'bullish_count': bullish_count,
                    'bearish_count': bearish_count,
                    'neutral_count': len(messages) - total,
                    'sentiment_score': round(sentiment_score, 3),
                    'sentiment_label': self._get_sentiment_label(sentiment_score),
                    'platform': 'stocktwits',
                    'scanned_at': datetime.now().isoformat()
                }
            else:
                logger.warning(f"StockTwits API error for {ticker}: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"Error fetching StockTwits sentiment for {ticker}: {e}")
            return {}

    def _get_sentiment_label(self, score: float) -> str:
        """Convert sentiment score to label"""
        if score >= 0.5:
            return "Very Bullish"
        elif score >= 0.2:
            return "Bullish"
        elif score <= -0.5:
            return "Very Bearish"
        elif score <= -0.2:
            return "Bearish"
        else:
            return "Neutral"

    def _get_mock_data(self) -> List[Dict]:
        """Return mock StockTwits data"""
        return [
            {
                'rank': 1,
                'ticker': 'TSLA',
                'name': 'Tesla Inc',
                'mentions': None,
                'sentiment_score': None,
                'platform': 'stocktwits',
                'scanned_at': datetime.now().isoformat()
            },
            {
                'rank': 2,
                'ticker': 'NVDA',
                'name': 'NVIDIA Corporation',
                'mentions': None,
                'sentiment_score': None,
                'platform': 'stocktwits',
                'scanned_at': datetime.now().isoformat()
            },
            {
                'rank': 3,
                'ticker': 'AAPL',
                'name': 'Apple Inc',
                'mentions': None,
                'sentiment_score': None,
                'platform': 'stocktwits',
                'scanned_at': datetime.now().isoformat()
            }
        ]


# Convenience functions for easy access

def scan_reddit_wallstreetbets(client_id: Optional[str] = None, client_secret: Optional[str] = None,
                               limit: int = 100) -> List[Dict]:
    """
    Convenience function to scan r/wallstreetbets

    Args:
        client_id: Reddit API client ID
        client_secret: Reddit API client secret
        limit: Number of posts to scan

    Returns:
        List of trending tickers with sentiment
    """
    scanner = RedditScanner(client_id=client_id, client_secret=client_secret)
    return scanner.scan_wallstreetbets(limit=limit)


def scan_reddit_stocks(client_id: Optional[str] = None, client_secret: Optional[str] = None,
                      limit: int = 100) -> List[Dict]:
    """
    Convenience function to scan r/stocks

    Args:
        client_id: Reddit API client ID
        client_secret: Reddit API client secret
        limit: Number of posts to scan

    Returns:
        List of trending tickers with sentiment
    """
    scanner = RedditScanner(client_id=client_id, client_secret=client_secret)
    return scanner.scan_stocks_subreddit(limit=limit)


def scan_stocktwits_trending(access_token: Optional[str] = None, limit: int = 30) -> List[Dict]:
    """
    Convenience function to get StockTwits trending stocks

    Args:
        access_token: StockTwits API access token
        limit: Number of trending stocks to return

    Returns:
        List of trending stocks
    """
    scanner = StockTwitsScanner(access_token=access_token)
    return scanner.get_trending_stocks(limit=limit)


# Example usage
if __name__ == "__main__":
    print("=== Social Scanner Service ===\n")

    # Test Reddit scanner
    print("1. Testing Reddit Scanner (r/wallstreetbets)...")
    reddit_scanner = RedditScanner()
    wsb_data = reddit_scanner.scan_wallstreetbets(limit=50)
    print(f"Found {len(wsb_data)} trending tickers on r/wallstreetbets")
    if wsb_data:
        print("\nTop 3 trending:")
        for item in wsb_data[:3]:
            print(f"  {item['ticker']}: {item['mentions']} mentions, "
                  f"sentiment: {item['sentiment_score']} ({item['sentiment_label']})")

    print("\n2. Testing Reddit Scanner (r/stocks)...")
    stocks_data = reddit_scanner.scan_stocks_subreddit(limit=50)
    print(f"Found {len(stocks_data)} trending tickers on r/stocks")
    if stocks_data:
        print("\nTop 3 trending:")
        for item in stocks_data[:3]:
            print(f"  {item['ticker']}: {item['mentions']} mentions, "
                  f"sentiment: {item['sentiment_score']} ({item['sentiment_label']})")

    # Test StockTwits scanner
    print("\n3. Testing StockTwits Scanner...")
    stocktwits_scanner = StockTwitsScanner()
    st_data = stocktwits_scanner.get_trending_stocks(limit=10)
    print(f"Found {len(st_data)} trending tickers on StockTwits")
    if st_data:
        print("\nTop 5 trending:")
        for item in st_data[:5]:
            print(f"  #{item['rank']}: {item['ticker']} - {item['name']}")

    # Test Twitter scanner
    print("\n4. Testing Twitter Scanner...")
    twitter_scanner = TwitterScanner()
    twitter_data = twitter_scanner.scan_trending_stocks(limit=10)
    print(f"Found {len(twitter_data)} trending tickers on Twitter (mock data)")

    print("\n=== Social Scanner Tests Complete ===")
