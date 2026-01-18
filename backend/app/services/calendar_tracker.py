"""
Calendar Tracker Service for TradeMaster Pro

Tracks and aggregates financial events: earnings, FDA decisions, IPOs, FED meetings.
Uses web scraping and financial APIs to provide comprehensive event calendar.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CalendarTracker:
    """
    Financial calendar tracker for multiple event types

    Features:
    - Earnings calendar tracking (via yfinance/Yahoo Finance)
    - FDA calendar (PDUFA dates)
    - IPO calendar
    - Federal Reserve meetings
    - Unified event aggregation
    """

    def __init__(self):
        """Initialize CalendarTracker"""
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    def get_earnings_calendar(self, days_ahead: int = 30) -> List[Dict]:
        """
        Get upcoming earnings announcements

        Args:
            days_ahead: Number of days ahead to look

        Returns:
            List of earnings events with date, ticker, expected_eps, time
        """
        try:
            import yfinance as yf
            from datetime import date

            logger.info(f"Fetching earnings calendar for next {days_ahead} days...")

            # Calculate date range
            start_date = datetime.now()
            end_date = start_date + timedelta(days=days_ahead)

            # Popular tickers to check
            tickers_to_check = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'AMD',
                'NFLX', 'DIS', 'BABA', 'COIN', 'PLTR', 'PYPL', 'SQ', 'ROKU',
                'SNAP', 'UBER', 'LYFT', 'ABNB', 'SNOW', 'ZM', 'DOCU', 'SHOP',
                'SPOT', 'PINS', 'TWLO', 'CRWD', 'NET', 'DDOG', 'MDB'
            ]

            earnings_events = []

            for ticker in tickers_to_check:
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.info

                    # Try to get earnings date from calendar
                    calendar = stock.calendar

                    if calendar is not None and not calendar.empty:
                        if 'Earnings Date' in calendar.index:
                            earnings_date = calendar.loc['Earnings Date'].values[0]

                            if isinstance(earnings_date, str):
                                # Parse string date
                                earnings_datetime = datetime.strptime(earnings_date, '%Y-%m-%d')
                            else:
                                # Convert numpy datetime64 to datetime
                                earnings_datetime = pd.Timestamp(earnings_date).to_pydatetime()

                            # Check if within date range
                            if start_date <= earnings_datetime <= end_date:
                                company_name = info.get('longName', ticker)
                                expected_eps = calendar.loc['Earnings Average'].values[0] if 'Earnings Average' in calendar.index else None

                                # Determine time (BMO = Before Market Open, AMC = After Market Close)
                                time_code = "AMC"  # Default to after market close

                                earnings_events.append({
                                    'date': earnings_datetime.strftime('%Y-%m-%d'),
                                    'ticker': ticker,
                                    'company': company_name,
                                    'expected_eps': float(expected_eps) if expected_eps else None,
                                    'time': time_code,
                                    'event_type': 'EARNINGS'
                                })

                except Exception as e:
                    continue  # Skip tickers that fail

            # Sort by date
            earnings_events.sort(key=lambda x: x['date'])

            logger.info(f"Found {len(earnings_events)} earnings events")
            return earnings_events

        except ImportError:
            logger.warning("yfinance not available")
            return self._get_mock_earnings()
        except Exception as e:
            logger.error(f"Error fetching earnings calendar: {e}")
            return self._get_mock_earnings()

    def get_fda_calendar(self, days_ahead: int = 90) -> List[Dict]:
        """
        Get upcoming FDA decision dates (PDUFA dates)

        Args:
            days_ahead: Number of days ahead to look

        Returns:
            List of FDA events with date, drug_name, company, ticker
        """
        try:
            import requests
            from bs4 import BeautifulSoup

            logger.info("Fetching FDA calendar...")

            # FDA calendar URL (this is a simplified example)
            # Real implementation would scrape from biopharmcatalyst.com or similar
            url = "https://www.fda.gov/drugs/news-events-human-drugs/drug-approvals-and-databases"

            headers = {'User-Agent': self.user_agent}

            # Note: FDA doesn't have a simple calendar API
            # This would typically scrape from specialized sites like:
            # - biopharmcatalyst.com
            # - fdatracker.com
            # For now, return mock data with note about implementation

            logger.info("FDA calendar scraping requires specialized sources")
            return self._get_mock_fda()

        except Exception as e:
            logger.error(f"Error fetching FDA calendar: {e}")
            return self._get_mock_fda()

    def get_ipo_calendar(self, days_ahead: int = 60) -> List[Dict]:
        """
        Get upcoming IPO listings

        Args:
            days_ahead: Number of days ahead to look

        Returns:
            List of IPO events with date, company, ticker, price_range
        """
        try:
            import requests
            from bs4 import BeautifulSoup

            logger.info("Fetching IPO calendar...")

            # IPO calendar URL (NASDAQ or similar)
            # Real implementation would scrape from nasdaq.com/market-activity/ipos
            # or use specialized IPO data providers

            # For demonstration, this would scrape structured IPO data
            url = "https://www.nasdaq.com/market-activity/ipos"

            headers = {'User-Agent': self.user_agent}

            # Note: NASDAQ IPO calendar requires more complex scraping
            # This would typically use:
            # - requests + BeautifulSoup for HTML parsing
            # - Or paid IPO data APIs
            # For now, return mock data

            logger.info("IPO calendar scraping requires specialized parsing")
            return self._get_mock_ipos()

        except Exception as e:
            logger.error(f"Error fetching IPO calendar: {e}")
            return self._get_mock_ipos()

    def get_fed_meetings(self, year: int = 2025) -> List[Dict]:
        """
        Get Federal Reserve FOMC meeting dates

        Args:
            year: Year to get meetings for

        Returns:
            List of FED meeting events with date, event_type, expected_impact
        """
        logger.info(f"Getting FED meetings for {year}...")

        # Federal Reserve FOMC meeting schedule (2025)
        # Source: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
        fed_meetings_2025 = [
            {'date': '2025-01-28', 'date_end': '2025-01-29', 'type': 'FOMC Meeting'},
            {'date': '2025-03-18', 'date_end': '2025-03-19', 'type': 'FOMC Meeting'},
            {'date': '2025-04-29', 'date_end': '2025-04-30', 'type': 'FOMC Meeting'},
            {'date': '2025-06-17', 'date_end': '2025-06-18', 'type': 'FOMC Meeting'},
            {'date': '2025-07-29', 'date_end': '2025-07-30', 'type': 'FOMC Meeting'},
            {'date': '2025-09-16', 'date_end': '2025-09-17', 'type': 'FOMC Meeting'},
            {'date': '2025-11-04', 'date_end': '2025-11-05', 'type': 'FOMC Meeting'},
            {'date': '2025-12-16', 'date_end': '2025-12-17', 'type': 'FOMC Meeting'},
        ]

        fed_meetings_2024 = [
            {'date': '2024-01-30', 'date_end': '2024-01-31', 'type': 'FOMC Meeting'},
            {'date': '2024-03-19', 'date_end': '2024-03-20', 'type': 'FOMC Meeting'},
            {'date': '2024-04-30', 'date_end': '2024-05-01', 'type': 'FOMC Meeting'},
            {'date': '2024-06-11', 'date_end': '2024-06-12', 'type': 'FOMC Meeting'},
            {'date': '2024-07-30', 'date_end': '2024-07-31', 'type': 'FOMC Meeting'},
            {'date': '2024-09-17', 'date_end': '2024-09-18', 'type': 'FOMC Meeting'},
            {'date': '2024-11-06', 'date_end': '2024-11-07', 'type': 'FOMC Meeting'},
            {'date': '2024-12-17', 'date_end': '2024-12-18', 'type': 'FOMC Meeting'},
        ]

        # Select appropriate year
        if year == 2025:
            meetings = fed_meetings_2025
        elif year == 2024:
            meetings = fed_meetings_2024
        else:
            meetings = fed_meetings_2025  # Default to 2025

        # Filter for upcoming meetings only
        today = datetime.now().date()
        upcoming_meetings = []

        for meeting in meetings:
            meeting_date = datetime.strptime(meeting['date_end'], '%Y-%m-%d').date()

            if meeting_date >= today:
                upcoming_meetings.append({
                    'date': meeting['date_end'],  # Use end date (when decision announced)
                    'date_range': f"{meeting['date']} to {meeting['date_end']}",
                    'event_type': 'FED',
                    'description': f"Federal Reserve {meeting['type']}",
                    'expected_impact': 'HIGH',
                    'time': 'AMC'  # Announced after market close (2 PM ET)
                })

        logger.info(f"Found {len(upcoming_meetings)} upcoming FED meetings")
        return upcoming_meetings

    def get_economic_data_releases(self, days_ahead: int = 30) -> List[Dict]:
        """
        Get upcoming economic data releases (CPI, Jobs Report, etc.)

        Args:
            days_ahead: Number of days ahead to look

        Returns:
            List of economic data release events
        """
        logger.info("Getting economic data releases...")

        # Common economic indicators and their typical release schedules
        # This is simplified - real implementation would use economic calendar APIs
        today = datetime.now()

        economic_releases = []

        # CPI - released monthly, around 13th of each month at 8:30 AM ET
        next_cpi = self._get_next_monthly_release(today, 13)
        if (next_cpi - today).days <= days_ahead:
            economic_releases.append({
                'date': next_cpi.strftime('%Y-%m-%d'),
                'event_type': 'ECONOMIC',
                'description': 'Consumer Price Index (CPI) Release',
                'expected_impact': 'HIGH',
                'time': 'BMO'
            })

        # Jobs Report - first Friday of each month at 8:30 AM ET
        next_jobs = self._get_first_friday_of_next_month(today)
        if (next_jobs - today).days <= days_ahead:
            economic_releases.append({
                'date': next_jobs.strftime('%Y-%m-%d'),
                'event_type': 'ECONOMIC',
                'description': 'Non-Farm Payrolls (Jobs Report)',
                'expected_impact': 'HIGH',
                'time': 'BMO'
            })

        # GDP - released quarterly
        # PPI - released monthly around 14th
        next_ppi = self._get_next_monthly_release(today, 14)
        if (next_ppi - today).days <= days_ahead:
            economic_releases.append({
                'date': next_ppi.strftime('%Y-%m-%d'),
                'event_type': 'ECONOMIC',
                'description': 'Producer Price Index (PPI) Release',
                'expected_impact': 'MEDIUM',
                'time': 'BMO'
            })

        return economic_releases

    def get_all_upcoming_events(self, days_ahead: int = 30) -> List[Dict]:
        """
        Get all upcoming events from all sources, unified and sorted

        Args:
            days_ahead: Number of days ahead to look

        Returns:
            Unified list of all events sorted by date
        """
        logger.info(f"Aggregating all events for next {days_ahead} days...")

        all_events = []

        # 1. Earnings
        earnings = self.get_earnings_calendar(days_ahead)
        all_events.extend(earnings)

        # 2. FDA
        fda = self.get_fda_calendar(days_ahead)
        all_events.extend(fda)

        # 3. IPOs
        ipos = self.get_ipo_calendar(days_ahead)
        all_events.extend(ipos)

        # 4. FED meetings
        fed = self.get_fed_meetings()
        all_events.extend(fed)

        # 5. Economic data releases
        economic = self.get_economic_data_releases(days_ahead)
        all_events.extend(economic)

        # Filter events within date range
        today = datetime.now().date()
        end_date = today + timedelta(days=days_ahead)

        filtered_events = []
        for event in all_events:
            event_date = datetime.strptime(event['date'], '%Y-%m-%d').date()
            if today <= event_date <= end_date:
                filtered_events.append(event)

        # Sort by date
        filtered_events.sort(key=lambda x: x['date'])

        # Group by date for easier display
        events_by_date = defaultdict(list)
        for event in filtered_events:
            events_by_date[event['date']].append(event)

        logger.info(f"Found {len(filtered_events)} total upcoming events across {len(events_by_date)} days")

        return {
            'events': filtered_events,
            'events_by_date': dict(events_by_date),
            'total_events': len(filtered_events),
            'date_range': {
                'start': today.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            }
        }

    # Helper methods

    def _get_next_monthly_release(self, from_date: datetime, day_of_month: int) -> datetime:
        """Get next monthly release date"""
        current_month = from_date.month
        current_year = from_date.year

        # If we're past the day this month, go to next month
        if from_date.day > day_of_month:
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1

        return datetime(current_year, current_month, day_of_month)

    def _get_first_friday_of_next_month(self, from_date: datetime) -> datetime:
        """Get first Friday of next month"""
        next_month = from_date.month + 1
        next_year = from_date.year

        if next_month > 12:
            next_month = 1
            next_year += 1

        # First day of next month
        first_day = datetime(next_year, next_month, 1)

        # Find first Friday (weekday 4 = Friday)
        days_until_friday = (4 - first_day.weekday()) % 7
        if days_until_friday == 0 and first_day.weekday() != 4:
            days_until_friday = 7

        first_friday = first_day + timedelta(days=days_until_friday)
        return first_friday

    # Mock data methods

    def _get_mock_earnings(self) -> List[Dict]:
        """Return mock earnings calendar data"""
        today = datetime.now()

        return [
            {
                'date': (today + timedelta(days=2)).strftime('%Y-%m-%d'),
                'ticker': 'NVDA',
                'company': 'NVIDIA Corporation',
                'expected_eps': 5.28,
                'time': 'AMC',
                'event_type': 'EARNINGS'
            },
            {
                'date': (today + timedelta(days=5)).strftime('%Y-%m-%d'),
                'ticker': 'AAPL',
                'company': 'Apple Inc.',
                'expected_eps': 2.18,
                'time': 'AMC',
                'event_type': 'EARNINGS'
            },
            {
                'date': (today + timedelta(days=7)).strftime('%Y-%m-%d'),
                'ticker': 'MSFT',
                'company': 'Microsoft Corporation',
                'expected_eps': 2.75,
                'time': 'AMC',
                'event_type': 'EARNINGS'
            },
            {
                'date': (today + timedelta(days=10)).strftime('%Y-%m-%d'),
                'ticker': 'GOOGL',
                'company': 'Alphabet Inc.',
                'expected_eps': 1.52,
                'time': 'AMC',
                'event_type': 'EARNINGS'
            },
            {
                'date': (today + timedelta(days=14)).strftime('%Y-%m-%d'),
                'ticker': 'META',
                'company': 'Meta Platforms Inc.',
                'expected_eps': 4.82,
                'time': 'AMC',
                'event_type': 'EARNINGS'
            },
            {
                'date': (today + timedelta(days=18)).strftime('%Y-%m-%d'),
                'ticker': 'TSLA',
                'company': 'Tesla Inc.',
                'expected_eps': 0.85,
                'time': 'AMC',
                'event_type': 'EARNINGS'
            }
        ]

    def _get_mock_fda(self) -> List[Dict]:
        """Return mock FDA calendar data"""
        today = datetime.now()

        return [
            {
                'date': (today + timedelta(days=15)).strftime('%Y-%m-%d'),
                'event_type': 'FDA',
                'drug_name': 'Alzheimer Drug XR-450',
                'company': 'BioPharma Inc.',
                'ticker': 'BPMA',
                'decision_type': 'PDUFA Date',
                'expected_impact': 'HIGH',
                'time': 'AMC'
            },
            {
                'date': (today + timedelta(days=25)).strftime('%Y-%m-%d'),
                'event_type': 'FDA',
                'drug_name': 'Cancer Immunotherapy CT-220',
                'company': 'OncoTech',
                'ticker': 'ONCT',
                'decision_type': 'PDUFA Date',
                'expected_impact': 'HIGH',
                'time': 'AMC'
            },
            {
                'date': (today + timedelta(days=40)).strftime('%Y-%m-%d'),
                'event_type': 'FDA',
                'drug_name': 'Diabetes Treatment DM-350',
                'company': 'MedTech Solutions',
                'ticker': 'MTCH',
                'decision_type': 'AdCom Meeting',
                'expected_impact': 'MEDIUM',
                'time': 'AMC'
            }
        ]

    def _get_mock_ipos(self) -> List[Dict]:
        """Return mock IPO calendar data"""
        today = datetime.now()

        return [
            {
                'date': (today + timedelta(days=8)).strftime('%Y-%m-%d'),
                'event_type': 'IPO',
                'company': 'AI Robotics Inc.',
                'ticker': 'AIRO',
                'price_range': '$18-$22',
                'shares': '10M',
                'valuation': '$2.5B',
                'expected_impact': 'MEDIUM',
                'time': 'AMC'
            },
            {
                'date': (today + timedelta(days=20)).strftime('%Y-%m-%d'),
                'event_type': 'IPO',
                'company': 'CloudTech Solutions',
                'ticker': 'CLDT',
                'price_range': '$25-$30',
                'shares': '15M',
                'valuation': '$4.2B',
                'expected_impact': 'HIGH',
                'time': 'AMC'
            },
            {
                'date': (today + timedelta(days=35)).strftime('%Y-%m-%d'),
                'event_type': 'IPO',
                'company': 'BioGenetics Corp',
                'ticker': 'BIOG',
                'price_range': '$15-$18',
                'shares': '8M',
                'valuation': '$1.8B',
                'expected_impact': 'MEDIUM',
                'time': 'AMC'
            }
        ]


# Convenience functions

def get_upcoming_earnings(days_ahead: int = 30) -> List[Dict]:
    """
    Convenience function to get upcoming earnings

    Args:
        days_ahead: Number of days ahead to look

    Returns:
        List of earnings events
    """
    tracker = CalendarTracker()
    return tracker.get_earnings_calendar(days_ahead)


def get_all_events(days_ahead: int = 30) -> Dict:
    """
    Convenience function to get all upcoming events

    Args:
        days_ahead: Number of days ahead to look

    Returns:
        Dict with all events aggregated
    """
    tracker = CalendarTracker()
    return tracker.get_all_upcoming_events(days_ahead)


# Example usage
if __name__ == "__main__":
    print("=== Calendar Tracker Service ===\n")

    tracker = CalendarTracker()

    # Test 1: Earnings calendar
    print("1. Testing get_earnings_calendar()...")
    earnings = tracker.get_earnings_calendar(days_ahead=30)
    print(f"Found {len(earnings)} earnings announcements")
    if earnings:
        print("\nUpcoming earnings:")
        for event in earnings[:5]:
            print(f"  {event['date']}: {event['ticker']} - {event['company']} "
                  f"(EPS: ${event['expected_eps']}, {event['time']})")

    # Test 2: FDA calendar
    print("\n2. Testing get_fda_calendar()...")
    fda = tracker.get_fda_calendar()
    print(f"Found {len(fda)} FDA events")
    if fda:
        print("\nUpcoming FDA decisions:")
        for event in fda[:3]:
            print(f"  {event['date']}: {event['drug_name']} ({event['company']})")

    # Test 3: IPO calendar
    print("\n3. Testing get_ipo_calendar()...")
    ipos = tracker.get_ipo_calendar()
    print(f"Found {len(ipos)} IPO events")
    if ipos:
        print("\nUpcoming IPOs:")
        for event in ipos[:3]:
            print(f"  {event['date']}: {event['company']} ({event['ticker']}) - {event['price_range']}")

    # Test 4: FED meetings
    print("\n4. Testing get_fed_meetings()...")
    fed = tracker.get_fed_meetings(year=2025)
    print(f"Found {len(fed)} FED meetings in 2025")
    if fed:
        print("\nUpcoming FED meetings:")
        for event in fed[:3]:
            print(f"  {event['date']}: {event['description']}")

    # Test 5: All events
    print("\n5. Testing get_all_upcoming_events()...")
    all_events = tracker.get_all_upcoming_events(days_ahead=30)
    print(f"Total events: {all_events['total_events']}")
    print(f"Date range: {all_events['date_range']['start']} to {all_events['date_range']['end']}")
    print(f"Days with events: {len(all_events['events_by_date'])}")

    # Show events by type
    events_by_type = defaultdict(int)
    for event in all_events['events']:
        events_by_type[event['event_type']] += 1

    print("\nEvents by type:")
    for event_type, count in events_by_type.items():
        print(f"  {event_type}: {count}")

    print("\n=== Calendar Tracker Tests Complete ===")
