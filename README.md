# TradeMaster Pro   https://trademaster.guru/ 

Data-driven stock analysis platform for Finnish and US markets with real-time market data and advanced technical analysis.

## What this is

TradeMaster Pro is a professional trading analysis platform that combines:

- **Advanced Stock Screening** - Multi-factor scoring algorithms analyze 1000+ stocks and generate buy/sell signals
- **Real-Time Market Data** - Prices, news, and social media sentiment update via WebSocket
- **Technical Analysis** - RSI, MACD, Bollinger Bands, moving averages, volume analysis
- **Social Sentiment Tracking** - Reddit (r/wallstreetbets, r/stocks) and Twitter sentiment monitoring
- **Portfolio Analysis** - Risk management and diversification analytics

Supports both **US markets** (S&P 500, NYSE, NASDAQ - 1000+ stocks) and **Finnish markets** (Helsinki Stock Exchange).

## Why I built this

I wanted to build a comprehensive trading tool that:

1. Automates stock analysis and saves time from manual research
2. Aggregates multiple data sources (prices, news, social media) into one view
3. Provides data-driven signals to support decision-making
4. Works in real-time with WebSocket connections
5. Teaches full-stack development with a modern tech stack

## How it works

### Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend     │────▶│     Backend     │────▶│   Data Sources  │
│    (Next.js)    │◀────│    (FastAPI)    │◀────│    (APIs)       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │
        │                       ▼
        │               ┌───────────────┐
        │               │  PostgreSQL   │
        │               │    + Redis    │
        │               └───────────────┘
        │                       │
        └───────── WebSocket ───┘
```

### Data Flow

1. **Backend** fetches data from external APIs (yfinance, Finnhub, Reddit, Twitter)
2. **Redis** caches data (prices 60s, analysis 12h, news 10min)
3. **Analysis engine** scores stocks using technical indicators and sentiment data
4. **WebSocket** sends real-time updates to frontend
5. **Frontend** displays data as interactive charts and cards

## Tech Stack

### Backend
```
Python 3.11+
├── FastAPI          # Web framework
├── SQLAlchemy       # ORM (PostgreSQL)
├── Redis            # Caching
├── Socket.IO        # Real-time communication
├── Pandas/NumPy     # Data analysis & calculations
├── TA-Lib patterns  # Technical indicator calculations
└── APScheduler      # Background tasks
```

### Frontend
```
TypeScript / Next.js 14
├── React 18          # UI library
├── React Query       # Server state management
├── Zustand           # Client state management
├── Tailwind CSS      # Styling
├── Recharts          # Charts
├── lightweight-charts # TradingView-style candlesticks
└── Socket.io-client  # WebSocket client
```

### Data Sources
```
├── yfinance          # Stock data, historical prices
├── Finnhub           # Real-time market data, news
├── NewsAPI           # Financial news
├── Reddit (PRAW)     # Social sentiment
├── Twitter (Tweepy)  # Social sentiment
├── FRED API          # Macroeconomic indicators
└── Binance           # Crypto data
```

## Quick Start

### Using Docker (Recommended)

```bash
# Clone the repo
git clone https://github.com/Pera213-max/trademasterstockanalysis.git
cd trademasterstockanalysis

# Copy environment template
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker-compose up -d
```

### Manual Setup

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

**Services:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Environment Variables

See `.env.example` for all required variables. Key APIs needed:

| Variable | Description | Required |
|----------|-------------|----------|
| `FINNHUB_API_KEY` | Market data & news | Yes |
| `NEWS_API_KEY` | Financial news | Yes |
| `REDDIT_CLIENT_ID` | Social sentiment | Optional |
| `REDDIT_CLIENT_SECRET` | Social sentiment | Optional |
| `DATABASE_URL` | PostgreSQL connection | Yes |
| `REDIS_URL` | Redis connection | Yes |

## Repository Structure

```
trademasterstockanalysis/
├── backend/
│   ├── app/
│   │   ├── routers/      # API endpoints
│   │   ├── services/     # Business logic
│   │   ├── models/       # Database models
│   │   └── config/       # Settings
│   ├── main.py           # FastAPI entry point
│   └── requirements.txt
├── frontend/
│   ├── app/              # Next.js pages
│   ├── components/       # React components
│   ├── lib/              # Utilities, API client
│   └── package.json
├── docs/
│   └── images/           # Screenshots
├── docker-compose.yml
└── README.md
```

## What I Learned

### Technical Lessons

1. **Full-stack Architecture** - Building a scalable app with separate frontend and backend
2. **Real-time Systems** - Managing WebSocket connections with Socket.IO
3. **Caching Strategies** - Redis patterns and TTL-based invalidation
4. **Data Pipeline Design** - Aggregating and processing data from multiple APIs
5. **API Integrations** - Combining multiple external APIs with rate limiting
6. **TypeScript** - Type-safe frontend development
7. **Docker** - Containerization and docker-compose for production

### Architectural Insights

- **Service layer importance** - Separates business logic from API routes
- **Caching is critical** - 90%+ cache hit rate significantly improves performance
- **Real-time data requires careful design** - Pub/Sub architecture scales well

## Code Examples

### Backend: Stock Analysis Endpoint (FastAPI)

```python
# backend/app/routers/stocks.py

@router.get("/api/stocks/analysis/{ticker}")
async def get_stock_analysis(ticker: str):
    # Check cache first
    cached = await redis.get(f"analysis:{ticker}")
    if cached:
        return json.loads(cached)

    # Fetch data and run analysis
    stock_data = await yfinance_service.get_stock_data(ticker)
    analysis = stock_analyzer.analyze(stock_data)

    result = {
        "ticker": ticker,
        "price": stock_data.current_price,
        "signal": analysis.signal,  # "BUY" / "SELL" / "HOLD"
        "score": analysis.score,
        "technical_indicators": {
            "rsi": stock_data.rsi,
            "macd": stock_data.macd,
        }
    }

    # Cache for 12 hours
    await redis.setex(f"analysis:{ticker}", 43200, json.dumps(result))
    return result
```

### Frontend: Real-time Price Updates (React + WebSocket)

```typescript
// frontend/components/TopMovers.tsx

import { useWebSocket } from '@/lib/websocket';
import { useQuery, useQueryClient } from '@tanstack/react-query';

export function TopMovers() {
  const queryClient = useQueryClient();

  const { data: movers } = useQuery({
    queryKey: ['top-movers'],
    queryFn: () => fetch('/api/stocks/top-movers').then(r => r.json()),
  });

  // Listen for real-time price updates
  useWebSocket('prices', (update) => {
    queryClient.setQueryData(['top-movers'], (old: Stock[]) =>
      old?.map(stock =>
        stock.ticker === update.ticker
          ? { ...stock, price: update.price, change: update.change }
          : stock
      )
    );
  });

  return (
    <div className="grid grid-cols-2 gap-4">
      {movers?.map(stock => (
        <StockCard
          key={stock.ticker}
          ticker={stock.ticker}
          price={stock.price}
          change={stock.change}
        />
      ))}
    </div>
  );
}
```

### Stock Scoring Algorithm

```python
# backend/app/services/predictor.py

class StockAnalyzer:
    def calculate_score(self, data: pd.DataFrame) -> float:
        score = 0.0

        # Technical indicators (40 points)
        if data['rsi'].iloc[-1] < 30:  # Oversold
            score += 15
        if data['close'].iloc[-1] > data['sma_50'].iloc[-1]:
            score += 15
        if data['macd'].iloc[-1] > data['macd_signal'].iloc[-1]:
            score += 10

        # Volume analysis (20 points)
        if data['volume'].iloc[-1] > data['volume_avg'].iloc[-1] * 1.5:
            score += 20

        # Momentum (20 points)
        weekly_change = (data['close'].iloc[-1] / data['close'].iloc[-5] - 1)
        if weekly_change > 0.05:
            score += 20

        # Sentiment bonus (20 points)
        score += self._calculate_sentiment_score(data)

        return min(score, 100)
```

## Roadmap

- [ ] Options trading analysis
- [ ] Advanced backtesting engine
- [ ] Mobile app (React Native)
- [ ] User authentication & saved portfolios
- [ ] Email/SMS alerts
- [ ] Expanded cryptocurrency support

## License

MIT

---

*Built for learning purposes - not financial advice!*
