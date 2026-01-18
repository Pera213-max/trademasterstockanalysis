"""
Macro Analyzer Service for TradeMaster Pro

Analyzes macroeconomic indicators and market environment.
Integrates FRED API, market indices (DXY, VIX), and provides comprehensive macro analysis.
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MacroAnalyzer:
    """
    Macroeconomic analyzer and market environment tracker

    Features:
    - FRED economic data (interest rates, CPI, unemployment, GDP)
    - US Dollar Index (DXY) tracking
    - VIX volatility index monitoring
    - Market environment analysis (Bull/Bear, Risk On/Off)
    - Sector rotation recommendations
    - Redis caching for performance
    """

    def __init__(self, fred_api_key: Optional[str] = None, redis_client=None):
        """
        Initialize MacroAnalyzer

        Args:
            fred_api_key: FRED API key (get free at https://fred.stlouisfed.org/docs/api/api_key.html)
            redis_client: Redis client for caching (optional)
        """
        self.fred_api_key = fred_api_key
        self.redis_client = redis_client
        self.cache_ttl = 3600  # 1 hour cache

        # Initialize FRED client
        self.fred = None
        if fred_api_key:
            try:
                from fredapi import Fred
                self.fred = Fred(api_key=fred_api_key)
                logger.info("FRED API initialized successfully")
            except ImportError:
                logger.warning("fredapi library not installed. Install with: pip install fredapi")
            except Exception as e:
                logger.error(f"Failed to initialize FRED API: {e}")

    def get_fred_data(self) -> Dict:
        """
        Fetch key economic indicators from FRED API

        Returns:
            Dict with interest rates, CPI, unemployment, GDP data
        """
        if not self.fred:
            logger.warning("FRED API not available. Using mock data.")
            return self._get_mock_fred_data()

        try:
            logger.info("Fetching FRED economic data...")

            # Federal Funds Rate (Interest Rate)
            fed_rate_series = self.fred.get_series('DFF')
            fed_rate = fed_rate_series.iloc[-1] if not fed_rate_series.empty else None

            # Consumer Price Index (CPI - Inflation)
            cpi_series = self.fred.get_series('CPIAUCSL')
            cpi_current = cpi_series.iloc[-1] if not cpi_series.empty else None
            cpi_year_ago = cpi_series.iloc[-13] if len(cpi_series) >= 13 else None
            cpi_yoy = ((cpi_current / cpi_year_ago - 1) * 100) if (cpi_current and cpi_year_ago) else None

            # Unemployment Rate
            unemployment_series = self.fred.get_series('UNRATE')
            unemployment = unemployment_series.iloc[-1] if not unemployment_series.empty else None

            # GDP Growth Rate (Quarterly)
            gdp_series = self.fred.get_series('A191RL1Q225SBEA')
            gdp_growth = gdp_series.iloc[-1] if not gdp_series.empty else None

            # 10-Year Treasury Yield
            treasury_10y_series = self.fred.get_series('DGS10')
            treasury_10y = treasury_10y_series.iloc[-1] if not treasury_10y_series.empty else None

            # 2-Year Treasury Yield (for yield curve)
            treasury_2y_series = self.fred.get_series('DGS2')
            treasury_2y = treasury_2y_series.iloc[-1] if not treasury_2y_series.empty else None

            # Calculate yield curve spread (10Y - 2Y)
            yield_curve_spread = (treasury_10y - treasury_2y) if (treasury_10y and treasury_2y) else None

            # Personal Consumption Expenditures (PCE) - Fed's preferred inflation measure
            pce_series = self.fred.get_series('PCEPI')
            pce_current = pce_series.iloc[-1] if not pce_series.empty else None
            pce_year_ago = pce_series.iloc[-13] if len(pce_series) >= 13 else None
            pce_yoy = ((pce_current / pce_year_ago - 1) * 100) if (pce_current and pce_year_ago) else None

            fred_data = {
                'fed_funds_rate': {
                    'value': round(float(fed_rate), 2) if fed_rate else None,
                    'label': 'Federal Funds Rate',
                    'unit': '%',
                    'last_updated': datetime.now().isoformat()
                },
                'cpi': {
                    'value': round(float(cpi_current), 2) if cpi_current else None,
                    'yoy_change': round(float(cpi_yoy), 2) if cpi_yoy else None,
                    'label': 'Consumer Price Index',
                    'unit': 'Index / % YoY',
                    'last_updated': datetime.now().isoformat()
                },
                'unemployment': {
                    'value': round(float(unemployment), 2) if unemployment else None,
                    'label': 'Unemployment Rate',
                    'unit': '%',
                    'last_updated': datetime.now().isoformat()
                },
                'gdp_growth': {
                    'value': round(float(gdp_growth), 2) if gdp_growth else None,
                    'label': 'GDP Growth Rate',
                    'unit': '% (Quarterly)',
                    'last_updated': datetime.now().isoformat()
                },
                'treasury_10y': {
                    'value': round(float(treasury_10y), 2) if treasury_10y else None,
                    'label': '10-Year Treasury Yield',
                    'unit': '%',
                    'last_updated': datetime.now().isoformat()
                },
                'treasury_2y': {
                    'value': round(float(treasury_2y), 2) if treasury_2y else None,
                    'label': '2-Year Treasury Yield',
                    'unit': '%',
                    'last_updated': datetime.now().isoformat()
                },
                'yield_curve': {
                    'spread': round(float(yield_curve_spread), 2) if yield_curve_spread else None,
                    'label': 'Yield Curve (10Y-2Y)',
                    'unit': 'bps',
                    'inverted': yield_curve_spread < 0 if yield_curve_spread else False,
                    'last_updated': datetime.now().isoformat()
                },
                'pce': {
                    'value': round(float(pce_current), 2) if pce_current else None,
                    'yoy_change': round(float(pce_yoy), 2) if pce_yoy else None,
                    'label': 'PCE Inflation',
                    'unit': 'Index / % YoY',
                    'last_updated': datetime.now().isoformat()
                }
            }

            logger.info("FRED data fetched successfully")
            return fred_data

        except Exception as e:
            logger.error(f"Error fetching FRED data: {e}")
            return self._get_mock_fred_data()

    def get_dxy_index(self) -> Dict:
        """
        Get US Dollar Index (DXY) current value and change

        Returns:
            Dict with current value, change, and percentage change
        """
        try:
            import yfinance as yf

            logger.info("Fetching US Dollar Index (DXY)...")

            # DXY ticker
            dxy = yf.Ticker("DX-Y.NYB")

            # Get current data
            hist = dxy.history(period="5d")

            if hist.empty:
                logger.warning("No DXY data available")
                return self._get_mock_dxy()

            current_price = hist['Close'].iloc[-1]
            previous_price = hist['Close'].iloc[-2] if len(hist) >= 2 else current_price

            change = current_price - previous_price
            change_percent = (change / previous_price * 100) if previous_price else 0

            # Get 52-week high/low
            hist_1y = dxy.history(period="1y")
            high_52w = hist_1y['High'].max() if not hist_1y.empty else current_price
            low_52w = hist_1y['Low'].min() if not hist_1y.empty else current_price

            dxy_data = {
                'value': round(float(current_price), 2),
                'change': round(float(change), 2),
                'changePercent': round(float(change_percent), 2),
                'high52w': round(float(high_52w), 2),
                'low52w': round(float(low_52w), 2),
                'label': 'US Dollar Index',
                'symbol': 'DXY',
                'interpretation': self._interpret_dxy(current_price, change_percent),
                'last_updated': datetime.now().isoformat()
            }

            logger.info(f"DXY: {dxy_data['value']} ({dxy_data['changePercent']:+.2f}%)")
            return dxy_data

        except Exception as e:
            logger.error(f"Error fetching DXY: {e}")
            return self._get_mock_dxy()

    def get_vix_index(self) -> Dict:
        """
        Get VIX volatility index (Fear Index)

        Returns:
            Dict with VIX value, change, and volatility interpretation
        """
        try:
            import yfinance as yf

            logger.info("Fetching VIX volatility index...")

            # VIX ticker
            vix = yf.Ticker("^VIX")

            # Get current data
            hist = vix.history(period="5d")

            if hist.empty:
                logger.warning("No VIX data available")
                return self._get_mock_vix()

            current_value = hist['Close'].iloc[-1]
            previous_value = hist['Close'].iloc[-2] if len(hist) >= 2 else current_value

            change = current_value - previous_value
            change_percent = (change / previous_value * 100) if previous_value else 0

            # Get 52-week high/low
            hist_1y = vix.history(period="1y")
            high_52w = hist_1y['High'].max() if not hist_1y.empty else current_value
            low_52w = hist_1y['Low'].min() if not hist_1y.empty else current_value

            # Interpret VIX levels
            interpretation = self._interpret_vix(current_value)

            vix_data = {
                'value': round(float(current_value), 2),
                'change': round(float(change), 2),
                'changePercent': round(float(change_percent), 2),
                'high52w': round(float(high_52w), 2),
                'low52w': round(float(low_52w), 2),
                'label': 'VIX Volatility Index',
                'symbol': 'VIX',
                'volatility_level': interpretation['level'],
                'interpretation': interpretation['description'],
                'market_sentiment': interpretation['sentiment'],
                'last_updated': datetime.now().isoformat()
            }

            logger.info(f"VIX: {vix_data['value']} - {vix_data['volatility_level']}")
            return vix_data

        except Exception as e:
            logger.error(f"Error fetching VIX: {e}")
            return self._get_mock_vix()

    def analyze_macro_environment(self) -> Dict:
        """
        Comprehensive macro environment analysis

        Analyzes all indicators to determine:
        - Bull/Bear market sentiment
        - Risk On/Off environment
        - Sector rotation recommendations
        - Overall market outlook

        Returns:
            Dict with comprehensive analysis and recommendations
        """
        logger.info("Analyzing macro environment...")

        # Gather all indicators
        fred_data = self.get_fred_data()
        dxy_data = self.get_dxy_index()
        vix_data = self.get_vix_index()

        # Extract key values
        fed_rate = fred_data['fed_funds_rate']['value']
        inflation = fred_data['cpi']['yoy_change']
        unemployment = fred_data['unemployment']['value']
        gdp_growth = fred_data['gdp_growth']['value']
        yield_curve_inverted = fred_data['yield_curve']['inverted']
        vix_value = vix_data['value']
        dxy_value = dxy_data['value']

        # Initialize scoring
        bull_score = 0
        bear_score = 0
        risk_on_score = 0
        risk_off_score = 0

        # Analyze each indicator
        signals = []

        # 1. VIX Analysis
        if vix_value:
            if vix_value < 15:
                bull_score += 2
                risk_on_score += 2
                signals.append("Low volatility (VIX < 15) suggests calm markets and risk appetite")
            elif vix_value > 30:
                bear_score += 2
                risk_off_score += 2
                signals.append("High volatility (VIX > 30) indicates fear and uncertainty")
            else:
                bull_score += 1
                signals.append("Moderate volatility suggests normal market conditions")

        # 2. Interest Rate Analysis
        if fed_rate:
            if fed_rate > 4:
                bear_score += 1
                signals.append("High interest rates pressure growth stocks and valuations")
            elif fed_rate < 2:
                bull_score += 1
                signals.append("Low interest rates support equity valuations")

        # 3. Inflation Analysis
        if inflation:
            if inflation > 4:
                bear_score += 1
                signals.append(f"High inflation ({inflation}%) erodes purchasing power")
            elif 2 <= inflation <= 3:
                bull_score += 1
                signals.append("Inflation in Fed's target range (2-3%) is healthy")
            elif inflation < 1:
                bear_score += 1
                signals.append("Low inflation may signal weak demand")

        # 4. Unemployment Analysis
        if unemployment:
            if unemployment < 4:
                bull_score += 1
                signals.append("Low unemployment indicates strong economy")
            elif unemployment > 6:
                bear_score += 1
                signals.append("High unemployment signals economic weakness")

        # 5. GDP Growth Analysis
        if gdp_growth:
            if gdp_growth > 3:
                bull_score += 2
                signals.append("Strong GDP growth above 3% indicates robust economy")
            elif gdp_growth < 0:
                bear_score += 2
                signals.append("Negative GDP growth signals recession")
            else:
                bull_score += 1
                signals.append("Moderate GDP growth suggests stable expansion")

        # 6. Yield Curve Analysis
        if yield_curve_inverted:
            bear_score += 2
            risk_off_score += 1
            signals.append("Inverted yield curve historically predicts recession")
        else:
            bull_score += 1
            signals.append("Normal yield curve supports growth outlook")

        # 7. Dollar Strength Analysis
        if dxy_data['changePercent'] > 2:
            risk_off_score += 1
            signals.append("Strong dollar may pressure commodities and emerging markets")
        elif dxy_data['changePercent'] < -2:
            risk_on_score += 1
            signals.append("Weak dollar supports commodity and EM rally")

        # Determine overall sentiment
        total_bull_bear = bull_score + bear_score
        bull_percentage = (bull_score / total_bull_bear * 100) if total_bull_bear > 0 else 50

        if bull_percentage >= 70:
            market_sentiment = "BULLISH"
            sentiment_description = "Strong bull market environment"
        elif bull_percentage >= 55:
            market_sentiment = "MODERATELY_BULLISH"
            sentiment_description = "Cautiously bullish environment"
        elif bull_percentage >= 45:
            market_sentiment = "NEUTRAL"
            sentiment_description = "Mixed signals, neutral stance recommended"
        elif bull_percentage >= 30:
            market_sentiment = "MODERATELY_BEARISH"
            sentiment_description = "Cautiously bearish environment"
        else:
            market_sentiment = "BEARISH"
            sentiment_description = "Strong bear market environment"

        # Risk On/Off determination
        total_risk = risk_on_score + risk_off_score
        risk_on_percentage = (risk_on_score / total_risk * 100) if total_risk > 0 else 50

        if risk_on_percentage >= 60:
            risk_environment = "RISK_ON"
            risk_description = "Risk-on environment favors growth and cyclical assets"
        elif risk_on_percentage >= 40:
            risk_environment = "NEUTRAL"
            risk_description = "Balanced risk environment"
        else:
            risk_environment = "RISK_OFF"
            risk_description = "Risk-off environment favors defensive and safe-haven assets"

        # Sector rotation recommendations
        sector_recommendations = self._get_sector_recommendations(
            market_sentiment, risk_environment, fred_data, vix_value
        )

        # Compile analysis
        analysis = {
            'market_sentiment': {
                'label': market_sentiment,
                'description': sentiment_description,
                'bull_score': bull_score,
                'bear_score': bear_score,
                'confidence': round(abs(bull_percentage - 50) * 2, 1)  # 0-100 scale
            },
            'risk_environment': {
                'label': risk_environment,
                'description': risk_description,
                'risk_on_score': risk_on_score,
                'risk_off_score': risk_off_score
            },
            'key_signals': signals,
            'sector_recommendations': sector_recommendations,
            'indicators_summary': {
                'vix': vix_data['value'],
                'dxy': dxy_data['value'],
                'fed_rate': fed_rate,
                'inflation': inflation,
                'unemployment': unemployment,
                'gdp_growth': gdp_growth
            },
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"Macro analysis: {market_sentiment} / {risk_environment}")
        return analysis

    def get_all_indicators(self, use_cache: bool = True) -> Dict:
        """
        Get all macro indicators with Redis caching

        Args:
            use_cache: Whether to use cached data (default: True)

        Returns:
            Dict with all indicators and analysis
        """
        cache_key = "macro_indicators_all"

        # Try to get from cache
        if use_cache and self.redis_client:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    logger.info("Returning cached macro indicators")
                    return json.loads(cached_data)
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")

        # Fetch fresh data
        logger.info("Fetching fresh macro indicators...")

        indicators = {
            'fred_data': self.get_fred_data(),
            'dxy': self.get_dxy_index(),
            'vix': self.get_vix_index(),
            'analysis': self.analyze_macro_environment(),
            'timestamp': datetime.now().isoformat(),
            'cache_ttl': self.cache_ttl
        }

        # Cache the results
        if self.redis_client:
            try:
                self.redis_client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(indicators)
                )
                logger.info(f"Cached macro indicators for {self.cache_ttl}s")
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")

        return indicators

    # Helper methods

    def _interpret_vix(self, vix_value: float) -> Dict:
        """Interpret VIX volatility levels"""
        if vix_value < 12:
            return {
                'level': 'VERY_LOW',
                'description': 'Extremely low volatility - complacent market',
                'sentiment': 'BULLISH'
            }
        elif vix_value < 20:
            return {
                'level': 'LOW',
                'description': 'Low volatility - calm market conditions',
                'sentiment': 'BULLISH'
            }
        elif vix_value < 30:
            return {
                'level': 'ELEVATED',
                'description': 'Elevated volatility - increased uncertainty',
                'sentiment': 'NEUTRAL'
            }
        elif vix_value < 40:
            return {
                'level': 'HIGH',
                'description': 'High volatility - fearful market',
                'sentiment': 'BEARISH'
            }
        else:
            return {
                'level': 'EXTREME',
                'description': 'Extreme volatility - panic mode',
                'sentiment': 'VERY_BEARISH'
            }

    def _interpret_dxy(self, dxy_value: float, change_percent: float) -> str:
        """Interpret DXY dollar strength"""
        if change_percent > 1:
            return "Strong dollar rally - headwinds for commodities and emerging markets"
        elif change_percent < -1:
            return "Weak dollar - supportive for commodities and international stocks"
        else:
            return "Dollar trading in stable range"

    def _get_sector_recommendations(self, sentiment: str, risk_env: str,
                                   fred_data: Dict, vix: float) -> List[Dict]:
        """Generate sector rotation recommendations based on environment"""
        recommendations = []

        if sentiment in ['BULLISH', 'MODERATELY_BULLISH'] and risk_env == 'RISK_ON':
            recommendations = [
                {'sector': 'Technology', 'rating': 'OVERWEIGHT', 'reason': 'Risk-on favors growth sectors'},
                {'sector': 'Consumer Discretionary', 'rating': 'OVERWEIGHT', 'reason': 'Strong economy supports spending'},
                {'sector': 'Financials', 'rating': 'NEUTRAL', 'reason': 'Interest rates supportive for banks'},
                {'sector': 'Utilities', 'rating': 'UNDERWEIGHT', 'reason': 'Defensive sectors underperform in risk-on'},
                {'sector': 'Healthcare', 'rating': 'NEUTRAL', 'reason': 'Defensive quality in balanced allocation'}
            ]
        elif sentiment in ['BEARISH', 'MODERATELY_BEARISH'] or risk_env == 'RISK_OFF':
            recommendations = [
                {'sector': 'Utilities', 'rating': 'OVERWEIGHT', 'reason': 'Safe haven in uncertain times'},
                {'sector': 'Consumer Staples', 'rating': 'OVERWEIGHT', 'reason': 'Defensive sector holds up in downturns'},
                {'sector': 'Healthcare', 'rating': 'OVERWEIGHT', 'reason': 'Quality defensive sector'},
                {'sector': 'Technology', 'rating': 'UNDERWEIGHT', 'reason': 'Growth stocks pressured in risk-off'},
                {'sector': 'Energy', 'rating': 'NEUTRAL', 'reason': 'Commodity sensitivity in uncertain macro'}
            ]
        else:  # NEUTRAL
            recommendations = [
                {'sector': 'Technology', 'rating': 'NEUTRAL', 'reason': 'Balanced exposure to growth'},
                {'sector': 'Healthcare', 'rating': 'OVERWEIGHT', 'reason': 'Quality defensive positioning'},
                {'sector': 'Financials', 'rating': 'NEUTRAL', 'reason': 'Interest rate sensitivity balanced'},
                {'sector': 'Consumer Discretionary', 'rating': 'NEUTRAL', 'reason': 'Wait for clearer direction'},
                {'sector': 'Industrials', 'rating': 'NEUTRAL', 'reason': 'Economic cycle exposure'}
            ]

        return recommendations

    def _get_mock_fred_data(self) -> Dict:
        """Return mock FRED data"""
        return {
            'fed_funds_rate': {'value': 5.33, 'label': 'Federal Funds Rate', 'unit': '%', 'last_updated': datetime.now().isoformat()},
            'cpi': {'value': 308.5, 'yoy_change': 3.2, 'label': 'Consumer Price Index', 'unit': 'Index / % YoY', 'last_updated': datetime.now().isoformat()},
            'unemployment': {'value': 3.7, 'label': 'Unemployment Rate', 'unit': '%', 'last_updated': datetime.now().isoformat()},
            'gdp_growth': {'value': 2.8, 'label': 'GDP Growth Rate', 'unit': '% (Quarterly)', 'last_updated': datetime.now().isoformat()},
            'treasury_10y': {'value': 4.25, 'label': '10-Year Treasury Yield', 'unit': '%', 'last_updated': datetime.now().isoformat()},
            'treasury_2y': {'value': 4.80, 'label': '2-Year Treasury Yield', 'unit': '%', 'last_updated': datetime.now().isoformat()},
            'yield_curve': {'spread': -0.55, 'label': 'Yield Curve (10Y-2Y)', 'unit': 'bps', 'inverted': True, 'last_updated': datetime.now().isoformat()},
            'pce': {'value': 280.2, 'yoy_change': 2.8, 'label': 'PCE Inflation', 'unit': 'Index / % YoY', 'last_updated': datetime.now().isoformat()}
        }

    def _get_mock_dxy(self) -> Dict:
        """Return mock DXY data"""
        return {
            'value': 103.45,
            'change': 0.32,
            'changePercent': 0.31,
            'high52w': 106.50,
            'low52w': 99.80,
            'label': 'US Dollar Index',
            'symbol': 'DXY',
            'interpretation': 'Dollar trading in stable range',
            'last_updated': datetime.now().isoformat()
        }

    def _get_mock_vix(self) -> Dict:
        """Return mock VIX data"""
        return {
            'value': 16.82,
            'change': -0.45,
            'changePercent': -2.61,
            'high52w': 28.50,
            'low52w': 12.20,
            'label': 'VIX Volatility Index',
            'symbol': 'VIX',
            'volatility_level': 'LOW',
            'interpretation': 'Low volatility - calm market conditions',
            'market_sentiment': 'BULLISH',
            'last_updated': datetime.now().isoformat()
        }


# Convenience functions

def get_macro_dashboard(fred_api_key: Optional[str] = None, redis_client=None) -> Dict:
    """
    Convenience function to get complete macro dashboard

    Args:
        fred_api_key: FRED API key
        redis_client: Redis client for caching

    Returns:
        Complete macro indicators dashboard
    """
    analyzer = MacroAnalyzer(fred_api_key=fred_api_key, redis_client=redis_client)
    return analyzer.get_all_indicators()


# Example usage
if __name__ == "__main__":
    print("=== Macro Analyzer Service ===\n")

    # Initialize analyzer
    analyzer = MacroAnalyzer()

    # Test 1: FRED data
    print("1. Testing get_fred_data()...")
    fred_data = analyzer.get_fred_data()
    print(f"Fed Funds Rate: {fred_data['fed_funds_rate']['value']}%")
    print(f"CPI Inflation: {fred_data['cpi']['yoy_change']}% YoY")
    print(f"Unemployment: {fred_data['unemployment']['value']}%")
    print(f"GDP Growth: {fred_data['gdp_growth']['value']}%")
    print(f"Yield Curve: {fred_data['yield_curve']['spread']} bps (Inverted: {fred_data['yield_curve']['inverted']})")

    # Test 2: DXY
    print("\n2. Testing get_dxy_index()...")
    dxy = analyzer.get_dxy_index()
    print(f"DXY: {dxy['value']} ({dxy['changePercent']:+.2f}%)")
    print(f"Interpretation: {dxy['interpretation']}")

    # Test 3: VIX
    print("\n3. Testing get_vix_index()...")
    vix = analyzer.get_vix_index()
    print(f"VIX: {vix['value']} - {vix['volatility_level']}")
    print(f"Market Sentiment: {vix['market_sentiment']}")
    print(f"Interpretation: {vix['interpretation']}")

    # Test 4: Macro environment analysis
    print("\n4. Testing analyze_macro_environment()...")
    analysis = analyzer.analyze_macro_environment()
    print(f"Market Sentiment: {analysis['market_sentiment']['label']}")
    print(f"  {analysis['market_sentiment']['description']}")
    print(f"  Confidence: {analysis['market_sentiment']['confidence']}%")
    print(f"\nRisk Environment: {analysis['risk_environment']['label']}")
    print(f"  {analysis['risk_environment']['description']}")

    print(f"\nKey Signals ({len(analysis['key_signals'])}):")
    for signal in analysis['key_signals'][:5]:
        print(f"  - {signal}")

    print(f"\nSector Recommendations:")
    for rec in analysis['sector_recommendations']:
        print(f"  {rec['sector']}: {rec['rating']} - {rec['reason']}")

    # Test 5: All indicators
    print("\n5. Testing get_all_indicators()...")
    all_indicators = analyzer.get_all_indicators(use_cache=False)
    print(f"Timestamp: {all_indicators['timestamp']}")
    print(f"Cache TTL: {all_indicators['cache_ttl']}s")
    print(f"Components: {list(all_indicators.keys())}")

    print("\n=== Macro Analyzer Tests Complete ===")
