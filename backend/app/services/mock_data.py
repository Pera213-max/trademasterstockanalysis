"""
TradeMaster Pro - Mock Data Service
====================================

Provides realistic mock data for testing and demo purposes.
Used when Yahoo Finance API is rate-limited or for development.
"""

from typing import List, Dict
from datetime import datetime, timedelta
import random

# S&P 500 Top 250 Stocks
SP500_TOP_250 = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "UNH", "JNJ",
    "V", "XOM", "WMT", "JPM", "MA", "PG", "LLY", "CVX", "HD", "MRK",
    "ABBV", "KO", "AVGO", "PEP", "COST", "TMO", "ADBE", "MCD", "CSCO", "ACN",
    "ABT", "CRM", "NFLX", "DHR", "WFC", "NKE", "VZ", "DIS", "TXN", "CMCSA",
    "NEE", "BMY", "PM", "ORCL", "UPS", "COP", "RTX", "QCOM", "HON", "INTC",
    "UNP", "MS", "AMGN", "LOW", "BA", "SPGI", "AMD", "CAT", "IBM", "SBUX",
    "GE", "INTU", "LMT", "DE", "AMAT", "AXP", "ISRG", "ELV", "BKNG", "PLD",
    "GILD", "MDLZ", "TJX", "ADI", "SYK", "MMC", "BLK", "ADP", "VRTX", "CB",
    "CI", "REGN", "TMUS", "MO", "C", "NOW", "ZTS", "DUK", "LRCX", "PGR",
    "SO", "BSX", "EOG", "HCA", "GD", "ETN", "SLB", "MMM", "USB", "ITW",
    "MU", "SCHW", "PNC", "TGT", "CL", "BDX", "FCX", "APD", "NOC", "FI",
    "HUM", "EQIX", "AON", "CME", "SHW", "NSC", "ICE", "WM", "MCK", "ATVI",
    "F", "GM", "PYPL", "GS", "MAR", "EMR", "COIN", "MRNA", "KLAC", "SNPS",
    "FISV", "MCO", "PSA", "TT", "EL", "AEP", "ROP", "APH", "NXPI", "ADM",
    "JCI", "DG", "SRE", "CCI", "ORLY", "AIG", "TFC", "MSCI", "D", "FDX",
    "PANW", "ECL", "AJG", "TEL", "AFL", "CARR", "CPRT", "COF", "KMB", "PAYX",
    "CMI", "PCG", "MSI", "EW", "ROST", "DLR", "PRU", "AMP", "O", "GIS",
    "CTVA", "NEM", "SPG", "CDNS", "PCAR", "KDP", "WELL", "PPG", "MNST", "AMT",
    "PSX", "OXY", "DHI", "ALL", "ED", "HES", "EA", "YUM", "CTAS", "FAST",
    "VLO", "PH", "LHX", "BK", "KR", "DXCM", "DOW", "IDXX", "KMI", "IQV",
    "ODFL", "BIIB", "CNC", "ACGL", "XEL", "KEYS", "WBA", "MTB", "KHC", "GWW",
    "APTV", "RSG", "MCHP", "VRSK", "GLW", "DVN", "VMC", "EXC", "LEN", "ADSK",
    "DD", "FTNT", "GEHC", "SBAC", "AWK", "HLT", "TTWO", "WAB", "CSGP", "MPWR",
    "EIX", "IT", "ON", "EXR", "ANSS", "MLM", "IR", "DFS", "LYB", "VICI",
    "ZBH", "FANG", "EBAY", "RMD", "WEC", "STT", "HPQ", "ENPH", "ROK", "TSCO"
]

# NASDAQ Top 250 Stocks
NASDAQ_TOP_250 = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "COST", "NFLX",
    "ADBE", "CSCO", "PEP", "CMCSA", "TMO", "INTC", "TXN", "QCOM", "HON", "AMD",
    "INTU", "AMAT", "ISRG", "BKNG", "ADI", "VRTX", "REGN", "LRCX", "GILD", "MDLZ",
    "ADP", "SBUX", "MU", "PYPL", "ATVI", "PANW", "KLAC", "SNPS", "FISV", "MRNA",
    "COIN", "MELI", "ORLY", "CDNS", "MNST", "MAR", "DXCM", "EA", "CTAS", "BIIB",
    "IDXX", "MCHP", "VRSK", "ADSK", "FTNT", "TTWO", "MPWR", "ANSS", "ENPH", "FAST",
    "ZM", "CRWD", "SNOW", "DDOG", "NET", "OKTA", "ZS", "MDB", "ESTC", "SPLK",
    "TEAM", "WDAY", "NOW", "CRM", "DOCU", "TWLO", "ZI", "COUP", "PLAN", "RNG",
    "BILL", "S", "FOUR", "TENB", "GTLB", "RBRK", "ASAN", "IOT", "TOST", "PATH",
    "FRSH", "FROG", "DOCN", "APPN", "NCNO", "SPSC", "PLTK", "ALRM", "DOCS", "PCOR",
    "SOUN", "IONQ", "RXRX", "DNA", "PACB", "NVAX", "GEVO", "PLUG", "FCEL", "BE",
    "BLNK", "CHPT", "LCID", "RIVN", "NIO", "XPEV", "LI", "TSLA", "FSR", "GOEV",
    "PLTR", "RBLX", "U", "ABNB", "DASH", "LYFT", "UBER", "CPNG", "SE", "SHOP",
    "SQ", "AFRM", "HOOD", "COIN", "SOFI", "UPST", "LC", "MARA", "RIOT", "HUT",
    "IREN", "CLSK", "BITF", "ARBK", "WULF", "CIFR", "CORZ", "BTBT", "CAN", "MIGI",
    "AI", "SMCI", "ARM", "AVGO", "MRVL", "QCOM", "ADI", "MCHP", "ON", "TER",
    "SWKS", "GFS", "MPWR", "MXL", "SLAB", "POWI", "CRUS", "LITE", "DIOD", "AOSL",
    "AAOI", "FORM", "COHR", "VCYT", "EXAS", "ILMN", "VRTX", "REGN", "GILD", "BIIB",
    "AMGN", "BMRN", "ALNY", "IONS", "RARE", "SRPT", "FOLD", "CRSP", "NTLA", "EDIT",
    "BEAM", "VERV", "BLUE", "SAGE", "INCY", "VCEL", "FATE", "ORTX", "AUPH", "APLS",
    "QURE", "RGNX", "BOLD", "SANA", "LYEL", "SEER", "SDGR", "RCKT", "ARQT", "PGEN",
    "CDMO", "DOCS", "VEEV", "ZM", "RNG", "DOCN", "FROG", "ESTC", "DDOG", "CRWD",
    "NET", "ZS", "OKTA", "PANW", "FTNT", "CYBR", "TENB", "RPD", "QLYS", "VRNS",
    "GTLB", "IOT", "PATH", "NCNO", "YEXT", "BLKB", "JAMF", "YOU", "APPF", "APPS",
    "ZUO", "BILL", "TOST", "SQ", "SHOP", "WIX", "BIGC", "SSTK", "ETSY", "W"
]

def get_mock_stock_picks(limit: int = 10, timeframe: str = "swing") -> List[Dict]:
    """Generate realistic mock stock picks"""

    # Combine and deduplicate stocks
    all_stocks = list(set(SP500_TOP_250 + NASDAQ_TOP_250))
    random.shuffle(all_stocks)

    picks = []
    base_date = datetime.now()

    # Define sectors for variety
    sectors = ["Technology", "Healthcare", "Finance", "Consumer", "Energy", "Industrial"]

    for i, ticker in enumerate(all_stocks[:limit]):
        # Generate realistic scoring
        technical_score = random.uniform(18, 30)
        momentum_score = random.uniform(18, 30)
        volume_score = random.uniform(12, 20)
        trend_score = random.uniform(12, 20)
        total_score = technical_score + momentum_score + volume_score + trend_score

        # Generate realistic prices
        base_price = random.uniform(20, 500)

        # Calculate targets based on timeframe
        if timeframe == "day":
            target_multiplier = random.uniform(1.01, 1.03)
        elif timeframe == "swing":
            target_multiplier = random.uniform(1.05, 1.15)
        else:  # long
            target_multiplier = random.uniform(1.15, 1.30)

        target_price = base_price * target_multiplier
        potential_return = ((target_price - base_price) / base_price) * 100

        # Generate realistic reasoning
        reasons = []
        if technical_score > 24:
            reasons.append("strong technical breakout pattern")
        elif technical_score > 20:
            reasons.append("favorable technical setup")

        if momentum_score > 24:
            reasons.append("exceptional price momentum")
        elif momentum_score > 20:
            reasons.append("positive momentum trend")

        if volume_score > 16:
            reasons.append("significant volume surge")
        elif volume_score > 13:
            reasons.append("above-average trading volume")

        if trend_score > 16:
            reasons.append("confirmed uptrend")
        elif trend_score > 13:
            reasons.append("emerging upward trend")

        reasoning = f"Strong opportunity driven by {', '.join(reasons[:2])}"

        # Generate signals
        signals = []
        if random.random() > 0.3:
            signals.append("Above SMA 20")
        if random.random() > 0.4:
            signals.append("Above SMA 50")
        if random.random() > 0.5:
            signals.append("RSI Neutral")
        if random.random() > 0.4:
            signals.append("MACD Bullish")
        if random.random() > 0.6:
            signals.append("High Volume")

        # Determine risk level
        if total_score > 75:
            risk_level = "LOW"
        elif total_score > 65:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        pick = {
            "rank": i + 1,
            "ticker": ticker,
            "sector": random.choice(sectors),
            "score": round(total_score, 1),
            "currentPrice": round(base_price, 2),
            "targetPrice": round(target_price, 2),
            "potentialReturn": round(potential_return, 2),
            "confidence": int(total_score),
            "timeHorizon": timeframe.upper(),
            "reasoning": reasoning,
            "signals": signals[:4],
            "riskLevel": risk_level,
            "breakdown": {
                "technical": round(technical_score, 1),
                "momentum": round(momentum_score, 1),
                "volume": round(volume_score, 1),
                "trend": round(trend_score, 1)
            },
            "fundamentals": {
                "marketCap": random.randint(10, 3000) * 1e9,
                "peRatio": round(random.uniform(10, 40), 2),
                "dividendYield": round(random.uniform(0, 4), 2) if random.random() > 0.3 else None,
                "beta": round(random.uniform(0.8, 1.5), 2),
                "revenueGrowth": round(random.uniform(-10, 50), 2)
            }
        }

        picks.append(pick)

    return picks


def get_mock_hidden_gems(limit: int = 10) -> List[Dict]:
    """Generate mock hidden gem stocks"""

    # Focus on smaller cap growth stocks
    gems = [
        "SNOW", "DDOG", "NET", "CRWD", "ZS", "OKTA", "MDB", "ESTC",
        "SOUN", "IONQ", "RXRX", "DNA", "PACB", "BILL", "FOUR", "TENB",
        "ASAN", "IOT", "TOST", "PATH", "FRSH", "FROG", "DOCN", "GTLB"
    ]

    random.shuffle(gems)

    picks = []
    for i, ticker in enumerate(gems[:limit]):
        score = random.uniform(70, 95)
        base_price = random.uniform(15, 200)
        target_price = base_price * random.uniform(1.20, 1.50)

        pick = {
            "rank": i + 1,
            "ticker": ticker,
            "score": round(score, 1),
            "currentPrice": round(base_price, 2),
            "targetPrice": round(target_price, 2),
            "potentialReturn": round(((target_price - base_price) / base_price) * 100, 2),
            "confidence": int(score),
            "gemType": "UNDERVALUED" if random.random() > 0.5 else "HIGH_GROWTH",
            "reasoning": f"Exceptional growth potential with {random.choice(['strong revenue acceleration', 'expanding margins', 'market share gains', 'innovative technology'])}",
            "catalysts": [
                random.choice(["Earnings beat expected", "New product launch", "Partnership announced"]),
                random.choice(["Institutional buying", "Market expansion", "Margin improvement"])
            ],
            "riskLevel": "MEDIUM",
            "marketCap": random.randint(1, 50) * 1e9,
            "analystCoverage": random.randint(3, 12)
        }
        picks.append(pick)

    return picks


def get_mock_quick_wins(limit: int = 10) -> List[Dict]:
    """Generate mock quick win opportunities"""

    # High volatility stocks good for day/swing trading
    tickers = [
        "NVDA", "TSLA", "AMD", "COIN", "MRNA", "PLTR", "RIVN", "LCID",
        "NIO", "MARA", "RIOT", "SMCI", "ARM", "SNOW", "CRWD"
    ]

    random.shuffle(tickers)

    picks = []
    for i, ticker in enumerate(tickers[:limit]):
        score = random.uniform(75, 95)
        base_price = random.uniform(30, 300)
        target_price = base_price * random.uniform(1.03, 1.08)

        pick = {
            "rank": i + 1,
            "ticker": ticker,
            "score": round(score, 1),
            "currentPrice": round(base_price, 2),
            "targetPrice": round(target_price, 2),
            "potentialReturn": round(((target_price - base_price) / base_price) * 100, 2),
            "timeframe": random.choice(["1-3 days", "3-7 days", "1-2 weeks"]),
            "confidence": int(score),
            "reasoning": random.choice([
                "Technical breakout with strong volume confirmation",
                "Oversold bounce setup with bullish divergence",
                "Gap fill opportunity with institutional support",
                "Momentum continuation pattern forming"
            ]),
            "entryZone": f"${round(base_price * 0.98, 2)}-${round(base_price * 1.02, 2)}",
            "stopLoss": round(base_price * 0.95, 2),
            "riskRewardRatio": round(random.uniform(2.5, 4.0), 1)
        }
        picks.append(pick)

    return picks


def get_mock_macro_indicators() -> Dict:
    """Generate mock macro economic indicators"""

    return {
        "gdp": {
            "value": round(random.uniform(2.0, 4.0), 1),
            "change": round(random.uniform(-0.5, 0.5), 1),
            "trend": "stable",
            "impact": "NEUTRAL"
        },
        "unemployment": {
            "value": round(random.uniform(3.5, 5.0), 1),
            "change": round(random.uniform(-0.3, 0.3), 1),
            "trend": "stable",
            "impact": "NEUTRAL"
        },
        "inflation": {
            "value": round(random.uniform(2.0, 4.5), 1),
            "change": round(random.uniform(-0.5, 0.5), 1),
            "trend": "declining",
            "impact": "POSITIVE"
        },
        "interestRate": {
            "value": round(random.uniform(4.5, 5.5), 2),
            "change": 0.0,
            "trend": "stable",
            "impact": "NEUTRAL"
        },
        "marketSentiment": {
            "value": random.choice(["BULLISH", "NEUTRAL", "CAUTIOUS"]),
            "vix": round(random.uniform(12, 20), 2),
            "trend": "improving",
            "impact": "POSITIVE"
        }
    }
