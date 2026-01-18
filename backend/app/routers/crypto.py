from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
import random
from app.services.predictor import CryptoPredictor

router = APIRouter(
    prefix="/api/crypto",
    tags=["crypto"]
)

# Initialize predictor
crypto_predictor = CryptoPredictor()


@router.get("/top-picks")
async def get_crypto_top_picks(
    timeframe: str = Query("swing", regex="^(day|swing|long)$"),
    limit: int = Query(10, ge=1, le=20)
):
    """
    Get AI-powered top cryptocurrency picks using real technical analysis

    Args:
        timeframe: Trading timeframe (day, swing, long)
        limit: Number of picks to return (1-20)

    Returns:
        Top crypto picks with AI confidence scores based on real market data
    """

    try:
        # Use real predictor service
        picks = crypto_predictor.predict_top_crypto(timeframe=timeframe, limit=limit)

        return {
            "success": True,
            "timeframe": timeframe,
            "count": len(picks),
            "data": picks
        }
    except Exception as e:
        # Log error and return error response
        print(f"Error in get_crypto_top_picks: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate crypto predictions: {str(e)}"
        )


@router.get("/movers")
async def get_crypto_movers():
    """
    Get top crypto movers - 24h gainers and losers

    Returns:
        Top gainers and losers for 24h period
    """

    gainers = [
        {
            "symbol": "BTC",
            "name": "Bitcoin",
            "price": 68500,
            "change": 4200,
            "changePercent": 6.53,
            "volume": 28500000000,
            "type": "crypto"
        },
        {
            "symbol": "ETH",
            "name": "Ethereum",
            "price": 3850,
            "change": 185,
            "changePercent": 5.05,
            "volume": 15200000000,
            "type": "crypto"
        },
        {
            "symbol": "SOL",
            "name": "Solana",
            "price": 145.20,
            "change": 6.80,
            "changePercent": 4.91,
            "volume": 2400000000,
            "type": "crypto"
        },
        {
            "symbol": "MATIC",
            "name": "Polygon",
            "price": 0.92,
            "change": 0.039,
            "changePercent": 4.43,
            "volume": 385000000,
            "type": "crypto"
        },
        {
            "symbol": "AVAX",
            "name": "Avalanche",
            "price": 38.50,
            "change": 1.50,
            "changePercent": 4.05,
            "volume": 520000000,
            "type": "crypto"
        }
    ]

    losers = [
        {
            "symbol": "DOGE",
            "name": "Dogecoin",
            "price": 0.0845,
            "change": -0.0048,
            "changePercent": -5.38,
            "volume": 850000000,
            "type": "crypto"
        },
        {
            "symbol": "SHIB",
            "name": "Shiba Inu",
            "price": 0.0000089,
            "change": -0.00000042,
            "changePercent": -4.51,
            "volume": 185000000,
            "type": "crypto"
        },
        {
            "symbol": "XRP",
            "name": "Ripple",
            "price": 0.52,
            "change": -0.021,
            "changePercent": -3.88,
            "volume": 1200000000,
            "type": "crypto"
        },
        {
            "symbol": "ADA",
            "name": "Cardano",
            "price": 0.62,
            "change": -0.022,
            "changePercent": -3.43,
            "volume": 485000000,
            "type": "crypto"
        },
        {
            "symbol": "TRX",
            "name": "TRON",
            "price": 0.105,
            "change": -0.0032,
            "changePercent": -2.96,
            "volume": 320000000,
            "type": "crypto"
        }
    ]

    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "period": "24h",
        "data": {
            "gainers": gainers,
            "losers": losers
        }
    }


@router.get("/{symbol}")
async def get_crypto_details(symbol: str):
    """
    Get detailed cryptocurrency information

    Args:
        symbol: Crypto symbol

    Returns:
        Comprehensive crypto data
    """

    symbol = symbol.upper()

    # Mock crypto names
    crypto_names = {
        "BTC": "Bitcoin",
        "ETH": "Ethereum",
        "BNB": "Binance Coin",
        "SOL": "Solana",
        "ADA": "Cardano",
        "DOGE": "Dogecoin",
        "MATIC": "Polygon",
        "DOT": "Polkadot",
    }

    # Mock prices
    prices = {
        "BTC": 68500,
        "ETH": 3850,
        "BNB": 585,
        "SOL": 145,
        "ADA": 0.62,
        "DOGE": 0.085,
        "MATIC": 0.92,
        "DOT": 7.45,
    }

    crypto_data = {
        "symbol": symbol,
        "name": crypto_names.get(symbol, symbol),
        "price": prices.get(symbol, 100),
        "change24h": 2850.50,
        "changePercent24h": 4.32,
        "volume24h": 28500000000,
        "marketCap": 1342000000000,
        "marketCapRank": 1,
        "circulatingSupply": 19650000,
        "totalSupply": 21000000,
        "maxSupply": 21000000 if symbol == "BTC" else None,
        "ath": 69000 if symbol == "BTC" else prices.get(symbol, 100) * 1.5,
        "athDate": "2021-11-10",
        "atl": 67.81 if symbol == "BTC" else prices.get(symbol, 100) * 0.1,
        "atlDate": "2013-07-06",
        "category": "Cryptocurrency",
        "description": f"{crypto_names.get(symbol, symbol)} is a leading cryptocurrency.",
        "website": f"https://{symbol.lower()}.org",
        "blockchain": symbol if symbol in ["BTC", "ETH", "SOL"] else "Multiple",
        "consensus": "Proof of Work" if symbol == "BTC" else "Proof of Stake",
        "launchDate": "2009" if symbol == "BTC" else "2015",
        "fearGreed": {
            "value": 68,
            "label": "Greed",
            "classification": "GREED",
            "lastUpdate": datetime.now().isoformat()
        },
        "onChain": {
            "transactions24h": 285420,
            "activeAddresses24h": 892450,
            "averageTxFee": 2.35,
            "hashRate": 450.5 if symbol == "BTC" else None,
            "stakingRate": 28.5 if symbol == "ETH" else None,
            "holders": 48250000,
            "whaleConcentration": 42.5
        }
    }

    return {
        "success": True,
        "data": crypto_data
    }


@router.get("/{symbol}/news")
async def get_crypto_news(
    symbol: str,
    limit: int = Query(10, ge=1, le=50)
):
    """
    Get news for a specific cryptocurrency

    Args:
        symbol: Crypto symbol
        limit: Number of news items to return

    Returns:
        List of news articles
    """

    symbol = symbol.upper()

    news_items = [
        {
            "id": "1",
            "symbol": symbol,
            "headline": f"{symbol} Surges on Institutional Adoption News",
            "summary": "Major institutions announce plans to allocate significant capital to cryptocurrency.",
            "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
            "category": "CRYPTO",
            "isHot": True,
            "impact": "HIGH",
            "url": "https://example.com/crypto/1"
        },
        {
            "id": "2",
            "symbol": symbol,
            "headline": f"{symbol} Network Upgrade Successfully Completed",
            "summary": "Latest network upgrade brings enhanced scalability and reduced fees.",
            "timestamp": (datetime.now() - timedelta(hours=4)).isoformat(),
            "category": "CRYPTO",
            "isHot": True,
            "impact": "HIGH",
            "url": "https://example.com/crypto/2"
        },
        {
            "id": "3",
            "symbol": symbol,
            "headline": f"Analysts Bullish on {symbol} Price Targets",
            "summary": "Multiple analysts raise price targets citing strong fundamentals and adoption.",
            "timestamp": (datetime.now() - timedelta(hours=6)).isoformat(),
            "category": "CRYPTO",
            "isHot": False,
            "impact": "MEDIUM",
            "url": "https://example.com/crypto/3"
        },
        {
            "id": "4",
            "symbol": symbol,
            "headline": f"{symbol} Trading Volume Hits Record High",
            "summary": "24-hour trading volume reaches all-time high as retail interest surges.",
            "timestamp": (datetime.now() - timedelta(hours=12)).isoformat(),
            "category": "CRYPTO",
            "isHot": False,
            "impact": "MEDIUM",
            "url": "https://example.com/crypto/4"
        }
    ]

    return {
        "success": True,
        "symbol": symbol,
        "count": len(news_items[:limit]),
        "data": news_items[:limit]
    }


@router.get("/fear-greed")
async def get_fear_greed_index():
    """
    Get Crypto Fear & Greed Index

    Returns:
        Current fear & greed index value and classification
    """

    # Mock Fear & Greed data
    value = random.randint(40, 80)

    if value >= 75:
        label = "Extreme Greed"
        classification = "EXTREME_GREED"
    elif value >= 55:
        label = "Greed"
        classification = "GREED"
    elif value >= 45:
        label = "Neutral"
        classification = "NEUTRAL"
    elif value >= 25:
        label = "Fear"
        classification = "FEAR"
    else:
        label = "Extreme Fear"
        classification = "EXTREME_FEAR"

    data = {
        "value": value,
        "label": label,
        "classification": classification,
        "lastUpdate": datetime.now().isoformat(),
        "historical": [
            {"date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"), "value": random.randint(30, 80)}
            for i in range(7)
        ]
    }

    return {
        "success": True,
        "data": data
    }


@router.get("/market")
async def get_crypto_market_overview():
    """
    Get overall crypto market overview

    Returns:
        Total market cap, volume, BTC dominance, etc.
    """

    market_data = {
        "totalMarketCap": 2450000000000,
        "totalVolume24h": 98500000000,
        "btcDominance": 52.3,
        "ethDominance": 17.8,
        "activeCryptocurrencies": 12845,
        "markets": 42180,
        "marketCapChange24h": 3.42,
        "topGainer24h": {
            "symbol": "SOL",
            "changePercent": 8.45
        },
        "topLoser24h": {
            "symbol": "DOGE",
            "changePercent": -6.23
        }
    }

    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "data": market_data
    }
