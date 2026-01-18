import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Optional

class AnalyticsService:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()

    def prepare_features(self, data: pd.DataFrame) -> np.ndarray:
        """Prepare features for ML model"""
        features = []

        # Technical indicators
        data['SMA_10'] = data['close'].rolling(window=10).mean()
        data['SMA_30'] = data['close'].rolling(window=30).mean()
        data['RSI'] = self.calculate_rsi(data['close'])
        data['MACD'] = self.calculate_macd(data['close'])

        # Volume indicators
        data['Volume_SMA'] = data['volume'].rolling(window=10).mean()

        # Price changes
        data['Price_Change'] = data['close'].pct_change()

        # Select features
        feature_columns = [
            'SMA_10', 'SMA_30', 'RSI', 'MACD',
            'Volume_SMA', 'Price_Change'
        ]

        return data[feature_columns].fillna(0).values

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_macd(
        self,
        prices: pd.Series,
        fast: int = 12,
        slow: int = 26
    ) -> pd.Series:
        """Calculate MACD indicator"""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        return macd

    async def predict_price(
        self,
        historical_data: List[Dict],
        days_ahead: int = 7
    ) -> Optional[Dict]:
        """Predict future prices using ML"""
        try:
            df = pd.DataFrame(historical_data)

            # Prepare features
            X = self.prepare_features(df)

            # Train model (simplified - in production, use pre-trained model)
            y = df['close'].values[len(df) - len(X):]
            X_train = X[:-days_ahead]
            y_train = y[:-days_ahead]

            # Fit model
            self.model.fit(X_train, y_train)

            # Make predictions
            predictions = self.model.predict(X[-days_ahead:])

            return {
                "predictions": predictions.tolist(),
                "confidence": float(self.model.score(X_train, y_train)),
                "days_ahead": days_ahead
            }
        except Exception as e:
            print(f"Error in price prediction: {e}")
            return None

    async def analyze_sentiment(self, texts: List[str]) -> float:
        """Analyze sentiment from text data (simplified)"""
        # Placeholder for sentiment analysis
        # In production, integrate with NLP models
        return 0.5
