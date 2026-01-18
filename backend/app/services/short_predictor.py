"""
TradeMaster Pro - Short Predictor Service
==========================================

AI-powered short opportunity detector. Finds overvalued stocks
with high short potential based on:
- Fundamental weakness (high P/E, low growth, poor margins)
- Technical bearish signals (below MAs, RSI overbought, volume)
- Negative news sentiment and catalysts
- Insider selling and institutional outflow
- Momentum reversal patterns

IMPORTANT: Short selling is high-risk. These are analytical signals only.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

from .yfinance_service import get_yfinance_service
from .news_service import get_news_service
from .stock_news_analyzer import get_stock_news_analyzer

logger = logging.getLogger(__name__)


class ShortPredictor:
    """
    Detect stocks with high short potential

    Scoring System (0-100 points):
    - Fundamental Weakness: 30 points (high P/E, low growth)
    - Technical Bearish: 25 points (below MAs, RSI overbought)
    - Negative Sentiment: 20 points (bad news, downgrades)
    - Momentum Reversal: 15 points (recent peak, declining)
    - Volume Signals: 10 points (distribution, low buying)
    """

    def __init__(self):
        self.yfinance = get_yfinance_service()
        self.news_service = get_news_service()
        self.news_analyzer = get_stock_news_analyzer()
        logger.info("ShortPredictor initialized")

    def find_short_opportunities(
        self,
        timeframe: str = "swing",
        limit: int = 10
    ) -> List[Dict]:
        """
        Find stocks with high short potential

        Args:
            timeframe: Trading timeframe (day, swing, long)
            limit: Number of picks to return

        Returns:
            List of short opportunity stocks with scores and analysis
        """
        logger.info(f"🔻 Searching for short opportunities ({timeframe})...")

        # Focus on large/mega cap stocks (easier to short, more liquid)
        # Avoid small caps (high volatility, hard to borrow)
        from .stock_universe import get_all_stocks

        all_tickers = get_all_stocks()

        # Analyze top 200 most liquid stocks for shorting
        tickers = all_tickers[:200]

        logger.info(f"📊 Analyzing {len(tickers)} stocks for short potential...")

        short_candidates = []

        for ticker in tickers:
            try:
                score_data = self._calculate_short_score(ticker)

                if score_data and score_data["total_score"] >= 50:
                    current_price = score_data.get("current_price", 0)
                    target_price = score_data.get("target_price", current_price)

                    if current_price > 0:
                        # For shorts, target is LOWER than current
                        potential_return = ((current_price - target_price) / current_price) * 100
                    else:
                        potential_return = 0

                    short_candidates.append({
                        "ticker": ticker,
                        "score": score_data["total_score"],
                        "currentPrice": float(current_price),
                        "targetPrice": float(target_price),
                        "potentialReturn": float(potential_return),  # Short profit
                        "confidence": int(score_data["total_score"]),
                        "timeHorizon": timeframe.upper(),
                        "reasoning": score_data["reasoning"],
                        "signals": score_data["signals"],
                        "riskLevel": "HIGH",  # Shorting is always high risk
                        "breakdown": score_data["breakdown"],
                        "category": "SHORT OPPORTUNITY 📉",
                        "company": score_data.get("company_name", ticker),
                        "sector": score_data.get("sector", "Unknown"),
                        "warnings": score_data.get("warnings", [])
                    })

            except Exception as e:
                logger.error(f"Error analyzing {ticker} for short: {str(e)}")
                continue

        # Sort by score (highest = best short opportunity)
        short_candidates.sort(key=lambda x: x["score"], reverse=True)

        # Add ranks
        for i, stock in enumerate(short_candidates[:limit], 1):
            stock["rank"] = i

        logger.info(f"🔻 Found {len(short_candidates)} short opportunities")
        return short_candidates[:limit]

    def _calculate_short_score(self, ticker: str) -> Optional[Dict]:
        """
        Calculate short opportunity score

        Returns score 0-100, higher = better short candidate
        """
        try:
            # Get current data
            quote = self.yfinance.get_quote(ticker)
            if not quote or quote.get('c', 0) == 0:
                return None

            fundamentals = self.yfinance.get_fundamentals(ticker)
            historical_data = self.yfinance.get_stock_data(ticker, period="6mo")

            if historical_data is None or len(historical_data) < 60:
                return None

            current_price = quote.get('c', 0)

            # Calculate component scores
            fundamental_weakness = self._calc_fundamental_weakness(fundamentals)  # 0-30
            technical_bearish = self._calc_technical_bearish(historical_data)  # 0-25
            negative_sentiment = self._calc_negative_sentiment(ticker)  # 0-20
            momentum_reversal = self._calc_momentum_reversal(historical_data)  # 0-15
            volume_signals = self._calc_volume_distribution(historical_data)  # 0-10

            total_score = (
                fundamental_weakness +
                technical_bearish +
                negative_sentiment +
                momentum_reversal +
                volume_signals
            )

            # Generate reasoning
            reasoning = self._generate_short_reasoning(
                fundamental_weakness,
                technical_bearish,
                negative_sentiment,
                momentum_reversal,
                volume_signals
            )

            # Generate signals
            signals = self._generate_short_signals(
                historical_data,
                fundamentals,
                quote
            )

            # Generate warnings
            warnings = self._generate_warnings(fundamentals, historical_data)

            # Estimate downside target (conservative)
            pe_ratio = fundamentals.get('peRatio', 20) if fundamentals else 20
            if pe_ratio > 30:
                # Overvalued - expect 15-30% drop
                drop_pct = min(0.30, (pe_ratio - 20) / 100)
            else:
                # Moderately valued - expect 10-15% drop
                drop_pct = 0.10

            target_price = current_price * (1 - drop_pct)

            return {
                "total_score": round(total_score, 2),
                "current_price": current_price,
                "target_price": round(target_price, 2),
                "company_name": fundamentals.get('shortName', ticker) if fundamentals else ticker,
                "sector": fundamentals.get('sector', 'Unknown') if fundamentals else 'Unknown',
                "breakdown": {
                    "fundamental_weakness": round(fundamental_weakness, 2),
                    "technical_bearish": round(technical_bearish, 2),
                    "negative_sentiment": round(negative_sentiment, 2),
                    "momentum_reversal": round(momentum_reversal, 2),
                    "volume_signals": round(volume_signals, 2)
                },
                "reasoning": reasoning,
                "signals": signals,
                "warnings": warnings
            }

        except Exception as e:
            logger.error(f"Error calculating short score for {ticker}: {str(e)}")
            return None

    def _calc_fundamental_weakness(self, fundamentals: dict) -> float:
        """Calculate fundamental weakness score (0-30 points)"""
        if not fundamentals:
            return 5  # Minimal score if no data

        score = 0

        # High P/E ratio (overvalued) - 0-12 points
        pe = fundamentals.get('peRatio', 0)
        if pe:
            if pe > 50:  # Extremely overvalued
                score += 12
            elif pe > 35:  # Very overvalued
                score += 9
            elif pe > 25:  # Overvalued
                score += 6
            elif pe > 20:  # Moderately high
                score += 3

        # Negative or low growth - 0-8 points
        revenue_growth = fundamentals.get('revenueGrowth', 0)
        if revenue_growth:
            if revenue_growth < -0.10:  # Declining revenue
                score += 8
            elif revenue_growth < 0:  # Negative growth
                score += 6
            elif revenue_growth < 0.05:  # Low growth
                score += 3

        # Poor profit margins - 0-6 points
        margin = fundamentals.get('profitMargins', 0)
        if margin:
            margin_pct = margin * 100
            if margin_pct < 0:  # Unprofitable
                score += 6
            elif margin_pct < 5:  # Very low margin
                score += 4
            elif margin_pct < 10:  # Low margin
                score += 2

        # High debt - 0-4 points
        debt_equity = fundamentals.get('debtToEquity', 0)
        if debt_equity:
            if debt_equity > 300:  # Very high debt
                score += 4
            elif debt_equity > 200:  # High debt
                score += 2

        return min(score, 30)

    def _calc_technical_bearish(self, data: pd.DataFrame) -> float:
        """Calculate technical bearish signals (0-25 points)"""
        score = 0
        current_price = data['Close'].iloc[-1]

        # Below moving averages - 0-10 points
        sma_20 = data['Close'].rolling(20).mean().iloc[-1]
        sma_50 = data['Close'].rolling(50).mean().iloc[-1] if len(data) >= 50 else sma_20
        sma_200 = data['Close'].rolling(200).mean().iloc[-1] if len(data) >= 200 else sma_50

        if current_price < sma_20:
            score += 3
        if current_price < sma_50:
            score += 4
        if current_price < sma_200:
            score += 3

        # RSI overbought - 0-8 points
        delta = data['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50

        if current_rsi > 75:  # Extremely overbought
            score += 8
        elif current_rsi > 70:  # Overbought
            score += 6
        elif current_rsi > 65:  # Moderately overbought
            score += 3

        # Death cross (SMA 50 below SMA 200) - 0-7 points
        if len(data) >= 200 and sma_50 < sma_200:
            score += 7

        return min(score, 25)

    def _calc_negative_sentiment(self, ticker: str) -> float:
        """Calculate negative news sentiment (0-20 points)"""
        score = 0

        try:
            # Get recent news
            major_news = self.news_analyzer.get_major_news(ticker, days=7)

            # Count negative news
            negative_count = sum(1 for news in major_news if news.get('sentiment', 'neutral') == 'negative')

            if negative_count >= 3:
                score += 20
            elif negative_count >= 2:
                score += 15
            elif negative_count >= 1:
                score += 10

        except:
            # If news fetch fails, use neutral score
            score = 5

        return min(score, 20)

    def _calc_momentum_reversal(self, data: pd.DataFrame) -> float:
        """Calculate momentum reversal signals (0-15 points)"""
        score = 0

        # Recent decline from highs - 0-10 points
        if len(data) >= 60:
            high_60d = data['High'].rolling(60).max().iloc[-1]
            current = data['Close'].iloc[-1]
            decline = (high_60d - current) / high_60d

            if decline > 0.25:  # 25%+ from highs
                score += 10
            elif decline > 0.15:  # 15%+ from highs
                score += 7
            elif decline > 0.10:  # 10%+ from highs
                score += 4

        # Recent negative momentum - 0-5 points
        if len(data) >= 20:
            returns_20 = (data['Close'].iloc[-1] - data['Close'].iloc[-20]) / data['Close'].iloc[-20]
            if returns_20 < -0.10:  # 10%+ decline
                score += 5
            elif returns_20 < -0.05:  # 5%+ decline
                score += 3

        return min(score, 15)

    def _calc_volume_distribution(self, data: pd.DataFrame) -> float:
        """Calculate distribution volume signals (0-10 points)"""
        score = 0

        # High volume on down days - 0-10 points
        recent_data = data.tail(10)
        down_days = recent_data[recent_data['Close'] < recent_data['Open']]

        if len(down_days) > 0:
            avg_down_volume = down_days['Volume'].mean()
            avg_total_volume = recent_data['Volume'].mean()

            if avg_down_volume > avg_total_volume * 1.3:  # Heavy selling
                score += 10
            elif avg_down_volume > avg_total_volume * 1.1:
                score += 6

        return min(score, 10)

    def _generate_short_reasoning(
        self,
        fundamental: float,
        technical: float,
        sentiment: float,
        momentum: float,
        volume: float
    ) -> str:
        """Generate reasoning for short opportunity"""
        reasons = []

        if fundamental >= 20:
            reasons.append("⚠️ severe fundamental weakness")
        elif fundamental >= 12:
            reasons.append("⚠️ fundamental concerns")

        if technical >= 18:
            reasons.append("📉 strong bearish technicals")
        elif technical >= 12:
            reasons.append("📉 bearish technical setup")

        if sentiment >= 15:
            reasons.append("📰 negative news flow")

        if momentum >= 10:
            reasons.append("🔻 momentum reversal")

        if volume >= 7:
            reasons.append("📊 distribution volume")

        if not reasons:
            return "Moderate short opportunity with mixed signals"

        return "SHORT CANDIDATE: " + ", ".join(reasons)

    def _generate_short_signals(
        self,
        data: pd.DataFrame,
        fundamentals: dict,
        quote: dict
    ) -> List[str]:
        """Generate short trading signals"""
        signals = []
        current_price = data['Close'].iloc[-1]

        # Technical signals
        sma_20 = data['Close'].rolling(20).mean().iloc[-1]
        if current_price < sma_20:
            signals.append("Below SMA 20")

        # Fundamental signals
        if fundamentals:
            pe = fundamentals.get('peRatio', 0)
            if pe and pe > 35:
                signals.append(f"High P/E: {pe:.1f}")

            growth = fundamentals.get('revenueGrowth', 0)
            if growth and growth < 0:
                signals.append("Declining Revenue")

        # Momentum signals
        if len(data) >= 20:
            returns_20 = (data['Close'].iloc[-1] - data['Close'].iloc[-20]) / data['Close'].iloc[-20]
            if returns_20 < -0.05:
                signals.append("Downtrend")

        # Volume signal
        recent_volume = data['Volume'].tail(5).mean()
        avg_volume = data['Volume'].rolling(20).mean().iloc[-1]
        if recent_volume > avg_volume * 1.2:
            signals.append("High Selling Volume")

        return signals[:5]

    def _generate_warnings(
        self,
        fundamentals: dict,
        data: pd.DataFrame
    ) -> List[str]:
        """Generate risk warnings for shorting"""
        warnings = []

        # Check for short squeeze risk
        current_price = data['Close'].iloc[-1]
        if len(data) >= 20:
            sma_20 = data['Close'].rolling(20).mean().iloc[-1]
            if current_price > sma_20 * 1.15:
                warnings.append("⚠️ High volatility - squeeze risk")

        # Check for strong balance sheet (harder to short)
        if fundamentals:
            debt_equity = fundamentals.get('debtToEquity', 0)
            current_ratio = fundamentals.get('currentRatio', 0)

            if debt_equity and debt_equity < 50 and current_ratio > 2:
                warnings.append("💪 Strong balance sheet - may be resilient")

        # Check for institutional support
        if fundamentals:
            inst_ownership = fundamentals.get('institutionalOwnership', 0)
            if inst_ownership and inst_ownership > 0.70:
                warnings.append("🏦 High institutional ownership - support risk")

        # General short warning
        warnings.append("⚠️ SHORT SELLING IS HIGH RISK - Use stops!")

        return warnings


# Global singleton
_short_predictor = None


def get_short_predictor() -> ShortPredictor:
    """Get or create singleton instance"""
    global _short_predictor
    if _short_predictor is None:
        _short_predictor = ShortPredictor()
    return _short_predictor
