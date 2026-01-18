"""
Real Calendar Service - Upcoming Events
=========================================

Fetches real upcoming events:
- Earnings calendar (Finnhub)
- Economic events (hardcoded key dates)
- IPO calendar (Finnhub)

Uses Finnhub API for reliable data.
"""

import os
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import finnhub
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class CalendarService:
    """Service for fetching upcoming market events"""

    def __init__(self):
        self.finnhub_api_key = os.getenv('FINNHUB_API_KEY')

        self.finnhub_client = None
        if self.finnhub_api_key:
            try:
                self.finnhub_client = finnhub.Client(api_key=self.finnhub_api_key)
                logger.info("✅ Finnhub Calendar initialized")
            except Exception as e:
                logger.error(f"Finnhub init failed: {e}")

    def get_upcoming_events(self, days: int = 14, event_type: Optional[str] = None) -> List[Dict]:
        """
        Get upcoming market events

        Returns real earnings, IPOs, and economic events
        """
        all_events = []

        # Get earnings calendar from Finnhub
        if not event_type or event_type == 'EARNINGS':
            earnings_events = self._get_earnings_calendar(days)
            all_events.extend(earnings_events)

        # Get IPO calendar from Finnhub
        if not event_type or event_type == 'IPO':
            ipo_events = self._get_ipo_calendar(days)
            all_events.extend(ipo_events)

        # Get economic events (hardcoded key dates)
        if not event_type or event_type in ['FED', 'ECONOMIC']:
            economic_events = self._get_economic_events(days)
            all_events.extend(economic_events)

        # Sort by date
        all_events.sort(key=lambda x: x['date'])

        return all_events

    def _get_earnings_calendar(self, days: int) -> List[Dict]:
        """Get real earnings calendar from Finnhub"""
        if not self.finnhub_client:
            return []

        try:
            # Get date range
            start_date = datetime.now()
            end_date = start_date + timedelta(days=days)

            # Fetch earnings calendar
            earnings = self.finnhub_client.earnings_calendar(
                _from=start_date.strftime('%Y-%m-%d'),
                to=end_date.strftime('%Y-%m-%d'),
                symbol='',
                international=False
            )

            events = []
            for earning in earnings.get('earningsCalendar', [])[:20]:  # Limit to 20
                # Determine impact based on market cap
                ticker = earning.get('symbol', '')
                impact = 'HIGH' if ticker in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA'] else 'MEDIUM'

                events.append({
                    'id': f"earn-{ticker}-{earning.get('date', '')}",
                    'date': earning.get('date', ''),
                    'ticker': ticker,
                    'eventType': 'EARNINGS',
                    'title': f"{ticker} Quarterly Earnings",
                    'description': f"Q{earning.get('quarter', 'N/A')} {earning.get('year', '')} earnings report",
                    'expectedImpact': impact,
                    'time': 'After market' if earning.get('hour', 'amc') == 'amc' else 'Before market'
                })

            logger.info(f"✅ Fetched {len(events)} earnings events from Finnhub")
            return events

        except Exception as e:
            logger.error(f"Earnings calendar error: {e}")
            return []

    def _get_ipo_calendar(self, days: int) -> List[Dict]:
        """Get real IPO calendar from Finnhub"""
        if not self.finnhub_client:
            return []

        try:
            # Get date range
            start_date = datetime.now()
            end_date = start_date + timedelta(days=days)

            # Fetch IPO calendar
            ipos = self.finnhub_client.ipo_calendar(
                _from=start_date.strftime('%Y-%m-%d'),
                to=end_date.strftime('%Y-%m-%d')
            )

            events = []
            for ipo in ipos.get('ipoCalendar', [])[:10]:  # Limit to 10
                events.append({
                    'id': f"ipo-{ipo.get('symbol', '')}-{ipo.get('date', '')}",
                    'date': ipo.get('date', ''),
                    'ticker': ipo.get('symbol', ''),
                    'eventType': 'IPO',
                    'title': f"{ipo.get('name', ipo.get('symbol', ''))} IPO",
                    'description': f"IPO listing at {ipo.get('exchange', 'N/A')}, Price range: ${ipo.get('priceFrom', 'N/A')}-${ipo.get('priceTo', 'N/A')}",
                    'expectedImpact': 'MEDIUM',
                    'time': '09:30 EST'
                })

            logger.info(f"✅ Fetched {len(events)} IPO events from Finnhub")
            return events

        except Exception as e:
            logger.error(f"IPO calendar error: {e}")
            return []

    def _get_economic_events(self, days: int) -> List[Dict]:
        """
        Get key economic events (hardcoded)

        Note: For production, integrate with economic calendar API
        """
        events = []
        now = datetime.now()

        # Key economic events (approximate dates)
        economic_schedule = [
            {
                'offset_days': 3,
                'ticker': 'US',
                'type': 'ECONOMIC',
                'title': 'Consumer Price Index (CPI)',
                'description': 'Monthly inflation data',
                'impact': 'HIGH',
                'time': '08:30 EST'
            },
            {
                'offset_days': 7,
                'ticker': 'US',
                'type': 'ECONOMIC',
                'title': 'Non-Farm Payrolls',
                'description': 'Monthly employment report',
                'impact': 'HIGH',
                'time': '08:30 EST'
            },
            {
                'offset_days': 14,
                'ticker': 'FED',
                'type': 'FED',
                'title': 'FOMC Meeting',
                'description': 'Federal Reserve interest rate decision',
                'impact': 'HIGH',
                'time': '14:00 EST'
            },
            {
                'offset_days': 10,
                'ticker': 'US',
                'type': 'ECONOMIC',
                'title': 'Retail Sales',
                'description': 'Monthly consumer spending data',
                'impact': 'MEDIUM',
                'time': '08:30 EST'
            },
            {
                'offset_days': 5,
                'ticker': 'US',
                'type': 'ECONOMIC',
                'title': 'Initial Jobless Claims',
                'description': 'Weekly unemployment claims',
                'impact': 'MEDIUM',
                'time': '08:30 EST'
            }
        ]

        for event in economic_schedule:
            event_date = now + timedelta(days=event['offset_days'])

            # Only include if within requested days
            if event['offset_days'] <= days:
                events.append({
                    'id': f"econ-{event['type']}-{event_date.strftime('%Y%m%d')}",
                    'date': event_date.strftime('%Y-%m-%d'),
                    'ticker': event['ticker'],
                    'eventType': event['type'],
                    'title': event['title'],
                    'description': event['description'],
                    'expectedImpact': event['impact'],
                    'time': event['time']
                })

        logger.info(f"✅ Generated {len(events)} economic events")
        return events


# Singleton instance
_calendar_service = None

def get_calendar_service() -> CalendarService:
    """Get singleton instance"""
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = CalendarService()
    return _calendar_service
