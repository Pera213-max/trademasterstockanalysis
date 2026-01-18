# TradeMaster Pro - Stock Universe Documentation

## Overview
TradeMaster Pro analyzes **5,000+ US-listed stocks** sourced from Nasdaq Trader symbol directories.
The universe file is regenerated to keep coverage current.

## Stock Universe File
- Primary universe: `backend/app/data/universe_tickers.json`
- Fallback static lists: `backend/app/services/stock_universe.py` (used only if the file is missing)

## How the Universe Loads
- `get_all_stocks()` loads the universe file when present.
- Delisted tickers are filtered using `backend/app/data/delisted_tickers.json`.
- If the universe file is absent, static lists are used instead.

## Functions Available

### Get All Stocks
```python
from app.services.stock_universe import get_all_stocks

stocks = get_all_stocks()  # Returns all 5,000+ unique stocks (sorted)
```

### Get Stocks by Exchange (Static Lists)
```python
from app.services.stock_universe import (
    get_sp500_stocks,
    get_nyse_stocks,
    get_nasdaq_stocks,
)
```

### Get Stock Counts
```python
from app.services.stock_universe import get_detailed_stock_count

counts = get_detailed_stock_count()
# Returns (example; values vary as the universe regenerates):
# {
#   "sp500": 503,
#   "nyse": 500,
#   "nasdaq": 1000,
#   "international": 160,
#   "small_mid_cap": 247,
#   "total_unique": 6891,
#   "total_with_duplicates": 2410,
#   "universe_file": 6891,
#   "static_total_unique": 2164,
#   "delisted_filtered": 40
# }
```

### Get Stocks by Sector
```python
from app.services.stock_universe import get_stocks_by_sector

tech_stocks = get_stocks_by_sector("tech")       # Technology stocks
energy_stocks = get_stocks_by_sector("energy")   # Energy stocks
# Available sectors: tech, energy, healthcare, finance, consumer
```

## AI Pickers Integration
All AI prediction services use the complete stock universe:

- **predictor.py** (Swing & Long-term picks): Uses `get_all_stocks()`
- **short_predictor.py** (Day trading picks): Uses `get_all_stocks()`
- Analysis covers 5,000+ US-listed stocks

## Recent Updates
- **2025-12-29**: Universe expanded to 5,000+ US-listed stocks (Nasdaq Trader lists)
- Delisted tickers filtered via `delisted_tickers.json`

## Display in Frontend
The stock count is displayed in the dashboard footer:
```
5,000+
US stocks analyzed in real-time
S&P 500 + NYSE + NASDAQ
```

Location: `frontend/app/dashboard/page.tsx`

## Notes
- Universe file is generated from Nasdaq Trader symbol directories
- Tickers are normalized to use `-` for class shares (e.g., `BRK-B`)
- Static lists remain as a fallback for offline or missing data scenarios
