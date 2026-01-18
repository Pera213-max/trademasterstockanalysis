import yfinance as yf
from typing import Dict, List, Optional
import redis
import json
from app.config.settings import settings

class MarketService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )

    async def get_ticker_data(self, symbol: str) -> Optional[Dict]:
        """Get ticker data from yfinance"""
        try:
            # Check cache first
            cached = self.redis_client.get(f"ticker:{symbol}")
            if cached:
                return json.loads(cached)

            # Fetch from yfinance
            ticker = yf.Ticker(symbol)
            info = ticker.info

            data = {
                "symbol": symbol,
                "price": info.get("currentPrice", 0),
                "change": info.get("regularMarketChangePercent", 0),
                "volume": info.get("volume", 0),
                "market_cap": info.get("marketCap", 0)
            }

            # Cache for 60 seconds
            self.redis_client.setex(
                f"ticker:{symbol}",
                60,
                json.dumps(data)
            )

            return data
        except Exception as e:
            print(f"Error fetching ticker data: {e}")
            return None

    async def get_historical_data(
        self,
        symbol: str,
        period: str = "1mo"
    ) -> Optional[List[Dict]]:
        """Get historical price data"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)

            data = []
            for index, row in hist.iterrows():
                data.append({
                    "date": index.strftime("%Y-%m-%d"),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"])
                })

            return data
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return None
