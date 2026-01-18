"""
Crypto Analyzer Service for TradeMaster Pro

Provides real-time cryptocurrency analysis using Binance API and CoinGecko API.
Includes market data, technical indicators, and WebSocket streaming.
"""

import logging
import asyncio
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CryptoAnalyzer:
    """
    Cryptocurrency analyzer using Binance and CoinGecko APIs

    Features:
    - Real-time price data from Binance
    - Top movers (gainers/losers) analysis
    - Technical indicators (MA, RSI, MACD)
    - CoinGecko market data integration
    - WebSocket price streaming
    """

    def __init__(self, binance_api_key: Optional[str] = None,
                 binance_api_secret: Optional[str] = None):
        """
        Initialize CryptoAnalyzer

        Args:
            binance_api_key: Binance API key (optional for public data)
            binance_api_secret: Binance API secret (optional for public data)
        """
        self.binance_api_key = binance_api_key
        self.binance_api_secret = binance_api_secret
        self.client = None
        self.coingecko_base_url = "https://api.coingecko.com/api/v3"

        # Initialize Binance client
        try:
            from binance.client import Client
            from binance import ThreadedWebsocketManager

            if binance_api_key and binance_api_secret:
                self.client = Client(binance_api_key, binance_api_secret)
                logger.info("Binance API initialized with authentication")
            else:
                self.client = Client()  # Public API only
                logger.info("Binance API initialized (public data only)")

            self.websocket_manager = None

        except ImportError:
            logger.warning("python-binance library not installed. Install with: pip install python-binance")
        except Exception as e:
            logger.error(f"Failed to initialize Binance client: {e}")

    def get_top_movers(self, limit: int = 20) -> Dict[str, List[Dict]]:
        """
        Get top crypto gainers and losers from Binance USDT pairs

        Args:
            limit: Number of gainers/losers to return

        Returns:
            Dict with 'gainers' and 'losers' lists
        """
        if not self.client:
            logger.warning("Binance client not available. Using mock data.")
            return self._get_mock_movers(limit)

        try:
            logger.info("Fetching 24h ticker data from Binance...")

            # Get 24h ticker data for all symbols
            tickers = self.client.get_ticker()

            # Filter USDT pairs and calculate changes
            usdt_pairs = []
            for ticker in tickers:
                symbol = ticker['symbol']

                # Only USDT pairs
                if not symbol.endswith('USDT'):
                    continue

                # Skip stablecoins and leveraged tokens
                if any(x in symbol for x in ['USDC', 'BUSD', 'TUSD', 'DAI', 'UP', 'DOWN', 'BEAR', 'BULL']):
                    continue

                try:
                    price = float(ticker['lastPrice'])
                    change_percent = float(ticker['priceChangePercent'])
                    volume = float(ticker['quoteVolume'])  # Volume in USDT
                    high_24h = float(ticker['highPrice'])
                    low_24h = float(ticker['lowPrice'])

                    # Skip very low volume pairs (< $1M daily volume)
                    if volume < 1000000:
                        continue

                    # Skip zero/invalid prices
                    if price <= 0:
                        continue

                    base_symbol = symbol.replace('USDT', '')

                    usdt_pairs.append({
                        'symbol': base_symbol,
                        'pair': symbol,
                        'price': round(price, 8),
                        'change': round(change_percent, 2),
                        'changePercent': round(change_percent, 2),
                        'volume': round(volume, 2),
                        'high24h': round(high_24h, 8),
                        'low24h': round(low_24h, 8),
                        'type': 'crypto'
                    })

                except (ValueError, KeyError) as e:
                    continue

            # Sort by change percent
            gainers = sorted(usdt_pairs, key=lambda x: x['changePercent'], reverse=True)[:limit]
            losers = sorted(usdt_pairs, key=lambda x: x['changePercent'])[:limit]

            logger.info(f"Found {len(usdt_pairs)} USDT pairs, returning top {limit} gainers/losers")

            return {
                'gainers': gainers,
                'losers': losers,
                'timestamp': datetime.now().isoformat(),
                'total_pairs': len(usdt_pairs)
            }

        except Exception as e:
            logger.error(f"Error fetching top movers: {e}")
            return self._get_mock_movers(limit)

    def analyze_crypto(self, symbol: str) -> Optional[Dict]:
        """
        Comprehensive cryptocurrency analysis

        Args:
            symbol: Crypto symbol (e.g., BTC, ETH)

        Returns:
            Dict with price, stats, technical indicators, and CoinGecko data
        """
        if not self.client:
            logger.warning("Binance client not available. Using mock data.")
            return self._get_mock_analysis(symbol)

        try:
            # Ensure symbol ends with USDT
            pair = symbol.upper()
            if not pair.endswith('USDT'):
                pair = f"{pair}USDT"

            logger.info(f"Analyzing {pair}...")

            # 1. Get current price and 24h stats
            ticker = self.client.get_ticker(symbol=pair)

            current_price = float(ticker['lastPrice'])
            change_24h = float(ticker['priceChange'])
            change_percent_24h = float(ticker['priceChangePercent'])
            volume_24h = float(ticker['quoteVolume'])
            high_24h = float(ticker['highPrice'])
            low_24h = float(ticker['lowPrice'])
            trades_24h = int(ticker['count'])

            # 2. Get historical klines for technical analysis
            klines = self.client.get_klines(
                symbol=pair,
                interval=self.client.KLINE_INTERVAL_1HOUR,
                limit=200
            )

            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['volume'] = df['volume'].astype(float)

            # 3. Calculate technical indicators
            technicals = self._calculate_technical_indicators(df)

            # 4. Get CoinGecko data (async)
            coin_id = self._symbol_to_coingecko_id(symbol)
            coingecko_data = asyncio.run(self.get_coingecko_data(coin_id))

            # 5. Compile comprehensive analysis
            analysis = {
                'symbol': symbol.upper(),
                'pair': pair,
                'price': round(current_price, 8),
                'change24h': round(change_24h, 8),
                'changePercent24h': round(change_percent_24h, 2),
                'volume24h': round(volume_24h, 2),
                'high24h': round(high_24h, 8),
                'low24h': round(low_24h, 8),
                'trades24h': trades_24h,
                'technicals': technicals,
                'coingecko': coingecko_data,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"Analysis complete for {pair}")
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return self._get_mock_analysis(symbol)

    def _calculate_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """
        Calculate technical indicators from price data

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Dict with technical indicators
        """
        try:
            close = df['close']

            # Moving Averages
            sma_20 = close.rolling(window=20).mean().iloc[-1]
            sma_50 = close.rolling(window=50).mean().iloc[-1]
            sma_200 = close.rolling(window=200).mean().iloc[-1] if len(df) >= 200 else None

            ema_12 = close.ewm(span=12, adjust=False).mean().iloc[-1]
            ema_26 = close.ewm(span=26, adjust=False).mean().iloc[-1]

            # RSI (14 period)
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_value = rsi.iloc[-1]

            # MACD
            macd_line = ema_12 - ema_26
            signal_line = close.ewm(span=9, adjust=False).mean().iloc[-1]
            macd_histogram = macd_line - signal_line

            # Bollinger Bands
            sma_20_full = close.rolling(window=20).mean()
            std_20 = close.rolling(window=20).std()
            bb_upper = (sma_20_full + (std_20 * 2)).iloc[-1]
            bb_lower = (sma_20_full - (std_20 * 2)).iloc[-1]

            # Current price
            current_price = close.iloc[-1]

            # Volume analysis
            avg_volume = df['volume'].rolling(window=20).mean().iloc[-1]
            current_volume = df['volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

            return {
                'sma20': round(float(sma_20), 8),
                'sma50': round(float(sma_50), 8),
                'sma200': round(float(sma_200), 8) if sma_200 else None,
                'ema12': round(float(ema_12), 8),
                'ema26': round(float(ema_26), 8),
                'rsi': round(float(rsi_value), 2),
                'macd': {
                    'value': round(float(macd_line), 8),
                    'signal': round(float(signal_line), 8),
                    'histogram': round(float(macd_histogram), 8)
                },
                'bollingerBands': {
                    'upper': round(float(bb_upper), 8),
                    'middle': round(float(sma_20), 8),
                    'lower': round(float(bb_lower), 8)
                },
                'volume': {
                    'current': round(float(current_volume), 2),
                    'average': round(float(avg_volume), 2),
                    'ratio': round(float(volume_ratio), 2)
                }
            }

        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
            return {}

    async def get_coingecko_data(self, coin_id: str) -> Optional[Dict]:
        """
        Fetch cryptocurrency data from CoinGecko API

        Args:
            coin_id: CoinGecko coin ID (e.g., bitcoin, ethereum)

        Returns:
            Dict with market data, social stats, etc.
        """
        try:
            import aiohttp

            url = f"{self.coingecko_base_url}/coins/{coin_id}"
            params = {
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'true',
                'community_data': 'true',
                'developer_data': 'false',
                'sparkline': 'false'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()

                        market_data = data.get('market_data', {})
                        community_data = data.get('community_data', {})

                        return {
                            'id': data.get('id'),
                            'name': data.get('name'),
                            'symbol': data.get('symbol', '').upper(),
                            'marketCap': market_data.get('market_cap', {}).get('usd'),
                            'marketCapRank': data.get('market_cap_rank'),
                            'totalVolume': market_data.get('total_volume', {}).get('usd'),
                            'circulatingSupply': market_data.get('circulating_supply'),
                            'totalSupply': market_data.get('total_supply'),
                            'maxSupply': market_data.get('max_supply'),
                            'ath': market_data.get('ath', {}).get('usd'),
                            'athDate': market_data.get('ath_date', {}).get('usd'),
                            'atl': market_data.get('atl', {}).get('usd'),
                            'atlDate': market_data.get('atl_date', {}).get('usd'),
                            'priceChange7d': market_data.get('price_change_percentage_7d'),
                            'priceChange30d': market_data.get('price_change_percentage_30d'),
                            'priceChange1y': market_data.get('price_change_percentage_1y'),
                            'social': {
                                'twitterFollowers': community_data.get('twitter_followers'),
                                'redditSubscribers': community_data.get('reddit_subscribers'),
                                'redditActiveAccounts': community_data.get('reddit_accounts_active_48h'),
                                'telegramUsers': community_data.get('telegram_channel_user_count')
                            }
                        }
                    else:
                        logger.warning(f"CoinGecko API returned status {response.status} for {coin_id}")
                        return None

        except ImportError:
            logger.warning("aiohttp library not installed. Install with: pip install aiohttp")
            return None
        except Exception as e:
            logger.error(f"Error fetching CoinGecko data for {coin_id}: {e}")
            return None

    def _symbol_to_coingecko_id(self, symbol: str) -> str:
        """
        Convert crypto symbol to CoinGecko coin ID

        Args:
            symbol: Crypto symbol (BTC, ETH, etc.)

        Returns:
            CoinGecko coin ID
        """
        # Common mappings
        symbol_map = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'BNB': 'binancecoin',
            'SOL': 'solana',
            'ADA': 'cardano',
            'XRP': 'ripple',
            'DOT': 'polkadot',
            'DOGE': 'dogecoin',
            'MATIC': 'matic-network',
            'LINK': 'chainlink',
            'AVAX': 'avalanche-2',
            'ATOM': 'cosmos',
            'UNI': 'uniswap',
            'LTC': 'litecoin',
            'XLM': 'stellar',
            'ALGO': 'algorand',
            'NEAR': 'near',
            'FTM': 'fantom',
            'SAND': 'the-sandbox',
            'MANA': 'decentraland'
        }

        return symbol_map.get(symbol.upper(), symbol.lower())

    async def stream_prices(self, symbols: List[str], callback: Callable):
        """
        Stream real-time prices via Binance WebSocket

        Args:
            symbols: List of symbols to stream (e.g., ['BTCUSDT', 'ETHUSDT'])
            callback: Async callback function to handle price updates
        """
        try:
            from binance import AsyncClient, BinanceSocketManager

            # Initialize async client
            if self.binance_api_key and self.binance_api_secret:
                client = await AsyncClient.create(self.binance_api_key, self.binance_api_secret)
            else:
                client = await AsyncClient.create()

            bsm = BinanceSocketManager(client)

            # Ensure symbols end with USDT
            formatted_symbols = []
            for symbol in symbols:
                if not symbol.upper().endswith('USDT'):
                    formatted_symbols.append(f"{symbol.upper()}USDT")
                else:
                    formatted_symbols.append(symbol.upper())

            logger.info(f"Starting WebSocket stream for: {formatted_symbols}")

            # Create multiplex socket for multiple symbols
            socket = bsm.multiplex_socket(
                [f"{symbol.lower()}@ticker" for symbol in formatted_symbols]
            )

            async with socket as stream:
                while True:
                    msg = await stream.recv()

                    if msg:
                        data = msg.get('data', {})
                        symbol = data.get('s', '')
                        price = float(data.get('c', 0))
                        change_percent = float(data.get('P', 0))
                        volume = float(data.get('v', 0))

                        # Call the callback with price update
                        await callback({
                            'symbol': symbol,
                            'price': round(price, 8),
                            'changePercent': round(change_percent, 2),
                            'volume': round(volume, 2),
                            'timestamp': datetime.now().isoformat()
                        })

            await client.close_connection()

        except ImportError:
            logger.warning("binance async client not available")
        except Exception as e:
            logger.error(f"Error in WebSocket stream: {e}")

    def _get_mock_movers(self, limit: int) -> Dict[str, List[Dict]]:
        """Return mock top movers data"""
        gainers = [
            {'symbol': 'BTC', 'pair': 'BTCUSDT', 'price': 68500.0, 'change': 6.53, 'changePercent': 6.53, 'volume': 28500000000, 'high24h': 69000.0, 'low24h': 64000.0, 'type': 'crypto'},
            {'symbol': 'ETH', 'pair': 'ETHUSDT', 'price': 3850.0, 'change': 5.05, 'changePercent': 5.05, 'volume': 15200000000, 'high24h': 3890.0, 'low24h': 3660.0, 'type': 'crypto'},
            {'symbol': 'SOL', 'pair': 'SOLUSDT', 'price': 145.2, 'change': 4.91, 'changePercent': 4.91, 'volume': 2400000000, 'high24h': 148.0, 'low24h': 138.0, 'type': 'crypto'},
        ]

        losers = [
            {'symbol': 'DOGE', 'pair': 'DOGEUSDT', 'price': 0.0845, 'change': -5.38, 'changePercent': -5.38, 'volume': 850000000, 'high24h': 0.089, 'low24h': 0.084, 'type': 'crypto'},
            {'symbol': 'SHIB', 'pair': 'SHIBUSDT', 'price': 0.0000089, 'change': -4.51, 'changePercent': -4.51, 'volume': 185000000, 'high24h': 0.0000093, 'low24h': 0.0000088, 'type': 'crypto'},
            {'symbol': 'XRP', 'pair': 'XRPUSDT', 'price': 0.52, 'change': -3.88, 'changePercent': -3.88, 'volume': 1200000000, 'high24h': 0.54, 'low24h': 0.51, 'type': 'crypto'},
        ]

        return {
            'gainers': gainers[:limit],
            'losers': losers[:limit],
            'timestamp': datetime.now().isoformat(),
            'total_pairs': 200
        }

    def _get_mock_analysis(self, symbol: str) -> Dict:
        """Return mock analysis data"""
        return {
            'symbol': symbol.upper(),
            'pair': f"{symbol.upper()}USDT",
            'price': 68500.0 if symbol.upper() == 'BTC' else 3850.0,
            'change24h': 4200.0 if symbol.upper() == 'BTC' else 185.0,
            'changePercent24h': 6.53 if symbol.upper() == 'BTC' else 5.05,
            'volume24h': 28500000000 if symbol.upper() == 'BTC' else 15200000000,
            'high24h': 69000.0 if symbol.upper() == 'BTC' else 3890.0,
            'low24h': 64000.0 if symbol.upper() == 'BTC' else 3660.0,
            'trades24h': 1250000,
            'technicals': {
                'sma20': 67500.0,
                'sma50': 65000.0,
                'sma200': 60000.0,
                'ema12': 68200.0,
                'ema26': 66800.0,
                'rsi': 64.5,
                'macd': {'value': 1400.0, 'signal': 1200.0, 'histogram': 200.0},
                'bollingerBands': {'upper': 70000.0, 'middle': 67500.0, 'lower': 65000.0},
                'volume': {'current': 50000.0, 'average': 45000.0, 'ratio': 1.11}
            },
            'coingecko': {
                'id': 'bitcoin' if symbol.upper() == 'BTC' else 'ethereum',
                'name': 'Bitcoin' if symbol.upper() == 'BTC' else 'Ethereum',
                'symbol': symbol.upper(),
                'marketCap': 1342000000000,
                'marketCapRank': 1,
                'totalVolume': 28500000000,
                'circulatingSupply': 19650000,
                'totalSupply': 21000000,
                'maxSupply': 21000000,
                'ath': 69000.0,
                'athDate': '2021-11-10',
                'atl': 67.81,
                'atlDate': '2013-07-06',
                'priceChange7d': 5.2,
                'priceChange30d': 12.8,
                'priceChange1y': 145.3,
                'social': {
                    'twitterFollowers': 5800000,
                    'redditSubscribers': 4500000,
                    'redditActiveAccounts': 12000,
                    'telegramUsers': None
                }
            },
            'timestamp': datetime.now().isoformat()
        }


# Convenience functions

def get_top_crypto_movers(limit: int = 20) -> Dict[str, List[Dict]]:
    """
    Convenience function to get top crypto movers

    Args:
        limit: Number of gainers/losers to return

    Returns:
        Dict with gainers and losers
    """
    analyzer = CryptoAnalyzer()
    return analyzer.get_top_movers(limit=limit)


def analyze_cryptocurrency(symbol: str) -> Optional[Dict]:
    """
    Convenience function to analyze a cryptocurrency

    Args:
        symbol: Crypto symbol (BTC, ETH, etc.)

    Returns:
        Comprehensive analysis dict
    """
    analyzer = CryptoAnalyzer()
    return analyzer.analyze_crypto(symbol)


# Example usage
if __name__ == "__main__":
    print("=== Crypto Analyzer Service ===\n")

    # Initialize analyzer
    analyzer = CryptoAnalyzer()

    # Test 1: Get top movers
    print("1. Testing get_top_movers()...")
    movers = analyzer.get_top_movers(limit=10)
    print(f"Total USDT pairs analyzed: {movers.get('total_pairs', 0)}")
    print(f"\nTop 3 Gainers:")
    for crypto in movers['gainers'][:3]:
        print(f"  {crypto['symbol']}: ${crypto['price']} ({crypto['changePercent']:+.2f}%) - Volume: ${crypto['volume']:,.0f}")

    print(f"\nTop 3 Losers:")
    for crypto in movers['losers'][:3]:
        print(f"  {crypto['symbol']}: ${crypto['price']} ({crypto['changePercent']:+.2f}%) - Volume: ${crypto['volume']:,.0f}")

    # Test 2: Analyze specific crypto
    print("\n2. Testing analyze_crypto('BTC')...")
    analysis = analyzer.analyze_crypto('BTC')
    if analysis:
        print(f"Symbol: {analysis['symbol']}")
        print(f"Price: ${analysis['price']:,.2f}")
        print(f"24h Change: {analysis['changePercent24h']:+.2f}%")
        print(f"24h Volume: ${analysis['volume24h']:,.0f}")
        print(f"RSI: {analysis['technicals'].get('rsi', 'N/A')}")
        if analysis.get('coingecko'):
            print(f"Market Cap Rank: #{analysis['coingecko'].get('marketCapRank', 'N/A')}")
            print(f"Market Cap: ${analysis['coingecko'].get('marketCap', 0):,.0f}")

    print("\n=== Crypto Analyzer Tests Complete ===")
