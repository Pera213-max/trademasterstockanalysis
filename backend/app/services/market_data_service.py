"""
Real Market Data Service
==========================

Fetches real-time market indicators:
- S&P 500, NASDAQ, DJI indices
- VIX (volatility index)
- Sector ETF performance
- Market breadth indicators

Uses yfinance for reliable data.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import yfinance as yf
from cachetools import TTLCache

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for fetching real market data"""

    def __init__(self):
        # Cache market data for 2 minutes
        self.cache = TTLCache(maxsize=10, ttl=120)

        # Market indices
        self.indices = {
            '^GSPC': 'S&P 500',
            '^IXIC': 'NASDAQ',
            '^DJI': 'Dow Jones',
            '^VIX': 'VIX'
        }

        # Sector ETFs
        self.sector_etfs = {
            'XLK': 'Technology',
            'XLE': 'Energy',
            'XLV': 'Healthcare',
            'XLF': 'Financial',
            'XLY': 'Consumer Discretionary',
            'XLP': 'Consumer Staples',
            'XLI': 'Industrial',
            'XLU': 'Utilities',
            'XLB': 'Materials'
        }

    def get_market_overview(self) -> Dict:
        """
        Get comprehensive market overview

        Returns current market conditions, sentiment, and sector performance
        """
        if 'overview' in self.cache:
            logger.info("📦 Returning cached market overview")
            return self.cache['overview']

        try:
            logger.info("🔄 Fetching real market data...")

            # Fetch indices
            indices_data = self._fetch_indices()

            # Fetch sector performance
            sectors_data = self._fetch_sectors()

            # Calculate market sentiment
            sentiment = self._calculate_sentiment(indices_data, sectors_data)

            # Build overview
            overview = {
                'indices': indices_data,
                'sectors': sectors_data,
                'sentiment': sentiment,
                'timestamp': datetime.now().isoformat(),
                'market_status': self._get_market_status()
            }

            # Cache result
            self.cache['overview'] = overview

            logger.info("✅ Market overview fetched successfully")
            return overview

        except Exception as e:
            logger.error(f"❌ Market overview fetch failed: {e}")
            return self._get_fallback_data()

    def _fetch_indices(self) -> List[Dict]:
        """Fetch major market indices"""
        indices = []

        for ticker, name in self.indices.items():
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                hist = stock.history(period='1d')

                if not hist.empty:
                    current = hist['Close'].iloc[-1]
                    previous = info.get('previousClose', current)
                    change = current - previous
                    change_pct = (change / previous * 100) if previous != 0 else 0

                    indices.append({
                        'ticker': ticker,
                        'name': name,
                        'price': round(float(current), 2),
                        'change': round(float(change), 2),
                        'changePercent': round(float(change_pct), 2),
                        'isPositive': bool(change >= 0)
                    })

            except Exception as e:
                logger.debug(f"Error fetching {ticker}: {e}")

        return indices

    def _fetch_sectors(self) -> List[Dict]:
        """Fetch sector ETF performance with robust error handling"""
        sectors = []
        failed_sectors = []

        for ticker, name in self.sector_etfs.items():
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period='5d')

                if not hist.empty and len(hist) >= 2:
                    current = hist['Close'].iloc[-1]
                    previous = hist['Close'].iloc[-2]
                    change = current - previous
                    change_pct = (change / previous * 100) if previous != 0 else 0

                    # Determine trend (up, down, flat)
                    if change_pct > 0.5:
                        trend = 'up'
                        status = 'Strong'
                    elif change_pct < -0.5:
                        trend = 'down'
                        status = 'Weak'
                    else:
                        trend = 'flat'
                        status = 'Neutral'

                    sectors.append({
                        'ticker': ticker,
                        'name': name,
                        'change': round(float(change), 2),
                        'changePercent': round(float(change_pct), 2),
                        'trend': trend,
                        'status': status
                    })
                    logger.debug(f"✅ {ticker} ({name}): {change_pct:+.2f}%")
                else:
                    # No data available - add with neutral values
                    logger.warning(f"⚠️ No data for {ticker} ({name}) - using neutral")
                    failed_sectors.append(ticker)
                    sectors.append({
                        'ticker': ticker,
                        'name': name,
                        'change': 0.0,
                        'changePercent': 0.0,
                        'trend': 'flat',
                        'status': 'Neutral'
                    })

            except Exception as e:
                logger.warning(f"❌ Error fetching {ticker} ({name}): {e}")
                failed_sectors.append(ticker)
                # Add sector with neutral values even on error
                sectors.append({
                    'ticker': ticker,
                    'name': name,
                    'change': 0.0,
                    'changePercent': 0.0,
                    'trend': 'flat',
                    'status': 'Neutral'
                })

        # Sort by performance
        sectors.sort(key=lambda x: x['changePercent'], reverse=True)

        logger.info(f"📊 Fetched {len(sectors)} sectors ({len(sectors) - len(failed_sectors)} live, {len(failed_sectors)} fallback)")
        if failed_sectors:
            logger.warning(f"⚠️ Failed sectors: {', '.join(failed_sectors)}")

        return sectors

    def _calculate_sentiment(self, indices: List[Dict], sectors: List[Dict]) -> Dict:
        """Calculate overall market sentiment score"""
        score = 50  # Start neutral

        # Analyze indices
        for index in indices:
            if index['ticker'] == '^GSPC':  # S&P 500 weight: 20 points
                score += (index['changePercent'] * 2)
            elif index['ticker'] == '^VIX':  # VIX inversely affects sentiment
                score -= (index['changePercent'] * 0.5)
            else:
                score += (index['changePercent'] * 1)

        # Analyze sectors (positive sectors boost sentiment)
        positive_sectors = sum(1 for s in sectors if s['changePercent'] > 0)
        sector_ratio = positive_sectors / len(sectors) if sectors else 0.5
        score += (sector_ratio - 0.5) * 20  # -10 to +10 based on sector breadth

        # Clamp score between 0-100
        score = max(0, min(100, score))

        # Determine label and color
        if score >= 70:
            label = 'BULLISH'
            color = 'green'
            description = 'Strong bullish trend. Most sectors positive.'
        elif score >= 55:
            label = 'SLIGHTLY BULLISH'
            color = 'lime'
            description = 'Moderate positive momentum across markets.'
        elif score >= 45:
            label = 'NEUTRAL'
            color = 'yellow'
            description = 'Mixed signals. Market awaiting direction.'
        elif score >= 30:
            label = 'SLIGHTLY BEARISH'
            color = 'orange'
            description = 'Caution advised. Weakness in key sectors.'
        else:
            label = 'BEARISH'
            color = 'red'
            description = 'Significant downward pressure. High risk.'

        # Risk level
        vix_index = next((i for i in indices if i['ticker'] == '^VIX'), None)
        vix_value = float(vix_index['price']) if vix_index else 15.0

        if vix_value > 30:
            risk = 'HIGH'
            risk_color = 'red'
        elif vix_value > 20:
            risk = 'MEDIUM'
            risk_color = 'yellow'
        else:
            risk = 'LOW'
            risk_color = 'green'

        # Trading style recommendation
        if score >= 65:
            style = 'Aggressive Growth'
            style_advice = 'Focus on tech and growth stocks with momentum'
        elif score >= 55:
            style = 'Moderate Growth'
            style_advice = 'Mix growth and value, favor trending sectors'
        elif score >= 45:
            style = 'Balanced'
            style_advice = 'Diversify equally, wait for clear direction'
        elif score >= 35:
            style = 'Conservative'
            style_advice = 'Favor defensive sectors, reduce exposure'
        else:
            style = 'Defensive'
            style_advice = 'Preserve capital, consider cash positions'

        return {
            'score': round(float(score), 1),
            'label': label,
            'color': color,
            'description': description,
            'risk': risk,
            'risk_color': risk_color,
            'vix': round(float(vix_value), 2),
            'trading_style': style,
            'advice': style_advice,
            'positive_sectors': int(positive_sectors),
            'total_sectors': int(len(sectors))
        }

    @staticmethod
    def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> int:
        first = datetime(year, month, 1)
        days_until = (weekday - first.weekday()) % 7
        return 1 + days_until + 7 * (n - 1)

    def _get_eastern_time(self) -> datetime:
        try:
            return datetime.now(ZoneInfo("America/New_York"))
        except Exception:
            now_utc = datetime.utcnow()
            year = now_utc.year
            dst_start_day = self._nth_weekday_of_month(year, 3, 6, 2)  # Second Sunday in March
            dst_end_day = self._nth_weekday_of_month(year, 11, 6, 1)   # First Sunday in November
            dst_start_utc = datetime(year, 3, dst_start_day, 7, 0)  # 2:00 AM EST -> 07:00 UTC
            dst_end_utc = datetime(year, 11, dst_end_day, 6, 0)     # 2:00 AM EDT -> 06:00 UTC
            is_dst = dst_start_utc <= now_utc < dst_end_utc
            offset_hours = 4 if is_dst else 5
            return now_utc - timedelta(hours=offset_hours)

    def _get_market_status(self) -> str:
        """Determine if market is open, closed, or pre/post market (US/Eastern)"""
        now = self._get_eastern_time()
        weekday = now.weekday()

        # Weekend
        if weekday >= 5:
            return 'closed'

        # Market hours (9:30 AM - 4:00 PM ET)
        minutes = now.hour * 60 + now.minute
        open_min = 9 * 60 + 30
        close_min = 16 * 60
        if open_min <= minutes < close_min:
            return 'open'
        if minutes < open_min:
            return 'pre-market'
        return 'after-hours'

    def _get_fallback_data(self) -> Dict:
        """Return fallback data if fetch fails"""
        return {
            'indices': [
                {'ticker': '^GSPC', 'name': 'S&P 500', 'price': 0, 'change': 0, 'changePercent': 0, 'isPositive': True}
            ],
            'sectors': [],
            'sentiment': {
                'score': 50,
                'label': 'NEUTRAL',
                'color': 'yellow',
                'description': 'Data temporarily unavailable',
                'risk': 'MEDIUM',
                'risk_color': 'yellow',
                'vix': 15,
                'trading_style': 'Balanced',
                'advice': 'Wait for data to update',
                'positive_sectors': 0,
                'total_sectors': 0
            },
            'timestamp': datetime.now().isoformat(),
            'market_status': 'unknown'
        }


# Singleton instance
_market_data_service = None

def get_market_data_service() -> MarketDataService:
    """Get singleton instance"""
    global _market_data_service
    if _market_data_service is None:
        _market_data_service = MarketDataService()
    return _market_data_service
