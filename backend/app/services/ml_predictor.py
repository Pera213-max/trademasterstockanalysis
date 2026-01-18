"""
TradeMaster Pro - ML-Powered Stock Predictor
============================================

Advanced machine learning system for finding stocks with 10%+ weekly growth potential.

Strategy:
- Technical breakout patterns (volume surge + momentum)
- Social sentiment signals (Reddit mention spikes)
- News catalyst detection (high-impact events)
- Fundamental strength (analyst ratings, price targets)

Model: XGBoost binary classifier
Target: Stocks that will rise 10%+ in next 7 days
"""

import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _calculate_rsi(series: pd.Series, length: int = 14) -> pd.Series:
    if series is None or len(series) < length + 1:
        return pd.Series(dtype=float)
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=length, min_periods=length).mean()
    avg_loss = loss.rolling(window=length, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _calculate_macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    if series is None or len(series) < slow + signal:
        empty = pd.Series(dtype=float)
        return empty, empty, empty
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def _calculate_bbands(
    series: pd.Series,
    length: int = 20,
    std: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    if series is None or len(series) < length:
        empty = pd.Series(dtype=float)
        return empty, empty, empty
    sma = series.rolling(window=length).mean()
    stddev = series.rolling(window=length).std()
    upper = sma + std * stddev
    lower = sma - std * stddev
    return lower, sma, upper


try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    logger.warning("yfinance not available - will use alternative data sources")
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import xgboost as xgb
import pickle
from pathlib import Path

from .finnhub_service import get_finnhub_service
from .reddit_service import get_reddit_service
from .news_service import get_news_service

class MLStockPredictor:
    """ML-powered stock predictor using XGBoost"""

    def __init__(self):
        self.finnhub = get_finnhub_service()
        self.reddit = get_reddit_service()
        self.news = get_news_service()

        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []

        # Model cache path
        self.model_path = Path(__file__).parent.parent / 'models'
        self.model_path.mkdir(exist_ok=True)

        # Try to load existing model
        self._load_model()

        logger.info("ML Stock Predictor initialized")

    def predict_stock(self, ticker: str) -> Optional[Dict]:
        """
        Predict if stock will rise 10%+ in next 7 days

        Returns:
            {
                'ticker': str,
                'prediction': float (0-1 probability),
                'confidence': float (0-100),
                'signals': {
                    'technical': float,
                    'sentiment': float,
                    'news': float,
                    'fundamental': float
                },
                'features': dict
            }
        """
        try:
            # Extract all features
            features = self._extract_features(ticker)
            if not features:
                logger.warning(f"Could not extract features for {ticker}")
                return None

            # Calculate signal scores
            signals = {
                'technical': self._calculate_technical_score(features),
                'sentiment': self._calculate_sentiment_score(features),
                'news': self._calculate_news_score(features),
                'fundamental': self._calculate_fundamental_score(features)
            }

            # If model exists, use it for prediction
            if self.model:
                prediction = self._predict_with_model(features)
            else:
                # Fallback: weighted combination of signals
                prediction = (
                    signals['technical'] * 0.35 +
                    signals['sentiment'] * 0.25 +
                    signals['news'] * 0.20 +
                    signals['fundamental'] * 0.20
                )

            # Calculate confidence (higher for extreme predictions)
            confidence = abs(prediction - 0.5) * 200  # 0-100 scale

            return {
                'ticker': ticker,
                'prediction': round(prediction, 3),
                'confidence': round(confidence, 1),
                'signals': {k: round(v, 3) for k, v in signals.items()},
                'features': features,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error predicting {ticker}: {str(e)}")
            return None

    def _extract_features(self, ticker: str) -> Optional[Dict]:
        """Extract all features for a stock"""
        features = {}

        try:
            # 1. Get historical price data (90 days for indicators)
            stock = yf.Ticker(ticker)
            hist = stock.history(period='3mo')

            if hist.empty or len(hist) < 20:
                return None

            # 2. Technical Indicators
            df = hist.copy()

            # RSI (Relative Strength Index)
            rsi_series = _calculate_rsi(df['Close'], length=14)
            rsi_value = rsi_series.iloc[-1] if not rsi_series.empty else None
            if rsi_value is None or not np.isfinite(rsi_value):
                rsi_value = 50
            features['rsi'] = float(rsi_value)

            # MACD (Moving Average Convergence Divergence)
            macd_line, macd_signal, macd_hist = _calculate_macd(df['Close'])
            if not macd_line.empty:
                macd_value = macd_line.iloc[-1]
                macd_signal_value = macd_signal.iloc[-1] if not macd_signal.empty else None
                macd_hist_value = macd_hist.iloc[-1] if not macd_hist.empty else None
                features['macd'] = float(macd_value) if np.isfinite(macd_value) else 0.0
                features['macd_signal'] = float(macd_signal_value) if macd_signal_value is not None and np.isfinite(macd_signal_value) else 0.0
                features['macd_histogram'] = float(macd_hist_value) if macd_hist_value is not None and np.isfinite(macd_hist_value) else 0.0
            else:
                features['macd'] = 0.0
                features['macd_signal'] = 0.0
                features['macd_histogram'] = 0.0

            # Bollinger Bands
            bb_lower, bb_mid, bb_upper = _calculate_bbands(df['Close'], length=20, std=2.0)
            bb_position = 0.5
            if not bb_lower.empty and not bb_upper.empty:
                lower = bb_lower.iloc[-1]
                upper = bb_upper.iloc[-1]
                current_price = df['Close'].iloc[-1]
                if np.isfinite(lower) and np.isfinite(upper) and np.isfinite(current_price) and upper != lower:
                    bb_position = (current_price - lower) / (upper - lower)
            features['bb_position'] = float(bb_position)

            # Volume analysis
            avg_volume = df['Volume'].rolling(window=20).mean().iloc[-1]
            current_volume = df['Volume'].iloc[-1]
            features['volume_ratio'] = current_volume / avg_volume if avg_volume > 0 else 1.0

            # Price momentum (% change)
            features['momentum_5d'] = ((df['Close'].iloc[-1] / df['Close'].iloc[-5]) - 1) * 100 if len(df) >= 5 else 0
            features['momentum_10d'] = ((df['Close'].iloc[-1] / df['Close'].iloc[-10]) - 1) * 100 if len(df) >= 10 else 0
            features['momentum_20d'] = ((df['Close'].iloc[-1] / df['Close'].iloc[-20]) - 1) * 100 if len(df) >= 20 else 0

            # Volatility (standard deviation)
            features['volatility'] = df['Close'].pct_change().rolling(window=20).std().iloc[-1] * 100 if len(df) >= 20 else 0

            # 3. Finnhub real-time data
            quote = self.finnhub.get_quote(ticker)
            if quote:
                features['current_price'] = quote.get('c', 0)
                features['daily_change'] = ((quote.get('c', 0) / quote.get('pc', 1)) - 1) * 100 if quote.get('pc', 0) > 0 else 0
                features['intraday_range'] = ((quote.get('h', 0) - quote.get('l', 1)) / quote.get('l', 1)) * 100 if quote.get('l', 0) > 0 else 0
            else:
                features['current_price'] = df['Close'].iloc[-1]
                features['daily_change'] = 0
                features['intraday_range'] = 0

            # Analyst data
            price_target = self.finnhub.get_price_target(ticker)
            if price_target:
                target_mean = price_target.get('targetMean', 0)
                if target_mean > 0 and features['current_price'] > 0:
                    features['upside_potential'] = ((target_mean / features['current_price']) - 1) * 100
                else:
                    features['upside_potential'] = 0
            else:
                features['upside_potential'] = 0

            # 4. Reddit sentiment
            features['reddit_mentions'] = 0
            features['reddit_sentiment_score'] = 0

            try:
                trending = self.reddit.get_trending_stocks(limit=50, hours=24)
                for stock in trending:
                    if stock['ticker'] == ticker:
                        features['reddit_mentions'] = stock['mentions']
                        features['reddit_sentiment_score'] = stock['sentimentScore']
                        break
            except Exception as e:
                logger.warning(f"Reddit sentiment unavailable for {ticker}: {str(e)}")

            # 5. News impact
            features['news_count_7d'] = 0
            features['has_news_bomb'] = 0

            try:
                company_news = self.news.get_stock_news(ticker, days=7)
                features['news_count_7d'] = len(company_news)

                # Check for news bombs (high-impact keywords)
                news_bombs = self.news.get_news_bombs(limit=20)
                for bomb in news_bombs:
                    if ticker.upper() in bomb.get('title', '').upper():
                        features['has_news_bomb'] = 1
                        break
            except Exception as e:
                logger.warning(f"News data unavailable for {ticker}: {str(e)}")

            return features

        except Exception as e:
            logger.error(f"Error extracting features for {ticker}: {str(e)}")
            return None

    def _calculate_technical_score(self, features: Dict) -> float:
        """Calculate technical analysis score (0-1)"""
        score = 0.0

        # RSI - oversold (< 30) is bullish, overbought (> 70) is bearish
        rsi = features.get('rsi', 50)
        if rsi < 30:
            score += 0.3  # Strong oversold signal
        elif rsi < 45:
            score += 0.15  # Moderate oversold
        elif rsi > 70:
            score -= 0.2  # Overbought warning

        # MACD - positive histogram and above signal line is bullish
        macd_hist = features.get('macd_histogram', 0)
        if macd_hist > 0:
            score += 0.2

        # Bollinger Bands - near lower band is potential reversal
        bb_pos = features.get('bb_position', 0.5)
        if bb_pos < 0.2:
            score += 0.2  # Near lower band
        elif bb_pos > 0.8:
            score -= 0.1  # Near upper band

        # Volume surge - 2x+ average volume is strong signal
        vol_ratio = features.get('volume_ratio', 1.0)
        if vol_ratio > 2.0:
            score += 0.3
        elif vol_ratio > 1.5:
            score += 0.15

        # Momentum - positive recent momentum
        momentum_5d = features.get('momentum_5d', 0)
        if momentum_5d > 5:
            score += 0.2
        elif momentum_5d > 2:
            score += 0.1
        elif momentum_5d < -5:
            score -= 0.2

        return max(0.0, min(1.0, score))

    def _calculate_sentiment_score(self, features: Dict) -> float:
        """Calculate social sentiment score (0-1)"""
        score = 0.5  # Neutral baseline

        # Reddit mentions (more = more interest)
        mentions = features.get('reddit_mentions', 0)
        if mentions > 20:
            score += 0.3  # Viral
        elif mentions > 10:
            score += 0.2  # Trending
        elif mentions > 5:
            score += 0.1  # Notable

        # Reddit sentiment
        sentiment = features.get('reddit_sentiment_score', 0)
        if sentiment > 2.0:
            score += 0.3  # Very bullish
        elif sentiment > 1.0:
            score += 0.2  # Bullish
        elif sentiment < -1.0:
            score -= 0.2  # Bearish

        return max(0.0, min(1.0, score))

    def _calculate_news_score(self, features: Dict) -> float:
        """Calculate news impact score (0-1)"""
        score = 0.5  # Neutral baseline

        # News bomb (high-impact event)
        if features.get('has_news_bomb', 0) == 1:
            score += 0.4

        # Recent news volume
        news_count = features.get('news_count_7d', 0)
        if news_count > 10:
            score += 0.2
        elif news_count > 5:
            score += 0.1

        return max(0.0, min(1.0, score))

    def _calculate_fundamental_score(self, features: Dict) -> float:
        """Calculate fundamental analysis score (0-1)"""
        score = 0.5  # Neutral baseline

        # Analyst upside potential
        upside = features.get('upside_potential', 0)
        if upside > 20:
            score += 0.3
        elif upside > 10:
            score += 0.2
        elif upside > 5:
            score += 0.1
        elif upside < -10:
            score -= 0.2

        # Daily change momentum
        daily_change = features.get('daily_change', 0)
        if daily_change > 3:
            score += 0.2
        elif daily_change > 1:
            score += 0.1
        elif daily_change < -3:
            score -= 0.2

        return max(0.0, min(1.0, score))

    def _predict_with_model(self, features: Dict) -> float:
        """Use trained XGBoost model for prediction"""
        try:
            # Convert features to array in correct order
            feature_vector = [features.get(name, 0) for name in self.feature_names]
            feature_vector = np.array(feature_vector).reshape(1, -1)

            # Scale features
            feature_vector_scaled = self.scaler.transform(feature_vector)

            # Predict probability
            dmatrix = xgb.DMatrix(feature_vector_scaled, feature_names=self.feature_names)
            prediction = self.model.predict(dmatrix)[0]

            return float(prediction)

        except Exception as e:
            logger.error(f"Error in model prediction: {str(e)}")
            return 0.5

    def train_model(self, tickers: List[str], lookback_days: int = 730):
        """
        Train XGBoost model on historical data

        Args:
            tickers: List of stock symbols to train on
            lookback_days: How many days of history to use (default 2 years)
        """
        logger.info(f"Training model on {len(tickers)} stocks with {lookback_days} days history")

        training_data = []

        for ticker in tickers:
            try:
                logger.info(f"Collecting training data for {ticker}")

                # Get historical data
                stock = yf.Ticker(ticker)
                hist = stock.history(period=f'{lookback_days}d')

                if len(hist) < 50:
                    continue

                # For each date, extract features and label
                for i in range(20, len(hist) - 7):  # Need 20 days for indicators, 7 days for label
                    date = hist.index[i]
                    future_date = hist.index[i + 7] if i + 7 < len(hist) else None

                    if not future_date:
                        continue

                    # Get price at current date and 7 days later
                    current_price = hist['Close'].iloc[i]
                    future_price = hist['Close'].iloc[i + 7]

                    # Label: 1 if stock rose 10%+ in next 7 days, 0 otherwise
                    label = 1 if (future_price / current_price - 1) >= 0.10 else 0

                    # Extract features for this date (using data up to this point)
                    features = self._extract_historical_features(hist.iloc[:i+1])

                    if features:
                        features['label'] = label
                        features['ticker'] = ticker
                        training_data.append(features)

            except Exception as e:
                logger.error(f"Error collecting data for {ticker}: {str(e)}")
                continue

        if len(training_data) < 100:
            logger.error("Not enough training data collected")
            return

        # Convert to DataFrame
        df = pd.DataFrame(training_data)
        logger.info(f"Collected {len(df)} training samples")

        # Separate features and labels
        X = df.drop(['label', 'ticker'], axis=1)
        y = df['label']

        # Store feature names
        self.feature_names = list(X.columns)

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )

        # Train XGBoost model
        logger.info("Training XGBoost model...")

        dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=self.feature_names)
        dtest = xgb.DMatrix(X_test, label=y_test, feature_names=self.feature_names)

        params = {
            'objective': 'binary:logistic',
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'eval_metric': 'logloss'
        }

        evals = [(dtrain, 'train'), (dtest, 'test')]
        self.model = xgb.train(
            params,
            dtrain,
            num_boost_round=100,
            evals=evals,
            early_stopping_rounds=10,
            verbose_eval=10
        )

        # Evaluate
        y_pred = self.model.predict(dtest)
        y_pred_binary = (y_pred > 0.5).astype(int)

        accuracy = (y_pred_binary == y_test).mean()
        logger.info(f"Model accuracy: {accuracy:.2%}")

        # Save model
        self._save_model()

        logger.info("Model training complete!")

    def _extract_historical_features(self, hist: pd.DataFrame) -> Optional[Dict]:
        """Extract features from historical data slice"""
        try:
            if len(hist) < 20:
                return None

            features = {}
            df = hist.copy()

            # Technical indicators
            rsi_series = _calculate_rsi(df['Close'], length=14)
            rsi_value = rsi_series.iloc[-1] if not rsi_series.empty else None
            if rsi_value is None or not np.isfinite(rsi_value):
                rsi_value = 50
            features['rsi'] = float(rsi_value)

            macd_line, macd_signal, macd_hist = _calculate_macd(df['Close'])
            if not macd_line.empty:
                macd_value = macd_line.iloc[-1]
                macd_signal_value = macd_signal.iloc[-1] if not macd_signal.empty else None
                macd_hist_value = macd_hist.iloc[-1] if not macd_hist.empty else None
                features['macd'] = float(macd_value) if np.isfinite(macd_value) else 0.0
                features['macd_signal'] = float(macd_signal_value) if macd_signal_value is not None and np.isfinite(macd_signal_value) else 0.0
                features['macd_histogram'] = float(macd_hist_value) if macd_hist_value is not None and np.isfinite(macd_hist_value) else 0.0
            else:
                features['macd'] = 0.0
                features['macd_signal'] = 0.0
                features['macd_histogram'] = 0.0

            # Volume
            avg_volume = df['Volume'].rolling(window=20).mean().iloc[-1]
            current_volume = df['Volume'].iloc[-1]
            features['volume_ratio'] = current_volume / avg_volume if avg_volume > 0 else 1.0

            # Momentum
            features['momentum_5d'] = ((df['Close'].iloc[-1] / df['Close'].iloc[-5]) - 1) * 100 if len(df) >= 5 else 0
            features['momentum_10d'] = ((df['Close'].iloc[-1] / df['Close'].iloc[-10]) - 1) * 100 if len(df) >= 10 else 0

            # Volatility
            features['volatility'] = df['Close'].pct_change().rolling(window=20).std().iloc[-1] * 100

            return features

        except Exception as e:
            return None

    def _save_model(self):
        """Save model and scaler to disk"""
        try:
            model_file = self.model_path / 'xgboost_model.json'
            scaler_file = self.model_path / 'scaler.pkl'
            features_file = self.model_path / 'feature_names.pkl'

            self.model.save_model(str(model_file))

            with open(scaler_file, 'wb') as f:
                pickle.dump(self.scaler, f)

            with open(features_file, 'wb') as f:
                pickle.dump(self.feature_names, f)

            logger.info(f"Model saved to {self.model_path}")

        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")

    def _load_model(self):
        """Load model and scaler from disk"""
        try:
            model_file = self.model_path / 'xgboost_model.json'
            scaler_file = self.model_path / 'scaler.pkl'
            features_file = self.model_path / 'feature_names.pkl'

            if model_file.exists() and scaler_file.exists() and features_file.exists():
                self.model = xgb.Booster()
                self.model.load_model(str(model_file))

                with open(scaler_file, 'rb') as f:
                    self.scaler = pickle.load(f)

                with open(features_file, 'rb') as f:
                    self.feature_names = pickle.load(f)

                logger.info("Model loaded successfully")
            else:
                logger.info("No pre-trained model found")

        except Exception as e:
            logger.warning(f"Could not load model: {str(e)}")


# Global singleton
_ml_predictor = None

def get_ml_predictor() -> MLStockPredictor:
    """Get or create ML predictor singleton"""
    global _ml_predictor
    if _ml_predictor is None:
        _ml_predictor = MLStockPredictor()
    return _ml_predictor
