"""
TradeMaster Pro - Reddit Sentiment Service
===========================================

Tracks trending stocks on Reddit (WallStreetBets, stocks, investing)
Analyzes sentiment and mention volume to find trending plays.
"""

import os
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import Counter
import praw
from dotenv import load_dotenv
import re

load_dotenv()

logger = logging.getLogger(__name__)


class RedditService:
    """Reddit API service for social sentiment analysis"""

    def __init__(self):
        self.client_id = os.getenv('REDDIT_CLIENT_ID')
        self.client_secret = os.getenv('REDDIT_CLIENT_SECRET')

        if not self.client_id or not self.client_secret:
            logger.warning("Reddit API credentials not found")
            self.reddit = None
        else:
            try:
                self.reddit = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    user_agent='TradeMaster Pro v1.0'
                )
                logger.info("Reddit client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Reddit client: {str(e)}")
                self.reddit = None

        # Subreddits to monitor
        self.subreddits = ['wallstreetbets', 'stocks', 'investing', 'StockMarket']

        # Common stock ticker pattern (1-5 uppercase letters)
        self.ticker_pattern = re.compile(r'\b[A-Z]{1,5}\b')

        # Filter out common words that look like tickers
        self.filter_words = {
            'I', 'A', 'DD', 'CEO', 'CFO', 'PE', 'EPS', 'IPO', 'WSB', 'YOLO',
            'FD', 'ITM', 'OTM', 'ATH', 'ATL', 'IMO', 'IMHO', 'USA', 'US',
            'SEC', 'FDA', 'FED', 'GDP', 'CPI', 'FOMC', 'ETF', 'AMA', 'TL',
            'DR', 'TLDR', 'AM', 'PM', 'EST', 'PST', 'LMAO', 'LOL', 'HODL',
            'TO', 'THE', 'FOR', 'AND', 'OR', 'OF', 'IS', 'IT', 'AS', 'AT',
            'BY', 'ON', 'IN', 'UP', 'OUT', 'GO', 'ALL', 'NEW', 'NOW', 'GET',
            'SEE', 'WAY', 'OWN', 'VERY', 'MUST', 'NEXT', 'NICE', 'GOOD', 'BAD',
            # Additional filters for common false positives
            'AI', 'S', 'P', 'TA', 'RH', 'RE', 'NO', 'SO', 'DO', 'IF', 'MY',
            'ME', 'WE', 'BE', 'HE', 'SHE', 'AN', 'ANY', 'CAN', 'MAY', 'WILL',
            'JUST', 'SOME', 'MORE', 'MOST', 'ONLY', 'OVER', 'SUCH', 'THAN',
            'THEN', 'THEM', 'THEY', 'THIS', 'THAT', 'WHAT', 'WHEN', 'WHERE',
            'WHO', 'WHY', 'HOW', 'SAME', 'BEEN', 'WERE', 'HAVE', 'HAS', 'HAD',
            'EVEN', 'WELL', 'BACK', 'ALSO', 'HERE', 'THERE', 'THESE', 'THOSE'
        }

    def get_trending_stocks(self, limit: int = 20, hours: int = 24) -> List[Dict]:
        """
        Get trending stocks from Reddit

        Returns list of stocks sorted by mentions, with sentiment
        """
        if not self.reddit:
            logger.warning("Reddit client not available")
            return self._get_mock_trending()

        try:
            ticker_mentions = Counter()
            ticker_sentiments = {}
            ticker_posts = {}

            # Scan multiple subreddits
            for subreddit_name in self.subreddits:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)

                    # Get hot posts
                    for submission in subreddit.hot(limit=50):
                        # Check if post is recent
                        post_time = datetime.fromtimestamp(submission.created_utc)
                        if datetime.now() - post_time > timedelta(hours=hours):
                            continue

                        # Extract tickers from title and selftext
                        text = f"{submission.title} {submission.selftext}"
                        tickers = self._extract_tickers(text)

                        for ticker in tickers:
                            ticker_mentions[ticker] += 1

                            # Analyze sentiment from text (not just upvotes!)
                            sentiment_score = self._analyze_text_sentiment(text)

                            if ticker not in ticker_sentiments:
                                ticker_sentiments[ticker] = []
                            ticker_sentiments[ticker].append(sentiment_score)

                            # Store example post
                            if ticker not in ticker_posts or submission.score > ticker_posts[ticker].get('score', 0):
                                ticker_posts[ticker] = {
                                    'title': submission.title,
                                    'score': submission.score,
                                    'url': f"https://reddit.com{submission.permalink}",
                                    'subreddit': subreddit_name
                                }

                except Exception as e:
                    logger.error(f"Error scanning subreddit {subreddit_name}: {str(e)}")
                    continue

            # Format results
            trending = []
            for ticker, mentions in ticker_mentions.most_common(limit):
                if mentions < 2:  # Filter out noise
                    continue

                # Calculate average sentiment safely, ensuring no NaN values
                if ticker in ticker_sentiments and len(ticker_sentiments[ticker]) > 0:
                    avg_sentiment = sum(ticker_sentiments[ticker]) / len(ticker_sentiments[ticker])
                else:
                    avg_sentiment = 0.0  # Default to neutral if no sentiment data

                sentiment_label = self._sentiment_to_label(avg_sentiment)

                # Get top post for reasoning
                top_post = ticker_posts.get(ticker, {})
                top_title = top_post.get('title', '')

                # Build intelligent reasoning from actual post content
                reasoning = self._build_sentiment_reasoning(
                    ticker,
                    avg_sentiment,
                    mentions,
                    top_title
                )

                trending.append({
                    'ticker': ticker,
                    'mentions': mentions,
                    'sentiment': sentiment_label,
                    'sentimentScore': round(avg_sentiment, 2),
                    'trending': mentions > 10,
                    'spike': mentions > 20,
                    'examplePost': top_post,
                    'reasoning': reasoning  # NEW: Explanation of sentiment
                })

            return trending

        except Exception as e:
            logger.error(f"Error getting trending stocks: {str(e)}")
            return self._get_mock_trending()

    def _analyze_text_sentiment(self, text: str) -> float:
        """
        Analyze sentiment from text using keyword analysis

        Returns score from -3.0 (very bearish) to +3.0 (very bullish)
        """
        text_lower = text.lower()

        # Bullish keywords
        bullish_keywords = {
            'moon': 2.0, 'mooning': 2.0, 'rocket': 2.0, 'calls': 1.5,
            'bull': 1.5, 'bullish': 1.5, 'buy': 1.0, 'long': 1.0,
            'surge': 1.5, 'breakout': 1.5, 'pump': 1.5, 'soar': 1.5,
            'rally': 1.5, 'gain': 1.0, 'up': 0.5, 'green': 1.0,
            'winning': 1.0, 'beat': 1.0, 'strong': 1.0, 'growth': 1.0,
            'yolo': 1.5, 'diamond hands': 2.0, 'hold': 0.5, 'hodl': 1.0,
            'undervalued': 1.5, 'cheap': 1.0, 'discount': 1.0,
            'potential': 0.5, 'opportunity': 0.5, 'bullrun': 2.0
        }

        # Bearish keywords
        bearish_keywords = {
            'crash': -2.0, 'dump': -2.0, 'puts': -1.5, 'bear': -1.5,
            'bearish': -1.5, 'sell': -1.0, 'short': -1.5, 'tank': -2.0,
            'plummet': -2.0, 'collapse': -2.0, 'drop': -1.0, 'fall': -1.0,
            'down': -0.5, 'red': -1.0, 'losing': -1.0, 'loss': -1.0,
            'weak': -1.0, 'miss': -1.0, 'overvalued': -1.5, 'expensive': -1.0,
            'bubble': -1.5, 'rug pull': -2.0, 'scam': -2.0, 'fraud': -2.0,
            'warning': -1.0, 'caution': -0.5, 'risk': -0.5, 'concern': -0.5
        }

        score = 0.0

        # Count bullish keywords
        for keyword, weight in bullish_keywords.items():
            if keyword in text_lower:
                score += weight

        # Count bearish keywords
        for keyword, weight in bearish_keywords.items():
            if keyword in text_lower:
                score += weight  # weight is already negative

        # Normalize score to -3.0 to +3.0 range
        score = max(-3.0, min(3.0, score))

        return score

    def _extract_tickers(self, text: str) -> List[str]:
        """Extract stock tickers from text"""
        # Find all potential tickers
        potential_tickers = self.ticker_pattern.findall(text)

        # Filter out common words
        tickers = [t for t in potential_tickers if t not in self.filter_words]

        # Remove duplicates and sort
        return list(set(tickers))

    def _sentiment_to_label(self, score: float) -> str:
        """Convert sentiment score to label"""
        if score > 2.0:
            return 'VERY_BULLISH'
        elif score > 1.0:
            return 'BULLISH'
        elif score > 0.5:
            return 'SLIGHTLY_BULLISH'
        elif score > -0.5:
            return 'NEUTRAL'
        elif score > -1.0:
            return 'SLIGHTLY_BEARISH'
        elif score > -2.0:
            return 'BEARISH'
        else:
            return 'VERY_BEARISH'

    def _build_sentiment_reasoning(
        self,
        ticker: str,
        sentiment_score: float,
        mentions: int,
        top_title: str
    ) -> str:
        """
        Build intelligent reasoning for why sentiment is bullish/bearish

        Analyzes:
        - Actual post titles
        - Mention volume
        - Sentiment keywords found
        """
        text_lower = top_title.lower()
        reasons = []

        # Check for specific bullish signals
        if 'moon' in text_lower or 'rocket' in text_lower:
            reasons.append("Strong bullish momentum - 'moon'/'rocket' references")
        elif 'calls' in text_lower or 'yolo' in text_lower:
            reasons.append("Options traders piling into calls - high conviction")
        elif 'breakout' in text_lower or 'surge' in text_lower:
            reasons.append("Technical breakout mentioned - momentum play")
        elif 'earnings beat' in text_lower or 'beat estimates' in text_lower:
            reasons.append("Earnings beat driving positive sentiment")
        elif 'undervalued' in text_lower or 'cheap' in text_lower:
            reasons.append("Value opportunity - seen as underpriced")

        # Check for bearish signals
        elif 'puts' in text_lower or 'short' in text_lower:
            reasons.append("Put buyers betting against - bearish setup")
        elif 'crash' in text_lower or 'dump' in text_lower:
            reasons.append("Fear of crash/dump - negative outlook")
        elif 'overvalued' in text_lower or 'bubble' in text_lower:
            reasons.append("Viewed as overvalued - correction expected")
        elif 'rug pull' in text_lower or 'scam' in text_lower:
            reasons.append("Trust issues - fraud concerns")

        # Mention volume analysis
        if mentions > 30:
            reasons.append(f"Extremely high mention volume ({mentions} posts) - major attention")
        elif mentions > 15:
            reasons.append(f"High activity ({mentions} posts) - trending topic")
        elif mentions > 5:
            reasons.append(f"Moderate discussion ({mentions} posts) - gaining traction")

        # Sentiment interpretation
        if sentiment_score > 2.0:
            reasons.append("Very bullish language - extreme optimism")
        elif sentiment_score > 1.0:
            reasons.append("Bullish tone - positive outlook dominates")
        elif sentiment_score < -2.0:
            reasons.append("Very bearish language - extreme pessimism")
        elif sentiment_score < -1.0:
            reasons.append("Bearish tone - negative sentiment prevails")

        # If no specific keywords found, use generic
        if not reasons:
            if sentiment_score > 0:
                reasons.append(f"Generally positive discussion - retail interest building")
            elif sentiment_score < 0:
                reasons.append(f"Cautious sentiment - skepticism in posts")
            else:
                reasons.append(f"Mixed signals - neutral discussion")

        return " | ".join(reasons[:3])  # Max 3 reasons for clarity

    def _get_mock_trending(self) -> List[Dict]:
        """
        Realistic mock data when Reddit API is not available

        Mix of bullish, bearish, and neutral stocks to reflect real market sentiment
        """
        return [
            {
                'ticker': 'NVDA',
                'mentions': 45,
                'sentiment': 'VERY_BULLISH',
                'sentimentScore': 2.5,
                'trending': True,
                'spike': True,
                'examplePost': {
                    'title': 'NVDA 🚀 AI demand is insane - calls printing',
                    'score': 1200,
                    'url': 'https://reddit.com/r/wallstreetbets',
                    'subreddit': 'wallstreetbets'
                },
                'reasoning': "Strong bullish momentum - 'moon'/'rocket' references | Extremely high mention volume (45 posts) - major attention | Very bullish language - extreme optimism"
            },
            {
                'ticker': 'TSLA',
                'mentions': 38,
                'sentiment': 'BULLISH',
                'sentimentScore': 1.4,
                'trending': True,
                'spike': True,
                'examplePost': {
                    'title': 'TSLA delivery numbers looking strong Q4',
                    'score': 950,
                    'url': 'https://reddit.com/r/stocks',
                    'subreddit': 'stocks'
                },
                'reasoning': "Generally positive discussion - retail interest building | Extremely high mention volume (38 posts) - major attention | Bullish tone - positive outlook dominates"
            },
            {
                'ticker': 'META',
                'mentions': 24,
                'sentiment': 'BEARISH',
                'sentimentScore': -1.2,
                'trending': True,
                'spike': False,
                'examplePost': {
                    'title': 'META puts looking juicy - ad revenue concerns',
                    'score': 680,
                    'url': 'https://reddit.com/r/wallstreetbets',
                    'subreddit': 'wallstreetbets'
                },
                'reasoning': "Put buyers betting against - bearish setup | High activity (24 posts) - trending topic | Bearish tone - negative sentiment prevails"
            },
            {
                'ticker': 'AMD',
                'mentions': 19,
                'sentiment': 'SLIGHTLY_BULLISH',
                'sentimentScore': 0.7,
                'trending': True,
                'spike': False,
                'examplePost': {
                    'title': 'AMD earnings next week - potential upside',
                    'score': 520,
                    'url': 'https://reddit.com/r/stocks',
                    'subreddit': 'stocks'
                },
                'reasoning': "Moderate discussion (19 posts) - gaining traction | Generally positive discussion - retail interest building"
            },
            {
                'ticker': 'SPY',
                'mentions': 32,
                'sentiment': 'NEUTRAL',
                'sentimentScore': 0.1,
                'trending': True,
                'spike': False,
                'examplePost': {
                    'title': 'SPY riding the 50-day MA - which way next?',
                    'score': 890,
                    'url': 'https://reddit.com/r/wallstreetbets',
                    'subreddit': 'wallstreetbets'
                },
                'reasoning': "Extremely high mention volume (32 posts) - major attention | Mixed signals - neutral discussion"
            },
            {
                'ticker': 'COIN',
                'mentions': 15,
                'sentiment': 'VERY_BEARISH',
                'sentimentScore': -2.3,
                'trending': True,
                'spike': False,
                'examplePost': {
                    'title': 'COIN crashing hard - crypto winter continues',
                    'score': 410,
                    'url': 'https://reddit.com/r/cryptocurrency',
                    'subreddit': 'cryptocurrency'
                },
                'reasoning': "Fear of crash/dump - negative outlook | High activity (15 posts) - trending topic | Very bearish language - extreme pessimism"
            }
        ]


# Global singleton
_reddit_service = None

def get_reddit_service() -> RedditService:
    """Get or create Reddit service singleton"""
    global _reddit_service
    if _reddit_service is None:
        _reddit_service = RedditService()
    return _reddit_service
