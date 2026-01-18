
import sys
import logging
import json
from datetime import datetime
import yfinance as yf

# Setup path
sys.path.append("/app")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_chart")

def check_history(ticker="NOKIA.HE"):
    logger.info(f"Checking history for {ticker}...")
    
    # 1. Fetch direct from yfinance
    try:
        stock = yf.Ticker(ticker)
        # Get 5 days of 1-minute data to see if we get TODAY
        # Or 1 month of daily data
        hist = stock.history(period="5d", interval="1d")
        
        logger.info(f"--- YFinance Direct Response ---")
        if hist.empty:
            logger.error("History is EMPTY!")
        else:
            logger.info(f"Columns: {hist.columns}")
            last_date = hist.index[-1]
            last_close = hist['Close'].iloc[-1]
            logger.info(f"Rows: {len(hist)}")
            logger.info(f"Last Date: {last_date}")
            logger.info(f"Last Close: {last_close}")
            logger.info(f"Data Tail:\n{hist.tail(2)}")

    except Exception as e:
        logger.error(f"YFinance fetch failed: {e}")

    # 2. Check Cache
    try:
        from database.redis.config import get_redis_cache
        cache = get_redis_cache()
        if cache and cache.is_connected():
            key = f"fi:history:1y:1d:{ticker}"
            cached_raw = cache.redis_client.get(key)
            if cached_raw:
                data = json.loads(cached_raw)
                logger.info(f"--- Redis Cache Content ({key}) ---")
                if data and len(data) > 0:
                    last_item = data[-1]
                    logger.info(f"Cached Items: {len(data)}")
                    logger.info(f"Last Cached Date: {last_item.get('date')}")
                    logger.info(f"Last Cached Close: {last_item.get('close')}")
                else:
                    logger.warning("Cache exists but list is empty")
            else:
                logger.warning(f"No cache found for {key}")
        else:
            logger.error("Could not connect to Redis")
            
    except Exception as e:
        logger.error(f"Cache check failed: {e}")

if __name__ == "__main__":
    check_history()
