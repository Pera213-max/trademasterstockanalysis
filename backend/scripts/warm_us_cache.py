from app.routers import stocks as stocks_router
from app.services.stock_universe import get_core_index_tickers
import os


def main() -> int:
    limit = int(os.getenv("US_ANALYSIS_PREFETCH_LIMIT", "250"))
    tickers = get_core_index_tickers()
    if limit > 0:
        tickers = tickers[:limit]
    result = stocks_router.warm_stock_analysis_cache(tickers, allow_external=True, force=False)
    print(f"US analysis warm complete: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
