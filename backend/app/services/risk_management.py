"""
TradeMaster Pro - Track Record System
======================================

Tracks and displays how well AI picks have performed.
Critical for building trust with commercial users.

Tracks:
- Historical picks and their performance
- Win rate (% of picks that were profitable)
- Average return
- Best/worst picks
- Performance by timeframe
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .yfinance_service import get_yfinance_service

logger = logging.getLogger(__name__)


class TrackRecordSystem:
    """Track and display AI pick performance"""

    def __init__(self):
        self.yfinance = get_yfinance_service()
        logger.info("TrackRecordSystem initialized")

    def calculate_pick_performance(
        self,
        ticker: str,
        entry_price: float,
        target_price: float,
        days_held: int = 7
    ) -> Dict:
        """
        Calculate how a pick performed

        Args:
            ticker: Stock symbol
            entry_price: Price when picked
            target_price: AI target price
            days_held: Days since pick (default 7 for swing)

        Returns:
            Performance metrics
        """
        try:
            # Get current price
            quote = self.yfinance.get_quote(ticker)
            if not quote:
                return None

            current_price = quote.get('c', 0)

            # Calculate performance
            actual_return = ((current_price - entry_price) / entry_price) * 100
            target_return = ((target_price - entry_price) / entry_price) * 100

            # Did it hit target?
            hit_target = current_price >= target_price

            # Status
            if actual_return > 10:
                status = "STRONG_WIN"
            elif actual_return > 5:
                status = "WIN"
            elif actual_return > 0:
                status = "SMALL_WIN"
            elif actual_return > -5:
                status = "SMALL_LOSS"
            else:
                status = "LOSS"

            return {
                'ticker': ticker,
                'entry_price': entry_price,
                'current_price': current_price,
                'target_price': target_price,
                'actual_return': round(actual_return, 2),
                'target_return': round(target_return, 2),
                'hit_target': hit_target,
                'status': status,
                'days_held': days_held
            }

        except Exception as e:
            logger.error(f"Error calculating performance for {ticker}: {str(e)}")
            return None

    def get_track_record_summary(self, picks: List[Dict]) -> Dict:
        """
        Get summary statistics for a list of picks

        Args:
            picks: List of {ticker, entry_price, target_price, days_held}

        Returns:
            Track record summary
        """
        try:
            if not picks:
                return self._empty_track_record()

            performances = []
            for pick in picks:
                perf = self.calculate_pick_performance(
                    pick['ticker'],
                    pick['entry_price'],
                    pick['target_price'],
                    pick.get('days_held', 7)
                )
                if perf:
                    performances.append(perf)

            if not performances:
                return self._empty_track_record()

            # Calculate metrics
            total_picks = len(performances)
            winners = [p for p in performances if p['actual_return'] > 0]
            losers = [p for p in performances if p['actual_return'] <= 0]

            win_rate = (len(winners) / total_picks * 100) if total_picks > 0 else 0

            avg_return = sum([p['actual_return'] for p in performances]) / total_picks
            avg_winner = sum([p['actual_return'] for p in winners]) / len(winners) if winners else 0
            avg_loser = sum([p['actual_return'] for p in losers]) / len(losers) if losers else 0

            best_pick = max(performances, key=lambda x: x['actual_return'])
            worst_pick = min(performances, key=lambda x: x['actual_return'])

            targets_hit = len([p for p in performances if p['hit_target']])
            target_hit_rate = (targets_hit / total_picks * 100) if total_picks > 0 else 0

            # Performance level
            if win_rate >= 70 and avg_return >= 5:
                performance_level = "EXCELLENT"
            elif win_rate >= 60 and avg_return >= 3:
                performance_level = "GOOD"
            elif win_rate >= 50:
                performance_level = "FAIR"
            else:
                performance_level = "POOR"

            return {
                'total_picks': total_picks,
                'win_rate': round(win_rate, 1),
                'avg_return': round(avg_return, 2),
                'avg_winner': round(avg_winner, 2),
                'avg_loser': round(avg_loser, 2),
                'best_pick': best_pick,
                'worst_pick': worst_pick,
                'targets_hit': targets_hit,
                'target_hit_rate': round(target_hit_rate, 1),
                'performance_level': performance_level,
                'performances': performances,
                'summary_message': self._get_summary_message(performance_level, win_rate, avg_return)
            }

        except Exception as e:
            logger.error(f"Error getting track record: {str(e)}")
            return self._empty_track_record()

    def get_timeframe_performance(self, picks_by_timeframe: Dict[str, List[Dict]]) -> Dict:
        """
        Get performance broken down by timeframe (day, swing, long)

        Args:
            picks_by_timeframe: Dict of timeframe -> list of picks

        Returns:
            Performance by timeframe
        """
        results = {}

        for timeframe, picks in picks_by_timeframe.items():
            results[timeframe] = self.get_track_record_summary(picks)

        return results

    def _get_summary_message(self, level: str, win_rate: float, avg_return: float) -> str:
        """Generate summary message"""
        messages = {
            "EXCELLENT": f"Outstanding performance! {win_rate:.0f}% win rate with {avg_return:.1f}% average return.",
            "GOOD": f"Solid performance. {win_rate:.0f}% win rate with {avg_return:.1f}% average return.",
            "FAIR": f"Decent track record. {win_rate:.0f}% win rate with {avg_return:.1f}% average return.",
            "POOR": f"Needs improvement. {win_rate:.0f}% win rate with {avg_return:.1f}% average return."
        }
        return messages.get(level, "Performance data available.")

    def _empty_track_record(self) -> Dict:
        """Return empty track record"""
        return {
            'total_picks': 0,
            'win_rate': 0,
            'avg_return': 0,
            'avg_winner': 0,
            'avg_loser': 0,
            'best_pick': None,
            'worst_pick': None,
            'targets_hit': 0,
            'target_hit_rate': 0,
            'performance_level': 'NONE',
            'performances': [],
            'summary_message': 'No picks to track yet'
        }


class PositionSizingCalculator:
    """Calculate optimal position size based on risk tolerance"""

    def calculate_position_size(
        self,
        account_value: float,
        risk_per_trade: float,
        entry_price: float,
        stop_loss_price: float
    ) -> Dict:
        """
        Calculate position size

        Args:
            account_value: Total account value
            risk_per_trade: % of account to risk per trade (1-5%)
            entry_price: Entry price
            stop_loss_price: Stop loss price

        Returns:
            Position sizing recommendation
        """
        try:
            # Risk amount in dollars
            risk_amount = account_value * (risk_per_trade / 100)

            # Risk per share
            risk_per_share = abs(entry_price - stop_loss_price)

            if risk_per_share == 0:
                return {
                    'error': 'Invalid stop loss - must be different from entry price'
                }

            # Number of shares
            shares = int(risk_amount / risk_per_share)

            # Position value
            position_value = shares * entry_price

            # Position as % of account
            position_pct = (position_value / account_value) * 100

            # Risk/reward if target is hit
            return {
                'shares': shares,
                'position_value': round(position_value, 2),
                'position_pct': round(position_pct, 1),
                'risk_amount': round(risk_amount, 2),
                'risk_per_share': round(risk_per_share, 2),
                'recommendation': self._get_size_recommendation(position_pct)
            }

        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return {'error': str(e)}

    def _get_size_recommendation(self, position_pct: float) -> str:
        """Get recommendation based on position size"""
        if position_pct > 20:
            return "Position too large - reduce size to manage risk"
        elif position_pct > 10:
            return "Aggressive position size - suitable for high conviction"
        elif position_pct > 5:
            return "Moderate position size - good for most trades"
        else:
            return "Conservative position size - lower risk"


class StopLossCalculator:
    """Calculate optimal stop loss levels"""

    def __init__(self):
        self.yfinance = get_yfinance_service()
        logger.info("StopLossCalculator initialized")

    def calculate_stop_loss(
        self,
        ticker: str,
        entry_price: float,
        risk_tolerance: str = 'MEDIUM'
    ) -> Dict:
        """
        Calculate stop loss recommendations

        Args:
            ticker: Stock symbol
            entry_price: Entry price
            risk_tolerance: LOW, MEDIUM, HIGH

        Returns:
            Stop loss recommendations
        """
        try:
            # Get fundamentals for volatility
            fundamentals = self.yfinance.get_fundamentals(ticker)

            # Get historical data for ATR-based stop
            historical = self.yfinance.get_stock_data(ticker, period='1mo')

            # Risk multipliers based on tolerance
            multipliers = {
                'LOW': 0.03,      # 3% stop
                'MEDIUM': 0.05,   # 5% stop
                'HIGH': 0.08      # 8% stop
            }

            multiplier = multipliers.get(risk_tolerance, 0.05)

            # Percentage-based stop loss
            pct_stop = entry_price * (1 - multiplier)

            # Technical stop (support level)
            technical_stop = None
            if historical is not None and len(historical) >= 20:
                # Use 20-day low as support
                technical_stop = historical['Low'].tail(20).min()

            # Choose the better stop
            if technical_stop and technical_stop > pct_stop:
                recommended_stop = technical_stop
                method = "Technical support level"
            else:
                recommended_stop = pct_stop
                method = f"Percentage-based ({multiplier*100:.0f}%)"

            risk_per_share = entry_price - recommended_stop
            risk_pct = (risk_per_share / entry_price) * 100

            return {
                'ticker': ticker,
                'entry_price': entry_price,
                'recommended_stop': round(recommended_stop, 2),
                'risk_per_share': round(risk_per_share, 2),
                'risk_pct': round(risk_pct, 2),
                'method': method,
                'risk_level': risk_tolerance,
                'recommendation': f"Set stop loss at ${recommended_stop:.2f} ({risk_pct:.1f}% risk)"
            }

        except Exception as e:
            logger.error(f"Error calculating stop loss for {ticker}: {str(e)}")
            return {'error': str(e)}


# Global singletons
_track_record = None
_position_calculator = None
_stop_loss_calculator = None


def get_track_record_system() -> TrackRecordSystem:
    """Get or create singleton"""
    global _track_record
    if _track_record is None:
        _track_record = TrackRecordSystem()
    return _track_record


def get_position_calculator() -> PositionSizingCalculator:
    """Get or create singleton"""
    global _position_calculator
    if _position_calculator is None:
        _position_calculator = PositionSizingCalculator()
    return _position_calculator


def get_stop_loss_calculator() -> StopLossCalculator:
    """Get or create singleton"""
    global _stop_loss_calculator
    if _stop_loss_calculator is None:
        _stop_loss_calculator = StopLossCalculator()
    return _stop_loss_calculator
