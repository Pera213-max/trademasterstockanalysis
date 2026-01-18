"""
Earnings Calendar Service - Track earnings dates and surprises

Data Sources:
- Yahoo Finance Earnings (yfinance)

This service tracks upcoming earnings dates and historical earnings
surprises to identify potential catalysts and trading opportunities.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging
import math

import yfinance as yf

logger = logging.getLogger(__name__)


class EarningsService:
    """Service for fetching and analyzing earnings data"""

    def __init__(self, finnhub_api_key: Optional[str] = None):
        self.finnhub_api_key = finnhub_api_key
        self.finnhub_base_url = "https://finnhub.io/api/v1"
        self.headers = {
            "User-Agent": "TradeMaster Pro trademasterpro@example.com"
        }
        self.cache_ttl_seconds = 60 * 60 * 12
        self._cache: Dict[str, Tuple[datetime, Dict]] = {}

    def _get_cached(self, ticker: str) -> Optional[Dict]:
        entry = self._cache.get(ticker)
        if not entry:
            return None
        expires_at, data = entry
        if datetime.now() >= expires_at:
            self._cache.pop(ticker, None)
            return None
        return data

    def _set_cached(self, ticker: str, data: Dict) -> None:
        self._cache[ticker] = (datetime.now() + timedelta(seconds=self.cache_ttl_seconds), data)

    def get_earnings_calendar(self, ticker: str) -> Dict:
        """
        Get earnings calendar data for a ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict with earnings calendar information
        """
        try:
            logger.info(f"Fetching earnings calendar for {ticker}")

            cached = self._get_cached(ticker)
            if cached:
                return cached

            earnings_data = self._get_yfinance_earnings_data(ticker)
            if not earnings_data:
                earnings_data = self._get_default_earnings_data(ticker)

            result = {
                "ticker": ticker,
                "next_earnings_date": earnings_data["next_date"],
                "days_until_earnings": earnings_data["days_until"],
                "estimated_eps": earnings_data["estimated_eps"],
                "previous_eps": earnings_data["previous_eps"],
                "earnings_history": earnings_data["history"],
                "beat_streak": self._calculate_beat_streak(earnings_data["history"]),
                "average_surprise": self._calculate_avg_surprise(earnings_data["history"]),
                "signal": self._generate_earnings_signal(earnings_data),
                "earnings_quality": self._assess_earnings_quality(earnings_data)
            }
            self._set_cached(ticker, result)
            return result

        except Exception as e:
            logger.error(f"Error fetching earnings calendar for {ticker}: {str(e)}")
            earnings_data = self._get_default_earnings_data(ticker)
            return {
                "ticker": ticker,
                "next_earnings_date": earnings_data["next_date"],
                "days_until_earnings": earnings_data["days_until"],
                "estimated_eps": earnings_data["estimated_eps"],
                "previous_eps": earnings_data["previous_eps"],
                "earnings_history": earnings_data["history"],
                "beat_streak": 0,
                "average_surprise": 0.0,
                "signal": None,
                "earnings_quality": "UNKNOWN"
            }

    def _safe_float(self, value: object) -> float:
        try:
            if value is None:
                return 0.0
            if isinstance(value, str) and not value.strip():
                return 0.0
            num = float(value)
            if math.isnan(num) or math.isinf(num):
                return 0.0
            return num
        except Exception:
            return 0.0

    def _is_nan(self, value: object) -> bool:
        if value is None:
            return True
        try:
            return math.isnan(float(value))
        except Exception:
            return False

    def _calculate_beat_streak(self, history: List[Dict]) -> int:
        """Calculate consecutive earnings beats"""
        streak = 0
        for earning in history:
            if earning["surprise_percent"] > 0:
                streak += 1
            else:
                break
        return streak

    def _calculate_avg_surprise(self, history: List[Dict]) -> float:
        """Calculate average earnings surprise percentage"""
        if not history:
            return 0.0

        total_surprise = sum(e["surprise_percent"] for e in history)
        return total_surprise / len(history)

    def _assess_earnings_quality(self, data: Dict) -> str:
        """
        Assess earnings quality based on historical performance

        Quality levels:
        - EXCELLENT: 4+ consecutive beats, avg surprise > 5%
        - GOOD: 2-3 consecutive beats, avg surprise > 0%
        - AVERAGE: Mixed results
        - POOR: Consistent misses
        """
        history = data["history"]
        if not history:
            return "UNKNOWN"

        beat_streak = self._calculate_beat_streak(history)
        avg_surprise = self._calculate_avg_surprise(history)

        if beat_streak >= 4 and avg_surprise >= 5:
            return "EXCELLENT"
        elif beat_streak >= 2 and avg_surprise > 0:
            return "GOOD"
        elif avg_surprise < -5:
            return "POOR"
        else:
            return "AVERAGE"

    def _generate_earnings_signal(self, data: Dict) -> Optional[str]:
        """Generate trading signal based on earnings data"""
        days_until = data["days_until"]
        beat_streak = self._calculate_beat_streak(data["history"])
        avg_surprise = self._calculate_avg_surprise(data["history"])

        if days_until is None:
            return None

        # Pre-earnings runup (7-14 days before earnings)
        if 7 <= days_until <= 14 and beat_streak >= 3:
            return "PRE_EARNINGS_RUNUP"

        # Earnings beat expected (strong historical performance)
        elif 0 <= days_until <= 7 and beat_streak >= 4 and avg_surprise >= 5:
            return "BEAT_EXPECTED"

        # Earnings risk (approaching earnings with poor history)
        elif 0 <= days_until <= 7 and avg_surprise < -3:
            return "EARNINGS_RISK"

        # Post-earnings opportunity (just reported)
        elif -3 <= days_until < 0 and beat_streak >= 1:
            return "POST_EARNINGS_MOMENTUM"

        return None

    def _get_yfinance_earnings_data(self, ticker: str) -> Optional[Dict]:
        try:
            stock = yf.Ticker(ticker)
            dates = None
            try:
                dates = stock.get_earnings_dates(limit=8)
            except Exception:
                dates = None

            history: List[Dict] = []
            if dates is not None and not dates.empty:
                try:
                    dates_sorted = dates.sort_index(ascending=False)
                except Exception:
                    dates_sorted = dates

                for idx, row in dates_sorted.iterrows():
                    reported = row.get("Reported EPS")
                    if self._is_nan(reported):
                        continue

                    estimated_raw = row.get("EPS Estimate")
                    surprise_pct_raw = row.get("Surprise(%)")

                    actual = self._safe_float(reported)
                    estimated = self._safe_float(estimated_raw)
                    surprise_pct = self._safe_float(surprise_pct_raw)
                    if abs(surprise_pct) <= 1:
                        surprise_pct = surprise_pct * 100

                    quarter_date = idx.date().isoformat() if hasattr(idx, "date") else str(idx)
                    history.append({
                        "quarter": quarter_date,
                        "date": quarter_date,
                        "actual_eps": actual,
                        "estimated_eps": estimated,
                        "surprise": actual - estimated,
                        "surprise_percent": surprise_pct
                    })

            estimated_eps = history[0]["estimated_eps"] if history else 0
            previous_eps = history[0]["actual_eps"] if history else 0

            next_date = None
            if dates is not None and not dates.empty:
                try:
                    today = datetime.now().date()
                    future_dates = [d.date() for d in dates.index if d.date() >= today]
                    if future_dates:
                        next_date = min(future_dates)
                except Exception:
                    next_date = None

            if next_date is None:
                next_date = self._get_yfinance_next_earnings_date(ticker)

            days_until = None
            if next_date:
                days_until = (next_date - datetime.now().date()).days

            if not history and next_date is None:
                return None

            return {
                "next_date": next_date.isoformat() if next_date else None,
                "days_until": days_until,
                "estimated_eps": estimated_eps,
                "previous_eps": previous_eps,
                "history": history
            }
        except Exception as e:
            logger.warning(f"yfinance earnings fetch failed for {ticker}: {str(e)}")
            return None

    def _get_yfinance_next_earnings_date(self, ticker: str) -> Optional[datetime.date]:
        try:
            stock = yf.Ticker(ticker)
            dates = None
            try:
                dates = stock.get_earnings_dates(limit=6)
            except Exception:
                dates = None

            if dates is not None and not dates.empty:
                future_dates = [d.date() for d in dates.index if d.date() >= datetime.now().date()]
                if future_dates:
                    return min(future_dates)

            calendar = stock.calendar
            if calendar is not None and not calendar.empty:
                if "Earnings Date" in calendar.index:
                    value = calendar.loc["Earnings Date"]
                    if isinstance(value, list) and value:
                        return value[0].date()
                    if isinstance(value, datetime):
                        return value.date()
                    if hasattr(value, "date"):
                        return value.date()

        except Exception:
            return None

        return None

    def _get_default_earnings_data(self, ticker: str) -> Dict:
        """Return default data when API fails"""
        return {
            "next_date": None,
            "days_until": None,
            "estimated_eps": 0,
            "previous_eps": 0,
            "history": []
        }

    def get_earnings_score(self, ticker: str) -> int:
        """
        Get earnings score for AI predictions (0-20 points)

        Returns:
            Score from 0-20 based on earnings performance
        """
        try:
            data = self.get_earnings_calendar(ticker)

            score = 10  # Neutral baseline

            beat_streak = data["beat_streak"]
            avg_surprise = data["average_surprise"]
            days_until = data["days_until_earnings"]

            # Excellent earnings track record
            if beat_streak >= 4 and avg_surprise >= 5:
                score += 10
            elif beat_streak >= 2 and avg_surprise > 0:
                score += 5

            # Poor earnings track record
            elif beat_streak == 0 and avg_surprise < -5:
                score -= 10
            elif avg_surprise < 0:
                score -= 3

            # Pre-earnings runup window (7-14 days before)
            if days_until and 7 <= days_until <= 14 and beat_streak >= 3:
                score += 5

            # Earnings risk (too close to earnings with uncertainty)
            elif days_until and 0 <= days_until <= 3 and beat_streak < 2:
                score -= 5

            # Clamp to 0-20 range
            return max(0, min(20, score))

        except Exception as e:
            logger.error(f"Error calculating earnings score for {ticker}: {str(e)}")
            return 10  # Neutral on error


# Global instance
_earnings_service = None

def get_earnings_service(finnhub_api_key: Optional[str] = None) -> EarningsService:
    """Get or create earnings service instance"""
    global _earnings_service
    if _earnings_service is None:
        _earnings_service = EarningsService(finnhub_api_key)
    return _earnings_service
