# TradeMaster Pro Backend API

FastAPI-based backend with real-time WebSocket support, AI predictions, and comprehensive market analytics.

## Features

- 🚀 **FastAPI** - High-performance async Python web framework
- 📡 **Socket.IO** - Real-time bidirectional communication
- 🤖 **AI-Powered** - Machine learning predictions and analytics
- 📊 **Market Data** - Stocks, crypto, social sentiment, macro indicators
- 🔒 **CORS** - Configured for frontend integration
- 📚 **Auto Documentation** - Swagger UI and ReDoc

## Quick Start

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Setup

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
DATABASE_URL=postgresql://trademaster:trademaster123@localhost:5432/trademaster
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 3. Run the Server

**Standard mode:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**With Socket.IO support:**
```bash
uvicorn main:socket_app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Root & Health

- `GET /` - API information
- `GET /health` - Health check
- `GET /ping` - Connectivity test

### Stocks

- `GET /api/stocks/top-picks?timeframe=[day|swing|long]` - AI stock picks
- `GET /api/stocks/movers` - Top gainers/losers
- `GET /api/stocks/{ticker}` - Stock details
- `GET /api/stocks/{ticker}/news` - Stock news
- `GET /api/stocks/{ticker}/sentiment` - Social sentiment

### Crypto

- `GET /api/crypto/top-picks` - AI crypto picks
- `GET /api/crypto/movers` - 24h top movers
- `GET /api/crypto/{symbol}` - Crypto details
- `GET /api/crypto/{symbol}/news` - Crypto news
- `GET /api/crypto/fear-greed` - Fear & Greed Index
- `GET /api/crypto/market` - Market overview

### Social Media

- `GET /api/social/trending` - Trending across platforms
- `GET /api/social/sentiment/{ticker}` - Detailed sentiment
- `GET /api/social/reddit/wallstreetbets` - WSB trending
- `GET /api/social/twitter/trending` - Twitter trending
- `GET /api/social/analysis/{ticker}` - Comprehensive analysis

### Macro Economics

- `GET /api/macro/indicators` - Economic indicators
- `GET /api/macro/fed` - Federal Reserve data
- `GET /api/macro/events/upcoming` - Upcoming events
- `GET /api/macro/calendar` - Economic calendar
- `GET /api/macro/market-sentiment` - Market sentiment

## WebSocket / Socket.IO

### Connect to Socket.IO

```javascript
import io from 'socket.io-client';

const socket = io('http://localhost:8000');

// Connection established
socket.on('connection_established', (data) => {
  console.log('Connected:', data);
});

// Subscribe to ticker updates
socket.emit('subscribe_ticker', { ticker: 'NVDA' });

// Listen for subscribed confirmation
socket.on('subscribed', (data) => {
  console.log('Subscribed to:', data.ticker);
});

// Unsubscribe
socket.emit('unsubscribe_ticker', { ticker: 'NVDA' });
```

### Socket.IO Events

**Client → Server:**
- `subscribe_ticker` - Subscribe to real-time updates for a ticker
- `unsubscribe_ticker` - Unsubscribe from ticker updates

**Server → Client:**
- `connection_established` - Connection confirmation
- `subscribed` - Subscription confirmation
- `unsubscribed` - Unsubscription confirmation
- `ticker_update` - Real-time ticker data (when implemented)

## Project Structure

```
backend/
├── app/
│   ├── api/              # Deprecated - removed
│   ├── config/           # Configuration
│   │   └── settings.py   # App settings
│   ├── models/           # Database models
│   │   └── database.py   # SQLAlchemy models
│   ├── routers/          # API routers
│   │   ├── stocks.py     # Stock endpoints
│   │   ├── crypto.py     # Crypto endpoints
│   │   ├── social.py     # Social media endpoints
│   │   └── macro.py      # Macro economics endpoints
│   └── services/         # Business logic
│       ├── analytics_service.py
│       └── market_service.py
├── main.py               # FastAPI app entry point
├── requirements.txt      # Python dependencies
└── .env.example          # Environment template
```

## CORS Configuration

CORS is configured to allow requests from:
- `http://localhost:3000` (Next.js development)
- `http://localhost:8000` (FastAPI development)
- `http://frontend:3000` (Docker container)

Additional origins can be configured in `app/config/settings.py`.

## Development

### Run with auto-reload

```bash
uvicorn main:socket_app --reload --host 0.0.0.0 --port 8000
```

### Run tests (when implemented)

```bash
pytest
```

### Code formatting

```bash
black .
isort .
```

## Docker

```bash
# Build
docker build -t trademaster-backend .

# Run
docker run -p 8000:8000 trademaster-backend
```

## Deployment

### Production Run

```bash
uvicorn main:socket_app --host 0.0.0.0 --port 8000 --workers 4
```

### With Gunicorn

```bash
gunicorn main:socket_app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## API Documentation

The API includes automatic interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
  - Interactive API testing
  - Request/response examples
  - Schema definitions

- **ReDoc**: http://localhost:8000/redoc
  - Clean, readable documentation
  - Search functionality
  - Code samples

## Monitoring

Health check endpoint for monitoring:

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-11-05T20:00:00.000000",
  "service": "TradeMaster Pro API",
  "version": "1.0.0"
}
```

## Troubleshooting

### Port already in use

```bash
# Find process using port 8000
lsof -i :8000
# Or on Windows
netstat -ano | findstr :8000

# Kill the process
kill -9 <PID>
```

### Module not found

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### CORS errors

Make sure the frontend URL is in the CORS allowed origins list in `main.py`.

## License

Private - All rights reserved

## Support

For issues and questions, please open an issue in the repository.
