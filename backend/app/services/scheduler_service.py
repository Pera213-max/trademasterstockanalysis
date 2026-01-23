"""
Background Task Scheduler
==========================

Automatically refreshes market data in the background:
- News updates every 5 minutes
- Market data every 2 minutes
- AI picks (Top Picks): day daily, swing every 2 days, long every 3 days
- Hidden gems: day daily, swing every 2 days, long every 3 days
- Quick wins: twice daily
- Smart alerts (program universe) every 15 minutes
- Stock data pre-fetch: every 30 minutes (4000+ stocks cached)

Uses APScheduler for reliable scheduling.
Ensures data is always fresh even when no users are online.

IMPORTANT: The stock pre-fetch task ensures user requests NEVER hit yfinance
directly - they always get cached data, preventing rate limit crashes.
"""

import asyncio
import logging
import os
import threading
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


class BackgroundScheduler:
    """Background task scheduler for auto-refreshing data"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    async def refresh_news_task(self):
        """Background task to refresh news (uses cache)"""
        try:
            logger.info("Refreshing news cache...")
            from app.routers import news as news_router

            # Refresh via router endpoint which handles caching
            await news_router.get_newest_news(days=7, limit=50)
            logger.info("News cache refreshed")

        except Exception as e:
            logger.error(f"News refresh failed: {e}")

    async def refresh_fi_disclosures_task(self):
        """Background task to refresh Finnish disclosures/news"""
        try:
            logger.info("Refreshing FI disclosures...")
            from app.services.fi_event_service import get_fi_event_service

            event_service = get_fi_event_service()
            added = event_service.ingest_nasdaq_company_news_bulk(analyze_new=True, limit=8)
            if added:
                logger.info("FI company news added: %s", added)

            rss_enabled = os.getenv("FI_NASDAQ_RSS_ENABLED", "false").lower() in ("1", "true", "yes")
            if rss_enabled:
                rss_added = event_service.ingest_nasdaq_rss(analyze_new=True, limit=80)
                if rss_added:
                    logger.info("FI RSS disclosures added: %s", rss_added)

            event_service.analyze_pending(limit=event_service.analysis_batch_limit)
        except Exception as e:
            logger.error("FI disclosures refresh failed: %s", e)

    async def refresh_fi_ir_headlines_task(self):
        """Background task to refresh Finnish IR news headlines (daily)."""
        try:
            if os.getenv("FI_IR_NEWS_ENABLED", "true").lower() not in ("1", "true", "yes"):
                logger.info("FI IR headlines refresh disabled by env")
                return

            limit = int(os.getenv("FI_IR_NEWS_LIMIT", "5"))
            logger.info("Refreshing FI IR headlines (limit=%s)...", limit)
            from app.services.fi_event_service import get_fi_event_service

            event_service = get_fi_event_service()
            added = event_service.ingest_ir_headlines_bulk(limit=limit)
            if added:
                logger.info("FI IR headlines added: %s", added)
            event_service.analyze_pending(limit=max(10, event_service.analysis_batch_limit))
        except Exception as e:
            logger.error("FI IR headlines refresh failed: %s", e)

    async def refresh_fi_shorts_task(self):
        """Background task to refresh Finnish short positions (FIVA)"""
        try:
            logger.info("Refreshing FI short positions...")
            from app.services.fi_event_service import get_fi_event_service

            event_service = get_fi_event_service()
            added = event_service.ingest_fiva_short_positions(analyze_new=True)
            if added:
                logger.info("FI short positions added: %s", added)
        except Exception as e:
            logger.error("FI short positions refresh failed: %s", e)

    async def refresh_fi_fundamentals_insights_task(self):
        """Background task to refresh Finnish fundamental insights"""
        try:
            logger.info("Refreshing FI fundamental insights...")
            from app.services.fi_insight_service import get_fi_insight_service
            from app.services.fi_data import get_fi_data_service

            insight_service = get_fi_insight_service()
            fi_service = get_fi_data_service()
            created = insight_service.generate_fundamental_insights(fi_service.get_all_tickers())
            if created:
                logger.info("FI fundamental insights created: %s", created)
        except Exception as e:
            logger.error("FI fundamental insights refresh failed: %s", e)

    async def refresh_fi_yfinance_news_task(self):
        """Deprecated: yfinance news ingestion is disabled by default."""
        logger.info("Skipping FI yfinance news refresh (disabled by default)")

    async def refresh_social_trending_task(self):
        """Background task to refresh Reddit trending (uses cache)"""
        try:
            logger.info("Refreshing Reddit trending cache...")
            from app.routers import social as social_router

            # Refresh via router endpoint which handles caching
            await social_router.get_social_trending(limit=50, hours=24)
            logger.info("Reddit trending cache refreshed")

        except Exception as e:
            logger.error(f"Reddit trending refresh failed: {e}")

    async def refresh_market_data_task(self):
        """Background task to refresh market indicators"""
        try:
            logger.info("Refreshing market data...")
            from app.services.market_data_service import get_market_data_service

            # Refresh market overview (S&P, VIX, sectors)
            market_service = get_market_data_service()
            overview = market_service.get_market_overview()
            logger.info(f"Market overview refreshed ({len(overview.get('indices', []))} indices)")

        except Exception as e:
            logger.error(f"Market data refresh failed: {e}")

    async def refresh_ai_picks_task(self, timeframe: str):
        """Background task to refresh AI top picks for a timeframe"""
        try:
            logger.info("Refreshing AI picks cache (%s)...", timeframe)
            from app.routers import stocks as stocks_router

            await stocks_router.get_top_picks(timeframe=timeframe, limit=10, force_refresh=True)
            logger.info("Top picks (%s) refreshed", timeframe)

        except Exception as e:
            logger.error("AI picks refresh failed (%s): %s", timeframe, e)

    async def refresh_hidden_gems_task(self, timeframe: str, reason: str = "interval"):
        """Background task to refresh hidden gems for a timeframe"""
        try:
            logger.info("Refreshing hidden gems cache (%s, %s)...", timeframe, reason)
            from app.routers import stocks as stocks_router

            await stocks_router.get_hidden_gems(timeframe=timeframe, limit=10, force_refresh=True)
            logger.info("Hidden gems (%s) refreshed (%s)", timeframe, reason)

        except Exception as e:
            logger.error("Hidden gems refresh failed (%s): %s", timeframe, e)

    async def refresh_quick_wins_task(self, reason: str = "interval"):
        """Background task to refresh quick wins"""
        try:
            logger.info("Refreshing quick wins cache (%s)...", reason)
            from app.routers import stocks as stocks_router

            await stocks_router.get_quick_wins(limit=10, force_refresh=True)
            logger.info("Quick wins refreshed (%s)", reason)

        except Exception as e:
            logger.error("Quick wins refresh failed: %s", e)

    async def refresh_universe_alerts_task(self):
        """Background task to refresh universe smart alerts"""
        try:
            logger.info("Refreshing universe smart alerts...")
            from app.routers import portfolio as portfolio_router

            await portfolio_router.get_universe_alerts(limit=20, force_refresh=True)
            logger.info("Universe smart alerts refreshed")

        except Exception as e:
            logger.error("Universe smart alerts refresh failed: %s", e)

    async def prefetch_stock_data_task(self):
        """
        Background task to pre-fetch stock data for all 4000+ stocks.

        This ensures user requests ALWAYS get cached data and NEVER
        directly hit yfinance API, preventing rate limit crashes.

        The task runs in a separate thread to not block the event loop.
        It uses rate limiting to avoid hitting Yahoo Finance limits.
        """
        try:
            logger.info("=" * 60)
            logger.info("Starting stock data pre-fetch task...")
            logger.info("=" * 60)

            # Run in separate thread to not block event loop
            def prefetch_in_thread():
                try:
                    from app.services.yfinance_data_manager import get_yfinance_data_manager
                    from app.services.stock_universe import get_all_stocks

                    data_manager = get_yfinance_data_manager()
                    universe = get_all_stocks()

                    # Get all tickers
                    all_tickers = list(universe.keys()) if isinstance(universe, dict) else list(universe)
                    logger.info(f"Pre-fetching data for {len(all_tickers)} stocks...")

                    # Start background worker if not running
                    data_manager.start_worker()

                    # Queue all tickers for background fetch
                    data_manager.queue_bulk_prefetch(all_tickers, ["quote", "fundamentals"])

                    # Also run batch pre-fetch for most important stocks first
                    # (top 500 by some metric, or just first 500)
                    priority_tickers = all_tickers[:500]
                    data_manager.process_batch_prefetch(priority_tickers)

                    stats = data_manager.get_queue_stats()
                    logger.info(f"Stock pre-fetch task completed. Stats: {stats}")

                except Exception as e:
                    logger.error(f"Stock pre-fetch thread error: {e}")

            # Run in background thread
            thread = threading.Thread(target=prefetch_in_thread, daemon=True)
            thread.start()
            logger.info("Stock pre-fetch task launched in background thread")

        except Exception as e:
            logger.error("Stock data pre-fetch task failed: %s", e)

    async def start_data_manager_worker(self):
        """Start the yfinance data manager background worker"""
        try:
            from app.services.yfinance_data_manager import get_yfinance_data_manager
            data_manager = get_yfinance_data_manager()
            data_manager.start_worker()
            logger.info("YFinanceDataManager worker started")
        except Exception as e:
            logger.error("Failed to start data manager worker: %s", e)

    async def warm_cache_on_startup(self):
        """Warm heavy caches so users do not wait on first request."""
        try:
            logger.info("Warming cache on startup...")

            # Start yfinance data manager worker FIRST
            await self.start_data_manager_worker()

            # Trigger initial stock data pre-fetch in background
            await self.prefetch_stock_data_task()

            # Warm Finnish stock caches in background
            try:
                from app.services.fi_data import get_fi_data_service
                fi_service = get_fi_data_service()
                fi_service.warm_cache_async()
            except Exception as e:
                logger.error("Failed to start FI cache warming: %s", e)

            # Warm US analysis cache on startup (core tickers only)
            if os.getenv("US_ANALYSIS_PREFETCH_ON_STARTUP", "true").lower() in ("1", "true", "yes"):
                await self.refresh_us_analysis_cache_task(reason="startup")

            # Then warm AI picks cache
            await self.refresh_ai_picks_task(timeframe="day")
            await self.refresh_ai_picks_task(timeframe="swing")
            await self.refresh_ai_picks_task(timeframe="long")
            await self.refresh_hidden_gems_task(timeframe="day", reason="startup")
            await self.refresh_hidden_gems_task(timeframe="swing", reason="startup")
            await self.refresh_hidden_gems_task(timeframe="long", reason="startup")
            await self.refresh_quick_wins_task(reason="startup")

            # Also refresh news and social on startup
            await self.refresh_news_task()
            await self.refresh_social_trending_task()
            await self.refresh_fi_disclosures_task()
            await self.refresh_fi_ir_headlines_task()

            # Warm FI macro indicators cache on startup
            await self.refresh_fi_macro_cache_task()

            # Warm FI momentum cache on startup
            await self.refresh_fi_momentum_cache_task()

            # Kick off a full FI cache warm (quotes + fundamentals + history)
            try:
                from app.services.fi_data import get_fi_data_service
                fi_service = get_fi_data_service()
                fi_service.warm_cache_async()
            except Exception as e:
                logger.error("Failed to start full FI cache warm: %s", e)

            logger.info("Startup cache warm completed")
        except Exception as e:
            logger.error("Startup cache warm failed: %s", e)

    async def refresh_fi_full_cache_task(self):
        """Run a full Finnish cache warm (daily)."""
        try:
            from app.services.fi_data import get_fi_data_service
            fi_service = get_fi_data_service()
            fi_service.warm_cache_async()
            logger.info("Triggered full FI cache warm")
        except Exception as e:
            logger.error("Full FI cache warm failed: %s", e)

    async def refresh_fi_macro_cache_task(self):
        """Background task to refresh Finnish macro indicators cache."""
        try:
            logger.info("Refreshing FI macro indicators cache...")
            from app.services.fi_macro_service import get_fi_macro_service

            macro_service = get_fi_macro_service()
            result = macro_service.warm_cache()
            logger.info("FI macro cache refreshed: %s indicators", result.get("count", 0))
        except Exception as e:
            logger.error("FI macro cache refresh failed: %s", e)

    async def refresh_fi_momentum_cache_task(self):
        """Background task to refresh Finnish weekly momentum cache."""
        try:
            logger.info("Refreshing FI momentum cache...")
            from app.services.fi_data import get_fi_data_service

            fi_service = get_fi_data_service()
            # This builds and caches momentum data
            result = fi_service.get_weekly_momentum(limit=10)
            gainers = len(result.get("weekly_gainers", []))
            losers = len(result.get("weekly_losers", []))
            volume = len(result.get("unusual_volume", []))
            logger.info("FI momentum cache refreshed: %s gainers, %s losers, %s volume signals", gainers, losers, volume)
        except Exception as e:
            logger.error("FI momentum cache refresh failed: %s", e)

    async def refresh_us_analysis_cache_task(self, reason: str = "interval"):
        """Background task to precompute US stock analysis caches."""
        try:
            if os.getenv("US_ANALYSIS_PREFETCH_ENABLED", "true").lower() not in ("1", "true", "yes"):
                logger.info("US analysis cache warm disabled by env")
                return

            limit = int(os.getenv("US_ANALYSIS_PREFETCH_LIMIT", "250"))
            from app.services.stock_universe import get_core_index_tickers
            from app.routers import stocks as stocks_router

            tickers = get_core_index_tickers()
            if limit > 0:
                tickers = tickers[:limit]

            logger.info("Refreshing US analysis cache (%s) for %s tickers...", reason, len(tickers))
            result = await asyncio.to_thread(
                stocks_router.warm_stock_analysis_cache,
                tickers,
                True,
                False,
            )
            logger.info("US analysis cache refreshed: %s", result)
        except Exception as e:
            logger.error("US analysis cache refresh failed: %s", e)

    def start(self):
        """Start the background scheduler"""
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        logger.info("=" * 60)
        logger.info("Starting Background Scheduler...")
        logger.info("=" * 60)

        # Add jobs with different intervals
        # News refresh - every 4 hours (cached, so no need for frequent updates)
        self.scheduler.add_job(
            self.refresh_news_task,
            trigger=IntervalTrigger(hours=4),
            id='refresh_news',
            name='Refresh News Every 4 Hours',
            replace_existing=True
        )

        # Finnish disclosures/news - once daily (reduce load, enough for FI market)
        self.scheduler.add_job(
            self.refresh_fi_disclosures_task,
            trigger=CronTrigger(hour=6, minute=30, timezone=ZoneInfo("Europe/Helsinki")),
            id='refresh_fi_disclosures',
            name='Refresh FI Disclosures Daily 06:30',
            replace_existing=True
        )

        # Finnish IR headlines - once daily
        self.scheduler.add_job(
            self.refresh_fi_ir_headlines_task,
            trigger=CronTrigger(hour=6, minute=45, timezone=ZoneInfo("Europe/Helsinki")),
            id='refresh_fi_ir_headlines',
            name='Refresh FI IR Headlines Daily 06:45',
            replace_existing=True
        )

        # Full Finnish cache warm - once daily after market close (18:30)
        self.scheduler.add_job(
            self.refresh_fi_full_cache_task,
            trigger=CronTrigger(hour=18, minute=50, timezone=ZoneInfo("Europe/Helsinki")),
            id='refresh_fi_full_cache',
            name='Refresh FI Cache Daily 18:50 (after market close)',
            replace_existing=True
        )

        # Finnish macro indicators - every 5 minutes (for real-time market data)
        self.scheduler.add_job(
            self.refresh_fi_macro_cache_task,
            trigger=IntervalTrigger(minutes=5),
            id='refresh_fi_macro_cache',
            name='Refresh FI Macro Indicators Every 5 Minutes',
            replace_existing=True
        )

        # Finnish momentum - every 15 minutes (weekly gainers/losers, volume, RSI)
        self.scheduler.add_job(
            self.refresh_fi_momentum_cache_task,
            trigger=IntervalTrigger(minutes=15),
            id='refresh_fi_momentum_cache',
            name='Refresh FI Momentum Every 15 Minutes',
            replace_existing=True
        )

        # US analysis cache warm - once daily (core tickers)
        self.scheduler.add_job(
            self.refresh_us_analysis_cache_task,
            trigger=CronTrigger(hour=3, minute=30, timezone=ZoneInfo("UTC")),
            id='refresh_us_analysis_cache',
            name='Refresh US Analysis Cache Daily 03:30 UTC',
            replace_existing=True
        )

        # Finnish short positions (FIVA) - once daily at 06:00 Helsinki time
        self.scheduler.add_job(
            self.refresh_fi_shorts_task,
            trigger=CronTrigger(hour=6, minute=0, timezone=ZoneInfo("Europe/Helsinki")),
            id='refresh_fi_shorts',
            name='Refresh FI Short Positions Daily',
            replace_existing=True
        )

        # Finnish fundamentals insights - once daily at 19:00 Helsinki time (after market close)
        self.scheduler.add_job(
            self.refresh_fi_fundamentals_insights_task,
            trigger=CronTrigger(hour=19, minute=0, timezone=ZoneInfo("Europe/Helsinki")),
            id='refresh_fi_fundamentals_insights',
            name='Refresh FI Fundamental Insights Daily 19:00 (after market close)',
            replace_existing=True
        )

        # Finnish yfinance news - disabled by default

        # Reddit trending - every 4 hours
        self.scheduler.add_job(
            self.refresh_social_trending_task,
            trigger=IntervalTrigger(hours=4),
            id='refresh_social_trending',
            name='Refresh Reddit Trending Every 4 Hours',
            replace_existing=True
        )

        self.scheduler.add_job(
            self.refresh_market_data_task,
            trigger=IntervalTrigger(minutes=2),
            id='refresh_market',
            name='Refresh Market Data Every 2 Minutes',
            replace_existing=True
        )

        self.scheduler.add_job(
            self.refresh_ai_picks_task,
            trigger=IntervalTrigger(days=1),
            id='refresh_ai_picks_day',
            name='Refresh AI Picks Day (Daily)',
            replace_existing=True,
            kwargs={"timeframe": "day"}
        )

        self.scheduler.add_job(
            self.refresh_ai_picks_task,
            trigger=IntervalTrigger(days=2),
            id='refresh_ai_picks_swing',
            name='Refresh AI Picks Swing (Every 2 Days)',
            replace_existing=True,
            kwargs={"timeframe": "swing"}
        )

        self.scheduler.add_job(
            self.refresh_ai_picks_task,
            trigger=IntervalTrigger(days=3),
            id='refresh_ai_picks_long',
            name='Refresh AI Picks Long (Every 3 Days)',
            replace_existing=True,
            kwargs={"timeframe": "long"}
        )

        self.scheduler.add_job(
            self.refresh_hidden_gems_task,
            trigger=IntervalTrigger(days=1),
            id='refresh_hidden_gems_day',
            name='Refresh Hidden Gems Day (Daily)',
            replace_existing=True,
            kwargs={"timeframe": "day"}
        )

        self.scheduler.add_job(
            self.refresh_hidden_gems_task,
            trigger=IntervalTrigger(days=2),
            id='refresh_hidden_gems_swing',
            name='Refresh Hidden Gems Swing (Every 2 Days)',
            replace_existing=True,
            kwargs={"timeframe": "swing"}
        )

        self.scheduler.add_job(
            self.refresh_hidden_gems_task,
            trigger=IntervalTrigger(days=3),
            id='refresh_hidden_gems_long',
            name='Refresh Hidden Gems Long (Every 3 Days)',
            replace_existing=True,
            kwargs={"timeframe": "long"}
        )

        self.scheduler.add_job(
            self.refresh_quick_wins_task,
            trigger=IntervalTrigger(hours=12),
            id='refresh_quick_wins',
            name='Refresh Quick Wins Twice Daily',
            replace_existing=True
        )

        self.scheduler.add_job(
            self.refresh_universe_alerts_task,
            trigger=IntervalTrigger(minutes=15),
            id='refresh_universe_alerts',
            name='Refresh Universe Alerts Every 15 Minutes',
            replace_existing=True
        )

        # Stock data pre-fetch - ensures all 4000+ stocks are cached
        # Runs every 30 minutes to keep cache fresh
        self.scheduler.add_job(
            self.prefetch_stock_data_task,
            trigger=IntervalTrigger(minutes=30),
            id='prefetch_stock_data',
            name='Pre-fetch Stock Data Every 30 Minutes',
            replace_existing=True
        )

        # Start the scheduler
        self.scheduler.start()
        self.is_running = True
        try:
            asyncio.get_running_loop()
            asyncio.create_task(self.warm_cache_on_startup())
            logger.info("Startup cache warm scheduled")
        except RuntimeError:
            logger.warning("No running event loop; skipping startup cache warm")

        logger.info("News refresh: Every 4 hours (cached)")
        logger.info("Reddit trending: Every 4 hours (cached)")
        logger.info("Market data: Every 2 minutes")
        logger.info("AI picks (Top Picks): day daily, swing every 2 days, long every 3 days")
        logger.info("Hidden gems: day daily, swing every 2 days, long every 3 days")
        logger.info("Quick wins: twice daily")
        logger.info("Universe smart alerts: Every 15 minutes")
        logger.info("Stock data pre-fetch: Every 30 minutes (4000+ stocks)")
        logger.info("=" * 60)

    def stop(self):
        """Stop the background scheduler"""
        if not self.is_running:
            return

        logger.info("Stopping Background Scheduler...")
        self.scheduler.shutdown()
        self.is_running = False
        logger.info("Scheduler stopped")

    def get_jobs(self):
        """Get all scheduled jobs"""
        return self.scheduler.get_jobs()


# Singleton instance
_scheduler = None

def get_scheduler() -> BackgroundScheduler:
    """Get singleton instance of scheduler"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler
