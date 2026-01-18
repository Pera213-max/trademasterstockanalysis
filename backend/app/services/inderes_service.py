
import logging
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class InderesService:
    """Service to scrape stock data from Inderes.fi as a fallback"""
    
    BASE_URL = "https://www.inderes.fi/companies"
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def _get_slug(self, ticker: str) -> str:
        """Convert ticker (SPRING.HE) to Inderes slug (Springvest)"""
        # Mapping for known problematic tickers
        mapping = {
            "SPRING.HE": "Springvest",
            "SPRING": "Springvest"
        }
        
        normalized = ticker.upper()
        if normalized in mapping:
            return mapping[normalized]
            
        # Default fallback: Remove .HE and capitalize
        return normalized.replace(".HE", "").capitalize()

    def get_stock_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        slug = self._get_slug(ticker)
        url = f"{self.BASE_URL}/{slug}"
        
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"Inderes fetch failed for {ticker} ({url}): {resp.status_code}")
                return None
                
            soup = BeautifulSoup(resp.text, "lxml")
            
            # 1. Price
            # <div class="flex items-center gap-x-2 text-3xl font-bold leading-tight text-white">
            price_div = soup.find("div", class_="text-3xl font-bold leading-tight text-white")
            if not price_div:
                logger.warning(f"Inderes price element not found for {ticker}")
                return None
                
            # Extract text "7,28" -> 7.28
            price_text = price_div.get_text(strip=True).replace("EUR", "").strip().replace(",", ".")
            try:
                price = float(price_text)
            except ValueError:
                logger.warning(f"Failed to parse price '{price_text}' for {ticker}")
                return None
                
            # 2. Change (Often adjacent or in a similar styled block)
            # We look for percentage styling often used by Tailwind/Inderes
            change_pct = 0.0
            # Try to find elements with green/red text classes often used for change
            # This is heuristic and might need adjustment
            change_candidates = soup.find_all("span", class_=lambda x: x and ("text-green" in x or "text-red" in x))
            for cand in change_candidates:
                text = cand.get_text(strip=True)
                if "%" in text:
                    try:
                        clean = text.replace("%", "").replace(",", ".").replace("+", "").strip()
                        change_pct = float(clean)
                        break
                    except ValueError:
                        continue

            return {
                "ticker": ticker,
                "price": price,
                "change": 0, # Absolute change hard to calculate without prev close
                "changePercent": change_pct,
                "currency": "EUR",
                "source": "Inderes",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error scraping Inderes for {ticker}: {e}")
            return None

_inderes_service = None

def get_inderes_service() -> InderesService:
    global _inderes_service
    if _inderes_service is None:
        _inderes_service = InderesService()
    return _inderes_service
