"""
TradeMaster Pro - Enhanced AI Predictor
=========================================

Advanced stock prediction with hidden gem detection, dark horse picks,
and smart money tracking. This system finds stocks others miss.

Key Features:
- Dark Horse Detection (low cap, high potential)
- Volume Surge Analysis
- Smart Money Tracking (institutional changes)
- Earnings Momentum
- Quick Wins for Day Trading
- Hidden Gems Finder

Data Sources:
- yfinance: Price data, historical data, basic fundamentals (rate limits possible)
- Finnhub: Analyst recommendations ONLY (60/min rate limit)

OPTIMIZATION: Use yfinance for bulk data, Finnhub sparingly for recommendations
"""

import pandas as pd
import numpy as np
import math
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
import time
import random

from .finnhub_service import get_finnhub_service
from .yfinance_service import get_yfinance_service
from .insider_trading_service import get_insider_service
from .short_interest_service import get_short_service
from .options_flow_service import get_options_service
from .earnings_service import get_earnings_service
from .enhanced_news_service import get_enhanced_news_service
from .stock_universe import get_all_stocks, get_core_index_tickers
from .delisted_registry import get_delisted_tickers
from app.config.settings import settings

logger = logging.getLogger(__name__)


class EnhancedStockPredictor:
    """
    Enhanced AI predictor that finds hidden gems and dark horse stocks

    Scoring System (0-270 points):
    Base Scoring (100 points):
    - Technical Analysis: 30 points
    - Momentum: 30 points
    - Volume Analysis: 25 points
    - Trend: 15 points

    Bonus Scoring (170 points):
    - Hidden Gem Bonus: 20 points
    - Smart Money Bonus: 15 points
    - Quick Win Bonus: 15 points
    - Insider Trading Bonus: 20 points
    - Short Interest Bonus: 20 points
    - Options Flow Bonus: 20 points
    - Earnings Calendar Bonus: 20 points
    - News Sentiment Bonus: 20 points (NEW!)
    - Social Media Buzz Bonus: 20 points (NEW!)
    """

    def __init__(self):
        self.lookback_days = 90
        self.finnhub = get_finnhub_service()
        self.yfinance = get_yfinance_service()  # Batch-friendly historical data
        all_tickers = get_all_stocks()
        self.ticker_universe = self._filter_ticker_universe(all_tickers)
        max_universe = settings.UNIVERSE_TICKER_LIMIT
        if max_universe and max_universe < len(self.ticker_universe):
            seed = datetime.utcnow().strftime("%Y-%m-%d")
            rng = random.Random(seed)
            core_tickers = set(get_core_index_tickers())
            core_in_universe = [ticker for ticker in self.ticker_universe if ticker in core_tickers]
            remaining = [ticker for ticker in self.ticker_universe if ticker not in core_tickers]
            if max_universe <= len(core_in_universe):
                logger.warning(
                    "Universe limit %s below core index size %s; keeping core only",
                    max_universe,
                    len(core_in_universe),
                )
                self.ticker_universe = core_in_universe
            else:
                sampled = rng.sample(remaining, max_universe - len(core_in_universe))
                self.ticker_universe = core_in_universe + sampled
        logger.info(
            "Ticker universe filtered: %s tradeable out of %s",
            len(self.ticker_universe),
            len(all_tickers)
        )

        # NEW: Advanced data services
        self.insider = get_insider_service()
        self.short_interest = get_short_service()
        self.options = get_options_service()
        self.earnings = get_earnings_service()
        self.news = get_enhanced_news_service()  # News analysis

    def _filter_ticker_universe(self, tickers: List[str]) -> List[str]:
        return [ticker for ticker in tickers if self._is_probably_tradeable_symbol(ticker)]

    def _is_probably_tradeable_symbol(self, ticker: str) -> bool:
        if not ticker:
            return False
        if any(ch in ticker for ch in ('.', '^', '/', '=')):
            return False
        return True

    def _prepare_stock_data(self, data: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
        if data is None or data.empty or len(data) < 20:
            return None
        data = data.copy()
        return self._add_technical_indicators(data)

    def _apply_score_gate(
        self,
        items: List[Dict],
        limit: int,
        percentile: float,
        min_score: float
    ) -> List[Dict]:
        if not items:
            return items
        scores = sorted((item.get("score", 0) for item in items), reverse=True)
        cutoff_index = max(limit, int(len(scores) * percentile)) - 1
        cutoff_index = max(0, min(cutoff_index, len(scores) - 1))
        cutoff_score = scores[cutoff_index]
        cutoff = max(cutoff_score, min_score)
        filtered = [item for item in items if item.get("score", 0) >= cutoff]
        if len(filtered) < min(limit, 3):
            return items
        return filtered

    def _to_float(self, value: object, default: float = 0.0) -> float:
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

    def _normalize_growth_rate(self, value: object, default: float = 0.0) -> float:
        growth = self._to_float(value, default)
        if pd.isna(growth):
            return default
        if abs(growth) > 5:
            growth = growth / 100.0
        if growth > 2.0:
            return 2.0
        if growth < -0.5:
            return -0.5
        return growth

    def _normalize_ratio(self, value: object, default: float = 0.0) -> float:
        ratio = self._to_float(value, default)
        if pd.isna(ratio):
            return default
        if abs(ratio) > 1:
            ratio = ratio / 100.0
        return max(0.0, min(ratio, 1.0))

    def find_hidden_gems(
        self,
        timeframe: str = "swing",
        limit: int = 10
    ) -> List[Dict]:
        """
        Find hidden gem stocks - high potential, low attention

        Criteria for hidden gems:
        - Market cap $500M - $10B (mid/small cap)
        - Revenue growth > 30% (or price growth > 20% proxy)
        - Volume surge in last 7 days (1.8x+)
        - Avg volume > 400k and price > $5
        - Strong technical + hidden gem bonus
        """
        logger.info("Searching for hidden gems...")

        delisted = get_delisted_tickers()
        tickers = self.ticker_universe
        if delisted:
            tickers = [ticker for ticker in tickers if ticker not in delisted]
        logger.info("Hidden gems scan: %s tickers (%s delisted filtered)", len(tickers), len(delisted))
        batch_data = self.yfinance.get_multiple_stocks(tickers, period="3mo")

        candidates = []
        scanned = 0
        no_data = 0

        for ticker in tickers:
            scanned += 1
            try:
                raw_data = batch_data.get(ticker)
                data = self._prepare_stock_data(raw_data)
                if data is None:
                    no_data += 1
                    continue

                current_price = data['Close'].iloc[-1]
                avg_volume = data['Volume'].rolling(20).mean().iloc[-1]
                if avg_volume <= 0 or current_price <= 0:
                    continue

                recent_volume = data['Volume'].iloc[-5:].mean()
                volume_ratio = recent_volume / avg_volume if avg_volume else 0

                price_30d_ago = data['Close'].iloc[-30] if len(data) >= 30 else data['Close'].iloc[0]
                price_growth = (current_price - price_30d_ago) / price_30d_ago if price_30d_ago > 0 else 0

                estimated_market_cap = current_price * avg_volume * 100  # Rough estimate

                technical_score = self._calculate_technical_score(data)
                momentum_score = self._calculate_momentum_score(data)
                volume_score = self._calculate_volume_score(data)
                trend_score = self._calculate_trend_score(data)
                base_score = technical_score + momentum_score + volume_score + trend_score

                cap_score = 0.0
                if estimated_market_cap > 0:
                    if 500_000_000 <= estimated_market_cap <= 10_000_000_000:
                        cap_score = 20
                    elif 300_000_000 <= estimated_market_cap < 500_000_000 or 10_000_000_000 < estimated_market_cap <= 20_000_000_000:
                        cap_score = 12
                    elif 100_000_000 <= estimated_market_cap < 300_000_000 or 20_000_000_000 < estimated_market_cap <= 35_000_000_000:
                        cap_score = 6

                growth_score = 0.0
                if price_growth >= 0.30:
                    growth_score = 20
                elif price_growth >= 0.20:
                    growth_score = 15
                elif price_growth >= 0.12:
                    growth_score = 10
                elif price_growth >= 0.06:
                    growth_score = 6

                surge_score = 0.0
                if volume_ratio >= 2.0:
                    surge_score = 15
                elif volume_ratio >= 1.5:
                    surge_score = 10
                elif volume_ratio >= 1.2:
                    surge_score = 6

                liquidity_score = 0.0
                if avg_volume >= 750_000 and current_price >= 5:
                    liquidity_score = 8
                elif avg_volume >= 400_000 and current_price >= 3:
                    liquidity_score = 5
                elif avg_volume >= 200_000 and current_price >= 2:
                    liquidity_score = 2

                fit_score = base_score + cap_score + growth_score + surge_score + liquidity_score

                candidates.append({
                    "ticker": ticker,
                    "data": data,
                    "current_price": current_price,
                    "avg_volume": avg_volume,
                    "volume_ratio": volume_ratio,
                    "price_growth": price_growth,
                    "estimated_market_cap": estimated_market_cap,
                    "fit_score": fit_score,
                    "base_score": base_score
                })

            except Exception as e:
                logger.error(f"Error analyzing {ticker}: {str(e)}")
                continue

        if not candidates:
            logger.warning(
                "Hidden gems scan: no candidates after data prep (%s scanned, %s no data)",
                scanned,
                no_data
            )
            return []

        candidates.sort(key=lambda x: (x["fit_score"], x["base_score"]), reverse=True)
        candidate_budget = max(limit * 25, 150)
        enrich_limit = settings.HIDDEN_GEMS_ENRICH_LIMIT
        if enrich_limit <= 0:
            candidate_budget = len(candidates)
        else:
            candidate_budget = min(candidate_budget, len(candidates), enrich_limit)
        logger.info("Hidden gems shortlist: %s candidates (budget=%s)", len(candidates), candidate_budget)

        scored_candidates = []
        for candidate in candidates[:candidate_budget]:
            ticker = candidate["ticker"]
            data = candidate["data"]
            current_price = candidate["current_price"]
            avg_volume = candidate["avg_volume"]

            if avg_volume < 150_000 or current_price < 2:
                continue

            fundamentals = self.yfinance.get_fundamentals(ticker)

            market_cap = self._to_float(candidate["estimated_market_cap"], 0.0)
            growth_rate = self._normalize_growth_rate(candidate["price_growth"], 0.0)
            if fundamentals:
                market_cap = self._to_float(fundamentals.get('marketCap'), market_cap)
                revenue_growth = fundamentals.get('revenueGrowth')
                if revenue_growth is not None:
                    growth_rate = self._normalize_growth_rate(revenue_growth, growth_rate)

            is_mid_small_cap = bool(market_cap) and 300_000_000 < market_cap < 20_000_000_000
            is_high_growth = bool(growth_rate) and growth_rate >= 0.12
            has_momentum = candidate["volume_ratio"] >= 1.2 or candidate["base_score"] >= 70

            inst_ownership = 0.0
            insider_ownership = 0.0
            if fundamentals:
                inst_ownership = self._normalize_ratio(
                    fundamentals.get('institutionalOwnership'),
                    0.0
                )
                insider_ownership = self._normalize_ratio(
                    fundamentals.get('insiderOwnership'),
                    0.0
                )

            info = {
                'marketCap': market_cap,
                'revenueGrowth': growth_rate,
                'heldPercentInstitutions': inst_ownership,
                'heldPercentInsiders': insider_ownership
            }

            score_data = self.calculate_enhanced_score(
                ticker,
                data,
                info,
                use_advanced_data=False,
                include_news=False
            )
            if not score_data or score_data["total_score"] < 70:
                continue

            hidden_gem_bonus = score_data["breakdown"].get("hidden_gem", 0)
            gem_score = (
                score_data["total_score"] +
                (hidden_gem_bonus * 2) +
                (candidate["price_growth"] * 100) +
                (min(candidate["volume_ratio"], 3) * 5)
            )

            market_cap_value = self._to_float(market_cap, 0.0)
            growth_rate_value = self._normalize_growth_rate(growth_rate, 0.0)

            scored_candidates.append({
                "ticker": ticker,
                "score": score_data["total_score"],
                "currentPrice": float(current_price),
                "targetPrice": 0,
                "potentialReturn": 0,
                "confidence": int(score_data["total_score"]),
                "timeHorizon": timeframe.upper(),
                "reasoning": score_data["reasoning"],
                "signals": score_data["signals"],
                "riskLevel": score_data["risk_level"],
                "breakdown": score_data["breakdown"],
                "category": "HIDDEN GEM",
                "marketCap": market_cap_value,
                "revenueGrowth": float(growth_rate_value * 100) if growth_rate_value else 0,
                "volumeSurge": bool(candidate["volume_ratio"] >= 1.2),
                "_gemScore": gem_score,
                "_isMidSmallCap": is_mid_small_cap,
                "_isHighGrowth": is_high_growth,
                "_hasMomentum": has_momentum,
                "_data": data,
                "_info": info
            })

        if not scored_candidates:
            logger.warning(
                "Hidden gems scan: no scored candidates after shortlist (%s scanned, %s no data)",
                scanned,
                no_data
            )
            return []

        strict = [
            item for item in scored_candidates
            if item.get("_isMidSmallCap") and item.get("_isHighGrowth") and item.get("_hasMomentum")
        ]
        relaxed = [
            item for item in scored_candidates
            if item.get("_isMidSmallCap") and (item.get("_isHighGrowth") or item.get("_hasMomentum"))
        ]
        hidden_gems = strict if len(strict) >= limit else relaxed if relaxed else scored_candidates

        # Apply target pricing after selection
        multiplier = {
            "day": 1.03,
            "swing": 1.15,
            "long": 1.35
        }.get(timeframe, 1.15)

        for item in hidden_gems:
            current_price = item["currentPrice"]
            target_price = current_price * multiplier
            item["targetPrice"] = float(target_price)
            item["potentialReturn"] = float(((target_price - current_price) / current_price) * 100)

        hidden_gems.sort(key=lambda x: x.get("_gemScore", 0), reverse=True)
        hidden_gems = self._apply_score_gate(hidden_gems, limit, percentile=0.15, min_score=75)

        # Apply news overlay only to final picks to keep runtime predictable
        for item in hidden_gems[:limit]:
            data = item.get("_data")
            info = item.get("_info")
            if data is None or info is None:
                continue
            score_data = self.calculate_enhanced_score(
                item["ticker"],
                data,
                info,
                use_advanced_data=False,
                include_news=True
            )
            if not score_data:
                continue
            item.update({
                "score": score_data["total_score"],
                "confidence": int(score_data["total_score"]),
                "reasoning": score_data["reasoning"],
                "signals": score_data["signals"],
                "riskLevel": score_data["risk_level"],
                "breakdown": score_data["breakdown"]
            })

        # Add ranks + cleanup
        for i, stock in enumerate(hidden_gems[:limit], 1):
            stock["rank"] = i
            stock.pop("_gemScore", None)
            stock.pop("_isMidSmallCap", None)
            stock.pop("_isHighGrowth", None)
            stock.pop("_hasMomentum", None)
            stock.pop("_data", None)
            stock.pop("_info", None)

        logger.info(
            "Hidden gems scan: %s picks from %s tickers (%s no data, %s scored)",
            len(hidden_gems),
            scanned,
            no_data,
            len(scored_candidates)
        )
        return hidden_gems[:limit]

    def find_quick_wins(self, limit: int = 10) -> List[Dict]:
        """
        Find quick win opportunities for day trading (SELECTIVE CRITERIA)

        Criteria for Quick Wins:
        - Momentum (0.6%+ in last 3 days) with volume increase (1.8x+)
          OR strong momentum (1.2%+) OR volume surge (3.0x+) with momentum
        - RSI between 40-70 (avoid extremes)
        - Avg volume >= 750k and price > $5
        - Enhanced score >= 75 with quick win bonus >= 8
        """
        logger.info("Searching for quick wins (SELECTIVE CRITERIA)...")

        # Use liquid large-cap stocks for day trading
        delisted = get_delisted_tickers()
        tickers = self.ticker_universe
        if delisted:
            tickers = [ticker for ticker in tickers if ticker not in delisted]
        logger.info("Quick wins scan: %s tickers (%s delisted filtered)", len(tickers), len(delisted))
        batch_data = self.yfinance.get_multiple_stocks(tickers, period="3mo")

        quick_wins = []
        relaxed_candidates = []
        fallback_candidates = []
        scanned = 0
        no_data = 0

        for ticker in tickers:
            scanned += 1
            try:
                raw_data = batch_data.get(ticker)
                data = self._prepare_stock_data(raw_data)
                if data is None:
                    no_data += 1
                    continue

                # Quick win scoring
                recent_returns = data['Close'].pct_change(fill_method=None).dropna().tail(3)
                if recent_returns.empty:
                    continue
                momentum = recent_returns.mean()
                if pd.isna(momentum):
                    continue

                current_price = data['Close'].iloc[-1]
                avg_volume = data['Volume'].rolling(20).mean().iloc[-1]
                if pd.isna(avg_volume) or avg_volume <= 0:
                    continue
                current_volume = data['Volume'].iloc[-1]
                if pd.isna(current_volume) or current_volume <= 0:
                    continue
                volume_ratio = current_volume / avg_volume
                if pd.isna(volume_ratio) or volume_ratio <= 0:
                    continue
                liquid_enough = avg_volume > 750_000
                price_ok = current_price > 5

                # Calculate RSI to avoid extreme overbought
                delta = data['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                current_rsi = rsi.iloc[-1]
                if pd.isna(current_rsi):
                    continue

                # SELECTIVE CRITERIA: tighten filters to surface standout picks
                # Path 1: Momentum + volume increase
                # Path 2: Strong momentum with some volume support
                # Path 3: Volume surge with positive momentum
                has_momentum_and_volume = momentum > 0.006 and volume_ratio > 1.8  # 0.6% + 80% volume
                has_strong_momentum = momentum > 0.012 and volume_ratio > 1.3  # 1.2% + 30% volume
                has_volume_surge = volume_ratio > 3.0 and momentum > 0.003  # 0.3% + 3.0x volume
                rsi_ok = 40 <= current_rsi <= 70

                relaxed_liquid = avg_volume >= 500_000
                relaxed_price_ok = current_price > 3
                relaxed_rsi_ok = 35 <= current_rsi <= 75
                relaxed_momentum = momentum > 0.003 and volume_ratio > 1.4
                relaxed_strong_momentum = momentum > 0.008 and volume_ratio > 1.1
                relaxed_volume_surge = volume_ratio > 2.2 and momentum > 0.001
                relaxed_match = (
                    relaxed_liquid and relaxed_price_ok and relaxed_rsi_ok and
                    (relaxed_momentum or relaxed_strong_momentum or relaxed_volume_surge)
                )
                fallback_liquid = avg_volume >= 250_000
                fallback_price_ok = current_price > 2
                fallback_rsi_ok = 30 <= current_rsi <= 80
                fallback_momentum = momentum > 0
                if fallback_liquid and fallback_price_ok and fallback_rsi_ok and fallback_momentum:
                    fallback_candidates.append({
                        "ticker": ticker,
                        "current_price": current_price,
                        "volume_ratio": volume_ratio,
                        "momentum": momentum,
                        "rsi": current_rsi
                    })

                if (liquid_enough and price_ok and rsi_ok and
                        (has_momentum_and_volume or has_strong_momentum or has_volume_surge)):
                    score_data = self.calculate_enhanced_score(
                        ticker,
                        data,
                        {},
                        use_advanced_data=False,
                        include_news=True
                    )

                    if (score_data and score_data["total_score"] >= 75 and
                            score_data["breakdown"].get("quick_win", 0) >= 8):
                        target_price = current_price * 1.025  # 2.5% target for day trade

                        # Build dynamic reasoning based on what triggered the match
                        reasons = []
                        if has_strong_momentum:
                            reasons.append(f"Strong momentum {momentum*100:.1f}%")
                        elif momentum > 0:
                            reasons.append(f"Momentum {momentum*100:.1f}%")

                        if has_volume_surge:
                            reasons.append(f"{volume_ratio:.1f}x volume surge")
                        elif volume_ratio > 1.6:
                            reasons.append(f"{volume_ratio:.1f}x volume increase")

                        reasons.append(f"RSI {current_rsi:.0f}")
                        reasoning_text = " + ".join(reasons)

                        quick_wins.append({
                            "ticker": ticker,
                            "score": score_data["total_score"],
                            "currentPrice": float(current_price),
                            "targetPrice": float(target_price),
                            "potentialReturn": 2.5,
                            "confidence": int(score_data["total_score"]),
                            "timeHorizon": "DAY",
                            "reasoning": reasoning_text,
                            "signals": score_data["signals"] + ["Day Trade", f"Vol {volume_ratio:.1f}x", f"RSI {current_rsi:.0f}"],
                            "riskLevel": "HIGH",
                            "breakdown": score_data["breakdown"],
                            "category": "QUICK WIN",
                            "volumeRatio": float(volume_ratio),
                            "momentum": float(momentum * 100),
                            "rsi": float(current_rsi)
                        })
                elif relaxed_match:
                    relaxed_candidates.append({
                        "ticker": ticker,
                        "data": data,
                        "current_price": current_price,
                        "volume_ratio": volume_ratio,
                        "momentum": momentum,
                        "rsi": current_rsi
                    })

            except Exception as e:
                logger.error(f"Error analyzing {ticker}: {str(e)}")
                continue

        if not quick_wins and relaxed_candidates:
            logger.info(
                "Quick wins scan: applying relaxed criteria (%s candidates)",
                len(relaxed_candidates)
            )
            for candidate in relaxed_candidates:
                ticker = candidate["ticker"]
                data = candidate["data"]
                score_data = self.calculate_enhanced_score(
                    ticker,
                    data,
                    {},
                    use_advanced_data=False,
                    include_news=True
                )
                if not score_data:
                    continue
                if (score_data["total_score"] >= 70 and
                        score_data["breakdown"].get("quick_win", 0) >= 6):
                    current_price = candidate["current_price"]
                    target_price = current_price * 1.02
                    momentum = candidate["momentum"]
                    volume_ratio = candidate["volume_ratio"]
                    current_rsi = candidate["rsi"]

                    reasons = []
                    if momentum > 0:
                        reasons.append(f"Momentum {momentum*100:.1f}%")
                    if volume_ratio > 1.2:
                        reasons.append(f"{volume_ratio:.1f}x volume")
                    reasons.append(f"RSI {current_rsi:.0f}")
                    reasoning_text = " + ".join(reasons)

                    quick_wins.append({
                        "ticker": ticker,
                        "score": score_data["total_score"],
                        "currentPrice": float(current_price),
                        "targetPrice": float(target_price),
                        "potentialReturn": 2.0,
                        "confidence": int(score_data["total_score"]),
                        "timeHorizon": "DAY",
                        "reasoning": reasoning_text,
                        "signals": score_data["signals"] + ["Day Trade", f"Vol {volume_ratio:.1f}x", f"RSI {current_rsi:.0f}"],
                        "riskLevel": "HIGH",
                        "breakdown": score_data["breakdown"],
                        "category": "QUICK WIN",
                        "volumeRatio": float(volume_ratio),
                        "momentum": float(momentum * 100),
                        "rsi": float(current_rsi)
                    })

        if not quick_wins and fallback_candidates:
            logger.info(
                "Quick wins scan: applying fallback momentum pool (%s candidates)",
                len(fallback_candidates)
            )
            fallback_candidates.sort(
                key=lambda x: (x["momentum"], x["volume_ratio"]),
                reverse=True
            )
            candidate_budget = min(len(fallback_candidates), max(limit * 6, 30))
            for candidate in fallback_candidates[:candidate_budget]:
                ticker = candidate["ticker"]
                raw_data = batch_data.get(ticker)
                data = self._prepare_stock_data(raw_data)
                if data is None:
                    continue
                score_data = self.calculate_enhanced_score(
                    ticker,
                    data,
                    {},
                    use_advanced_data=False,
                    include_news=True
                )
                if not score_data:
                    continue
                if (score_data["total_score"] >= 65 and
                        score_data["breakdown"].get("quick_win", 0) >= 4):
                    current_price = candidate["current_price"]
                    target_price = current_price * 1.015
                    momentum = candidate["momentum"]
                    volume_ratio = candidate["volume_ratio"]
                    current_rsi = candidate["rsi"]

                    reasons = []
                    if momentum > 0:
                        reasons.append(f"Momentum {momentum*100:.1f}%")
                    if volume_ratio > 1.1:
                        reasons.append(f"{volume_ratio:.1f}x volume")
                    reasons.append(f"RSI {current_rsi:.0f}")
                    reasoning_text = " + ".join(reasons)

                    quick_wins.append({
                        "ticker": ticker,
                        "score": score_data["total_score"],
                        "currentPrice": float(current_price),
                        "targetPrice": float(target_price),
                        "potentialReturn": 1.5,
                        "confidence": int(score_data["total_score"]),
                        "timeHorizon": "DAY",
                        "reasoning": reasoning_text,
                        "signals": score_data["signals"] + ["Day Trade", f"Vol {volume_ratio:.1f}x", f"RSI {current_rsi:.0f}"],
                        "riskLevel": "HIGH",
                        "breakdown": score_data["breakdown"],
                        "category": "QUICK WIN",
                        "volumeRatio": float(volume_ratio),
                        "momentum": float(momentum * 100),
                        "rsi": float(current_rsi)
                    })

        # Sort and rank (prioritize score, then momentum and volume)
        quick_wins.sort(
            key=lambda x: (x["score"], x.get("momentum", 0), x.get("volumeRatio", 0)),
            reverse=True
        )

        quick_wins = self._apply_score_gate(quick_wins, limit, percentile=0.2, min_score=75)

        for i, stock in enumerate(quick_wins[:limit], 1):
            stock["rank"] = i

        logger.info(
            "Quick wins scan: %s picks from %s tickers (%s no data)",
            len(quick_wins),
            scanned,
            no_data
        )
        if len(quick_wins) > 0:
            logger.info(f"Top quick win: {quick_wins[0]['ticker']} (score: {quick_wins[0]['score']}, momentum: {quick_wins[0]['momentum']:.1f}%, volume: {quick_wins[0]['volumeRatio']:.1f}x)")
        else:
            logger.warning("No quick wins found - criteria may be too strict or market conditions unfavorable")

        return quick_wins[:limit]

    def calculate_enhanced_score(
        self,
        ticker: str,
        data: pd.DataFrame,
        info: Dict,
        use_advanced_data: bool = True,
        include_news: bool = False
    ) -> Optional[Dict]:
        """
        Enhanced scoring with bonuses for hidden gems and smart money

        Total: 270 points possible
        - Base technical/momentum/volume/trend: 100 points
        - Hidden gem bonus: 20 points
        - Smart money bonus: 15 points
        - Quick win bonus: 15 points
        - Insider trading bonus: 20 points
        - Short interest bonus: 20 points
        - Options flow bonus: 20 points
        - Earnings calendar bonus: 20 points
        - News sentiment bonus: 20 points (NEW!)
        - Social media buzz bonus: 20 points (NEW!)
        """
        try:
            # Base scoring (100 points)
            technical_score = self._calculate_technical_score(data)
            momentum_score = self._calculate_momentum_score(data)
            volume_score = self._calculate_volume_score(data)
            trend_score = self._calculate_trend_score(data)

            base_score = technical_score + momentum_score + volume_score + trend_score

            # Original bonus scoring (50 points)
            hidden_gem_bonus = self._calculate_hidden_gem_bonus(info, data)
            smart_money_bonus = self._calculate_smart_money_bonus(info)
            quick_win_bonus = self._calculate_quick_win_bonus(data)

            # NEW: Advanced data bonus scoring (80 points)
            include_news_signals = use_advanced_data or include_news

            if use_advanced_data:
                insider_bonus = self._calculate_insider_bonus(ticker)
                short_interest_bonus = self._calculate_short_interest_bonus(ticker)
                options_bonus = self._calculate_options_bonus(ticker)
                earnings_bonus = self._calculate_earnings_bonus(ticker)

                # NEWEST: News and social media bonus scoring (40 points)
                news_bonus = self._calculate_news_bonus(ticker)
                social_bonus = self._calculate_social_bonus(ticker)
            else:
                insider_bonus = 10.0
                short_interest_bonus = 10.0
                options_bonus = 10.0
                earnings_bonus = 10.0
                news_bonus = self._calculate_news_bonus(ticker) if include_news else 10.0
                social_bonus = 10.0

            total_score = (
                base_score + hidden_gem_bonus + smart_money_bonus + quick_win_bonus +
                insider_bonus + short_interest_bonus + options_bonus + earnings_bonus +
                news_bonus + social_bonus
            )

            # Generate enhanced reasoning
            reasoning = self._generate_enhanced_reasoning(
                technical_score, momentum_score, volume_score, trend_score,
                hidden_gem_bonus, smart_money_bonus, quick_win_bonus,
                insider_bonus, short_interest_bonus, options_bonus, earnings_bonus,
                news_bonus, social_bonus
            )

            signals = self._generate_signals(
                data,
                ticker,
                include_advanced=use_advanced_data,
                include_news=include_news_signals
            )
            risk_level = self._determine_risk_level(data, total_score)

            return {
                "total_score": round(min(total_score, 270), 2),
                "breakdown": {
                    "technical": round(technical_score, 2),
                    "momentum": round(momentum_score, 2),
                    "volume": round(volume_score, 2),
                    "trend": round(trend_score, 2),
                    "hidden_gem": round(hidden_gem_bonus, 2),
                    "smart_money": round(smart_money_bonus, 2),
                    "quick_win": round(quick_win_bonus, 2),
                    "insider_trading": round(insider_bonus, 2),
                    "short_interest": round(short_interest_bonus, 2),
                    "options_flow": round(options_bonus, 2),
                    "earnings": round(earnings_bonus, 2),
                    "news_sentiment": round(news_bonus, 2),
                    "social_buzz": round(social_bonus, 2)
                },
                "reasoning": reasoning,
                "signals": signals,
                "risk_level": risk_level
            }

        except Exception as e:
            logger.error(f"Error calculating enhanced score for {ticker}: {str(e)}")
            return None

    def _calculate_hidden_gem_bonus(self, info: Dict, data: pd.DataFrame) -> float:
        """
        Bonus points for hidden gem characteristics (0-20 points)
        """
        bonus = 0.0

        # Market cap bonus (mid/small cap)
        market_cap = self._to_float(info.get('marketCap'), 0.0)
        if 500_000_000 < market_cap < 5_000_000_000:
            bonus += 8  # Small-mid cap
        elif 5_000_000_000 < market_cap < 10_000_000_000:
            bonus += 5  # Mid cap

        # Revenue growth bonus
        revenue_growth = self._normalize_growth_rate(info.get('revenueGrowth'), 0.0)
        if revenue_growth:
            if revenue_growth > 0.50:  # 50%+ growth
                bonus += 7
            elif revenue_growth > 0.30:  # 30%+ growth
                bonus += 5
            elif revenue_growth > 0.20:  # 20%+ growth
                bonus += 3

        # Low analyst coverage bonus (undiscovered)
        # This is a proxy - in real implementation would check actual analyst count
        bonus += 5  # Assume low coverage for now

        return min(bonus, 20)

    def _calculate_smart_money_bonus(self, info: Dict) -> float:
        """
        Bonus for institutional ownership and smart money indicators (0-15 points)
        """
        bonus = 0.0

        # Institutional ownership
        inst_ownership = self._normalize_ratio(info.get('heldPercentInstitutions'), 0.0)
        if inst_ownership:
            if 0.40 < inst_ownership < 0.70:  # Sweet spot
                bonus += 8
            elif 0.30 < inst_ownership < 0.80:
                bonus += 5

        # Insider ownership (skin in the game)
        insider_ownership = self._normalize_ratio(info.get('heldPercentInsiders'), 0.0)
        if insider_ownership and insider_ownership > 0.05:  # 5%+ insider ownership
            bonus += 7

        return min(bonus, 15)

    def _calculate_quick_win_bonus(self, data: pd.DataFrame) -> float:
        """
        Bonus for day trading opportunities (0-15 points)
        """
        bonus = 0.0

        # Recent momentum (last 3 days)
        recent_returns = data['Returns'].tail(3).mean()
        if recent_returns > 0.02:  # 2%+ momentum
            bonus += 7
        elif recent_returns > 0.01:
            bonus += 4

        # Volume surge
        if 'Volume_Ratio' in data.columns and not pd.isna(data['Volume_Ratio'].iloc[-1]):
            volume_ratio = data['Volume_Ratio'].iloc[-1]
            if volume_ratio > 3.0:  # 3x volume
                bonus += 8
            elif volume_ratio > 2.0:  # 2x volume
                bonus += 5

        return min(bonus, 15)

    def _calculate_insider_bonus(self, ticker: str) -> float:
        """
        Bonus for insider trading activity (0-20 points)

        Insider buying is a strong bullish signal - company insiders
        know the business better than anyone.
        """
        try:
            score = self.insider.get_insider_score(ticker)
            # Score is already 0-20, just return it
            return float(score)
        except Exception as e:
            logger.warning(f"Insider trading data unavailable for {ticker}: {str(e)}")
            return 10.0  # Neutral score on error

    def _calculate_short_interest_bonus(self, ticker: str) -> float:
        """
        Bonus for short squeeze potential (0-20 points)

        High short interest + low days to cover = squeeze potential
        """
        try:
            score = self.short_interest.get_short_score(ticker)
            # Score is already 0-20, just return it
            return float(score)
        except Exception as e:
            logger.warning(f"Short interest data unavailable for {ticker}: {str(e)}")
            return 10.0  # Neutral score on error

    def _calculate_options_bonus(self, ticker: str) -> float:
        """
        Bonus for unusual options activity (0-20 points)

        Unusual call buying = smart money positioning
        """
        try:
            score = self.options.get_options_score(ticker)
            # Score is already 0-20, just return it
            return float(score)
        except Exception as e:
            logger.warning(f"Options flow data unavailable for {ticker}: {str(e)}")
            return 10.0  # Neutral score on error

    def _calculate_earnings_bonus(self, ticker: str) -> float:
        """
        Bonus for earnings calendar and beat streak (0-20 points)

        Companies that consistently beat earnings tend to keep beating
        """
        try:
            score = self.earnings.get_earnings_score(ticker)
            # Score is already 0-20, just return it
            return float(score)
        except Exception as e:
            logger.warning(f"Earnings data unavailable for {ticker}: {str(e)}")
            return 10.0  # Neutral score on error

    def _calculate_news_bonus(self, ticker: str) -> float:
        """
        Bonus for positive news sentiment (0-20 points)

        Positive news = stock price catalyst
        High impact news (FDA approval, merger, earnings beat) = major moves
        """
        try:
            # Get recent news for this stock
            news_articles = self.news.get_stock_news_yfinance(ticker, limit=10)

            if not news_articles:
                return 10.0  # Neutral if no news

            score = 0.0

            # Analyze news impact
            high_impact_count = 0
            positive_categories = ['FDA_APPROVAL', 'MERGER', 'ACQUISITION', 'EARNINGS_BEAT',
                                 'BREAKTHROUGH', 'GUIDANCE_RAISED', 'IPO']
            negative_categories = ['BANKRUPTCY', 'EARNINGS_MISS', 'INVESTIGATION',
                                  'LAWSUIT', 'GUIDANCE_LOWERED']

            for article in news_articles[:5]:  # Focus on most recent 5
                category = article.get('category', 'GENERAL')
                impact = article.get('impact', 'LOW')

                # Positive news scoring
                if category in positive_categories:
                    if impact == 'HIGH':
                        score += 6  # Major catalyst
                    elif impact == 'MEDIUM':
                        score += 4
                    else:
                        score += 2

                # Negative news penalty
                elif category in negative_categories:
                    if impact == 'HIGH':
                        score -= 6  # Major negative
                    elif impact == 'MEDIUM':
                        score -= 4
                    else:
                        score -= 2

                if impact == 'HIGH':
                    high_impact_count += 1

            # Bonus for multiple high-impact positive news
            if high_impact_count >= 2:
                score += 5

            # Normalize to 0-20 range (10 = neutral, <10 = bearish, >10 = bullish)
            score = max(0, min(20, 10 + score))

            return float(score)

        except Exception as e:
            logger.warning(f"News data unavailable for {ticker}: {str(e)}")
            return 10.0  # Neutral score on error

    def _calculate_social_bonus(self, ticker: str) -> float:
        """
        Bonus for social media buzz and trending (0-20 points)

        Reddit/Twitter trending = retail interest = potential momentum
        BUT avoid pure meme stocks (pump and dump risk)
        """
        try:
            # For now, return neutral score
            # In production, would integrate with social.py router:
            # - Check if ticker is in Reddit WallStreetBets trending
            # - Check Twitter mentions volume
            # - Check sentiment from social media
            # - Penalty if TOO much buzz (meme stock risk)

            # Placeholder logic - would need to import social trending data
            # For MVP, return neutral to not affect scores
            return 10.0  # Neutral score

            # TODO: Implement actual social media scoring:
            # 1. Get Reddit trending data
            # 2. Get Twitter mentions
            # 3. Calculate buzz score (moderate buzz = good, excessive = risky)
            # 4. Return 0-20 points

        except Exception as e:
            logger.warning(f"Social media data unavailable for {ticker}: {str(e)}")
            return 10.0  # Neutral score on error

    # Reuse technical indicator methods from original predictor
    def _calculate_technical_score(self, data: pd.DataFrame) -> float:
        """Technical analysis score (0-30 points)"""
        score = 0.0
        current_price = data['Close'].iloc[-1]

        # Moving averages
        if not pd.isna(data['SMA_20'].iloc[-1]):
            if current_price > data['SMA_20'].iloc[-1]:
                score += 3
            if current_price > data['SMA_50'].iloc[-1]:
                score += 3
            if current_price > data['SMA_200'].iloc[-1]:
                score += 4

        # RSI
        if not pd.isna(data['RSI'].iloc[-1]):
            rsi = data['RSI'].iloc[-1]
            if 40 <= rsi <= 60:
                score += 10
            elif 30 <= rsi < 40:
                score += 8
            elif 60 < rsi <= 70:
                score += 7

        # MACD
        if not pd.isna(data['MACD'].iloc[-1]):
            if data['MACD'].iloc[-1] > data['MACD_Signal'].iloc[-1]:
                score += 10

        return min(score, 30)

    def _calculate_momentum_score(self, data: pd.DataFrame) -> float:
        """Momentum score (0-30 points)"""
        score = 0.0

        if not pd.isna(data['Returns_20'].iloc[-1]):
            returns_20 = data['Returns_20'].iloc[-1]
            if returns_20 > 0.15:
                score += 15
            elif returns_20 > 0.10:
                score += 12
            elif returns_20 > 0.05:
                score += 9

        recent_returns = data['Returns'].tail(5).mean()
        if recent_returns > 0.02:
            score += 15
        elif recent_returns > 0.01:
            score += 12

        return min(score, 30)

    def _calculate_volume_score(self, data: pd.DataFrame) -> float:
        """Volume score (0-25 points) - increased from 20"""
        score = 0.0

        if 'Volume_Ratio' in data.columns and not pd.isna(data['Volume_Ratio'].iloc[-1]):
            volume_ratio = data['Volume_Ratio'].iloc[-1]
            if volume_ratio > 3.0:  # Very high volume
                score += 25
            elif volume_ratio > 2.0:
                score += 20
            elif volume_ratio > 1.5:
                score += 16
            elif volume_ratio > 1.2:
                score += 12

        return min(score, 25)

    def _calculate_trend_score(self, data: pd.DataFrame) -> float:
        """Trend score (0-20 points)"""
        score = 0.0

        if (not pd.isna(data['SMA_20'].iloc[-1]) and
            not pd.isna(data['SMA_50'].iloc[-1])):
            if data['SMA_20'].iloc[-1] > data['SMA_50'].iloc[-1]:
                score += 10

        recent_highs = data['High'].tail(20)
        if recent_highs.iloc[-1] > recent_highs.iloc[0]:
            score += 10

        return min(score, 20)

    def _generate_enhanced_reasoning(
        self,
        technical: float,
        momentum: float,
        volume: float,
        trend: float,
        hidden_gem: float,
        smart_money: float,
        quick_win: float,
        insider: float = 10,
        short_interest: float = 10,
        options: float = 10,
        earnings: float = 10,
        news: float = 10,
        social: float = 10
    ) -> str:
        """Generate enhanced reasoning with bonus highlights"""
        reasons = []

        # Base signals
        if technical >= 20:
            reasons.append("strong technical setup")
        if momentum >= 20:
            reasons.append("excellent momentum")
        if volume >= 18:
            reasons.append("unusual volume surge")
        if trend >= 12:
            reasons.append("clear uptrend")

        # Original bonuses
        if hidden_gem >= 12:
            reasons.append("Hidden gem potential")
        if smart_money >= 10:
            reasons.append("Smart money accumulating")
        if quick_win >= 10:
            reasons.append("Quick win opportunity")

        # Advanced data signals
        if insider >= 15:
            reasons.append("Insider buying detected")
        if short_interest >= 15:
            reasons.append("Squeeze potential")
        if options >= 15:
            reasons.append("Unusual options activity")
        if earnings >= 15:
            reasons.append("Earnings beat streak")

        # NEWEST: News and social signals
        if news >= 15:
            reasons.append("Positive news catalyst")
        if social >= 15:
            reasons.append("Social media buzz")

        if not reasons:
            return "Mixed signals, moderate opportunity"

        return "Premium opportunity: " + ", ".join(reasons)

    def _generate_signals(
        self,
        data: pd.DataFrame,
        ticker: str = None,
        include_advanced: bool = True,
        include_news: bool = False
    ) -> List[str]:
        """Generate trading signals including new data sources"""
        signals = []
        current_price = data['Close'].iloc[-1]

        # Technical signals
        if not pd.isna(data['SMA_20'].iloc[-1]) and current_price > data['SMA_20'].iloc[-1]:
            signals.append("Above SMA 20")

        if not pd.isna(data['RSI'].iloc[-1]):
            rsi = data['RSI'].iloc[-1]
            if rsi < 30:
                signals.append("RSI Oversold")
            elif 40 <= rsi <= 60:
                signals.append("RSI Neutral")

        if not pd.isna(data['MACD'].iloc[-1]):
            if data['MACD'].iloc[-1] > data['MACD_Signal'].iloc[-1]:
                signals.append("MACD Bullish")

        if 'Volume_Ratio' in data.columns and not pd.isna(data['Volume_Ratio'].iloc[-1]):
            if data['Volume_Ratio'].iloc[-1] > 2.0:
                signals.append("Volume Spike")

        # NEW: Advanced data signals
        if ticker and include_advanced:
            try:
                # Insider trading signal
                insider_data = self.insider.get_insider_activity(ticker)
                if insider_data.get('signal') == 'INSIDER_BUYING':
                    signals.append("Insider Buying")

                # Short interest signal
                short_data = self.short_interest.get_short_interest(ticker)
                if short_data.get('signal') == 'SQUEEZE_SETUP':
                    signals.append("Squeeze Setup")

                # Options flow signal
                options_data = self.options.get_options_activity(ticker)
                if options_data.get('signal') == 'UNUSUAL_CALL_ACTIVITY':
                    signals.append("Unusual Calls")

                # Earnings signal
                earnings_data = self.earnings.get_earnings_calendar(ticker)
                if earnings_data.get('signal') == 'BEAT_EXPECTED':
                    signals.append("Earnings Beat Expected")

            except Exception as e:
                logger.debug(f"Could not fetch advanced signals for {ticker}: {str(e)}")

        if ticker and include_news:
            try:
                news_articles = self.news.get_stock_news_yfinance(ticker, limit=3)
                positive_news = any(
                    article.get('category') in ['FDA_APPROVAL', 'MERGER', 'ACQUISITION', 'EARNINGS_BEAT', 'BREAKTHROUGH']
                    for article in news_articles
                )
                if positive_news:
                    signals.append("Positive News")
            except Exception as e:
                logger.debug(f"Could not fetch news signals for {ticker}: {str(e)}")

        return signals[:8]  # Increased from 7 to 8 to show more signals

    def _determine_risk_level(self, data: pd.DataFrame, score: float) -> str:
        """Determine risk level"""
        returns = data['Returns'].tail(20)
        volatility = returns.std()

        if volatility > 0.05:
            return "HIGH"
        elif volatility > 0.03:
            return "MEDIUM"
        else:
            return "LOW"

    def get_stock_data(self, ticker: str, allow_external: Optional[bool] = None) -> Optional[pd.DataFrame]:
        """
        Fetch historical stock data using yfinance (batching recommended)

        Much faster and more accurate than Finnhub's free tier.
        yfinance provides full historical OHLCV data without restrictions.
        """
        try:
            # Use yfinance for historical data
            data = self.yfinance.get_stock_data(
                ticker,
                period="3mo",
                allow_external=allow_external
            )

            if data is None or len(data) < 20:
                logger.debug(f"No yfinance data for {ticker}")
                return None

            # Add technical indicators
            data = self._add_technical_indicators(data)

            return data

        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {str(e)}")
            return None

    def _add_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add all technical indicators"""
        # Moving Averages
        data['SMA_20'] = data['Close'].rolling(window=20).mean()
        data['SMA_50'] = data['Close'].rolling(window=50).mean()
        data['SMA_200'] = data['Close'].rolling(window=200).mean()
        data['EMA_12'] = data['Close'].ewm(span=12, adjust=False).mean()
        data['EMA_26'] = data['Close'].ewm(span=26, adjust=False).mean()

        # RSI
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))

        # MACD
        data['MACD'] = data['EMA_12'] - data['EMA_26']
        data['MACD_Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()

        # Volume
        data['Volume_SMA'] = data['Volume'].rolling(window=20).mean()
        data['Volume_Ratio'] = data['Volume'] / data['Volume_SMA']

        # Returns
        data['Returns'] = data['Close'].pct_change(fill_method=None)
        data['Returns_20'] = data['Close'].pct_change(20, fill_method=None)

        return data


# Global singleton
_enhanced_predictor = None

def get_enhanced_predictor() -> EnhancedStockPredictor:
    """Get or create EnhancedStockPredictor singleton"""
    global _enhanced_predictor
    if _enhanced_predictor is None:
        _enhanced_predictor = EnhancedStockPredictor()
    return _enhanced_predictor
