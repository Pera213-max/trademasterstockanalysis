"""
TradeMaster Pro - Smart Alerts System
======================================

AI-powered alerts for:
- Abnormal price movements
- Volume spikes
- News-driven events
- Analyst changes
- Technical breakouts
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from .yfinance_service import get_yfinance_service
from .finnhub_service import get_finnhub_service
from .stock_news_analyzer import get_stock_news_analyzer

logger = logging.getLogger(__name__)


class SmartAlertsSystem:
    """Generate intelligent stock alerts"""

    # Thresholds for alerts
    PRICE_SPIKE_THRESHOLD = 5.0  # 5% move
    VOLUME_SPIKE_THRESHOLD = 2.0  # 2x average volume
    HIGH_IMPACT_NEWS_THRESHOLD = 'HIGH'

    def __init__(self):
        self.yfinance = get_yfinance_service()
        self.finnhub = get_finnhub_service()
        self.news_analyzer = get_stock_news_analyzer()
        logger.info("SmartAlertsSystem initialized")

    def check_alerts(
        self,
        tickers: List[str],
        limit: int = 20,
        include_news: bool = True,
        max_workers: Optional[int] = None
    ) -> List[Dict]:
        """
        Check for alerts on given tickers

        Args:
            tickers: List of stock symbols to monitor

        Returns:
            List of alerts
        """
        try:
            alerts = []

            if not tickers:
                return []

            if max_workers is None:
                if len(tickers) <= 15:
                    max_workers = 1
                else:
                    max_workers = min(8, max(2, len(tickers) // 75))

            if max_workers > 1:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(self._check_ticker, ticker, include_news): ticker
                        for ticker in tickers
                    }
                    for future in as_completed(futures):
                        try:
                            ticker_alerts = future.result()
                        except Exception:
                            continue
                        if ticker_alerts:
                            alerts.extend(ticker_alerts)
            else:
                for ticker in tickers:
                    ticker_alerts = self._check_ticker(ticker, include_news)
                    alerts.extend(ticker_alerts)

            # Sort by severity and timestamp
            alerts.sort(key=lambda x: (
                0 if x['severity'] == 'HIGH' else 1 if x['severity'] == 'MEDIUM' else 2,
                -x['timestamp']
            ))

            return alerts[:limit]

        except Exception as e:
            logger.error(f"Error checking alerts: {str(e)}")
            return []

    def _check_ticker(self, ticker: str, include_news: bool = True) -> List[Dict]:
        """Check all alert types for a ticker"""
        alerts = []

        try:
            # Get quote
            quote = self.yfinance.get_quote(ticker)
            if not quote:
                return []

            # Check price movement alert
            price_alert = self._check_price_movement(ticker, quote)
            if price_alert:
                alerts.append(price_alert)

            # Check volume spike
            volume_alert = self._check_volume_spike(ticker, quote)
            if volume_alert:
                alerts.append(volume_alert)

            # Check major news
            if include_news:
                news_alerts = self._check_major_news(ticker)
                alerts.extend(news_alerts)

            # Check 52-week high/low
            extreme_alert = self._check_52_week_extremes(ticker, quote)
            if extreme_alert:
                alerts.append(extreme_alert)

        except Exception as e:
            logger.error(f"Error checking ticker {ticker}: {str(e)}")

        return alerts

    def _check_price_movement(self, ticker: str, quote: Dict) -> Optional[Dict]:
        """Check for abnormal price movements"""
        current = quote.get('c', 0)
        prev_close = quote.get('pc', 0)

        if not current or not prev_close:
            return None

        change_pct = ((current - prev_close) / prev_close) * 100

        if abs(change_pct) >= self.PRICE_SPIKE_THRESHOLD:
            severity = 'HIGH' if abs(change_pct) >= 10 else 'MEDIUM'
            direction = 'up' if change_pct > 0 else 'down'

            return {
                'ticker': ticker,
                'type': 'PRICE_SPIKE',
                'severity': severity,
                'title': f'{ticker} {direction} {abs(change_pct):.1f}%',
                'message': f'Unusual price movement detected - {ticker} is {direction} {abs(change_pct):.1f}% today',
                'action': f'Check news and fundamentals for {ticker}',
                'data': {
                    'current_price': current,
                    'previous_close': prev_close,
                    'change_percent': round(change_pct, 2)
                },
                'timestamp': int(datetime.now().timestamp())
            }

        return None

    def _check_volume_spike(self, ticker: str, quote: Dict) -> Optional[Dict]:
        """Check for volume spikes"""
        try:
            fundamentals = self.yfinance.get_fundamentals(ticker)
            if not fundamentals:
                return None

            current_volume = quote.get('v', 0)
            avg_volume = fundamentals.get('averageVolume', 0)

            if not current_volume or not avg_volume:
                return None

            volume_ratio = current_volume / avg_volume

            if volume_ratio >= self.VOLUME_SPIKE_THRESHOLD:
                severity = 'HIGH' if volume_ratio >= 4 else 'MEDIUM'

                return {
                    'ticker': ticker,
                    'type': 'VOLUME_SPIKE',
                    'severity': severity,
                    'title': f'{ticker} volume {volume_ratio:.1f}x normal',
                    'message': f'Unusual trading activity - volume is {volume_ratio:.1f}x the average',
                    'action': 'Investigate reason for increased interest',
                    'data': {
                        'current_volume': current_volume,
                        'average_volume': avg_volume,
                        'ratio': round(volume_ratio, 2)
                    },
                    'timestamp': int(datetime.now().timestamp())
                }

        except Exception as e:
            logger.error(f"Error checking volume for {ticker}: {str(e)}")

        return None

    def _check_major_news(self, ticker: str) -> List[Dict]:
        """Check for major news events"""
        alerts = []

        try:
            major_news = self.news_analyzer.get_major_news(ticker, days=1)

            for news in major_news[:3]:  # Top 3 events
                if news['impact'] in ['HIGH', 'VERY HIGH']:
                    severity = 'HIGH' if news['impact'] == 'VERY HIGH' else 'MEDIUM'

                    alerts.append({
                        'ticker': ticker,
                        'type': 'NEWS_IMPACT',
                        'severity': severity,
                        'title': f"{ticker} {news['category'].upper()} - {news['sentiment']}",
                        'message': news['reason'],
                        'action': f"Read: {news['headline'][:100]}",
                        'data': {
                            'category': news['category'],
                            'sentiment': news['sentiment'],
                            'headline': news['headline'],
                            'url': news['url']
                        },
                        'timestamp': news['timestamp']
                    })

        except Exception as e:
            logger.error(f"Error checking news for {ticker}: {str(e)}")

        return alerts

    def _check_52_week_extremes(self, ticker: str, quote: Dict) -> Optional[Dict]:
        """Check if near 52-week high or low"""
        try:
            fundamentals = self.yfinance.get_fundamentals(ticker)
            if not fundamentals:
                return None

            current = quote.get('c', 0)
            high_52 = fundamentals.get('fiftyTwoWeekHigh', 0)
            low_52 = fundamentals.get('fiftyTwoWeekLow', 0)

            if not all([current, high_52, low_52]):
                return None

            # Within 2% of 52-week high
            if current >= high_52 * 0.98:
                return {
                    'ticker': ticker,
                    'type': 'TECHNICAL_BREAKOUT',
                    'severity': 'MEDIUM',
                    'title': f'{ticker} near 52-week high',
                    'message': f'{ticker} is trading near its 52-week high of ${high_52:.2f}',
                    'action': 'Potential breakout - watch for momentum continuation',
                    'data': {
                        'current_price': current,
                        'high_52': high_52,
                        'distance_pct': round(((high_52 - current) / high_52) * 100, 2)
                    },
                    'timestamp': int(datetime.now().timestamp())
                }

            # Within 5% of 52-week low
            if current <= low_52 * 1.05:
                return {
                    'ticker': ticker,
                    'type': 'TECHNICAL_OVERSOLD',
                    'severity': 'MEDIUM',
                    'title': f'{ticker} near 52-week low',
                    'message': f'{ticker} is trading near its 52-week low of ${low_52:.2f}',
                    'action': 'Potential value opportunity or further downside - check fundamentals',
                    'data': {
                        'current_price': current,
                        'low_52': low_52,
                        'distance_pct': round(((current - low_52) / low_52) * 100, 2)
                    },
                    'timestamp': int(datetime.now().timestamp())
                }

        except Exception as e:
            logger.error(f"Error checking 52-week extremes for {ticker}: {str(e)}")

        return None

    def get_watchlist_alerts(self, watchlist: List[str]) -> Dict:
        """Get summary of alerts for a watchlist"""
        try:
            all_alerts = self.check_alerts(watchlist)

            # Categorize by type
            alerts_by_type = {}
            for alert in all_alerts:
                alert_type = alert['type']
                if alert_type not in alerts_by_type:
                    alerts_by_type[alert_type] = []
                alerts_by_type[alert_type].append(alert)

            # Count by severity
            high_severity = len([a for a in all_alerts if a['severity'] == 'HIGH'])
            medium_severity = len([a for a in all_alerts if a['severity'] == 'MEDIUM'])

            return {
                'total_alerts': len(all_alerts),
                'high_severity': high_severity,
                'medium_severity': medium_severity,
                'alerts_by_type': {k: len(v) for k, v in alerts_by_type.items()},
                'recent_alerts': all_alerts[:10],  # Top 10 most recent
                'summary': f'{high_severity} high priority, {medium_severity} medium priority alerts'
            }

        except Exception as e:
            logger.error(f"Error getting watchlist alerts: {str(e)}")
            return {
                'total_alerts': 0,
                'high_severity': 0,
                'medium_severity': 0,
                'alerts_by_type': {},
                'recent_alerts': [],
                'summary': 'No alerts'
            }


# Global singleton
_smart_alerts = None


def get_smart_alerts_system() -> SmartAlertsSystem:
    """Get or create singleton instance"""
    global _smart_alerts
    if _smart_alerts is None:
        _smart_alerts = SmartAlertsSystem()
    return _smart_alerts
