"""
Options Flow Service - Track unusual options activity

Data Sources:
- yfinance Options (Free, basic options chain)
- Unusual Whales API (Premium $50/month)
- CBOE Options Data (Free but limited)

This service identifies unusual options activity that may signal
smart money positioning before major price moves.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

import yfinance as yf

logger = logging.getLogger(__name__)


class OptionsFlowService:
    """Service for fetching and analyzing options flow data"""

    def __init__(self):
        self.headers = {
            "User-Agent": "TradeMaster Pro trademasterpro@example.com"
        }
        self.cache_ttl_seconds = 60 * 60 * 6
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

    def get_options_activity(self, ticker: str) -> Dict:
        """
        Get options activity for a ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict with options flow metrics
        """
        try:
            logger.info(f"Fetching options activity for {ticker}")

            cached = self._get_cached(ticker)
            if cached:
                return cached

            options_data = self._get_yfinance_options_data(ticker)
            if not options_data:
                return self._get_default_options_data(ticker)

            result = {
                "ticker": ticker,
                "call_volume": options_data["call_volume"],
                "put_volume": options_data["put_volume"],
                "total_volume": options_data["call_volume"] + options_data["put_volume"],
                "put_call_ratio": self._calculate_pc_ratio(options_data),
                "call_open_interest": options_data["call_oi"],
                "put_open_interest": options_data["put_oi"],
                "unusual_activity": options_data["unusual_activity"],
                "flow_sentiment": self._calculate_flow_sentiment(options_data),
                "signal": self._generate_options_signal(options_data),
                "large_trades": options_data["large_trades"]
            }
            self._set_cached(ticker, result)
            return result

        except Exception as e:
            logger.error(f"Error fetching options activity for {ticker}: {str(e)}")
            return self._get_default_options_data(ticker)

    def _get_yfinance_options_data(self, ticker: str) -> Optional[Dict]:
        try:
            stock = yf.Ticker(ticker)
            expirations = stock.options or []
            if not expirations:
                return None

            expiry = expirations[0]
            chain = stock.option_chain(expiry)
            calls = chain.calls
            puts = chain.puts

            call_volume = float(calls["volume"].fillna(0).sum()) if not calls.empty else 0.0
            put_volume = float(puts["volume"].fillna(0).sum()) if not puts.empty else 0.0
            call_oi = float(calls["openInterest"].fillna(0).sum()) if not calls.empty else 0.0
            put_oi = float(puts["openInterest"].fillna(0).sum()) if not puts.empty else 0.0

            unusual_activity = False
            if (call_oi + put_oi) > 0:
                unusual_activity = (call_volume + put_volume) > 2 * (call_oi + put_oi)

            return {
                "call_volume": call_volume,
                "put_volume": put_volume,
                "call_oi": call_oi,
                "put_oi": put_oi,
                "unusual_activity": unusual_activity,
                "large_trades": []
            }
        except Exception as e:
            logger.warning(f"Options chain unavailable for {ticker}: {str(e)}")
            return None

    def _calculate_pc_ratio(self, data: Dict) -> float:
        """
        Calculate Put/Call ratio

        PC Ratio interpretation:
        - < 0.7: Bullish (more calls than puts)
        - 0.7 - 1.0: Neutral
        - > 1.0: Bearish (more puts than calls)
        """
        call_vol = data["call_volume"]
        if call_vol == 0:
            return 0

        return data["put_volume"] / call_vol

    def _calculate_flow_sentiment(self, data: Dict) -> str:
        """Calculate overall options flow sentiment"""
        pc_ratio = self._calculate_pc_ratio(data)
        unusual = data["unusual_activity"]

        if pc_ratio < 0.5 and unusual:
            return "VERY_BULLISH"
        elif pc_ratio < 0.7:
            return "BULLISH"
        elif pc_ratio > 1.5 and unusual:
            return "VERY_BEARISH"
        elif pc_ratio > 1.0:
            return "BEARISH"
        else:
            return "NEUTRAL"

    def _generate_options_signal(self, data: Dict) -> Optional[str]:
        """Generate trading signal based on options flow"""
        pc_ratio = self._calculate_pc_ratio(data)
        call_vol = data["call_volume"]
        put_vol = data["put_volume"]
        unusual = data["unusual_activity"]

        # Unusual call buying (bullish)
        if unusual and pc_ratio < 0.5 and call_vol > 1000:
            return "UNUSUAL_CALL_ACTIVITY"

        # Unusual put buying (bearish)
        elif unusual and pc_ratio > 1.5 and put_vol > 1000:
            return "UNUSUAL_PUT_ACTIVITY"

        # Heavy call volume (bullish)
        elif pc_ratio < 0.6 and call_vol > 5000:
            return "HEAVY_CALL_VOLUME"

        # Heavy put volume (bearish)
        elif pc_ratio > 1.2 and put_vol > 5000:
            return "HEAVY_PUT_VOLUME"

        return None

    def _get_mock_options_data(self, ticker: str) -> Dict:
        """
        Mock options data - replace with yfinance or Unusual Whales API

        Real implementation:
        ```python
        import yfinance as yf
        stock = yf.Ticker(ticker)
        options = stock.option_chain()
        calls = options.calls
        puts = options.puts

        call_volume = calls['volume'].sum()
        put_volume = puts['volume'].sum()
        call_oi = calls['openInterest'].sum()
        put_oi = puts['openInterest'].sum()

        # Detect unusual activity: volume > 2x open interest
        unusual = (call_volume + put_volume) > 2 * (call_oi + put_oi)
        ```
        """

        # Simulate options flow based on ticker hash
        hash_val = sum(ord(c) for c in ticker) % 10

        if hash_val > 7:  # 20% chance - unusual call activity (bullish)
            call_volume = 15000
            put_volume = 3000
            call_oi = 50000
            put_oi = 20000
            unusual_activity = True
            large_trades = [
                {
                    "type": "CALL",
                    "strike": 150,
                    "expiry": "2025-02-21",
                    "volume": 5000,
                    "premium": 8.50,
                    "total_value": 4250000
                },
                {
                    "type": "CALL",
                    "strike": 155,
                    "expiry": "2025-02-21",
                    "volume": 3000,
                    "premium": 6.25,
                    "total_value": 1875000
                }
            ]
        elif hash_val < 3:  # 30% chance - unusual put activity (bearish)
            call_volume = 2000
            put_volume = 12000
            call_oi = 15000
            put_oi = 40000
            unusual_activity = True
            large_trades = [
                {
                    "type": "PUT",
                    "strike": 140,
                    "expiry": "2025-02-21",
                    "volume": 4000,
                    "premium": 7.75,
                    "total_value": 3100000
                }
            ]
        else:  # 50% chance - normal activity
            call_volume = 5000
            put_volume = 4000
            call_oi = 30000
            put_oi = 25000
            unusual_activity = False
            large_trades = []

        return {
            "call_volume": call_volume,
            "put_volume": put_volume,
            "call_oi": call_oi,
            "put_oi": put_oi,
            "unusual_activity": unusual_activity,
            "large_trades": large_trades
        }

    def _get_default_options_data(self, ticker: str) -> Dict:
        """Return default data when API fails"""
        return {
            "ticker": ticker,
            "call_volume": 0,
            "put_volume": 0,
            "total_volume": 0,
            "put_call_ratio": 0,
            "call_open_interest": 0,
            "put_open_interest": 0,
            "unusual_activity": False,
            "flow_sentiment": "UNKNOWN",
            "signal": None,
            "large_trades": []
        }

    def get_options_score(self, ticker: str) -> int:
        """
        Get options flow score for AI predictions (0-20 points)

        Returns:
            Score from 0-20 based on options activity
        """
        try:
            activity = self.get_options_activity(ticker)

            score = 10  # Neutral baseline

            pc_ratio = activity["put_call_ratio"]
            unusual = activity["unusual_activity"]

            # Unusual call activity (very bullish)
            if unusual and pc_ratio < 0.5:
                score += 10

            # Heavy call volume (bullish)
            elif pc_ratio < 0.7:
                score += 5

            # Unusual put activity (very bearish)
            elif unusual and pc_ratio > 1.5:
                score -= 10

            # Heavy put volume (bearish)
            elif pc_ratio > 1.2:
                score -= 5

            # Bonus for large trade activity
            if len(activity["large_trades"]) >= 2:
                score += 3

            # Clamp to 0-20 range
            return max(0, min(20, score))

        except Exception as e:
            logger.error(f"Error calculating options score for {ticker}: {str(e)}")
            return 10  # Neutral on error


# Global instance
_options_service = None

def get_options_service() -> OptionsFlowService:
    """Get or create options flow service instance"""
    global _options_service
    if _options_service is None:
        _options_service = OptionsFlowService()
    return _options_service
