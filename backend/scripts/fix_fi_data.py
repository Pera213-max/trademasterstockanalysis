
import sys
import os
import json
import logging
import yfinance as yf
from datetime import datetime

# Setup path
sys.path.append("/app")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fix_fi_data")

def test_springvest():
    ticker = "SPRING.HE"
    logger.info(f"Testing yfinance data for {ticker}...")
    
    try:
        # 1. Test Info
        stock = yf.Ticker(ticker)
        info = stock.info
        logger.info(f"Info keys found: {len(info.keys())}")
        if 'currentPrice' in info:
            logger.info(f"Current Price: {info['currentPrice']}")
        elif 'previousClose' in info:
            logger.info(f"Previous Close: {info['previousClose']}")
        else:
            logger.warning("No price data found in info!")
            
        # 2. Test History
        hist = stock.history(period="1mo")
        logger.info(f"History rows: {len(hist)}")
        if not hist.empty:
            logger.info(f"Last date: {hist.index[-1]}")
            logger.info(f"Last close: {hist['Close'].iloc[-1]}")
        else:
            logger.warning("History is empty!")
            
        # 3. Test Inderes Fallback
        logger.info(f"Testing Inderes fallback for {ticker}...")
        try:
            from app.services.inderes_service import get_inderes_service
            inderes = get_inderes_service()
            data = inderes.get_stock_data(ticker)
            if data:
                logger.info(f"✅ Inderes Success: Price={data.get('price')} EUR, Change={data.get('changePercent')}%")
            else:
                logger.error("❌ Inderes returned None")
        except Exception as e:
            logger.error(f"Inderes test error: {e}")

    except Exception as e:
        logger.error(f"Error fetching {ticker}: {e}")

def refresh_news():
    logger.info("Refreshing FI news data...")
    try:
        from app.services.fi_event_service import get_fi_event_service
        service = get_fi_event_service()
        
        # 1. Ingest RSS (General market news)
        logger.info("Ingesting Nasdaq RSS feeds...")
        count_rss = service.ingest_nasdaq_rss(analyze_new=True, limit=20)
        logger.info(f"Added {count_rss} RSS events")
        
        # 2. Ingest Significant Events (Company specific) for dashboard
        # We'll prioritize Blue Chips for speed
        logger.info("Ingesting Company News (Blue Chips)...")
        from app.services.fi_data import get_fi_data_service
        fi_data = get_fi_data_service()
        universe = fi_data.get_universe()
        blue_chips = universe.get("blue_chips", [])
        
        count_news = 0
        for ticker in blue_chips[:10]: # Do top 10 first to show results quickly
            logger.info(f"Fetching news for {ticker}...")
            added = service.ingest_nasdaq_company_news_for_ticker(ticker, analyze_new=False, limit=5)
            count_news += added
            
        logger.info(f"Added {count_news} company news events")
        
    except Exception as e:
        logger.error(f"Error refreshing news: {e}")

if __name__ == "__main__":
    logger.info("--- Starting Diagnostics & Fix ---")
    test_springvest()
    refresh_news()
    logger.info("--- Done ---")
