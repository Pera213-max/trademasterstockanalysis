"""
Short Interest Service - Track short squeeze potential

Data Sources:
- FINRA Short Interest (Free, updated bi-monthly)
- Finnhub Short Interest API (requires premium)
- Alternative: MarketBeat, Ortex (scraping)

This service tracks short interest percentage and days to cover to identify
potential short squeeze opportunities.
"""

from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

from .yfinance_service import get_yfinance_service

logger = logging.getLogger(__name__)


class ShortInterestService:
    """Service for fetching and analyzing short interest data"""

    def __init__(self):
        # FINRA publishes short interest data twice a month
        self.finra_url = "https://www.finra.org/finra-data/browse-catalog/short-sale-volume-data"
        self.headers = {
            "User-Agent": "TradeMaster Pro trademasterpro@example.com"
        }
        self.yfinance = get_yfinance_service()
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

    def get_short_interest(self, ticker: str) -> Dict:
        """
        Get short interest data for a ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict with short interest metrics
        """
        try:
            logger.info(f"Fetching short interest for {ticker}")

            cached = self._get_cached(ticker)
            if cached:
                return cached

            short_data = self._get_yfinance_short_data(ticker)
            if not short_data:
                return self._get_default_short_data(ticker)

            result = {
                "ticker": ticker,
                "short_percent_float": short_data["short_percent"],
                "short_percent_outstanding": short_data["short_percent_outstanding"],
                "short_shares": short_data["short_shares"],
                "float_shares": short_data["float_shares"],
                "average_daily_volume": short_data["avg_volume"],
                "days_to_cover": short_data["days_to_cover"],
                "short_ratio": short_data["short_ratio"],
                "squeeze_potential": self._calculate_squeeze_potential(short_data),
                "signal": self._generate_short_signal(short_data),
                "last_updated": short_data["last_updated"]
            }
            self._set_cached(ticker, result)
            return result

        except Exception as e:
            logger.error(f"Error fetching short interest for {ticker}: {str(e)}")
            return self._get_default_short_data(ticker)

    def _get_yfinance_short_data(self, ticker: str) -> Optional[Dict]:
        fundamentals = self.yfinance.get_fundamentals(ticker)
        if not fundamentals:
            return None

        short_pct = fundamentals.get("shortPercentOfFloat", 0) or 0
        short_ratio = fundamentals.get("shortRatio", 0) or 0
        float_shares = fundamentals.get("sharesFloat", 0) or 0
        avg_volume = fundamentals.get("averageVolume", 0) or 0

        if short_pct and short_pct > 1:
            short_pct = short_pct / 100.0

        short_shares = float_shares * short_pct if float_shares and short_pct else 0
        days_to_cover = short_ratio or (short_shares / avg_volume if avg_volume else 0)

        return {
            "short_percent": short_pct * 100 if short_pct else 0,
            "short_percent_outstanding": (short_pct * 0.85 * 100) if short_pct else 0,
            "short_shares": short_shares,
            "float_shares": float_shares,
            "avg_volume": avg_volume,
            "days_to_cover": days_to_cover,
            "short_ratio": short_ratio or days_to_cover,
            "last_updated": datetime.now().isoformat()
        }

    def _calculate_squeeze_potential(self, data: Dict) -> str:
        """
        Calculate short squeeze potential based on metrics

        High squeeze potential when:
        - Short interest > 20% AND Days to cover > 2
        """
        short_pct = data["short_percent"]
        dtc = data["days_to_cover"]

        if short_pct >= 30 and dtc >= 5:
            return "EXTREME"
        elif short_pct >= 20 and dtc >= 3:
            return "HIGH"
        elif short_pct >= 15 and dtc >= 2:
            return "MODERATE"
        elif short_pct >= 10:
            return "LOW"
        else:
            return "MINIMAL"

    def _generate_short_signal(self, data: Dict) -> Optional[str]:
        """Generate trading signal based on short interest"""
        short_pct = data["short_percent"]
        dtc = data["days_to_cover"]

        # Extreme squeeze setup: High short interest + High days to cover
        if short_pct >= 25 and dtc >= 4:
            return "SQUEEZE_SETUP"

        # High short interest but normal coverage
        elif short_pct >= 20:
            return "HIGH_SHORT_INTEREST"

        # Low short interest (bullish - shorts covered)
        elif short_pct <= 3:
            return "LOW_SHORT_INTEREST"

        return None

    def _get_mock_short_data(self, ticker: str) -> Dict:
        """
        Mock short interest data - replace with FINRA or Finnhub API

        Real implementation options:
        1. FINRA Short Interest Data (free, bi-monthly updates)
        2. Finnhub Short Interest API: finnhub_client.stock_short_interest(ticker)
        3. MarketBeat scraping
        """

        # Simulate short interest based on ticker hash (consistent mock data)
        hash_val = sum(ord(c) for c in ticker) % 10

        if hash_val > 7:  # 20% chance - high short interest (squeeze potential)
            short_percent = 28.5
            short_shares = 15000000
            float_shares = 50000000
            avg_volume = 2500000
        elif hash_val < 3:  # 30% chance - low short interest (bullish)
            short_percent = 2.8
            short_shares = 1000000
            float_shares = 35000000
            avg_volume = 5000000
        else:  # 50% chance - moderate short interest
            short_percent = 12.3
            short_shares = 5000000
            float_shares = 40000000
            avg_volume = 3000000

        days_to_cover = short_shares / avg_volume if avg_volume > 0 else 0

        return {
            "short_percent": short_percent,
            "short_percent_outstanding": short_percent * 0.85,  # Usually slightly lower
            "short_shares": short_shares,
            "float_shares": float_shares,
            "avg_volume": avg_volume,
            "days_to_cover": days_to_cover,
            "short_ratio": days_to_cover,  # Same as DTC
            "last_updated": (datetime.now() - timedelta(days=7)).isoformat()  # FINRA updates bi-monthly
        }

    def _get_default_short_data(self, ticker: str) -> Dict:
        """Return default data when API fails"""
        return {
            "ticker": ticker,
            "short_percent_float": 0,
            "short_percent_outstanding": 0,
            "short_shares": 0,
            "float_shares": 0,
            "average_daily_volume": 0,
            "days_to_cover": 0,
            "short_ratio": 0,
            "squeeze_potential": "UNKNOWN",
            "signal": None,
            "last_updated": None
        }

    def get_short_score(self, ticker: str) -> int:
        """
        Get short interest score for AI predictions (0-20 points)

        Returns:
            Score from 0-20 based on short squeeze potential
        """
        try:
            data = self.get_short_interest(ticker)

            score = 10  # Neutral baseline

            short_pct = data["short_percent_float"]
            dtc = data["days_to_cover"]

            # High short interest = potential squeeze (bullish)
            if short_pct >= 30 and dtc >= 5:
                score += 10  # Extreme squeeze potential
            elif short_pct >= 20 and dtc >= 3:
                score += 7   # High squeeze potential
            elif short_pct >= 15 and dtc >= 2:
                score += 4   # Moderate squeeze potential

            # Low short interest = shorts covered (bullish)
            elif short_pct <= 3:
                score += 3   # Positive sign

            # Very high short interest can also be bearish (smart money)
            elif short_pct >= 40:
                score -= 5   # Possibly overvalued

            # Clamp to 0-20 range
            return max(0, min(20, score))

        except Exception as e:
            logger.error(f"Error calculating short score for {ticker}: {str(e)}")
            return 10  # Neutral on error


# Global instance
_short_service = None

def get_short_service() -> ShortInterestService:
    """Get or create short interest service instance"""
    global _short_service
    if _short_service is None:
        _short_service = ShortInterestService()
    return _short_service
