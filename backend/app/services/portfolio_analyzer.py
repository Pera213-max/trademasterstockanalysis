"""
TradeMaster Pro - Portfolio Health Analyzer
===========================================

Analyzes user portfolio for:
- Risk concentration
- Sector diversification
- Volatility assessment
- Correlation analysis (NEW!)
- Sharpe ratio & risk-adjusted returns (NEW!)
- Benchmark comparison vs S&P 500 (NEW!)
- Performance tracking (NEW!)
- Rebalancing recommendations
"""

import logging
from typing import List, Dict, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from .yfinance_service import get_yfinance_service
from .finnhub_service import get_finnhub_service

logger = logging.getLogger(__name__)


class PortfolioHealthAnalyzer:
    """Analyze portfolio health and provide recommendations"""

    def __init__(self):
        self.yfinance = get_yfinance_service()
        self.finnhub = get_finnhub_service()
        logger.info("PortfolioHealthAnalyzer initialized")

    def analyze_portfolio(self, holdings: List[Dict]) -> Dict:
        """
        Analyze portfolio health

        Args:
            holdings: List of {ticker: str, shares: int, avg_cost: float}

        Returns:
            Comprehensive portfolio analysis
        """
        try:
            if not holdings:
                return self._empty_portfolio_response()

            # Get current data for all holdings
            positions = []
            total_value = 0

            for holding in holdings:
                ticker = holding['ticker']
                shares = holding['shares']
                avg_cost = holding.get('avg_cost', 0)

                # Get current price
                quote = self.yfinance.get_quote(ticker, allow_external=False)
                if not quote:
                    continue

                current_price = quote.get('c', 0)
                current_value = current_price * shares
                cost_basis = avg_cost * shares
                gain_loss = current_value - cost_basis if cost_basis > 0 else 0
                gain_loss_pct = (gain_loss / cost_basis * 100) if cost_basis > 0 else 0

                # Get fundamentals
                fundamentals = self.yfinance.get_fundamentals(ticker, allow_external=False)
                holding_currency = holding.get('currency')
                currency = holding_currency or (fundamentals.get('currency') if fundamentals else None) or 'EUR'

                # Extract dividend info
                dividend_yield = fundamentals.get('dividendYield', 0) if fundamentals else 0
                dividend_yield = dividend_yield if dividend_yield else 0
                expected_annual_dividend = current_value * dividend_yield

                position = {
                    'ticker': ticker,
                    'shares': shares,
                    'current_price': current_price,
                    'current_value': current_value,
                    'cost_basis': cost_basis,
                    'gain_loss': gain_loss,
                    'gain_loss_pct': gain_loss_pct,
                    'name': fundamentals.get('shortName', ticker) if fundamentals else ticker,
                    'currency': currency,
                    'sector': fundamentals.get('sector', 'Unknown') if fundamentals else 'Unknown',
                    'beta': fundamentals.get('beta', 1) if fundamentals else 1,
                    'dividend_yield': round(dividend_yield * 100, 2) if dividend_yield else 0,
                    'expected_annual_dividend': round(expected_annual_dividend, 2)
                }

                positions.append(position)
                total_value += current_value

            # FX conversion (EUR) for mixed-currency portfolios
            currencies = {p.get('currency') or 'EUR' for p in positions}
            fx_rates = self._get_fx_rates(list(currencies))
            positions_calc = []
            total_value_eur = 0.0
            total_gain_loss_eur = 0.0
            total_cost_basis_eur = 0.0
            for p in positions:
                currency = p.get('currency') or 'EUR'
                fx_rate = fx_rates.get(currency, 1.0)
                current_value_eur = p['current_value'] * fx_rate
                gain_loss_eur = p['gain_loss'] * fx_rate
                cost_basis_eur = p['cost_basis'] * fx_rate
                total_value_eur += current_value_eur
                total_gain_loss_eur += gain_loss_eur
                total_cost_basis_eur += cost_basis_eur
                p['current_value_eur'] = current_value_eur
                p['gain_loss_eur'] = gain_loss_eur
                p['cost_basis_eur'] = cost_basis_eur
                p_calc = dict(p)
                p_calc['current_value'] = current_value_eur
                p_calc['gain_loss'] = gain_loss_eur
                p_calc['cost_basis'] = cost_basis_eur
                positions_calc.append(p_calc)

            total_gain_loss_pct_eur = (total_gain_loss_eur / total_cost_basis_eur * 100) if total_cost_basis_eur > 0 else 0

            # Calculate metrics (use EUR-converted values for weights)
            risk_score = self._calculate_risk_score(positions_calc, total_value_eur if total_value_eur else total_value)
            diversification = self._analyze_diversification(positions_calc, total_value_eur if total_value_eur else total_value)
            rebalancing = self._get_rebalancing_recommendations(positions_calc, total_value_eur if total_value_eur else total_value)

            # NEW: Advanced analytics
            correlation_matrix = self._calculate_correlation_matrix([p['ticker'] for p in positions])
            sharpe_ratio = self._calculate_sharpe_ratio(positions)
            benchmark_comparison = self._compare_to_benchmark(positions_calc)
            performance_metrics = self._calculate_performance_metrics(positions_calc, total_value_eur if total_value_eur else total_value)

            health_score = self._calculate_health_score(risk_score, diversification)

            # Calculate total gain/loss
            total_gain_loss = sum([p['gain_loss'] for p in positions])
            total_cost_basis = sum([p['cost_basis'] for p in positions if p['cost_basis'] > 0])
            total_gain_loss_pct = (total_gain_loss / total_cost_basis * 100) if total_cost_basis > 0 else 0

            # Convert sectors dict to array for frontend
            sector_breakdown = [
                {'sector': sector, 'percentage': pct, 'count': 1}
                for sector, pct in diversification['sectors'].items()
            ]

            return {
                'total_value': round(total_value, 2),
                'total_positions': len(positions),
                'health_score': health_score,
                'total_gain_loss': round(total_gain_loss, 2),
                'total_gain_loss_pct': round(total_gain_loss_pct, 2),
                'total_value_eur': round(total_value_eur, 2),
                'total_gain_loss_eur': round(total_gain_loss_eur, 2),
                'total_gain_loss_pct_eur': round(total_gain_loss_pct_eur, 2),
                'reporting_currency': 'EUR',
                'fx_rates': fx_rates,
                'risk_analysis': {
                    'overall_risk': risk_score['level'],
                    'concentration_risk': risk_score['concentration']['max_position'],
                    'volatility_risk': risk_score['volatility']['weighted_beta'],
                    'losses_risk': risk_score['losses']['losing_positions'],
                    'total_risk_score': risk_score['score']
                },
                'diversification': {
                    'score': diversification['score'],
                    'status': diversification['level'],
                    'sector_breakdown': sector_breakdown
                },
                'rebalancing': rebalancing['recommendations'],
                'positions': [
                    {
                        'ticker': p['ticker'],
                        'name': p.get('name'),
                        'shares': p['shares'],
                        'entry_price': p.get('cost_basis', 0) / p['shares'] if p['shares'] > 0 else 0,
                        'current_price': p['current_price'],
                        'value': round(p['current_value'], 2),
                        'value_eur': round(p.get('current_value_eur', p['current_value']), 2),
                        'gain_loss': round(p['gain_loss'], 2),
                        'gain_loss_eur': round(p.get('gain_loss_eur', p['gain_loss']), 2),
                        'gain_loss_pct': round(p['gain_loss_pct'], 2),
                        'weight': round((p.get('current_value_eur', p['current_value']) / total_value_eur * 100) if total_value_eur > 0 else 0, 2),
                        'sector': p['sector'],
                        'currency': p.get('currency'),
                        'dividend_yield': p.get('dividend_yield', 0),
                        'expected_annual_dividend': p.get('expected_annual_dividend', 0),
                    }
                    for p in positions
                ],
                # Dividend analysis
                'dividends': {
                    'total_expected_annual': round(sum(p.get('expected_annual_dividend', 0) for p in positions), 2),
                    'portfolio_yield': round((sum(p.get('expected_annual_dividend', 0) for p in positions) / total_value_eur * 100) if total_value_eur > 0 else 0, 2),
                    'dividend_paying_positions': len([p for p in positions if p.get('dividend_yield', 0) > 0]),
                },
                # NEW: Advanced analytics
                'correlation': correlation_matrix,
                'sharpe_ratio': sharpe_ratio,
                'benchmark_comparison': benchmark_comparison,
                'performance': performance_metrics,
                'summary': self._generate_summary(health_score, risk_score, diversification),
                'alerts': self._generate_alerts(positions, risk_score, diversification)
            }

        except Exception as e:
            logger.error(f"Error analyzing portfolio: {str(e)}")
            return self._empty_portfolio_response()

    def _calculate_risk_score(self, positions: List[Dict], total_value: float) -> Dict:
        """Calculate portfolio risk metrics"""
        if not positions or total_value == 0:
            return {'score': 50, 'level': 'MEDIUM', 'factors': []}

        # Concentration risk
        max_position_pct = max([p['current_value'] / total_value * 100 for p in positions])
        concentration_risk = 'HIGH' if max_position_pct > 25 else 'MEDIUM' if max_position_pct > 15 else 'LOW'

        # Volatility risk (beta-weighted)
        weighted_beta = sum([p['beta'] * (p['current_value'] / total_value) for p in positions])
        volatility_risk = 'HIGH' if weighted_beta > 1.3 else 'MEDIUM' if weighted_beta > 0.8 else 'LOW'

        # Unrealized losses
        losers = [p for p in positions if p['gain_loss'] < 0]
        loss_risk = 'HIGH' if len(losers) > len(positions) / 2 else 'MEDIUM' if losers else 'LOW'

        # Calculate overall risk score (0-100, lower is better)
        risk_factors = {
            'concentration': 30 if concentration_risk == 'HIGH' else 15 if concentration_risk == 'MEDIUM' else 5,
            'volatility': 40 if volatility_risk == 'HIGH' else 20 if volatility_risk == 'MEDIUM' else 10,
            'losses': 30 if loss_risk == 'HIGH' else 15 if loss_risk == 'MEDIUM' else 5
        }

        risk_score = sum(risk_factors.values())
        risk_level = 'HIGH' if risk_score > 60 else 'MEDIUM' if risk_score > 35 else 'LOW'

        return {
            'score': risk_score,
            'level': risk_level,
            'concentration': {'level': concentration_risk, 'max_position': max_position_pct},
            'volatility': {'level': volatility_risk, 'weighted_beta': round(weighted_beta, 2)},
            'losses': {'level': loss_risk, 'losing_positions': len(losers)},
            'factors': self._get_risk_factors(concentration_risk, volatility_risk, loss_risk)
        }

    def _analyze_diversification(self, positions: List[Dict], total_value: float) -> Dict:
        """Analyze portfolio diversification"""
        if not positions:
            return {'score': 0, 'level': 'POOR', 'sectors': {}}

        # Sector breakdown
        sectors = {}
        for p in positions:
            sector = p['sector']
            pct = (p['current_value'] / total_value * 100)
            sectors[sector] = sectors.get(sector, 0) + pct

        # Number of sectors
        num_sectors = len(sectors)

        # Largest sector concentration
        max_sector_pct = max(sectors.values()) if sectors else 100

        # Diversification score (0-100, higher is better)
        sector_score = min(num_sectors * 20, 60)  # Max 60 points for 3+ sectors
        balance_score = 40 if max_sector_pct < 40 else 20 if max_sector_pct < 60 else 10

        div_score = sector_score + balance_score
        div_level = 'EXCELLENT' if div_score >= 80 else 'GOOD' if div_score >= 60 else 'FAIR' if div_score >= 40 else 'POOR'

        return {
            'score': div_score,
            'level': div_level,
            'num_sectors': num_sectors,
            'sectors': {k: round(v, 1) for k, v in sectors.items()},
            'recommendations': self._get_diversification_tips(num_sectors, max_sector_pct, sectors)
        }

    def _get_rebalancing_recommendations(self, positions: List[Dict], total_value: float) -> Dict:
        """Generate rebalancing recommendations"""
        if not positions or total_value == 0:
            return {'needed': False, 'recommendations': []}

        recommendations = []

        # Check for over-concentrated positions (>20% of portfolio)
        for p in positions:
            pct = (p['current_value'] / total_value * 100)
            if pct > 20:
                recommendations.append({
                    'action': 'TRIM',
                    'ticker': p['ticker'],
                    'current_pct': round(pct, 1),
                    'suggested_pct': 15.0,
                    'reason': f"Position is {pct:.1f}% of portfolio - reduce to 15% for better risk management"
                })

        # Check for big losers (>25% down)
        for p in positions:
            pct = (p['current_value'] / total_value * 100)
            if p['gain_loss_pct'] < -25:
                recommendations.append({
                    'action': 'REVIEW',
                    'ticker': p['ticker'],
                    'current_pct': round(pct, 1),
                    'suggested_pct': None,  # No specific target for review
                    'loss_pct': round(p['gain_loss_pct'], 1),
                    'reason': f"Down {abs(p['gain_loss_pct']):.1f}% - review fundamentals or cut losses"
                })

        # Check for big winners (consider taking profits)
        for p in positions:
            pct = (p['current_value'] / total_value * 100)
            if p['gain_loss_pct'] > 100 and pct > 15:
                recommendations.append({
                    'action': 'TAKE_PROFITS',
                    'ticker': p['ticker'],
                    'current_pct': round(pct, 1),
                    'suggested_pct': round(pct * 0.7, 1),  # Suggest reducing by 30%
                    'gain_pct': round(p['gain_loss_pct'], 1),
                    'reason': f"Up {p['gain_loss_pct']:.1f}% - consider taking partial profits"
                })

        return {
            'needed': len(recommendations) > 0,
            'recommendations': recommendations[:5]  # Top 5
        }

    def _calculate_health_score(self, risk_score: Dict, diversification: Dict) -> int:
        """Calculate overall portfolio health score (0-100)"""
        # Lower risk = higher health
        risk_component = 100 - risk_score['score']
        # Higher diversification = higher health
        div_component = diversification['score']

        # Weighted average (60% risk, 40% diversification)
        health = (risk_component * 0.6) + (div_component * 0.4)

        return int(health)

    def _generate_summary(self, health_score: int, risk_score: Dict, diversification: Dict) -> Dict:
        """Generate portfolio summary"""
        if health_score >= 80:
            status = "EXCELLENT"
            message = "Your portfolio is well-balanced with good diversification and manageable risk."
        elif health_score >= 60:
            status = "GOOD"
            message = "Your portfolio is in decent shape but could benefit from some adjustments."
        elif health_score >= 40:
            status = "FAIR"
            message = "Your portfolio needs attention - consider rebalancing to reduce risk."
        else:
            status = "POOR"
            message = "Your portfolio has significant risks - rebalancing strongly recommended."

        return {
            'status': status,
            'message': message,
            'health_score': health_score,
            'risk_level': risk_score['level'],
            'diversification_level': diversification['level']
        }

    def _generate_alerts(self, positions: List[Dict], risk_score: Dict, diversification: Dict) -> List[Dict]:
        """Generate portfolio alerts"""
        alerts = []

        # High risk alert
        if risk_score['level'] == 'HIGH':
            alerts.append({
                'severity': 'HIGH',
                'type': 'RISK',
                'message': 'Portfolio risk is high - review positions and consider rebalancing',
                'action': 'Review risk factors and reduce concentrated positions'
            })

        # Poor diversification
        if diversification['level'] in ['POOR', 'FAIR']:
            alerts.append({
                'severity': 'MEDIUM',
                'type': 'DIVERSIFICATION',
                'message': f'Portfolio only spans {diversification["num_sectors"]} sectors',
                'action': 'Add positions in different sectors for better diversification'
            })

        # Big losers
        big_losers = [p for p in positions if p['gain_loss_pct'] < -30]
        if big_losers:
            alerts.append({
                'severity': 'HIGH',
                'type': 'LOSSES',
                'message': f'{len(big_losers)} position(s) down >30%',
                'action': 'Review fundamentals or consider cutting losses'
            })

        return alerts

    def _get_risk_factors(self, concentration: str, volatility: str, losses: str) -> List[str]:
        """Get list of risk factors"""
        factors = []
        if concentration == 'HIGH':
            factors.append("Over-concentrated in single positions")
        if volatility == 'HIGH':
            factors.append("High portfolio volatility (beta)")
        if losses == 'HIGH':
            factors.append("Multiple positions with unrealized losses")
        return factors

    def _get_diversification_tips(self, num_sectors: int, max_pct: float, sectors: Dict) -> List[str]:
        """Get diversification improvement tips"""
        tips = []

        if num_sectors < 3:
            tips.append(f"Add positions in {3 - num_sectors} more sectors")

        if max_pct > 50:
            max_sector = max(sectors.items(), key=lambda x: x[1])[0]
            tips.append(f"Reduce {max_sector} concentration (currently {max_pct:.1f}%)")

        if num_sectors >= 4:
            tips.append("Good sector coverage - maintain this diversity")

        return tips

    def _get_fx_rates(self, currencies: List[str]) -> Dict[str, float]:
        """
        Fetch FX conversion rates to EUR.

        Returns mapping: currency -> EUR conversion factor
        (value_in_eur = value_in_currency * factor)
        """
        if not currencies:
            return {"EUR": 1.0}

        fx_pairs = {
            "USD": "EURUSD=X",
            "SEK": "EURSEK=X",
            "NOK": "EURNOK=X",
            "DKK": "EURDKK=X",
            "GBP": "EURGBP=X",
            "CHF": "EURCHF=X",
            "JPY": "EURJPY=X",
            "CAD": "EURCAD=X",
        }

        rates = {"EUR": 1.0}
        for currency in currencies:
            if not currency or currency == "EUR" or currency in rates:
                continue
            pair = fx_pairs.get(currency)
            if not pair:
                continue
            quote = self.yfinance.get_quote(pair, allow_external=False)
            rate = quote.get("c") if quote else None
            if rate and rate > 0:
                # Pair is EURXXX, so 1 EUR = rate XXX -> convert XXX to EUR by dividing
                rates[currency] = 1.0 / rate

        return rates

    def _calculate_correlation_matrix(self, tickers: List[str]) -> Dict:
        """
        Calculate correlation matrix between portfolio positions

        High correlation = moves together = less diversification benefit
        """
        try:
            if len(tickers) < 2:
                return {
                    'avg_correlation': 0,
                    'max_correlation': 0,
                    'message': 'Need at least 2 positions for correlation analysis'
                }

            # Get 3 months of historical data for each ticker
            returns_data = {}
            for ticker in tickers:
                try:
                    data = self.yfinance.get_stock_data(
                        ticker,
                        period='3mo',
                        allow_external=False
                    )
                    if data is not None and len(data) > 20:
                        returns_data[ticker] = data['Close'].pct_change().dropna()
                except Exception as e:
                    logger.warning(f"Could not fetch data for {ticker}: {str(e)}")
                    continue

            if len(returns_data) < 2:
                return {
                    'avg_correlation': 0,
                    'max_correlation': 0,
                    'message': 'Insufficient data for correlation analysis'
                }

            # Create returns dataframe
            returns_df = pd.DataFrame(returns_data)

            # Calculate correlation matrix
            corr_matrix = returns_df.corr()

            # Get average correlation (excluding diagonal)
            mask = np.ones_like(corr_matrix, dtype=bool)
            np.fill_diagonal(mask, 0)
            avg_corr = corr_matrix.where(mask).mean().mean()

            # Get max correlation (excluding diagonal)
            max_corr = corr_matrix.where(mask).max().max()

            # Assessment
            if avg_corr > 0.7:
                assessment = 'HIGH - Positions move together, limited diversification benefit'
            elif avg_corr > 0.4:
                assessment = 'MODERATE - Some diversification benefit'
            else:
                assessment = 'LOW - Good diversification, positions move independently'

            return {
                'avg_correlation': round(float(avg_corr), 2),
                'max_correlation': round(float(max_corr), 2),
                'assessment': assessment,
                'message': f'Average correlation: {avg_corr:.2f} - {assessment}'
            }

        except Exception as e:
            logger.error(f"Error calculating correlation: {str(e)}")
            return {
                'avg_correlation': 0,
                'max_correlation': 0,
                'message': 'Correlation analysis unavailable'
            }

    def _guess_currency_from_ticker(self, ticker: str) -> str:
        if not ticker:
            return "EUR"
        normalized = str(ticker).upper()
        if normalized.endswith(".HE") or normalized.startswith("^OMX") or normalized.startswith("^STOXX") or normalized.startswith("^GDAXI"):
            return "EUR"
        if normalized.endswith(".ST"):
            return "SEK"
        if normalized.endswith(".OL"):
            return "NOK"
        if normalized.endswith(".CO"):
            return "DKK"
        if normalized.endswith(".L"):
            return "GBP"
        return "USD"

    def get_portfolio_performance_series(
        self,
        holdings: List[Dict],
        period: str = "6mo",
        benchmarks: Optional[List[str]] = None
    ) -> Dict:
        """
        Build normalized performance series for portfolio vs benchmarks.

        Returns daily index series (base=100).
        """
        if not holdings:
            return {"series": [], "benchmarks": [], "message": "No holdings"}

        tickers = [h.get("ticker") for h in holdings if h.get("ticker")]
        if not tickers:
            return {"series": [], "benchmarks": [], "message": "No tickers"}

        bench = benchmarks or ["^OMXH25", "SPY"]

        # Currency map for holdings
        currencies = []
        for holding in holdings:
            currency = holding.get("currency")
            if not currency:
                currency = self._guess_currency_from_ticker(holding.get("ticker", ""))
            currencies.append(currency)

        fx_rates = self._get_fx_rates(list(set(currencies)))

        # Fetch price history
        data_map = self.yfinance.get_multiple_stocks(
            tickers,
            period=period,
            allow_external=False
        )
        if not data_map:
            return {"series": [], "benchmarks": bench, "message": "No data"}

        # Build portfolio value series
        series_list = []
        for holding in holdings:
            ticker = holding.get("ticker")
            shares = holding.get("shares", 0)
            if not ticker or shares <= 0:
                continue
            df = data_map.get(ticker)
            if df is None or df.empty or "Close" not in df.columns:
                continue
            currency = holding.get("currency") or self._guess_currency_from_ticker(ticker)
            fx_rate = fx_rates.get(currency, 1.0)
            values = df["Close"] * float(shares) * fx_rate
            series_list.append(values.rename(ticker))

        if not series_list:
            return {"series": [], "benchmarks": bench, "message": "No series"}

        portfolio_df = pd.concat(series_list, axis=1, join="outer").sort_index().ffill().dropna()
        portfolio_series = portfolio_df.sum(axis=1)

        # Benchmarks
        bench_data = self.yfinance.get_multiple_stocks(
            bench,
            period=period,
            allow_external=False
        )
        bench_series = {}
        if bench_data:
            for ticker in bench:
                df = bench_data.get(ticker)
                if df is None or df.empty or "Close" not in df.columns:
                    continue
                bench_series[ticker] = df["Close"].rename(ticker)

        # Merge and normalize (base 100)
        combined = pd.DataFrame({"portfolio": portfolio_series})
        for ticker, series in bench_series.items():
            combined = combined.join(series, how="outer")

        combined = combined.sort_index().ffill().dropna()
        if combined.empty:
            return {"series": [], "benchmarks": bench, "message": "No combined data"}

        normalized = combined.copy()
        for col in normalized.columns:
            base = normalized[col].iloc[0]
            normalized[col] = (normalized[col] / base * 100) if base else normalized[col]

        output = [
            {"date": idx.strftime("%Y-%m-%d"), **{col: round(val, 2) for col, val in row.items()}}
            for idx, row in normalized.iterrows()
        ]

        return {
            "series": output,
            "benchmarks": list(bench_series.keys()),
            "period": period,
            "fx_rates": fx_rates,
        }

    def _calculate_sharpe_ratio(self, positions: List[Dict]) -> Dict:
        """
        Calculate Sharpe Ratio (risk-adjusted returns)

        Sharpe > 2.0 = Excellent
        Sharpe > 1.0 = Good
        Sharpe > 0.5 = Fair
        Sharpe < 0.5 = Poor
        """
        try:
            if not positions:
                return {'ratio': 0, 'assessment': 'N/A', 'message': 'No positions'}

            # Calculate portfolio return
            total_return = sum([p['gain_loss_pct'] for p in positions if p.get('cost_basis', 0) > 0])
            avg_return = total_return / len(positions) if positions else 0

            # Estimate annualized return (assuming holdings period)
            ann_return = avg_return  # Simplified - in reality would need time period

            # Calculate portfolio volatility (std dev of returns)
            returns = [p['gain_loss_pct'] for p in positions if p.get('cost_basis', 0) > 0]
            volatility = np.std(returns) if returns else 0

            # Risk-free rate (assume 4% treasury)
            risk_free_rate = 4.0

            # Sharpe ratio = (Return - Risk Free Rate) / Volatility
            sharpe = (ann_return - risk_free_rate) / volatility if volatility > 0 else 0

            # Assessment
            if sharpe > 2.0:
                assessment = 'EXCELLENT - Outstanding risk-adjusted returns'
            elif sharpe > 1.0:
                assessment = 'GOOD - Solid risk-adjusted performance'
            elif sharpe > 0.5:
                assessment = 'FAIR - Acceptable risk/reward ratio'
            elif sharpe > 0:
                assessment = 'POOR - Low returns for the risk taken'
            else:
                assessment = 'NEGATIVE - Losses with high volatility'

            return {
                'ratio': round(float(sharpe), 2),
                'assessment': assessment,
                'annual_return': round(ann_return, 2),
                'volatility': round(volatility, 2),
                'message': f'Sharpe Ratio: {sharpe:.2f} - {assessment}'
            }

        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {str(e)}")
            return {'ratio': 0, 'assessment': 'N/A', 'message': 'Sharpe ratio unavailable'}

    def _compare_to_benchmark(self, positions: List[Dict]) -> Dict:
        """
        Compare portfolio performance to S&P 500 benchmark

        Alpha = Portfolio Return - Benchmark Return
        """
        try:
            if not positions:
                return {'alpha': 0, 'message': 'No positions'}

            # Calculate portfolio return
            total_gain_loss = sum([p['gain_loss'] for p in positions])
            total_cost = sum([p['cost_basis'] for p in positions if p['cost_basis'] > 0])
            portfolio_return = (total_gain_loss / total_cost * 100) if total_cost > 0 else 0

            # Get S&P 500 (SPY) performance for comparison
            try:
                spy_data = self.yfinance.get_stock_data(
                    'SPY',
                    period='3mo',
                    allow_external=False
                )
                if spy_data is not None and len(spy_data) > 20:
                    spy_return = ((spy_data['Close'].iloc[-1] - spy_data['Close'].iloc[0]) /
                                 spy_data['Close'].iloc[0] * 100)
                else:
                    spy_return = 8.0  # Assume 8% for fallback
            except:
                spy_return = 8.0  # Fallback S&P 500 average

            # Calculate alpha (excess return vs benchmark)
            alpha = portfolio_return - spy_return

            # Assessment
            if alpha > 10:
                assessment = 'CRUSHING IT - Significantly outperforming S&P 500'
            elif alpha > 5:
                assessment = 'EXCELLENT - Strong outperformance vs market'
            elif alpha > 0:
                assessment = 'GOOD - Beating the market'
            elif alpha > -5:
                assessment = 'FAIR - Slightly underperforming market'
            else:
                assessment = 'POOR - Significantly underperforming market'

            return {
                'portfolio_return': round(portfolio_return, 2),
                'benchmark_return': round(spy_return, 2),
                'alpha': round(alpha, 2),
                'assessment': assessment,
                'message': f'Alpha: {alpha:+.2f}% vs S&P 500 - {assessment}'
            }

        except Exception as e:
            logger.error(f"Error comparing to benchmark: {str(e)}")
            return {'alpha': 0, 'message': 'Benchmark comparison unavailable'}

    def _calculate_performance_metrics(self, positions: List[Dict], total_value: float) -> Dict:
        """
        Calculate detailed performance metrics

        - Winners vs Losers
        - Best/Worst performers
        - Win rate
        """
        try:
            if not positions:
                return {
                    'winners': 0,
                    'losers': 0,
                    'win_rate': 0,
                    'best_performer': None,
                    'worst_performer': None
                }

            # Count winners and losers
            winners = [p for p in positions if p['gain_loss_pct'] > 0]
            losers = [p for p in positions if p['gain_loss_pct'] < 0]
            neutral = len(positions) - len(winners) - len(losers)

            win_rate = (len(winners) / len(positions) * 100) if positions else 0

            # Find best and worst performers
            best = max(positions, key=lambda x: x['gain_loss_pct'])
            worst = min(positions, key=lambda x: x['gain_loss_pct'])

            return {
                'total_positions': len(positions),
                'winners': len(winners),
                'losers': len(losers),
                'neutral': neutral,
                'win_rate': round(win_rate, 1),
                'best_performer': {
                    'ticker': best['ticker'],
                    'return': round(best['gain_loss_pct'], 2),
                    'value': round(best['current_value'], 2)
                },
                'worst_performer': {
                    'ticker': worst['ticker'],
                    'return': round(worst['gain_loss_pct'], 2),
                    'value': round(worst['current_value'], 2)
                },
                'avg_position_return': round(sum([p['gain_loss_pct'] for p in positions]) / len(positions), 2),
                'message': f'{len(winners)} winners, {len(losers)} losers - {win_rate:.1f}% win rate'
            }

        except Exception as e:
            logger.error(f"Error calculating performance metrics: {str(e)}")
            return {
                'winners': 0,
                'losers': 0,
                'win_rate': 0,
                'best_performer': None,
                'worst_performer': None
            }

    def _empty_portfolio_response(self) -> Dict:
        """Return empty portfolio response"""
        return {
            'total_value': 0,
            'total_positions': 0,
            'health_score': 0,
            'total_gain_loss': 0,
            'total_gain_loss_pct': 0,
            'risk_analysis': {
                'overall_risk': 'UNKNOWN',
                'concentration_risk': 0,
                'volatility_risk': 0,
                'losses_risk': 0,
                'total_risk_score': 0
            },
            'diversification': {
                'score': 0,
                'status': 'POOR',
                'sector_breakdown': []
            },
            'rebalancing': [],
            'positions': [],
            'correlation': {'avg_correlation': 0, 'message': 'No data'},
            'sharpe_ratio': {'ratio': 0, 'message': 'No data'},
            'benchmark_comparison': {'alpha': 0, 'message': 'No data'},
            'performance': {'winners': 0, 'losers': 0, 'win_rate': 0},
            'summary': {
                'status': 'EMPTY',
                'message': 'Add positions to analyze your portfolio',
                'health_score': 0
            },
            'alerts': []
        }


# Global singleton
_portfolio_analyzer = None


def get_portfolio_analyzer() -> PortfolioHealthAnalyzer:
    """Get or create singleton instance"""
    global _portfolio_analyzer
    if _portfolio_analyzer is None:
        _portfolio_analyzer = PortfolioHealthAnalyzer()
    return _portfolio_analyzer
