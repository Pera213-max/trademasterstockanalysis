# 🚀 TradeMaster Pro - Quick Start Guide

Get up and running in 10 minutes!

---

## Step 1: Get API Keys (5 minutes)

### Required APIs

1. **Finnhub** (Market Data) - FREE
   - Visit: https://finnhub.io/register
   - Sign up with email
   - Copy your API key
   - Free tier: 60 calls/minute ✅

2. **NewsAPI** (Financial News) - FREE
   - Visit: https://newsapi.org/register
   - Sign up with email
   - Copy your API key
   - Free tier: 100 requests/day ✅

3. **Reddit API** (Social Sentiment) - FREE
   - Visit: https://www.reddit.com/prefs/apps
   - Click "Create App" or "Create Another App"
   - Fill in:
     - Name: TradeMaster Pro
     - Type: **script**
     - Redirect URI: http://localhost:8000
   - Click "Create app"
   - Copy:
     - Client ID (under app name)
     - Client Secret
   - Completely FREE ✅

---

## Step 2: Setup Backend (3 minutes)

```bash
# 1. Navigate to backend folder
cd backend

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create .env file
cp .env.example .env

# 6. Edit .env file and add your API keys:
# - FINNHUB_API_KEY=your_key_here
# - NEWS_API_KEY=your_key_here
# - REDDIT_CLIENT_ID=your_id_here
# - REDDIT_CLIENT_SECRET=your_secret_here
```

**Important:** Open `.env` in a text editor and paste your API keys!

---

## Step 3: Setup Frontend (2 minutes)

```bash
# 1. Navigate to frontend folder (open new terminal)
cd frontend

# 2. Install dependencies
npm install

# 3. Create .env.local file
cp .env.example .env.local

# 4. Edit .env.local (optional - defaults work)
# NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Step 4: Run the Application

### Terminal 1 - Backend
```bash
cd backend
# Make sure virtual environment is activated
uvicorn main:socket_app --reload
```

**Backend running at:** http://localhost:8000

### Terminal 2 - Frontend
```bash
cd frontend
npm run dev
```

**Frontend running at:** http://localhost:3000

---

## Step 5: Verify Everything Works ✅

1. **Open Browser**
   - Go to: http://localhost:3000

2. **Check Dashboard**
   - You should see:
     - Market Pulse (Live S&P 500, NASDAQ, Dow)
     - AI Top Picks
     - News Feed
     - Social Trending
     - Upcoming Events

3. **Verify Real Data**
   - Market indices should show real numbers
   - News should be recent (today's date)
   - Social trending from Reddit
   - AI picks refreshing every 30 minutes

4. **Check API Docs**
   - Open: http://localhost:8000/docs
   - Swagger UI with all endpoints
   - Try "GET /health" endpoint

---

## Troubleshooting

### "Module not found" errors
```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### "FINNHUB_API_KEY not found"
- Check `.env` file exists in `backend/` folder
- Verify API key is correct (no spaces)
- Restart backend server

### "CORS Error" in browser
- Make sure backend is running on port 8000
- Frontend should be on port 3000
- Check `CORS_ORIGINS` in backend `.env`

### API Rate Limits
- Finnhub Free: 60 calls/minute (sufficient for testing)
- NewsAPI Free: 100 calls/day (limited, upgrade if needed)
- Reddit API: No limits on free tier

### Port Already in Use
```bash
# Backend (port 8000)
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Mac/Linux:
lsof -ti:8000 | xargs kill

# Frontend (port 3000)
# Windows:
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Mac/Linux:
lsof -ti:3000 | xargs kill
```

---

## What You Get

### Real-Time Data
- ✅ 1,015 stocks (S&P 500, NYSE, NASDAQ, International)
- ✅ Live market indices (S&P, NASDAQ, Dow, VIX)
- ✅ Sector performance (9 sectors)
- ✅ Auto-updates every 2-5 minutes

### AI Predictions
- ✅ Day trading picks (1-3 days)
- ✅ Swing trading picks (1-4 weeks)
- ✅ Long-term investments (3+ months)
- ✅ Hidden gems (undervalued)
- ✅ Quick wins (momentum)

### News & Social
- ✅ Multi-source news (Finnhub, NewsAPI, yfinance)
- ✅ Reddit trending (r/wallstreetbets, r/stocks)
- ✅ Sentiment analysis
- ✅ Economic calendar (earnings, IPOs, Fed events)

### Analytics
- ✅ Sector heatmap
- ✅ Top movers (gainers/losers)
- ✅ Technical indicators
- ✅ Portfolio analyzer
- ✅ Smart alerts

---

## Next Steps

### Customize Settings
Edit `backend/.env` to configure:
- Cache durations
- API rate limits
- Data refresh intervals

### Deploy to Production
See [DEPLOYMENT.md](DEPLOYMENT.md) for:
- Railway deployment (backend)
- Vercel deployment (frontend)
- Custom domain setup
- Production configuration

### Upgrade API Plans
For production use:
- **Finnhub Premium**: $10-25/month (more calls/minute)
- **NewsAPI Business**: $449/month (unlimited, real-time)
- **Reddit API**: Always free!

---

## Need Help?

### Check Documentation
- **README.md** - Full project documentation
- **DEPLOYMENT.md** - Deployment guides
- **API Docs** - http://localhost:8000/docs

### Common Issues
1. **No data showing:**
   - Check API keys in `.env`
   - Verify backend is running
   - Check browser console for errors

2. **Slow loading:**
   - First load takes longer (fetching data)
   - Data is cached after first load
   - Auto-updates in background

3. **PRAW warnings:**
   - Warning about async PRAW is normal
   - Reddit data still works fine
   - Can be ignored safely

---

## Development Tips

### Hot Reload
- **Backend:** Auto-reloads on code changes (--reload flag)
- **Frontend:** Hot Module Replacement (HMR) enabled
- Just save files and see changes!

### View Logs
```bash
# Backend logs show:
- API requests
- Data fetches
- Cache hits/misses
- Background scheduler
- Errors

# Frontend logs in browser console:
- API calls
- Component renders
- React Query cache
```

### API Testing
Use Swagger UI at http://localhost:8000/docs:
- Test all endpoints
- See request/response formats
- Try different parameters
- No Postman needed!

---

**You're all set! Happy trading! 📈**

---

## Quick Reference

### Start Development
```bash
# Terminal 1 (Backend)
cd backend && venv\Scripts\activate && uvicorn main:socket_app --reload

# Terminal 2 (Frontend)
cd frontend && npm run dev
```

### Stop Servers
- Press `Ctrl + C` in each terminal

### Update Dependencies
```bash
# Backend
cd backend && pip install -r requirements.txt

# Frontend
cd frontend && npm install
```

### View Logs
- Backend: Check terminal output
- Frontend: Browser Developer Tools (F12)

---

**Last Updated:** 2025-11-25  
**Version:** 1.0.0  
**Status:** Production Ready
