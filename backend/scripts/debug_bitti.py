
import sys
import logging
import json

# Setup path
sys.path.append("/app")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_bitti")

def check_bitti():
    ticker = "BITTI.HE"
    logger.info(f"Checking analysis for {ticker}...")
    
    try:
        from app.services.fi_data import get_fi_data_service
        service = get_fi_data_service()
        
        # 1. Quote
        quote = service.get_quote(ticker)
        logger.info(f"Quote: {quote}")
        
        # 2. Fundamentals
        fund = service.get_fundamentals(ticker)
        logger.info(f"Fundamentals: {fund}")
        
        # 3. History
        hist = service.get_history(ticker, range="1y")
        logger.info(f"History items: {len(hist) if hist else 0}")
        if hist and len(hist) > 0:
            logger.info(f"Last history: {hist[-1]}")
            
        # 4. Full Analysis
        analysis = service.get_analysis(ticker)
        if analysis:
            logger.info("Analysis: OK")
            logger.info(f"Score: {analysis.get('score')}")
            logger.info(f"Metrics: {analysis.get('metrics')}")
        else:
            logger.error("Analysis: NONE")

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)

if __name__ == "__main__":
    check_bitti()
