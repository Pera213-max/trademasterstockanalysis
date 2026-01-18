"""
Insider Trading Service - Track insider buying/selling activity

Data Source: SEC Edgar (Free, no API key needed)
Alternative: Finnhub Insider Trading API (requires premium)

This service scrapes SEC Form 4 filings to track insider transactions.
"""

import requests
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
import logging

from .finnhub_service import get_finnhub_service

logger = logging.getLogger(__name__)


class InsiderTradingService:
    """Service for fetching and analyzing insider trading data"""

    def __init__(self):
        self.sec_base_url = "https://www.sec.gov/cgi-bin/browse-edgar"
        # SEC requires User-Agent header
        self.headers = {
            "User-Agent": "TradeMaster Pro trademasterpro@example.com",
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov"
        }
        self.finnhub = get_finnhub_service()
        self.cache_ttl_seconds = 60 * 60 * 12
        self._cache: Dict[str, Tuple[datetime, Dict]] = {}
        self._cik_map: Dict[str, str] = {}
        self._cik_map_fetched_at: Optional[datetime] = None
        self._cik_map_ttl = timedelta(days=7)

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

    def get_insider_activity(self, ticker: str, days: int = 90) -> Dict:
        """
        Get insider trading activity for a ticker

        Args:
            ticker: Stock ticker symbol
            days: Number of days to look back (default 90)

        Returns:
            Dict with insider activity summary
        """
        try:
            logger.info(f"Fetching insider activity for {ticker} (last {days} days)")

            cached = self._get_cached(ticker)
            if cached:
                return cached

            insider_data = self._get_finnhub_insider_data(ticker, days)
            if not insider_data:
                insider_data = self._get_sec_insider_data(ticker, days)
            if not insider_data:
                insider_data = self._get_default_insider_data(ticker)

            result = {
                "ticker": ticker,
                "period_days": days,
                "total_transactions": insider_data["total_transactions"],
                "insider_buys": insider_data["buys"],
                "insider_sells": insider_data["sells"],
                "net_activity": insider_data["buys"] - insider_data["sells"],
                "total_buy_value": insider_data["total_buy_value"],
                "total_sell_value": insider_data["total_sell_value"],
                "net_value": insider_data["total_buy_value"] - insider_data["total_sell_value"],
                "insider_sentiment": self._calculate_insider_sentiment(insider_data),
                "signal": self._generate_insider_signal(insider_data),
                "transactions": insider_data["transactions"]
            }
            self._set_cached(ticker, result)
            return result

        except Exception as e:
            logger.error(f"Error fetching insider activity for {ticker}: {str(e)}")
            return self._get_default_insider_data(ticker)

    def _get_finnhub_insider_data(self, ticker: str, days: int) -> Optional[Dict]:
        if not self.finnhub:
            return None

        transactions = self.finnhub.get_insider_transactions(ticker, days=days)
        if not transactions:
            return None

        buys = 0
        sells = 0
        total_buy_value = 0.0
        total_sell_value = 0.0
        parsed_transactions = []

        for item in transactions:
            code = (
                str(item.get("transactionCode") or item.get("transactionType") or "")
                .strip()
                .upper()
            )
            shares = float(item.get("share") or item.get("shares") or 0)
            price = float(item.get("transactionPrice") or item.get("price") or 0)
            value = shares * price if shares and price else 0.0

            if code in {"P", "A", "BUY"}:
                buys += 1
                total_buy_value += value
                direction = "BUY"
            elif code in {"S", "D", "SELL"}:
                sells += 1
                total_sell_value += value
                direction = "SELL"
            else:
                direction = "OTHER"

            parsed_transactions.append({
                "insider_name": item.get("name", ""),
                "title": item.get("position", ""),
                "transaction_type": direction,
                "shares": shares,
                "price": price,
                "value": value,
                "date": item.get("transactionDate", "")
            })

        return {
            "total_transactions": buys + sells,
            "buys": buys,
            "sells": sells,
            "total_buy_value": total_buy_value,
            "total_sell_value": total_sell_value,
            "transactions": parsed_transactions
        }

    def _load_cik_map(self) -> None:
        if self._cik_map_fetched_at and (datetime.now() - self._cik_map_fetched_at) < self._cik_map_ttl:
            return

        url = "https://www.sec.gov/files/company_tickers.json"
        try:
            response = requests.get(url, headers=self.headers, timeout=20)
            response.raise_for_status()
            payload = response.json()
        except Exception as e:
            logger.warning(f"Failed to fetch SEC ticker map: {str(e)}")
            return

        cik_map = {}
        for item in payload.values():
            ticker_value = str(item.get("ticker", "")).upper()
            cik_str = str(item.get("cik_str", ""))
            if ticker_value and cik_str:
                cik_map[ticker_value] = cik_str.zfill(10)

        self._cik_map = cik_map
        self._cik_map_fetched_at = datetime.now()

    def _get_cik_for_ticker(self, ticker: str) -> Optional[str]:
        self._load_cik_map()
        return self._cik_map.get(ticker.upper())

    def _get_sec_insider_data(self, ticker: str, days: int) -> Optional[Dict]:
        cik = self._get_cik_for_ticker(ticker)
        if not cik:
            return None

        submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        try:
            response = requests.get(submissions_url, headers=self.headers, timeout=20)
            response.raise_for_status()
            submissions = response.json()
        except Exception as e:
            logger.warning(f"SEC submissions fetch failed for {ticker}: {str(e)}")
            return None

        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accession_numbers = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        primary_docs = recent.get("primaryDocument", [])

        form_indexes = [
            idx for idx, form in enumerate(forms)
            if str(form).upper().startswith("4")
        ]

        if not form_indexes:
            return None

        cutoff_date = datetime.now().date() - timedelta(days=days)
        selected_index = None
        for idx in form_indexes:
            try:
                filing_date = datetime.strptime(filing_dates[idx], "%Y-%m-%d").date()
            except Exception:
                filing_date = None

            if filing_date and filing_date < cutoff_date:
                continue

            selected_index = idx
            break

        if selected_index is None:
            return None

        accession = accession_numbers[selected_index]
        primary_doc = primary_docs[selected_index]
        if not accession or not primary_doc:
            return None

        accession_path = accession.replace("-", "")
        filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_path}/{primary_doc}"

        try:
            filing_response = requests.get(filing_url, headers=self.headers, timeout=20)
            filing_response.raise_for_status()
            xml_text = filing_response.text
        except Exception as e:
            logger.warning(f"SEC Form 4 fetch failed for {ticker}: {str(e)}")
            return None

        try:
            root = ET.fromstring(xml_text)
        except Exception as e:
            logger.warning(f"SEC Form 4 parse failed for {ticker}: {str(e)}")
            return None

        buys = 0
        sells = 0
        total_buy_value = 0.0
        total_sell_value = 0.0
        parsed_transactions = []

        transactions = root.findall(".//{*}nonDerivativeTransaction")
        for tx in transactions:
            code_node = tx.find(".//{*}transactionAcquiredDisposedCode/{*}value")
            shares_node = tx.find(".//{*}transactionShares/{*}value")
            price_node = tx.find(".//{*}transactionPricePerShare/{*}value")
            date_node = tx.find(".//{*}transactionDate/{*}value")

            code = (code_node.text or "").strip().upper() if code_node is not None else ""
            shares = float(shares_node.text) if shares_node is not None and shares_node.text else 0.0
            price = float(price_node.text) if price_node is not None and price_node.text else 0.0
            value = shares * price if shares and price else 0.0

            if code == "A":
                buys += 1
                total_buy_value += value
                direction = "BUY"
            elif code == "D":
                sells += 1
                total_sell_value += value
                direction = "SELL"
            else:
                direction = "OTHER"

            parsed_transactions.append({
                "insider_name": "",
                "title": "",
                "transaction_type": direction,
                "shares": shares,
                "price": price,
                "value": value,
                "date": date_node.text if date_node is not None else ""
            })

        if buys == 0 and sells == 0:
            return None

        return {
            "total_transactions": buys + sells,
            "buys": buys,
            "sells": sells,
            "total_buy_value": total_buy_value,
            "total_sell_value": total_sell_value,
            "transactions": parsed_transactions
        }

    def _calculate_insider_sentiment(self, data: Dict) -> str:
        """Calculate overall insider sentiment"""
        net = data["buys"] - data["sells"]

        if net >= 3:
            return "VERY_BULLISH"
        elif net >= 1:
            return "BULLISH"
        elif net <= -3:
            return "VERY_BEARISH"
        elif net <= -1:
            return "BEARISH"
        else:
            return "NEUTRAL"

    def _generate_insider_signal(self, data: Dict) -> Optional[str]:
        """Generate trading signal based on insider activity"""
        net_buys = data["buys"] - data["sells"]
        net_value = data["total_buy_value"] - data["total_sell_value"]

        # Strong buy signal: 3+ net buys OR $1M+ net buying
        if net_buys >= 3 or net_value >= 1000000:
            return "INSIDER_BUYING"

        # Strong sell signal: 3+ net sells OR $1M+ net selling
        elif net_buys <= -3 or net_value <= -1000000:
            return "INSIDER_SELLING"

        return None

    def _get_mock_insider_data(self, ticker: str, days: int) -> Dict:
        """
        Mock insider data - replace with actual SEC Edgar scraping

        Real implementation options:
        1. Scrape SEC Edgar Form 4 filings
        2. Use Finnhub Insider Trading API: finnhub_client.stock_insider_transactions(ticker)
        3. Use OpenInsider data
        """

        # Simulate insider activity based on ticker hash (consistent mock data)
        hash_val = sum(ord(c) for c in ticker) % 10

        if hash_val > 7:  # 20% chance - bullish insiders
            buys = 4
            sells = 1
            total_buy_value = 2500000
            total_sell_value = 500000
        elif hash_val < 3:  # 30% chance - bearish insiders
            buys = 1
            sells = 4
            total_buy_value = 300000
            total_sell_value = 1800000
        else:  # 50% chance - neutral
            buys = 2
            sells = 2
            total_buy_value = 800000
            total_sell_value = 900000

        return {
            "total_transactions": buys + sells,
            "buys": buys,
            "sells": sells,
            "total_buy_value": total_buy_value,
            "total_sell_value": total_sell_value,
            "transactions": [
                {
                    "insider_name": "John Doe",
                    "title": "CEO",
                    "transaction_type": "BUY" if i < buys else "SELL",
                    "shares": 10000,
                    "price": 150.00,
                    "value": 1500000,
                    "date": (datetime.now() - timedelta(days=i*10)).isoformat()
                }
                for i in range(buys + sells)
            ]
        }

    def _get_default_insider_data(self, ticker: str) -> Dict:
        """Return default data when API fails"""
        return {
            "ticker": ticker,
            "period_days": 90,
            "total_transactions": 0,
            "insider_buys": 0,
            "insider_sells": 0,
            "net_activity": 0,
            "total_buy_value": 0,
            "total_sell_value": 0,
            "net_value": 0,
            "insider_sentiment": "UNKNOWN",
            "signal": None,
            "transactions": []
        }

    def get_insider_score(self, ticker: str) -> int:
        """
        Get insider trading score for AI predictions (0-20 points)

        Returns:
            Score from 0-20 based on insider activity
        """
        try:
            activity = self.get_insider_activity(ticker, days=90)

            score = 10  # Neutral baseline

            # Add points for insider buying
            if activity["net_activity"] >= 3:
                score += 10  # Very bullish
            elif activity["net_activity"] >= 1:
                score += 5   # Bullish

            # Subtract points for insider selling
            elif activity["net_activity"] <= -3:
                score -= 10  # Very bearish
            elif activity["net_activity"] <= -1:
                score -= 5   # Bearish

            # Adjust based on transaction value
            if activity["net_value"] >= 1000000:
                score += 5  # Large buys
            elif activity["net_value"] <= -1000000:
                score -= 5  # Large sells

            # Clamp to 0-20 range
            return max(0, min(20, score))

        except Exception as e:
            logger.error(f"Error calculating insider score for {ticker}: {str(e)}")
            return 10  # Neutral on error


# Global instance
_insider_service = None

def get_insider_service() -> InsiderTradingService:
    """Get or create insider trading service instance"""
    global _insider_service
    if _insider_service is None:
        _insider_service = InsiderTradingService()
    return _insider_service
