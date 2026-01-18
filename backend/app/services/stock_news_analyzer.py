"""
TradeMaster Pro - Stock-Specific News Analyzer
===============================================

Detects and categorizes major news events for individual stocks:
- Earnings announcements
- FDA approvals/rejections
- Mergers & Acquisitions
- Product launches
- Executive changes
- Legal issues
- Partnership announcements
"""

import logging
import json
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .finnhub_service import get_finnhub_service
from app.config.settings import settings
from database.redis.config import get_redis_cache

logger = logging.getLogger(__name__)


class StockNewsAnalyzer:
    """Analyze stock-specific major news events"""

    # Keywords for different event types
    EVENT_KEYWORDS = {
        "earnings": [
            "earnings", "quarterly results", "q1", "q2", "q3", "q4",
            "revenue", "profit", "eps", "beat estimates", "miss estimates",
            "guidance", "outlook"
        ],
        "fda": [
            "fda", "approval", "drug", "clinical trial", "phase",
            "medication", "treatment", "biotech", "pharmaceutical"
        ],
        "merger": [
            "merger", "acquisition", "acquire", "bought", "takeover",
            "deal", "buyout", "m&a"
        ],
        "product": [
            "launch", "unveil", "announce", "new product", "release",
            "debut", "introduce"
        ],
        "executive": [
            "ceo", "cfo", "cto", "executive", "appoint", "resign",
            "hire", "depart", "management change"
        ],
        "legal": [
            "lawsuit", "settle", "court", "sec", "investigation",
            "fine", "penalty", "litigation"
        ],
        "partnership": [
            "partner", "collaborate", "joint venture", "agreement",
            "deal", "contract", "alliance"
        ],
        "analyst": [
            "upgrade", "downgrade", "price target", "analyst",
            "rating", "buy", "sell", "hold"
        ]
    }

    # Impact levels for different event types
    EVENT_IMPACT = {
        "earnings": "HIGH",
        "fda": "VERY HIGH",
        "merger": "VERY HIGH",
        "product": "MEDIUM",
        "executive": "MEDIUM",
        "legal": "HIGH",
        "partnership": "MEDIUM",
        "analyst": "MEDIUM"
    }

    def __init__(self):
        self.finnhub = get_finnhub_service()
        self.redis_cache = get_redis_cache()
        logger.info("StockNewsAnalyzer initialized")

    def _get_cached_major_news(self, cache_key: str) -> Optional[List[Dict]]:
        if not self.redis_cache or not self.redis_cache.is_connected():
            return None
        try:
            cached_data = self.redis_cache.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as exc:
            logger.debug("Failed to read cached Finnhub news: %s", exc)
        return None

    def _set_cached_major_news(self, cache_key: str, data: List[Dict]) -> None:
        if not self.redis_cache or not self.redis_cache.is_connected():
            return
        try:
            self.redis_cache.redis_client.setex(
                cache_key,
                settings.FINNHUB_COMPANY_NEWS_TTL,
                json.dumps(data)
            )
        except Exception as exc:
            logger.debug("Failed to cache Finnhub news: %s", exc)

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
            logger.debug("Failed to acquire Finnhub news lock: %s", exc)
            return True

    def _release_lock(self, lock_key: str) -> None:
        if not self.redis_cache or not self.redis_cache.is_connected():
            return
        try:
            self.redis_cache.redis_client.delete(lock_key)
        except Exception as exc:
            logger.debug("Failed to release Finnhub news lock: %s", exc)

    def get_major_news(self, ticker: str, days: int = 7) -> List[Dict]:
        """
        Get major news events for a specific stock

        Args:
            ticker: Stock ticker symbol
            days: Number of days to look back

        Returns:
            List of categorized major news events
        """
        lock_acquired = False
        ticker = ticker.upper()
        cache_key = f"finnhub:company_news:{ticker}:{days}"
        lock_key = f"{cache_key}:lock"

        try:
            cached = self._get_cached_major_news(cache_key)
            if cached is not None:
                return cached

            lock_acquired = self._acquire_lock(lock_key)
            if not lock_acquired:
                for _ in range(3):
                    time.sleep(0.5)
                    cached = self._get_cached_major_news(cache_key)
                    if cached is not None:
                        return cached
                return []

            if not self.finnhub:
                self._set_cached_major_news(cache_key, [])
                return []

            # Get company news from Finnhub
            raw_news = self.finnhub.get_company_news(ticker, days)

            if not raw_news:
                self._set_cached_major_news(cache_key, [])
                return []

            # Categorize and filter for major events
            major_news = []
            for article in raw_news:
                event = self._categorize_news(article)
                if event and event["impact"] in ["HIGH", "VERY HIGH"]:
                    major_news.append(event)

            # Sort by impact and date
            major_news.sort(key=lambda x: (
                0 if x["impact"] == "VERY HIGH" else 1 if x["impact"] == "HIGH" else 2,
                -x["timestamp"]
            ))

            major_news = major_news[:5]  # Return top 5 major events
            self._set_cached_major_news(cache_key, major_news)
            return major_news

        except Exception as e:
            logger.error(f"Error getting major news for {ticker}: {str(e)}")
            return []
        finally:
            if lock_acquired:
                self._release_lock(lock_key)

    def _categorize_news(self, article: Dict) -> Optional[Dict]:
        """
        Categorize a news article by event type

        Returns:
            Dict with category, impact, and article info
        """
        try:
            headline = article.get("headline", "").lower()
            summary = article.get("summary", "").lower()
            combined_text = f"{headline} {summary}"

            # Check for each event type
            matched_categories = []
            for category, keywords in self.EVENT_KEYWORDS.items():
                if any(keyword in combined_text for keyword in keywords):
                    matched_categories.append(category)

            if not matched_categories:
                return None

            # Use the first matched category (highest priority)
            primary_category = matched_categories[0]

            # Determine sentiment
            sentiment = self._determine_sentiment(combined_text, primary_category)

            # Get timestamp and create datetime
            timestamp = article.get("datetime", 0)
            pub_datetime = datetime.fromtimestamp(timestamp) if timestamp > 0 else datetime.now()

            # Generate comprehensive impact analysis
            impact_analysis = self._generate_impact_analysis(
                primary_category, sentiment, headline, summary
            )

            return {
                "category": primary_category,
                "impact": self.EVENT_IMPACT.get(primary_category, "MEDIUM").lower(),
                "sentiment": sentiment.lower(),
                "title": article.get("headline", ""),
                "headline": article.get("headline", ""),
                "summary": article.get("summary", "")[:200],  # Limit summary length
                "source": article.get("source", "Unknown"),
                "url": article.get("url", ""),
                "timestamp": timestamp,
                "date": pub_datetime.strftime("%Y-%m-%d %H:%M"),
                "published_at": pub_datetime.isoformat(),
                "reason": self._generate_reason(primary_category, sentiment, headline),
                "ai_impact": impact_analysis
            }

        except Exception as e:
            logger.error(f"Error categorizing news: {str(e)}")
            return None

    def _determine_sentiment(self, text: str, category: str) -> str:
        """Determine if news is positive, negative, or neutral"""

        # Positive indicators
        positive_words = [
            "beat", "exceed", "surge", "gain", "approve", "success",
            "growth", "record", "high", "upgrade", "strong", "profit",
            "win", "award", "breakthrough", "positive"
        ]

        # Negative indicators
        negative_words = [
            "miss", "decline", "loss", "reject", "fail", "lawsuit",
            "investigation", "downgrade", "weak", "concern", "risk",
            "warning", "cut", "reduce", "slump", "drop"
        ]

        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)

        if positive_count > negative_count:
            return "POSITIVE"
        elif negative_count > positive_count:
            return "NEGATIVE"
        else:
            return "NEUTRAL"

    def _generate_impact_analysis(self, category: str, sentiment: str, headline: str, summary: str) -> str:
        """
        Generate comprehensive AI-powered impact analysis
        Explains HOW the news will affect the stock price
        """
        sentiment_upper = sentiment.upper()

        # Detailed impact analysis by category and sentiment
        impact_templates = {
            "earnings": {
                "POSITIVE": "📈 BULLISH IMPACT: Strong earnings performance typically drives institutional buying. Expect 3-8% upside in next 1-2 weeks as momentum traders enter. Watch for continued strength if guidance is also raised.",
                "NEGATIVE": "📉 BEARISH IMPACT: Earnings disappointment often triggers algorithmic selling. Expect 5-12% downside pressure as funds reduce exposure. Stock may find support at next technical level.",
                "NEUTRAL": "➡️ NEUTRAL IMPACT: In-line earnings suggest stock trades fairly valued. Expect consolidation around current levels. Watch for catalyst from guidance or analyst commentary."
            },
            "fda": {
                "POSITIVE": "🚀 MAJOR CATALYST: FDA approval can trigger 20-50% rally in biotech/pharma stocks. This unlocks multi-billion dollar market opportunity. Expect strong institutional accumulation and analyst upgrades.",
                "NEGATIVE": "⚠️ SIGNIFICANT RISK: FDA rejection often causes 30-60% decline in biotech stocks. This delays revenue potential by years. Expect heavy selling until new catalyst emerges.",
                "NEUTRAL": "⏳ PENDING CATALYST: FDA decision timeline creates high volatility. Options traders positioning for big move. Stock may remain range-bound until resolution."
            },
            "merger": {
                "POSITIVE": "💰 ACQUISITION PREMIUM: M&A activity typically offers 20-40% premium to current price. Arbitrage funds will buy, creating floor. Upside limited to deal price unless competing bid emerges.",
                "NEGATIVE": "🔻 DEAL UNCERTAINTY: Failed merger talks or antitrust concerns create downside. Stock may gap down 15-25% if deal collapses. Risk/reward favors sellers until clarity.",
                "NEUTRAL": "📋 DEAL IN PROGRESS: M&A negotiations ongoing. Stock will trade toward rumored price. Watch for regulatory approval timeline and potential competing bids."
            },
            "product": {
                "POSITIVE": "✨ GROWTH DRIVER: New product launch expands addressable market. Could add 5-15% to revenue estimates. Watch for early adoption metrics and pre-order data.",
                "NEGATIVE": "⚡ PRODUCT RISK: Launch delays or quality issues hurt brand reputation. May reduce revenue guidance by 3-8%. Monitor customer reviews and return rates.",
                "NEUTRAL": "📦 PRODUCT UPDATE: Routine product refresh maintains competitive position. Limited stock impact unless paired with strong demand signals."
            },
            "executive": {
                "POSITIVE": "👔 LEADERSHIP STRENGTH: Key executive hire from top competitor signals growth ambitions. Market rewards talent acquisition with 2-5% premium. Watch for strategic shifts.",
                "NEGATIVE": "🚪 LEADERSHIP CONCERN: Unexpected departure of C-suite creates uncertainty. Stock may decline 3-8% until succession plan clear. Watch for board announcements.",
                "NEUTRAL": "🔄 MANAGEMENT CHANGE: Planned transition suggests continuity. Limited market impact unless new leader brings major strategic pivot."
            },
            "legal": {
                "POSITIVE": "⚖️ LEGAL RESOLUTION: Favorable settlement removes overhang. Stock could rally 5-15% as legal risk premium evaporates. Clears path for normal operations.",
                "NEGATIVE": "🚨 LEGAL RISK: New lawsuit or investigation creates uncertainty. Expect 8-20% decline as investors price in potential fines and damages. Timeline uncertain.",
                "NEUTRAL": "📜 LEGAL PROCEEDINGS: Ongoing litigation with unclear outcome. Stock may remain volatile. Watch for settlement negotiations or court rulings."
            },
            "partnership": {
                "POSITIVE": "🤝 STRATEGIC WIN: Major partnership validates technology/product. Could expand distribution and add credibility. Expect 5-12% boost as analysts raise estimates.",
                "NEGATIVE": "❌ PARTNERSHIP LOST: Failed partnership talks or contract termination. May reduce revenue by 3-10%. Watch for management guidance revision.",
                "NEUTRAL": "📝 PARTNERSHIP NEWS: Standard business development activity. Limited impact unless partner is industry leader or deal size material."
            },
            "analyst": {
                "POSITIVE": "📊 ANALYST UPGRADE: Price target increase by top analyst often triggers momentum. Expect 2-5% move as retail follows institutional lead. Watch for upgrade cycle.",
                "NEGATIVE": "📉 ANALYST DOWNGRADE: Rating cut by respected analyst creates selling pressure. Stock may decline 3-8% as funds adjust positions. Watch for earnings revision.",
                "NEUTRAL": "📋 ANALYST OPINION: Neutral rating suggests hold-and-watch. Limited trading impact. Wait for fundamental catalyst before position change."
            }
        }

        # Get the appropriate template
        category_templates = impact_templates.get(category, {
            "POSITIVE": "📈 Positive development detected. This news could support higher stock prices in the near term. Monitor market reaction and volume for confirmation.",
            "NEGATIVE": "📉 Negative development detected. This news may create downward pressure on stock price. Consider risk management and position sizing carefully.",
            "NEUTRAL": "➡️ Neutral development. This news unlikely to significantly move stock price. Continue monitoring for additional catalysts."
        })

        impact_text = category_templates.get(sentiment_upper, category_templates.get("NEUTRAL", ""))

        # Add specific timing context based on headline/summary keywords
        headline_lower = headline.lower()
        if "immediate" in headline_lower or "now" in headline_lower or "today" in headline_lower:
            impact_text += " ⏰ IMMEDIATE IMPACT EXPECTED."
        elif "next quarter" in headline_lower or "upcoming" in headline_lower:
            impact_text += " 📅 Impact expected over next 30-90 days."

        return impact_text

    def _generate_reason(self, category: str, sentiment: str, headline: str) -> str:
        """Generate a reason why this news is important"""

        reasons = {
            "earnings": {
                "POSITIVE": "Strong earnings beat expectations - could drive stock higher",
                "NEGATIVE": "Earnings miss or guidance cut - may pressure stock price",
                "NEUTRAL": "Earnings in line with expectations - maintain current view"
            },
            "fda": {
                "POSITIVE": "FDA approval is major catalyst - significant upside potential",
                "NEGATIVE": "FDA rejection or delay - substantial downside risk",
                "NEUTRAL": "FDA decision pending - high volatility expected"
            },
            "merger": {
                "POSITIVE": "Acquisition at premium - immediate upside for shareholders",
                "NEGATIVE": "Merger concerns or regulatory issues - uncertainty ahead",
                "NEUTRAL": "Merger announcement - assess strategic fit and valuation"
            },
            "product": {
                "POSITIVE": "New product launch - potential revenue driver",
                "NEGATIVE": "Product issues or recalls - reputation and sales at risk",
                "NEUTRAL": "Product update announced - monitor market reception"
            },
            "executive": {
                "POSITIVE": "Strategic leadership hire - confidence in future direction",
                "NEGATIVE": "Unexpected executive departure - management instability",
                "NEUTRAL": "Leadership change - transitional period ahead"
            },
            "legal": {
                "POSITIVE": "Favorable legal outcome - removes overhang",
                "NEGATIVE": "New lawsuit or investigation - legal costs and reputation risk",
                "NEUTRAL": "Legal proceedings ongoing - watch for developments"
            },
            "partnership": {
                "POSITIVE": "Strategic partnership - validates business model",
                "NEGATIVE": "Partnership issues - questions about strategy",
                "NEUTRAL": "Collaboration announced - evaluate long-term benefits"
            },
            "analyst": {
                "POSITIVE": "Analyst upgrade - improved outlook from Wall Street",
                "NEGATIVE": "Analyst downgrade - weakening sentiment",
                "NEUTRAL": "Mixed analyst views - diverging opinions"
            }
        }

        return reasons.get(category, {}).get(sentiment, "Significant news event detected")

    def get_news_summary(self, ticker: str) -> Dict:
        """
        Get a summary of major news for a stock

        Returns:
            Dict with news count by category and recent major events
        """
        try:
            news = self.get_major_news(ticker, days=7)

            # Count by category
            category_counts = {}
            for event in news:
                cat = event["category"]
                category_counts[cat] = category_counts.get(cat, 0) + 1

            # Get most impactful event
            most_impactful = None
            if news:
                very_high = [n for n in news if n["impact"] == "VERY HIGH"]
                most_impactful = very_high[0] if very_high else news[0]

            return {
                "total_major_events": len(news),
                "category_breakdown": category_counts,
                "most_impactful_event": most_impactful,
                "recent_events": news[:3]  # Last 3 major events
            }

        except Exception as e:
            logger.error(f"Error getting news summary for {ticker}: {str(e)}")
            return {
                "total_major_events": 0,
                "category_breakdown": {},
                "most_impactful_event": None,
                "recent_events": []
            }


# Global singleton
_news_analyzer = None


def get_stock_news_analyzer() -> StockNewsAnalyzer:
    """Get or create singleton instance"""
    global _news_analyzer
    if _news_analyzer is None:
        _news_analyzer = StockNewsAnalyzer()
    return _news_analyzer
