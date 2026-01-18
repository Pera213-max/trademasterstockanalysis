"""
TradeMaster Pro - AI Predictor Service
=======================================

Advanced stock and crypto prediction using:
- Machine Learning (XGBoost) for 10%+ weekly predictions
- Real-time data from Finnhub API
- Social sentiment from Reddit
- News impact analysis from NewsAPI
- Advanced technical indicators (pandas-ta)
- Traditional technical analysis, momentum, volume, trend detection

Data Sources:
- Finnhub: Real-time quotes, analyst ratings, price targets
- Reddit: Social sentiment, mention volume, trending stocks
- NewsAPI: Market news, company news, high-impact events
- yfinance: Historical data for backtesting
- pandas-ta: Professional-grade technical indicators
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
import time
import random
import math

from .ml_predictor import get_ml_predictor
from .finnhub_service import get_finnhub_service
from .yfinance_service import get_yfinance_service
from .reddit_service import get_reddit_service
from .news_service import get_news_service
from .stock_news_analyzer import get_stock_news_analyzer
from .stock_universe import (
    get_all_stocks,
    get_core_index_tickers,
    get_stocks_by_sector,
    get_stock_count,
)
from app.config.settings import settings
from database.redis.config import get_redis_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StockPredictor:
    """
    AI-powered stock predictor using technical analysis

    Analyzes stocks based on:
    - Technical indicators (30 points)
    - Momentum (30 points)
    - Volume analysis (20 points)
    - Trend detection (20 points)
    """

    # Sector definitions
    SECTORS = {
        "tech": ["NVDA", "AAPL", "MSFT", "GOOGL", "META", "AMD", "ORCL", "ADBE", "CRM", "INTC", "AVGO", "QCOM"],
        "energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HAL"],
        "healthcare": ["JNJ", "UNH", "PFE", "ABBV", "TMO", "MRK", "ABT", "DHR", "LLY", "BMY", "MRNA", "GILD"],
        "finance": ["JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW", "AXP", "USB"],
        "consumer": ["AMZN", "TSLA", "WMT", "HD", "NKE", "SBUX", "MCD", "TGT", "LOW", "COST", "DIS", "NFLX"]
    }

    # Theme definitions with screening criteria
    THEMES = {
        "growth": {
            "description": "High growth potential stocks",
            "criteria": lambda data: data['Returns_20'].iloc[-1] > 0.10 if not pd.isna(data['Returns_20'].iloc[-1]) else False
        },
        "value": {
            "description": "Undervalued stocks with solid fundamentals",
            "criteria": lambda data: data['RSI'].iloc[-1] < 50 if not pd.isna(data['RSI'].iloc[-1]) else False
        },
        "esg": {
            "description": "ESG-focused sustainable companies",
            "preferred_tickers": ["TSLA", "AAPL", "MSFT", "JNJ", "UNH", "TMO", "ABBV", "ADBE", "CRM"]
        }
    }

    def __init__(self):
        self.lookback_days = 90

        # Initialize data services
        self.ml_predictor = get_ml_predictor()
        self.finnhub = get_finnhub_service()
        self.yfinance = get_yfinance_service()
        self.reddit = get_reddit_service()
        self.news = get_news_service()
        self.news_analyzer = get_stock_news_analyzer()
        self.redis_cache = get_redis_cache()
        self.fundamentals_cache_ttl = settings.CACHE_TTL_AI_PICKS

        logger.info("StockPredictor initialized with hybrid yfinance + Finnhub + AI news analysis")

    def _get_cached_fundamentals(self, ticker: str) -> Optional[Dict]:
        if not self.redis_cache or not self.redis_cache.is_connected():
            return None
        return self.redis_cache.get(f"fundamentals:{ticker}")

    def _cache_fundamentals(self, ticker: str, fundamentals: Dict) -> None:
        if not self.redis_cache or not self.redis_cache.is_connected():
            return
        self.redis_cache.set(f"fundamentals:{ticker}", fundamentals, ex=self.fundamentals_cache_ttl)

    def _normalize_timeframe(self, timeframe: Optional[str]) -> str:
        normalized = (timeframe or "swing").lower()
        if normalized not in {"day", "swing", "long"}:
            return "swing"
        return normalized

    def _get_timeframe_period(self, timeframe: str) -> str:
        if timeframe == "day":
            return "1mo"
        if timeframe == "long":
            return "1y"
        return "3mo"

    def _get_timeframe_score_weights(self, timeframe: str) -> Dict[str, float]:
        if timeframe == "day":
            return {"financial": 20.0, "market": 15.0, "technical": 35.0, "momentum": 30.0}
        if timeframe == "long":
            return {"financial": 45.0, "market": 35.0, "technical": 15.0, "momentum": 5.0}
        return {"financial": 35.0, "market": 25.0, "technical": 25.0, "momentum": 15.0}

    def _get_timeframe_target_weights(self, timeframe: str) -> Tuple[float, float]:
        if timeframe == "day":
            return 0.15, 0.005
        if timeframe == "long":
            return 0.7, 0.015
        return 0.4, 0.01

    def _to_float(self, value: Any, default: float = 0.0) -> float:
        if value is None:
            return default
        if isinstance(value, bool):
            return default
        if isinstance(value, (int, float)):
            number = float(value)
            return number if math.isfinite(number) else default
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return default
            lowered = cleaned.lower()
            if lowered in {"n/a", "na", "none", "null", "nan"}:
                return default
            negative = False
            if cleaned.startswith("(") and cleaned.endswith(")"):
                cleaned = cleaned[1:-1]
                negative = True
            cleaned = cleaned.replace(",", "").replace("$", "").replace("%", "")
            try:
                number = float(cleaned)
            except ValueError:
                return default
            if negative:
                number = -number
            return number if math.isfinite(number) else default
        return default

    def _normalize_growth_rate(self, value: Optional[float], source: Optional[str] = None) -> float:
        """Normalize revenue growth into a sensible decimal rate."""
        if value in (None, "", 0):
            return 0.1
        growth = self._to_float(value, default=0.1)
        if pd.isna(growth):
            return 0.1

        if source == "finnhub":
            if abs(growth) > 1:
                growth = growth / 100.0
        else:
            if abs(growth) > 5:
                growth = growth / 100.0

        if growth > 2.0:
            return 2.0
        if growth < -0.5:
            return -0.5
        return growth

    def _clamp_target_price(
        self,
        current_price: float,
        target_price: float,
        fundamentals: Optional[Dict],
        timeframe: str = "swing"
    ) -> float:
        """Clamp target price into a realistic band vs current price."""
        if not current_price or current_price <= 0:
            return target_price

        timeframe = self._normalize_timeframe(timeframe)
        if timeframe == "day":
            min_multiplier = 0.98
            max_multiplier = 1.08
        elif timeframe == "long":
            min_multiplier = 0.85
            max_multiplier = 1.75
        else:
            min_multiplier = 0.90
            max_multiplier = 1.35

        if fundamentals:
            market_cap = self._to_float(fundamentals.get("marketCap"), 0.0)
            if market_cap >= 200_000_000_000:
                max_multiplier = min(max_multiplier, 1.3)
            elif market_cap >= 10_000_000_000:
                max_multiplier = min(max_multiplier, 1.45)
            elif market_cap >= 2_000_000_000:
                max_multiplier = min(max_multiplier, 1.6)
            elif market_cap >= 300_000_000:
                max_multiplier = min(max_multiplier, 1.8)
            else:
                max_multiplier = min(max_multiplier, 2.2)

            high_52 = self._to_float(
                fundamentals.get("fiftyTwoWeekHigh") or fundamentals.get("52WeekHigh"),
                0.0
            )
            if high_52 and high_52 > 0:
                max_multiplier = min(max_multiplier, (high_52 * 1.2) / current_price)

            low_52 = self._to_float(
                fundamentals.get("fiftyTwoWeekLow") or fundamentals.get("52WeekLow"),
                0.0
            )
            if low_52 and low_52 > 0:
                min_multiplier = max(min_multiplier, (low_52 * 0.9) / current_price)

        if max_multiplier < min_multiplier:
            max_multiplier = min_multiplier

        target_price = min(target_price, current_price * max_multiplier)
        target_price = max(target_price, current_price * min_multiplier)
        return target_price

    def _get_timeframe_upside_cap(self, timeframe: str) -> float:
        timeframe = self._normalize_timeframe(timeframe)
        if timeframe == "day":
            return 8.0
        if timeframe == "long":
            return 75.0
        return 35.0

    def _apply_target_guardrails(
        self,
        current_price: float,
        target_price: float,
        fundamentals: Optional[Dict],
        timeframe: str
    ) -> Tuple[float, float]:
        if not current_price or current_price <= 0:
            return 0.0, 0.0

        safe_current = float(current_price)
        safe_target = float(target_price) if target_price and target_price > 0 else safe_current
        safe_target = self._clamp_target_price(safe_current, safe_target, fundamentals, timeframe=timeframe)

        if not safe_target or safe_target <= 0:
            safe_target = safe_current

        potential_return = ((safe_target - safe_current) / safe_current) * 100
        if not math.isfinite(potential_return):
            potential_return = 0.0

        max_upside = self._get_timeframe_upside_cap(timeframe)
        if potential_return > max_upside:
            potential_return = max_upside
            safe_target = safe_current * (1 + max_upside / 100)

        return safe_target, potential_return

    def _get_finnhub_fundamentals_for_scoring(self, ticker: str) -> Optional[Dict]:
        if not self.finnhub:
            return None

        profile = self.finnhub.get_company_profile(ticker) or {}
        financials = self.finnhub.get_basic_financials(ticker) or {}
        metrics = financials.get("metric", {}) if isinstance(financials, dict) else {}

        if not profile and not metrics:
            return None

        market_cap = 0
        if profile.get("marketCapitalization"):
            market_cap = float(profile.get("marketCapitalization", 0)) * 1_000_000
        if not market_cap:
            market_cap = metrics.get("marketCapitalization", 0) or 0

        return {
            "_source": "finnhub",
            "marketCap": market_cap or 0,
            "peRatio": metrics.get("peBasicExclExtraTTM") or metrics.get("peTTM") or 0,
            "forwardPE": metrics.get("peTTM") or 0,
            "pegRatio": metrics.get("pegTTM") or 0,
            "priceToBook": metrics.get("pbQuarterly") or 0,
            "dividendYield": metrics.get("dividendYieldIndicatedAnnual") or 0,
            "profitMargins": metrics.get("netProfitMarginTTM") or 0,
            "revenueGrowth": (
                metrics.get("revenueGrowthQuarterlyYoy")
                or metrics.get("revenueGrowthTTM")
                or 0
            ),
            "earningsGrowth": metrics.get("epsGrowthQuarterlyYoy") or 0,
            "returnOnEquity": metrics.get("roeTTM") or 0,
            "debtToEquity": metrics.get("totalDebt/totalEquityQuarterly") or 0,
            "beta": metrics.get("beta") or profile.get("beta") or 1,
            "fiftyTwoWeekHigh": metrics.get("52WeekHigh") or 0,
            "fiftyTwoWeekLow": metrics.get("52WeekLow") or 0,
            "shortName": profile.get("name") or profile.get("ticker") or ticker,
            "sector": profile.get("finnhubIndustry") or "Unknown",
            "industry": profile.get("finnhubIndustry") or "Unknown"
        }

    def _get_fundamentals_for_scoring(self, ticker: str) -> Optional[Dict]:
        cached = self._get_cached_fundamentals(ticker)
        if cached:
            return cached

        fundamentals = self.yfinance.get_fundamentals(ticker)
        if fundamentals:
            fundamentals.setdefault("_source", "yfinance")
            self._cache_fundamentals(ticker, fundamentals)
            return fundamentals

        fallback = self._get_finnhub_fundamentals_for_scoring(ticker)
        if fallback:
            logger.info("Using Finnhub fundamentals fallback for %s", ticker)
            fallback.setdefault("_source", "finnhub")
            self._cache_fundamentals(ticker, fallback)
        return fallback

    def predict_top_stocks(
        self,
        timeframe: str = "swing",
        limit: int = 10
    ) -> List[Dict]:
        """
        Predict top stocks based on timeframe using FREE Finnhub endpoints only

        Uses: quotes, profiles, financials, recommendations, price targets
        Does NOT use: candles (premium feature)

        Args:
            timeframe: Trading timeframe (day, swing, long)
            limit: Number of stocks to return

        Returns:
            List of top stocks with scores and analysis
        """
        timeframe = self._normalize_timeframe(timeframe)
        logger.info(f"Predicting top {limit} stocks for {timeframe} timeframe")
        logger.info(f"Total stock universe: {get_stock_count()} stocks")

        # Use full stock universe - analyze in batches
        all_tickers = get_all_stocks()

        # INSTITUTIONAL-GRADE COVERAGE: scan whole universe (S&P 500 + NASDAQ + NYSE + intl + SMID)
        tickers = all_tickers
        max_universe = settings.UNIVERSE_TICKER_LIMIT
        if max_universe and max_universe < len(tickers):
            seed = datetime.utcnow().strftime("%Y-%m-%d")
            rng = random.Random(seed)
            core_tickers = set(get_core_index_tickers())
            core_in_universe = [ticker for ticker in tickers if ticker in core_tickers]
            remaining = [ticker for ticker in tickers if ticker not in core_tickers]
            if max_universe <= len(core_in_universe):
                logger.warning(
                    "Universe limit %s below core index size %s; keeping core only",
                    max_universe,
                    len(core_in_universe),
                )
                tickers = core_in_universe
            else:
                sampled = rng.sample(remaining, max_universe - len(core_in_universe))
                tickers = core_in_universe + sampled
            logger.info(
                "Universe limit applied: %s/%s tickers (core kept: %s)",
                len(tickers),
                len(all_tickers),
                len(core_in_universe),
            )

        logger.info(f"Analyzing {len(tickers)} stocks using batch yfinance processing...")

        # BATCH PROCESSING: Fetch all historical data at once (10x faster!)
        period = self._get_timeframe_period(timeframe)
        batch_data = self.yfinance.get_multiple_stocks(tickers, period=period)
        logger.info(f"Fetched historical data for {len(batch_data)} stocks in batch")

        stocks_with_scores = []
        scanned = 0
        no_data = 0
        errors = 0

        for ticker in tickers:
            scanned += 1
            try:
                # Use pre-fetched batch data (no API call per stock)
                historical_data = batch_data.get(ticker)
                if historical_data is None or historical_data.empty:
                    no_data += 1
                    continue
                score_data = self.calculate_strength_score_free(
                    ticker,
                    historical_data,
                    use_fundamentals=False,
                    timeframe=timeframe
                )

                if score_data and score_data["total_score"] > 0:
                    current_price = score_data.get("current_price", 0)
                    target_price = score_data.get("target_price", current_price)
                    target_price, potential_return = self._apply_target_guardrails(
                        current_price,
                        target_price,
                        None,
                        timeframe
                    )

                    stocks_with_scores.append({
                        "ticker": ticker,
                        "score": score_data["total_score"],
                        "currentPrice": float(current_price),
                        "targetPrice": float(target_price),
                        "potentialReturn": float(potential_return),
                        "confidence": int(score_data["total_score"]),
                        "timeHorizon": timeframe.upper(),
                        "reasoning": score_data["reasoning"],
                        "signals": score_data["signals"],
                        "riskLevel": score_data["risk_level"],
                        "breakdown": score_data["breakdown"],
                        "company": score_data.get("company_name", ticker),
                        "sector": score_data.get("sector", "Unknown")
                    })

                if scanned % 50 == 0:
                    logger.info(f"Scanned {scanned} stocks...")

            except Exception as e:
                errors += 1
                if errors < 10:  # Only log first 10 errors
                    logger.error(f"Error analyzing {ticker}: {str(e)}")
                continue

        # Sort by score and enrich top candidates with fundamentals + news
        stocks_with_scores.sort(key=lambda x: x["score"], reverse=True)
        enrich_limit = settings.AI_PICKS_ENRICH_LIMIT
        if enrich_limit <= 0:
            candidate_count = len(stocks_with_scores)
        else:
            candidate_count = min(len(stocks_with_scores), min(max(limit * 5, 30), enrich_limit))
        if candidate_count > 0:
            self._upgrade_scores_with_fundamentals(stocks_with_scores, batch_data, candidate_count, timeframe)
            stocks_with_scores.sort(key=lambda x: x["score"], reverse=True)
            self._apply_news_overlay(stocks_with_scores, candidate_count)
            stocks_with_scores.sort(key=lambda x: x["score"], reverse=True)

        # Add ranks
        for i, stock in enumerate(stocks_with_scores[:limit], 1):
            stock["rank"] = i

        logger.info(
            "Top picks scan: %s tickers (%s no data), %s scored, %s errors",
            scanned,
            no_data,
            len(stocks_with_scores),
            errors
        )
        return stocks_with_scores[:limit]

    def _apply_news_overlay(self, picks: List[Dict], max_candidates: int) -> None:
        """
        Apply news-based adjustment to top-ranked picks.

        News impact scoring (max ~12 points):
        - Positive sentiment: +4 per article (max 2 = +8)
        - Negative sentiment: -4 per article (max 2 = -8)
        - High impact events: +3 bonus per HIGH impact article
        - News volume bonus: +1.5 per article (max 3 = +4.5)

        This gives news a meaningful ~10-12% impact on final score.
        """
        if not picks or max_candidates <= 0:
            return

        candidate_count = min(len(picks), max_candidates)
        for pick in picks[:candidate_count]:
            ticker = pick.get("ticker")
            if not ticker:
                continue
            try:
                major_news = self.news_analyzer.get_major_news(ticker, days=7)
            except Exception as e:
                logger.debug("News overlay failed for %s: %s", ticker, e)
                continue

            if not major_news:
                continue

            # Count sentiments with weights
            positive_count = 0
            negative_count = 0
            high_impact_count = 0

            for event in major_news:
                sentiment = event.get("sentiment", "").upper()
                impact = event.get("impact", "").upper()

                if sentiment == "POSITIVE":
                    positive_count += 1
                elif sentiment == "NEGATIVE":
                    negative_count += 1

                if impact == "HIGH":
                    high_impact_count += 1

            # Calculate score adjustment
            score_adjust = 0.0

            # Sentiment impact: +4/-4 per article (capped at 2 each direction)
            score_adjust += min(positive_count, 2) * 4.0
            score_adjust -= min(negative_count, 2) * 4.0

            # High impact bonus: +3 per HIGH impact article (cap at 2)
            score_adjust += min(high_impact_count, 2) * 3.0

            # News volume bonus: +1.5 per article (cap at 3)
            score_adjust += min(len(major_news), 3) * 1.5

            if score_adjust == 0:
                continue

            new_score = max(0.0, min(100.0, pick.get("score", 0) + score_adjust))
            pick["score"] = round(new_score, 2)
            pick["confidence"] = int(round(new_score))

            signals = pick.get("signals") or []
            if positive_count > 0 and "Positive News" not in signals:
                signals.append("Positive News")
            if negative_count > 0 and "Negative News" not in signals:
                signals.append("Negative News")
            if high_impact_count > 0 and "Breaking News" not in signals:
                signals.append("Breaking News")
            if len(major_news) >= 3 and "News Catalyst" not in signals:
                signals.append("News Catalyst")
            pick["signals"] = signals

            breakdown = pick.get("breakdown")
            if isinstance(breakdown, dict):
                breakdown["news_activity"] = len(major_news)
                breakdown["news_sentiment"] = round(score_adjust, 2)

    def _upgrade_scores_with_fundamentals(
        self,
        picks: List[Dict],
        batch_data: Dict[str, pd.DataFrame],
        max_candidates: int,
        timeframe: str = "swing"
    ) -> None:
        """Recalculate scores for top candidates using fundamentals."""
        if not picks or max_candidates <= 0:
            return

        timeframe = self._normalize_timeframe(timeframe)
        candidate_count = min(len(picks), max_candidates)
        for pick in picks[:candidate_count]:
            ticker = pick.get("ticker")
            if not ticker:
                continue
            historical_data = batch_data.get(ticker)
            score_data = self.calculate_strength_score_free(
                ticker,
                historical_data,
                use_fundamentals=True,
                timeframe=timeframe
            )
            if not score_data:
                continue

            current_price = score_data.get("current_price", pick.get("currentPrice", 0))
            target_price = score_data.get("target_price", pick.get("targetPrice", current_price))
            target_price, potential_return = self._apply_target_guardrails(
                current_price,
                target_price,
                None,
                timeframe
            )

            pick.update({
                "score": score_data["total_score"],
                "currentPrice": float(current_price),
                "targetPrice": float(target_price),
                "potentialReturn": float(potential_return),
                "confidence": int(score_data["total_score"]),
                "reasoning": score_data["reasoning"],
                "signals": score_data["signals"],
                "riskLevel": score_data["risk_level"],
                "breakdown": score_data["breakdown"],
                "company": score_data.get("company_name", ticker),
                "sector": score_data.get("sector", pick.get("sector", "Unknown"))
            })

    def calculate_strength_score_free(
        self,
        ticker: str,
        historical_data: Optional[pd.DataFrame] = None,
        use_fundamentals: bool = True,
        timeframe: str = "swing"
    ) -> Optional[Dict]:
        """
        Calculate strength score using PURE yfinance approach (NO RATE LIMITS!)

        Scoring (0-100 points):
        - Financial Metrics: 40 points (yfinance)
        - Market Position: 30 points (yfinance)
        - Technical Analysis: 20 points (historical data)
        - Momentum: 10 points (historical data)

        100% yfinance - NO API RATE LIMITS!

        Args:
            ticker: Stock ticker symbol
            historical_data: Pre-fetched historical data (for batch processing)
            use_fundamentals: Whether to fetch yfinance fundamentals/quotes

        Returns:
            Dictionary with score and analysis
        """
        try:
            timeframe = self._normalize_timeframe(timeframe)
            quote = None
            fundamentals = None
            current_price = None
            previous_close = None

            if historical_data is not None and not historical_data.empty:
                if 'Close' in historical_data.columns:
                    closes = historical_data['Close'].dropna()
                    if len(closes) >= 1:
                        current_price = float(closes.iloc[-1])
                        previous_close = float(closes.iloc[-2]) if len(closes) >= 2 else current_price

            if use_fundamentals:
                fundamentals = self._get_fundamentals_for_scoring(ticker)

            if (current_price is None or previous_close is None or current_price <= 0 or
                    pd.isna(current_price) or pd.isna(previous_close)):
                if not use_fundamentals:
                    return None
                quote = self.yfinance.get_quote(ticker)
                if not quote or quote.get('c', 0) == 0:
                    return None
                current_price = quote.get('c', 0)
                previous_close = quote.get('pc', current_price)

            if quote is None:
                quote = {
                    'c': float(current_price),
                    'pc': float(previous_close)
                }

            # Calculate individual scores (NO API CALLS!)
            financial_score = self._calc_financial_score_yf(fundamentals)  # 0-40 points
            market_score = self._calc_market_position_score_yf(fundamentals)  # 0-30 points

            # Technical & Momentum scoring from historical data
            technical_score = 0
            momentum_score = 0
            if historical_data is not None and len(historical_data) > 20:
                technical_score = self._calc_technical_score(historical_data, timeframe)  # 0-20 points
                momentum_score = self._calc_momentum_score(historical_data, timeframe)  # 0-10 points

            weights = self._get_timeframe_score_weights(timeframe)
            total_score = (
                (financial_score / 40) * weights["financial"] +
                (market_score / 30) * weights["market"] +
                (technical_score / 20) * weights["technical"] +
                (momentum_score / 10) * weights["momentum"]
            )
            total_score = max(0.0, min(100.0, total_score))

            # Generate reasoning and signals
            reasoning = self._generate_yf_reasoning(financial_score, market_score, technical_score, momentum_score)
            signals = self._generate_signals_yf(quote or {}, fundamentals, None)
            risk_level = self._determine_risk_yf(fundamentals, total_score)

            # Estimate target based on fundamentals + momentum
            growth = self._normalize_growth_rate(
                fundamentals.get('revenueGrowth') if fundamentals else None,
                fundamentals.get("_source") if fundamentals else None
            )

            # Boost target if strong momentum
            growth_weight, momentum_boost = self._get_timeframe_target_weights(timeframe)
            momentum_multiplier = 1.0 + (momentum_score * momentum_boost)
            estimated_target = current_price * (1 + (growth * growth_weight)) * momentum_multiplier
            estimated_target = self._clamp_target_price(
                current_price,
                estimated_target,
                fundamentals,
                timeframe=timeframe
            )

            return {
                "total_score": round(total_score, 2),
                "current_price": current_price,
                "target_price": round(estimated_target, 2),
                "company_name": fundamentals.get('shortName', ticker) if fundamentals else ticker,
                "sector": fundamentals.get('sector', 'Unknown') if fundamentals else 'Unknown',
                "breakdown": {
                    "financials": round(financial_score, 2),
                    "market_position": round(market_score, 2),
                    "technical": round(technical_score, 2),
                    "momentum": round(momentum_score, 2)
                },
                "reasoning": reasoning,
                "signals": signals,
                "risk_level": risk_level
            }

        except Exception as e:
            logger.error(f"Error calculating score for {ticker}: {str(e)}")
            return None

    def _calc_financial_score_yf(self, fundamentals: dict) -> float:
        """Calculate score from yfinance fundamentals (0-40 points)"""
        if not fundamentals:
            return 20

        score = 0

        # P/E Ratio (0-12 points) - lower is better for value
        pe = self._to_float(fundamentals.get('peRatio', 0), 0.0)
        if pe > 0:
            if 5 <= pe <= 15:
                score += 12
            elif 15 < pe <= 25:
                score += 10
            elif 25 < pe <= 40:
                score += 6
            elif pe > 40:
                score += 3

        # ROE - Return on Equity (0-10 points)
        roe = self._to_float(fundamentals.get('returnOnEquity', 0), 0.0)
        if roe:
            roe_pct = roe * 100
            if roe_pct >= 20:
                score += 10
            elif roe_pct >= 15:
                score += 7
            elif roe_pct >= 10:
                score += 5
            elif roe_pct >= 5:
                score += 3

        # Profit Margin (0-8 points)
        margin = self._to_float(fundamentals.get('profitMargins', 0), 0.0)
        if margin:
            margin_pct = margin * 100
            if margin_pct >= 20:
                score += 8
            elif margin_pct >= 15:
                score += 6
            elif margin_pct >= 10:
                score += 4
            elif margin_pct >= 5:
                score += 2

        # Revenue Growth (0-10 points)
        growth = self._normalize_growth_rate(
            fundamentals.get('revenueGrowth', 0),
            fundamentals.get("_source")
        )
        if growth:
            growth_pct = growth * 100
            if growth_pct >= 30:
                score += 10
            elif growth_pct >= 20:
                score += 8
            elif growth_pct >= 10:
                score += 5
            elif growth_pct >= 5:
                score += 3

        return min(score, 40)

    def _calc_market_position_score_yf(self, fundamentals: dict) -> float:
        """Calculate score from yfinance market position (0-30 points)"""
        if not fundamentals:
            return 15

        score = 0
        market_cap = self._to_float(fundamentals.get('marketCap', 0), 0.0)

        # Market cap tier (0-18 points)
        if market_cap >= 200_000_000_000:  # Mega cap ($200B+)
            score += 18
        elif market_cap >= 10_000_000_000:  # Large cap ($10B+)
            score += 15
        elif market_cap >= 2_000_000_000:  # Mid cap ($2B+)
            score += 11
        elif market_cap >= 300_000_000:  # Small cap ($300M+)
            score += 7
        else:
            score += 3

        # Beta bonus (stability) (0-12 points)
        beta = self._to_float(fundamentals.get('beta', 1), 1.0)
        if 0.8 <= beta <= 1.2:
            score += 12  # Stable
        elif 0.5 <= beta <= 1.5:
            score += 8
        else:
            score += 4

        return min(score, 30)

    def _generate_signals_yf(self, quote: dict, fundamentals: dict, recommendations: list) -> List[str]:
        """Generate signals from yfinance data"""
        signals = []

        # NOTE: Removed "Up/Down X% today" signals because they become stale
        # when picks are cached for multiple days. The price shown at pick time
        # may be very different from actual current price, making the signal misleading.

        # Analyst signals
        if recommendations:
            latest = recommendations[0]
            buy = latest.get('buy', 0) + latest.get('strongBuy', 0)
            total = buy + latest.get('hold', 0) + latest.get('sell', 0) + latest.get('strongSell', 0)
            if total > 0 and buy / total >= 0.7:
                signals.append("Strong Buy consensus")

        # Fundamental signals
        if fundamentals:
            roe = self._to_float(fundamentals.get('returnOnEquity', 0), 0.0)
            if roe >= 0.20:
                signals.append("High ROE")

            growth = self._normalize_growth_rate(
                fundamentals.get('revenueGrowth', 0),
                fundamentals.get("_source")
            )
            if growth >= 0.20:
                signals.append("Strong growth")

            # 52-week position
            high_52 = self._to_float(fundamentals.get('fiftyTwoWeekHigh', 0), 0.0)
            low_52 = self._to_float(fundamentals.get('fiftyTwoWeekLow', 0), 0.0)
            current = self._to_float(quote.get('c', 0), 0.0)
            if high_52 and low_52 and current:
                range_pct = (current - low_52) / (high_52 - low_52) if (high_52 - low_52) > 0 else 0.5
                if range_pct >= 0.9:
                    signals.append("Near 52-week high")
                elif range_pct <= 0.2:
                    signals.append("Near 52-week low")

        # Market cap signal
        if fundamentals:
            cap = self._to_float(fundamentals.get('marketCap', 0), 0.0)
            if cap >= 200_000_000_000:
                signals.append("Mega Cap")
            elif cap >= 10_000_000_000:
                signals.append("Large Cap")

        return signals[:5]

    def _determine_risk_yf(self, fundamentals: dict, score: float) -> str:
        """Determine risk level from yfinance fundamentals"""
        if not fundamentals:
            return "MEDIUM"

        # Check debt levels
        debt_equity = self._to_float(fundamentals.get('debtToEquity', 0), 0.0)
        beta = self._to_float(fundamentals.get('beta', 1), 1.0)

        if debt_equity > 200:  # High debt
            return "HIGH"
        if beta > 1.5:
            return "HIGH"
        if score < 40:
            return "HIGH"
        if score >= 70:
            return "LOW"
        return "MEDIUM"

    def _calc_technical_score(self, data: pd.DataFrame, timeframe: str = "swing") -> float:
        """Calculate technical analysis score from historical data (0-20 points)"""
        try:
            timeframe = self._normalize_timeframe(timeframe)
            score = 0
            current_price = data['Close'].iloc[-1]
            close_series = data['Close']
            volume_series = data['Volume']

            if timeframe == "day":
                sma_fast_period = 5
                sma_slow_period = 10
                rsi_window = 7
                volume_window = 10
                recent_volume_window = 3
            elif timeframe == "long":
                sma_fast_period = 50
                sma_slow_period = 200
                rsi_window = 21
                volume_window = 60
                recent_volume_window = 10
            else:
                sma_fast_period = 20
                sma_slow_period = 50
                rsi_window = 14
                volume_window = 20
                recent_volume_window = 5

            # Moving averages (0-8 points)
            if len(close_series) >= sma_fast_period:
                sma_fast = close_series.rolling(sma_fast_period).mean().iloc[-1]
            else:
                sma_fast = close_series.mean()
            if len(close_series) >= sma_slow_period:
                sma_slow = close_series.rolling(sma_slow_period).mean().iloc[-1]
            else:
                sma_slow = sma_fast

            if current_price > sma_fast:
                score += 4
            if current_price > sma_slow:
                score += 4

            # RSI (0-6 points)
            if len(close_series) >= rsi_window:
                delta = close_series.diff()
                gain = delta.where(delta > 0, 0).rolling(rsi_window).mean()
                loss = -delta.where(delta < 0, 0).rolling(rsi_window).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
            else:
                current_rsi = 50

            if 40 <= current_rsi <= 60:  # Neutral zone (best for entry)
                score += 6
            elif 30 <= current_rsi < 40 or 60 < current_rsi <= 70:
                score += 4

            # Volume (0-6 points)
            if len(volume_series) >= volume_window:
                avg_volume = volume_series.rolling(volume_window).mean().iloc[-1]
            else:
                avg_volume = volume_series.mean()
            recent_volume = volume_series.tail(recent_volume_window).mean()
            if recent_volume > avg_volume * 1.2:  # Volume surge
                score += 6
            elif recent_volume > avg_volume:
                score += 3

            return min(score, 20)
        except:
            return 0

    def _calc_momentum_score(self, data: pd.DataFrame, timeframe: str = "swing") -> float:
        """Calculate momentum score from historical data (0-10 points)"""
        try:
            timeframe = self._normalize_timeframe(timeframe)
            score = 0

            if timeframe == "day":
                lookback = 5
                thresholds = (0.06, 0.04, 0.02, 0)
                recent_window = 3
                recent_thresholds = (0.02, 0.01, 0)
            elif timeframe == "long":
                lookback = 90
                thresholds = (0.30, 0.20, 0.10, 0)
                recent_window = 20
                recent_thresholds = (0.015, 0.0075, 0)
            else:
                lookback = 20
                thresholds = (0.15, 0.10, 0.05, 0)
                recent_window = 5
                recent_thresholds = (0.02, 0.01, 0)

            if len(data) >= 2:
                effective_lookback = min(lookback, len(data) - 1)
                past_price = data['Close'].iloc[-effective_lookback]
                current_price = data['Close'].iloc[-1]
                if past_price and past_price > 0:
                    returns = (current_price - past_price) / past_price
                    if returns > thresholds[0]:
                        score += 6
                    elif returns > thresholds[1]:
                        score += 5
                    elif returns > thresholds[2]:
                        score += 3
                    elif returns > thresholds[3]:
                        score += 1

            effective_recent = min(recent_window, len(data) - 1)
            if effective_recent >= 2:
                recent_returns = data['Close'].pct_change(fill_method=None).tail(effective_recent).mean()
                if recent_returns > recent_thresholds[0]:
                    score += 4
                elif recent_returns > recent_thresholds[1]:
                    score += 2
                elif recent_returns > recent_thresholds[2]:
                    score += 1

            return min(score, 10)
        except:
            return 0

    def _generate_yf_reasoning(self, financial: float, market: float, technical: float, momentum: float) -> str:
        """Generate reasoning from yfinance-only analysis"""
        reasons = []

        if financial >= 30:
            reasons.append("excellent fundamentals")
        elif financial >= 20:
            reasons.append("solid financials")

        if market >= 20:
            reasons.append("strong market position")

        if technical >= 15:
            reasons.append("bullish technical setup")
        elif technical >= 10:
            reasons.append("favorable technicals")

        if momentum >= 7:
            reasons.append("strong momentum")
        elif momentum >= 4:
            reasons.append("positive momentum")

        if not reasons:
            return "Mixed signals - moderate opportunity"

        return "Institutional-grade pick: " + ", ".join(reasons)

    def _calc_recommendation_score(self, recommendations: list) -> float:
        """Calculate score from analyst recommendations (0-30 points)"""
        if not recommendations:
            return 15  # Neutral

        # Get most recent recommendation
        latest = recommendations[0] if recommendations else {}

        buy = latest.get('buy', 0) + latest.get('strongBuy', 0)
        hold = latest.get('hold', 0)
        sell = latest.get('sell', 0) + latest.get('strongSell', 0)
        total = buy + hold + sell

        if total == 0:
            return 15

        # Calculate buy ratio
        buy_ratio = buy / total

        if buy_ratio >= 0.8:
            return 30
        elif buy_ratio >= 0.6:
            return 25
        elif buy_ratio >= 0.4:
            return 18
        elif buy_ratio >= 0.2:
            return 12
        else:
            return 6

    def _calc_target_score(self, price_target: dict, current_price: float) -> Tuple[float, float]:
        """Calculate score from price target vs current price (0-25 points)
        NOTE: This method is kept for compatibility but price_target is PREMIUM
        """
        if not price_target or current_price == 0:
            return 12.5, 0

        target_mean = self._to_float(price_target.get('targetMean', 0), 0.0)
        target_high = self._to_float(price_target.get('targetHigh', 0), 0.0)

        if target_mean <= 0:
            return 12.5, 0

        # Calculate upside potential
        upside = ((target_mean - current_price) / current_price) * 100

        if upside >= 50:
            score = 25
        elif upside >= 30:
            score = 22
        elif upside >= 20:
            score = 18
        elif upside >= 10:
            score = 15
        elif upside >= 5:
            score = 12
        elif upside >= 0:
            score = 8
        else:
            score = 3  # Downside

        return score, target_mean

    def _calc_financial_score(self, financials: dict) -> float:
        """Calculate score from financial metrics (0-35 points)"""
        if not financials:
            return 17.5

        metrics = financials.get('metric', {})
        score = 0

        # P/E Ratio (0-10 points) - lower is better for value
        pe = self._to_float(metrics.get('peBasicExclExtraTTM', 0), 0.0)
        if pe:
            if 5 <= pe <= 15:
                score += 10
            elif 15 < pe <= 25:
                score += 8
            elif 25 < pe <= 40:
                score += 5
            elif pe > 40:
                score += 3

        # ROE - Return on Equity (0-8 points)
        roe = self._to_float(metrics.get('roeTTM', 0), 0.0)
        if roe:
            if roe >= 20:
                score += 8
            elif roe >= 15:
                score += 6
            elif roe >= 10:
                score += 4
            elif roe >= 5:
                score += 2

        # Profit Margin (0-8 points)
        margin = self._to_float(metrics.get('netProfitMarginTTM', 0), 0.0)
        if margin:
            if margin >= 20:
                score += 8
            elif margin >= 15:
                score += 6
            elif margin >= 10:
                score += 4
            elif margin >= 5:
                score += 2

        # Revenue Growth (0-9 points)
        growth = self._normalize_growth_rate(
            metrics.get('revenueGrowthQuarterlyYoy', 0),
            "finnhub"
        )
        if growth:
            growth_pct = growth * 100
            if growth_pct >= 30:
                score += 9
            elif growth_pct >= 20:
                score += 7
            elif growth_pct >= 10:
                score += 5
            elif growth_pct >= 5:
                score += 3

        return min(score, 35)

    def _calc_market_position_score(self, profile: dict) -> float:
        """Calculate score from market position (0-20 points)"""
        if not profile:
            return 10

        score = 0
        market_cap = self._to_float(profile.get('marketCapitalization', 0), 0.0)  # In millions

        # Market cap tier (0-12 points)
        if market_cap >= 200000:  # Mega cap ($200B+)
            score += 12
        elif market_cap >= 10000:  # Large cap ($10B+)
            score += 10
        elif market_cap >= 2000:  # Mid cap ($2B+)
            score += 7
        elif market_cap >= 300:  # Small cap ($300M+)
            score += 5
        else:
            score += 2

        # Listed on major exchange (0-8 points)
        exchange = profile.get('exchange', '')
        if 'NYSE' in exchange or 'NASDAQ' in exchange:
            score += 8
        elif exchange:
            score += 4

        return min(score, 20)

    def _calc_news_activity_score(self, ticker: str) -> float:
        """Calculate score from news activity (0-15 points)"""
        try:
            news = self.finnhub.get_company_news(ticker, days=7)

            if not news:
                return 7.5  # Neutral

            news_count = len(news)

            if news_count >= 20:
                return 15  # Very active
            elif news_count >= 10:
                return 12
            elif news_count >= 5:
                return 9
            elif news_count >= 2:
                return 6
            else:
                return 4

        except:
            return 7.5

    def _generate_free_reasoning(self, rec: float, target: float, fin: float, market: float, news: float) -> str:
        """Generate reasoning from free endpoint scores"""
        reasons = []

        if rec >= 20:
            reasons.append("strong analyst buy ratings")
        elif rec >= 15:
            reasons.append("positive analyst sentiment")

        if target >= 20:
            reasons.append("significant upside to price targets")
        elif target >= 15:
            reasons.append("good upside potential")

        if fin >= 20:
            reasons.append("excellent financials")
        elif fin >= 15:
            reasons.append("solid fundamentals")

        if market >= 12:
            reasons.append("established market position")

        if news >= 8:
            reasons.append("high news activity")

        if not reasons:
            return "Mixed signals, moderate opportunity"

        return "Opportunity with " + ", ".join(reasons)

    def _generate_free_signals(self, quote: dict, profile: dict, financials: dict, recommendations: list) -> List[str]:
        """Generate signals from free endpoints"""
        signals = []

        # NOTE: Removed "Up/Down X% today" signals because they become stale
        # when picks are cached. See _generate_signals_yf for details.

        # Analyst signals
        if recommendations:
            latest = recommendations[0]
            buy = latest.get('buy', 0) + latest.get('strongBuy', 0)
            total = buy + latest.get('hold', 0) + latest.get('sell', 0) + latest.get('strongSell', 0)
            if total > 0 and buy / total >= 0.7:
                signals.append("Strong Buy consensus")

        # Financial signals
        if financials:
            metrics = financials.get('metric', {})
            roe = self._to_float(metrics.get('roeTTM', 0), 0.0)
            if roe >= 20:
                signals.append("High ROE")

            growth = self._normalize_growth_rate(metrics.get('revenueGrowthQuarterlyYoy', 0), "finnhub")
            if growth * 100 >= 20:
                signals.append("Strong growth")

        # Market cap signal
        if profile:
            cap = self._to_float(profile.get('marketCapitalization', 0), 0.0)
            if cap >= 200000:
                signals.append("Mega Cap")
            elif cap >= 10000:
                signals.append("Large Cap")

        return signals[:5]

    def _determine_risk_free(self, financials: dict, score: float) -> str:
        """Determine risk level from financials"""
        if not financials:
            return "MEDIUM"

        metrics = financials.get('metric', {})

        # Check debt levels
        debt_equity = self._to_float(metrics.get('totalDebt/totalEquityQuarterly', 0), 0.0)
        beta = self._to_float(metrics.get('beta', 1), 1.0)

        if debt_equity > 2:
            return "HIGH"
        if beta > 1.5:
            return "HIGH"
        if score < 40:
            return "HIGH"
        if score >= 70:
            return "LOW"
        return "MEDIUM"

    def predict_stocks_by_sector(
        self,
        sector: Optional[str] = None,
        theme: Optional[str] = None,
        timeframe: str = "swing",
        limit: int = 10
    ) -> List[Dict]:
        """
        Predict top stocks filtered by sector and/or theme using FREE endpoints

        Args:
            sector: Sector filter (tech, energy, healthcare, finance, consumer)
            theme: Theme filter (growth, value, esg)
            timeframe: Trading timeframe (day, swing, long)
            limit: Number of stocks to return

        Returns:
            List of top stocks matching filters with scores and analysis
        """
        timeframe = self._normalize_timeframe(timeframe)
        logger.info(f"Predicting stocks - Sector: {sector}, Theme: {theme}, Timeframe: {timeframe}")

        # Get tickers by sector from stock universe
        if sector and sector.lower() in ["tech", "energy", "healthcare", "finance", "consumer"]:
            tickers = get_stocks_by_sector(sector.lower())
        else:
            tickers = get_all_stocks()

        # Filter by ESG theme (preferred tickers)
        if theme and theme.lower() == "esg" and "preferred_tickers" in self.THEMES["esg"]:
            tickers = [t for t in tickers if t in self.THEMES["esg"]["preferred_tickers"]]

        max_universe = settings.SECTOR_PICKS_UNIVERSE_LIMIT
        if max_universe and max_universe < len(tickers):
            seed = datetime.utcnow().strftime("%Y-%m-%d")
            rng = random.Random(seed)
            tickers = rng.sample(tickers, max_universe)
            logger.info("Sector picks universe limit applied: %s/%s tickers", len(tickers), len(get_all_stocks()))

        stocks_with_scores = []
        period = self._get_timeframe_period(timeframe)
        batch_data = self.yfinance.get_multiple_stocks(tickers, period=period)
        scanned = 0
        no_data = 0

        for ticker in tickers:
            scanned += 1
            try:
                historical_data = batch_data.get(ticker)
                if historical_data is None or historical_data.empty:
                    no_data += 1
                    continue
                score_data = self.calculate_strength_score_free(
                    ticker,
                    historical_data,
                    use_fundamentals=False,
                    timeframe=timeframe
                )

                if score_data and score_data["total_score"] > 0:
                    current_price = score_data.get("current_price", 0)
                    target_price = score_data.get("target_price", current_price)
                    target_price, potential_return = self._apply_target_guardrails(
                        current_price,
                        target_price,
                        None,
                        timeframe
                    )

                    stocks_with_scores.append({
                        "ticker": ticker,
                        "sector": score_data.get("sector", sector or "Unknown"),
                        "theme": theme if theme else "general",
                        "score": score_data["total_score"],
                        "currentPrice": float(current_price),
                        "targetPrice": float(target_price),
                        "potentialReturn": float(potential_return),
                        "confidence": int(score_data["total_score"]),
                        "timeHorizon": timeframe.upper(),
                        "reasoning": score_data["reasoning"],
                        "signals": score_data["signals"],
                        "riskLevel": score_data["risk_level"],
                        "breakdown": score_data["breakdown"],
                        "company": score_data.get("company_name", ticker)
                    })

            except Exception as e:
                logger.error(f"Error analyzing {ticker}: {str(e)}")
                continue

        # Sort by score and enrich top candidates with fundamentals + news
        stocks_with_scores.sort(key=lambda x: x["score"], reverse=True)
        enrich_limit = settings.AI_PICKS_ENRICH_LIMIT
        if enrich_limit <= 0:
            candidate_count = len(stocks_with_scores)
        else:
            candidate_count = min(len(stocks_with_scores), min(max(limit * 5, 30), enrich_limit))
        if candidate_count > 0:
            self._upgrade_scores_with_fundamentals(
                stocks_with_scores,
                batch_data,
                candidate_count,
                timeframe
            )
            stocks_with_scores.sort(key=lambda x: x["score"], reverse=True)
            self._apply_news_overlay(stocks_with_scores, candidate_count)
            stocks_with_scores.sort(key=lambda x: x["score"], reverse=True)

        # Add ranks
        for i, stock in enumerate(stocks_with_scores[:limit], 1):
            stock["rank"] = i

        logger.info(
            "Sector picks scan: %s tickers (%s no data), %s scored (sector=%s, theme=%s)",
            scanned,
            no_data,
            len(stocks_with_scores),
            sector,
            theme
        )
        return stocks_with_scores[:limit]

    def calculate_strength_score(
        self,
        ticker: str,
        data: Optional[pd.DataFrame] = None
    ) -> Optional[Dict]:
        """
        Calculate comprehensive strength score (0-100)

        Enhanced Breakdown:
        - Technical Analysis: 20 points
        - Momentum: 20 points
        - Volume: 15 points
        - Trend: 15 points
        - ML Prediction: 15 points (NEW - XGBoost model)
        - Social Sentiment: 10 points (NEW - Reddit)
        - News Impact: 5 points (NEW - NewsAPI)

        Args:
            ticker: Stock ticker symbol
            data: Optional pre-loaded data

        Returns:
            Dictionary with score and analysis
        """
        try:
            # Get data if not provided
            if data is None:
                data = self.get_stock_data(ticker)
                if data is None:
                    return None

            # Calculate traditional indicators
            technical_score = self._calculate_technical_score(data) * 0.67  # Scale 30 -> 20
            momentum_score = self._calculate_momentum_score(data) * 0.67   # Scale 30 -> 20
            volume_score = self._calculate_volume_score(data) * 0.75       # Scale 20 -> 15
            trend_score = self._calculate_trend_score(data) * 0.75          # Scale 20 -> 15

            # NEW: ML Prediction Score (15 points)
            ml_score = self._calculate_ml_score(ticker)

            # NEW: Social Sentiment Score (10 points)
            sentiment_score = self._calculate_social_sentiment_score(ticker)

            # NEW: News Impact Score (5 points)
            news_score = self._calculate_news_impact_score(ticker)

            total_score = (
                technical_score +
                momentum_score +
                volume_score +
                trend_score +
                ml_score +
                sentiment_score +
                news_score
            )

            # Generate reasoning
            reasoning = self._generate_reasoning(
                technical_score, momentum_score, volume_score, trend_score,
                ml_score, sentiment_score, news_score
            )

            # Generate signals
            signals = self._generate_signals(data, ticker)

            # Determine risk level
            risk_level = self._determine_risk_level(data, total_score)

            return {
                "total_score": round(total_score, 2),
                "breakdown": {
                    "technical": round(technical_score, 2),
                    "momentum": round(momentum_score, 2),
                    "volume": round(volume_score, 2),
                    "trend": round(trend_score, 2),
                    "ml_prediction": round(ml_score, 2),
                    "social_sentiment": round(sentiment_score, 2),
                    "news_impact": round(news_score, 2)
                },
                "reasoning": reasoning,
                "signals": signals,
                "risk_level": risk_level
            }

        except Exception as e:
            logger.error(f"Error calculating score for {ticker}: {str(e)}")
            return None

    def get_stock_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """
        Fetch stock data from Finnhub

        Args:
            ticker: Stock ticker symbol

        Returns:
            DataFrame with OHLCV data and indicators
        """
        try:
            # Rate limiting: wait 0.2 seconds between requests
            time.sleep(0.2)

            # Get candles from Finnhub
            candles = self.finnhub.get_stock_candles(ticker, 'D', self.lookback_days)

            if not candles or candles.get('s') != 'ok':
                logger.warning(f"No data found for {ticker}")
                return None

            # Convert to DataFrame
            data = pd.DataFrame({
                'Open': candles['o'],
                'High': candles['h'],
                'Low': candles['l'],
                'Close': candles['c'],
                'Volume': candles['v']
            }, index=pd.to_datetime(candles['t'], unit='s'))

            if data.empty:
                logger.warning(f"No data found for {ticker}")
                return None

            # Calculate technical indicators
            data = self._add_technical_indicators(data)

            return data

        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {str(e)}")
            return None

    def get_fundamentals(self, ticker: str) -> Dict:
        """
        Fetch fundamental data for a stock using Finnhub

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with fundamental metrics
        """
        try:
            # Rate limiting
            time.sleep(0.2)

            profile = self.finnhub.get_company_profile(ticker)
            financials = self.finnhub.get_basic_financials(ticker)

            metrics = financials.get('metric', {}) if financials else {}

            return {
                "marketCap": (profile.get('marketCapitalization', 0) * 1000000) if profile else None,
                "peRatio": metrics.get('peBasicExclExtraTTM'),
                "forwardPE": metrics.get('peTTM'),
                "dividendYield": metrics.get('dividendYieldIndicatedAnnual'),
                "eps": metrics.get('epsBasicExclExtraItemsTTM'),
                "beta": metrics.get('beta'),
                "revenue": metrics.get('revenuePerShareTTM'),
                "profitMargin": metrics.get('netProfitMarginTTM'),
                "debtToEquity": metrics.get('totalDebt/totalEquityQuarterly'),
                "roe": metrics.get('roeTTM'),
                "bookValue": metrics.get('bookValuePerShareQuarterly'),
                "priceToBook": metrics.get('pbQuarterly'),
                "revenueGrowth": metrics.get('revenueGrowthQuarterlyYoy'),
                "earningsGrowth": metrics.get('epsGrowthQuarterlyYoy')
            }

        except Exception as e:
            logger.error(f"Error fetching fundamentals for {ticker}: {str(e)}")
            return {}

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _add_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to dataframe"""

        # Moving Averages
        data['SMA_20'] = data['Close'].rolling(window=20).mean()
        data['SMA_50'] = data['Close'].rolling(window=50).mean()
        data['SMA_200'] = data['Close'].rolling(window=200).mean()
        data['EMA_12'] = data['Close'].ewm(span=12, adjust=False).mean()
        data['EMA_26'] = data['Close'].ewm(span=26, adjust=False).mean()

        # RSI (Relative Strength Index)
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))

        # MACD
        data['MACD'] = data['EMA_12'] - data['EMA_26']
        data['MACD_Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
        data['MACD_Hist'] = data['MACD'] - data['MACD_Signal']

        # Bollinger Bands
        data['BB_Middle'] = data['Close'].rolling(window=20).mean()
        bb_std = data['Close'].rolling(window=20).std()
        data['BB_Upper'] = data['BB_Middle'] + (bb_std * 2)
        data['BB_Lower'] = data['BB_Middle'] - (bb_std * 2)

        # Volume indicators
        data['Volume_SMA'] = data['Volume'].rolling(window=20).mean()
        data['Volume_Ratio'] = data['Volume'] / data['Volume_SMA']

        # Price momentum
        data['Returns'] = data['Close'].pct_change()
        data['Returns_20'] = data['Close'].pct_change(20)

        return data

    def _calculate_technical_score(self, data: pd.DataFrame) -> float:
        """Calculate technical analysis score (0-30 points)"""
        score = 0.0
        current_price = data['Close'].iloc[-1]

        # Moving Average signals (10 points)
        if not pd.isna(data['SMA_20'].iloc[-1]):
            if current_price > data['SMA_20'].iloc[-1]:
                score += 3
            if current_price > data['SMA_50'].iloc[-1]:
                score += 3
            if current_price > data['SMA_200'].iloc[-1]:
                score += 4

        # RSI (10 points)
        if not pd.isna(data['RSI'].iloc[-1]):
            rsi = data['RSI'].iloc[-1]
            if 40 <= rsi <= 60:  # Neutral/healthy
                score += 10
            elif 30 <= rsi < 40:  # Slight oversold (good buy)
                score += 8
            elif 60 < rsi <= 70:  # Slight overbought (momentum)
                score += 7
            elif rsi < 30:  # Oversold
                score += 5
            elif rsi > 70:  # Overbought
                score += 3

        # MACD (10 points)
        if not pd.isna(data['MACD'].iloc[-1]) and not pd.isna(data['MACD_Signal'].iloc[-1]):
            macd = data['MACD'].iloc[-1]
            signal = data['MACD_Signal'].iloc[-1]
            hist = data['MACD_Hist'].iloc[-1]

            if macd > signal and hist > 0:  # Bullish
                score += 10
            elif macd > signal:  # Turning bullish
                score += 7
            elif macd < signal and hist < 0:  # Bearish
                score += 3

        return min(score, 30)

    def _calculate_momentum_score(self, data: pd.DataFrame) -> float:
        """Calculate momentum score (0-30 points)"""
        score = 0.0

        # Price momentum (15 points)
        if not pd.isna(data['Returns_20'].iloc[-1]):
            returns_20 = data['Returns_20'].iloc[-1]
            if returns_20 > 0.15:  # Strong uptrend
                score += 15
            elif returns_20 > 0.10:
                score += 12
            elif returns_20 > 0.05:
                score += 9
            elif returns_20 > 0:
                score += 6
            else:
                score += 3

        # Recent momentum (15 points)
        recent_returns = data['Returns'].tail(5).mean()
        if recent_returns > 0.02:  # Strong recent momentum
            score += 15
        elif recent_returns > 0.01:
            score += 12
        elif recent_returns > 0:
            score += 8
        else:
            score += 4

        return min(score, 30)

    def _calculate_volume_score(self, data: pd.DataFrame) -> float:
        """Calculate volume score (0-20 points)"""
        score = 0.0

        if not pd.isna(data['Volume_Ratio'].iloc[-1]):
            volume_ratio = data['Volume_Ratio'].iloc[-1]

            # Unusual volume is a strong signal
            if volume_ratio > 2.0:  # Very high volume
                score += 20
            elif volume_ratio > 1.5:
                score += 16
            elif volume_ratio > 1.2:
                score += 12
            elif volume_ratio > 1.0:
                score += 8
            else:
                score += 5

        return min(score, 20)

    def _calculate_trend_score(self, data: pd.DataFrame) -> float:
        """Calculate trend score (0-20 points)"""
        score = 0.0

        # Check if in uptrend (10 points)
        if (not pd.isna(data['SMA_20'].iloc[-1]) and
            not pd.isna(data['SMA_50'].iloc[-1])):

            sma_20 = data['SMA_20'].iloc[-1]
            sma_50 = data['SMA_50'].iloc[-1]

            if sma_20 > sma_50:  # Golden cross territory
                score += 10

        # Check trend strength (10 points)
        recent_highs = data['High'].tail(20)
        recent_lows = data['Low'].tail(20)

        if recent_highs.is_monotonic_increasing:  # Consistent higher highs
            score += 10
        elif recent_highs.iloc[-1] > recent_highs.iloc[0]:
            score += 7
        else:
            score += 3

        return min(score, 20)

    def _calculate_ml_score(self, ticker: str) -> float:
        """Calculate ML prediction score (0-15 points)"""
        try:
            prediction_result = self.ml_predictor.predict_stock(ticker)

            if not prediction_result:
                return 7.5  # Neutral score if prediction fails

            # ML prediction is probability 0-1, scale to 0-15
            prediction_prob = prediction_result.get('prediction', 0.5)
            ml_score = prediction_prob * 15

            logger.info(f"{ticker} ML prediction: {prediction_prob:.3f} -> {ml_score:.2f}/15 points")
            return ml_score

        except Exception as e:
            logger.error(f"Error calculating ML score for {ticker}: {str(e)}")
            return 7.5  # Neutral on error

    def _calculate_social_sentiment_score(self, ticker: str) -> float:
        """Calculate social sentiment score (0-10 points)"""
        try:
            # Get trending stocks from Reddit
            trending = self.reddit.get_trending_stocks(limit=50, hours=24)

            score = 5.0  # Neutral baseline

            for stock in trending:
                if stock['ticker'] == ticker:
                    # Mention volume score (0-5 points)
                    mentions = stock['mentions']
                    if mentions > 30:
                        score += 3
                    elif mentions > 20:
                        score += 2.5
                    elif mentions > 10:
                        score += 2
                    elif mentions > 5:
                        score += 1
                    else:
                        score += 0.5

                    # Sentiment score (0-5 points based on label)
                    sentiment = stock.get('sentiment', 'NEUTRAL')
                    if sentiment == 'VERY_BULLISH':
                        score += 3
                    elif sentiment == 'BULLISH':
                        score += 2
                    elif sentiment == 'SLIGHTLY_BULLISH':
                        score += 1
                    elif sentiment == 'SLIGHTLY_BEARISH':
                        score -= 1
                    elif sentiment == 'BEARISH':
                        score -= 2
                    elif sentiment == 'VERY_BEARISH':
                        score -= 3

                    logger.info(f"{ticker} Reddit: {mentions} mentions, {sentiment} -> {score:.2f}/10 points")
                    break

            return max(0, min(10, score))

        except Exception as e:
            logger.error(f"Error calculating sentiment score for {ticker}: {str(e)}")
            return 5.0  # Neutral on error

    def _calculate_news_impact_score(self, ticker: str) -> float:
        """Calculate news impact score (0-5 points)"""
        try:
            score = 2.5  # Neutral baseline

            # Check for news bombs (high-impact events)
            news_bombs = self.news.get_news_bombs(limit=20)
            has_bomb = False

            for bomb in news_bombs:
                if ticker.upper() in bomb.get('title', '').upper() or \
                   ticker.upper() in bomb.get('description', '').upper():
                    score += 2.0  # Major boost for news bomb
                    has_bomb = True
                    logger.info(f"{ticker} NEWS BOMB: {bomb.get('title', '')[:50]}...")
                    break

            # Check company-specific news volume
            if not has_bomb:
                company_news = self.news.get_stock_news(ticker, days=3)
                news_count = len(company_news)

                if news_count > 5:
                    score += 0.5
                elif news_count > 3:
                    score += 0.3

            logger.info(f"{ticker} News impact: {score:.2f}/5 points")
            return max(0, min(5, score))

        except Exception as e:
            logger.error(f"Error calculating news score for {ticker}: {str(e)}")
            return 2.5  # Neutral on error

    def _generate_reasoning(
        self,
        technical: float,
        momentum: float,
        volume: float,
        trend: float,
        ml_score: float = 0,
        sentiment_score: float = 0,
        news_score: float = 0
    ) -> str:
        """Generate human-readable reasoning"""
        reasons = []

        # Technical (20 points)
        if technical >= 15:
            reasons.append("strong technical indicators")
        elif technical >= 12:
            reasons.append("favorable technical setup")

        # Momentum (20 points)
        if momentum >= 15:
            reasons.append("excellent momentum")
        elif momentum >= 12:
            reasons.append("positive momentum")

        # Volume (15 points)
        if volume >= 12:
            reasons.append("unusual volume surge")
        elif volume >= 9:
            reasons.append("above-average volume")

        # Trend (15 points)
        if trend >= 12:
            reasons.append("clear uptrend")
        elif trend >= 9:
            reasons.append("positive trend")

        # ML Prediction (15 points)
        if ml_score >= 12:
            reasons.append("AI predicts strong 10%+ weekly gain")
        elif ml_score >= 10:
            reasons.append("AI predicts good upside potential")

        # Social Sentiment (10 points)
        if sentiment_score >= 8:
            reasons.append("viral on Reddit with bullish sentiment")
        elif sentiment_score >= 7:
            reasons.append("trending on social media")

        # News Impact (5 points)
        if news_score >= 4:
            reasons.append("breaking high-impact news")
        elif news_score >= 3.5:
            reasons.append("recent positive news coverage")

        if not reasons:
            return "Mixed signals, moderate opportunity"

        return "Strong opportunity with " + ", ".join(reasons)

    def _generate_signals(self, data: pd.DataFrame, ticker: str) -> List[str]:
        """Generate list of trading signals"""
        signals = []

        current_price = data['Close'].iloc[-1]

        # MA signals
        if not pd.isna(data['SMA_20'].iloc[-1]) and current_price > data['SMA_20'].iloc[-1]:
            signals.append("Above SMA 20")

        if not pd.isna(data['SMA_50'].iloc[-1]) and current_price > data['SMA_50'].iloc[-1]:
            signals.append("Above SMA 50")

        # RSI signals
        if not pd.isna(data['RSI'].iloc[-1]):
            rsi = data['RSI'].iloc[-1]
            if rsi < 30:
                signals.append("RSI Oversold")
            elif rsi > 70:
                signals.append("RSI Overbought")
            elif 40 <= rsi <= 60:
                signals.append("RSI Neutral")

        # MACD signals
        if (not pd.isna(data['MACD'].iloc[-1]) and
            not pd.isna(data['MACD_Signal'].iloc[-1])):
            if data['MACD'].iloc[-1] > data['MACD_Signal'].iloc[-1]:
                signals.append("MACD Bullish")

        # Volume signals
        if not pd.isna(data['Volume_Ratio'].iloc[-1]):
            if data['Volume_Ratio'].iloc[-1] > 1.5:
                signals.append("High Volume")

        # NEW: Social signals
        try:
            trending = self.reddit.get_trending_stocks(limit=30, hours=24)
            for stock in trending:
                if stock['ticker'] == ticker:
                    if stock.get('spike', False):
                        signals.append(f"Reddit Spike ({stock['mentions']} mentions)")
                    elif stock.get('trending', False):
                        signals.append(f"Trending on WSB")
                    break
        except:
            pass

        # NEW: News signals
        try:
            news_bombs = self.news.get_news_bombs(limit=10)
            for bomb in news_bombs:
                if ticker.upper() in bomb.get('title', '').upper():
                    signals.append("Breaking news")
                    break
        except:
            pass

        return signals[:5]  # Return top 5 signals

    def _determine_risk_level(self, data: pd.DataFrame, score: float) -> str:
        """Determine risk level based on volatility and score"""

        # Calculate volatility
        returns = data['Returns'].tail(20)
        volatility = returns.std()

        if volatility > 0.05:  # High volatility
            return "HIGH"
        elif volatility > 0.03:
            return "MEDIUM"
        else:
            return "LOW"


class CryptoPredictor:
    """
    AI-powered crypto predictor using technical analysis

    Similar to StockPredictor but optimized for crypto markets:
    - 24/7 trading consideration
    - Higher volatility tolerance
    - Crypto-specific indicators
    """

    def __init__(self):
        self.lookback_days = 90

    def predict_top_crypto(
        self,
        timeframe: str = "swing",
        limit: int = 10
    ) -> List[Dict]:
        """
        Predict top cryptocurrencies

        Args:
            timeframe: Trading timeframe (day, swing, long)
            limit: Number of cryptos to return

        Returns:
            List of top cryptos with scores and analysis
        """
        logger.info(f"Predicting top {limit} cryptos for {timeframe} timeframe")

        # Popular crypto symbols (in USD pairs)
        symbols = [
            "BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "ADA-USD",
            "DOGE-USD", "MATIC-USD", "DOT-USD", "AVAX-USD", "LINK-USD",
            "UNI-USD", "ATOM-USD", "LTC-USD", "XRP-USD", "TRX-USD"
        ]

        cryptos_with_scores = []

        for symbol in symbols:
            try:
                logger.info(f"Analyzing {symbol}...")

                # Get crypto data
                data = self.get_crypto_data(symbol)
                if data is None or len(data) < 20:
                    continue

                # Calculate strength score
                score_data = self.calculate_strength_score(symbol, data)

                if score_data:
                    current_price = data['Close'].iloc[-1]
                    ticker = symbol.replace("-USD", "")

                    # Calculate target price (crypto has higher potential)
                    multiplier = {
                        "day": 1.05,      # 5% for day trading
                        "swing": 1.20,    # 20% for swing
                        "long": 1.50      # 50% for long term
                    }.get(timeframe, 1.20)

                    target_price = current_price * multiplier
                    potential_return = ((target_price - current_price) / current_price) * 100

                    cryptos_with_scores.append({
                        "symbol": ticker,
                        "score": score_data["total_score"],
                        "currentPrice": float(current_price),
                        "targetPrice": float(target_price),
                        "potentialReturn": float(potential_return),
                        "confidence": int(score_data["total_score"]),
                        "timeHorizon": timeframe.upper(),
                        "reasoning": score_data["reasoning"],
                        "signals": score_data["signals"],
                        "riskLevel": score_data["risk_level"],
                        "breakdown": score_data["breakdown"]
                    })

            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {str(e)}")
                continue

        # Sort by score
        cryptos_with_scores.sort(key=lambda x: x["score"], reverse=True)

        # Add ranks
        for i, crypto in enumerate(cryptos_with_scores[:limit], 1):
            crypto["rank"] = i

        logger.info(f"Successfully analyzed {len(cryptos_with_scores)} cryptos")
        return cryptos_with_scores[:limit]

    def calculate_strength_score(
        self,
        symbol: str,
        data: Optional[pd.DataFrame] = None
    ) -> Optional[Dict]:
        """
        Calculate crypto strength score (0-100)

        Uses same methodology as stocks but with crypto adjustments
        """
        # Reuse StockPredictor logic
        predictor = StockPredictor()
        predictor.lookback_days = self.lookback_days

        return predictor.calculate_strength_score(symbol, data)

    def get_crypto_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Fetch crypto data (using mock data since Finnhub free tier doesn't support crypto)

        Args:
            symbol: Crypto symbol (e.g., BTC-USD)

        Returns:
            DataFrame with OHLCV data and indicators
        """
        try:
            # Generate mock crypto data for now
            # In production, would use a crypto-specific API
            import random

            dates = pd.date_range(end=datetime.now(), periods=90, freq='D')
            base_prices = {
                'BTC-USD': 45000, 'ETH-USD': 2500, 'BNB-USD': 300,
                'SOL-USD': 100, 'ADA-USD': 0.5, 'DOGE-USD': 0.08,
                'MATIC-USD': 0.8, 'DOT-USD': 7, 'AVAX-USD': 35,
                'LINK-USD': 15, 'UNI-USD': 6, 'ATOM-USD': 9,
                'LTC-USD': 70, 'XRP-USD': 0.5, 'TRX-USD': 0.1
            }

            base_price = base_prices.get(symbol, 100)
            prices = [base_price * (1 + random.uniform(-0.02, 0.03)) for _ in range(90)]

            # Create cumulative trend
            for i in range(1, len(prices)):
                prices[i] = prices[i-1] * (1 + random.uniform(-0.03, 0.035))

            data = pd.DataFrame({
                'Open': [p * (1 + random.uniform(-0.01, 0.01)) for p in prices],
                'High': [p * (1 + random.uniform(0, 0.02)) for p in prices],
                'Low': [p * (1 - random.uniform(0, 0.02)) for p in prices],
                'Close': prices,
                'Volume': [random.randint(1000000, 10000000) for _ in range(90)]
            }, index=dates)

            if data.empty:
                logger.warning(f"No data found for {symbol}")
                return None

            # Add technical indicators
            predictor = StockPredictor()
            data = predictor._add_technical_indicators(data)

            return data

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None


# ============================================================================
# Convenience Functions
# ============================================================================

def get_stock_predictions(timeframe: str = "swing", limit: int = 10) -> List[Dict]:
    """
    Get stock predictions

    Args:
        timeframe: Trading timeframe
        limit: Number of stocks

    Returns:
        List of top stock predictions
    """
    predictor = StockPredictor()
    return predictor.predict_top_stocks(timeframe, limit)


def get_crypto_predictions(timeframe: str = "swing", limit: int = 10) -> List[Dict]:
    """
    Get crypto predictions

    Args:
        timeframe: Trading timeframe
        limit: Number of cryptos

    Returns:
        List of top crypto predictions
    """
    predictor = CryptoPredictor()
    return predictor.predict_top_crypto(timeframe, limit)


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Test stock predictions
    print("=== Stock Predictions ===")
    stock_predictor = StockPredictor()
    stocks = stock_predictor.predict_top_stocks("swing", 5)

    for stock in stocks:
        print(f"\n{stock['rank']}. {stock['ticker']}")
        print(f"   Score: {stock['score']}/100")
        print(f"   Price: ${stock['currentPrice']:.2f} -> ${stock['targetPrice']:.2f}")
        print(f"   Return: +{stock['potentialReturn']:.2f}%")
        print(f"   Reasoning: {stock['reasoning']}")
        print(f"   Signals: {', '.join(stock['signals'])}")

    # Test crypto predictions
    print("\n\n=== Crypto Predictions ===")
    crypto_predictor = CryptoPredictor()
    cryptos = crypto_predictor.predict_top_crypto("swing", 5)

    for crypto in cryptos:
        print(f"\n{crypto['rank']}. {crypto['symbol']}")
        print(f"   Score: {crypto['score']}/100")
        print(f"   Price: ${crypto['currentPrice']:.2f} -> ${crypto['targetPrice']:.2f}")
        print(f"   Return: +{crypto['potentialReturn']:.2f}%")
        print(f"   Reasoning: {crypto['reasoning']}")
        print(f"   Signals: {', '.join(crypto['signals'])}")

    def _calculate_rsi(self, data: pd.DataFrame) -> float:
        """Calculate current RSI value"""
        try:
            if data is None or len(data) < 14:
                return 50
            
            delta = data['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50
        except:
            return 50

    def _get_bullish_factors(self, fundamentals: dict, data: pd.DataFrame) -> List[str]:
        """Get list of bullish factors"""
        factors = []
        
        if fundamentals:
            # Growth
            if fundamentals.get('revenueGrowth', 0) > 0.15:
                factors.append("Strong revenue growth (>15%)")
            
            # Profitability
            margin = fundamentals.get('profitMargins', 0)
            if margin and margin > 0.15:
                factors.append(f"High profit margin ({margin*100:.1f}%)")
            
            # ROE
            roe = fundamentals.get('returnOnEquity', 0)
            if roe and roe > 0.15:
                factors.append(f"Strong ROE ({roe*100:.1f}%)")
            
            # Low debt
            debt = fundamentals.get('debtToEquity', 0)
            if debt and debt < 100:
                factors.append("Low debt levels")
        
        if data is not None and len(data) >= 50:
            current = data['Close'].iloc[-1]
            sma_50 = data['Close'].rolling(50).mean().iloc[-1]
            
            if current > sma_50:
                factors.append("Trading above 50-day MA")
        
        return factors

    def _get_bearish_factors(self, fundamentals: dict, data: pd.DataFrame) -> List[str]:
        """Get list of bearish factors"""
        factors = []
        
        if fundamentals:
            # High valuation
            pe = fundamentals.get('peRatio', 0)
            if pe and pe > 35:
                factors.append(f"High P/E ratio ({pe:.1f})")
            
            # Declining growth
            growth = fundamentals.get('revenueGrowth', 0)
            if growth and growth < 0:
                factors.append("Declining revenue")
            
            # High debt
            debt = fundamentals.get('debtToEquity', 0)
            if debt and debt > 200:
                factors.append(f"High debt ({debt:.0f}% D/E)")
        
        if data is not None and len(data) >= 50:
            current = data['Close'].iloc[-1]
            sma_50 = data['Close'].rolling(50).mean().iloc[-1]
            
            if current < sma_50:
                factors.append("Trading below 50-day MA")
        
        return factors

    def _generate_recommendation(self, fundamentals: dict, data: pd.DataFrame) -> str:
        """Generate buy/hold/sell recommendation"""
        bullish = len(self._get_bullish_factors(fundamentals, data))
        bearish = len(self._get_bearish_factors(fundamentals, data))
        
        if bullish > bearish + 1:
            return "Buy"
        elif bearish > bullish + 1:
            return "Sell"
        else:
            return "Hold"
