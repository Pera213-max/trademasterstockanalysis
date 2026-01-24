Context
We have an existing stock-analysis web app (“TradeMaster”) with a Next.js frontend and a FastAPI backend. Currently it focuses on US stocks (NYSE/NASDAQ/S&P 500). We want to add a Finland market mode (Nasdaq Helsinki) under the same product/brand, accessible from a landing page with two buttons: “US” and “Finland”.

High-level goal
Implement a market selector landing page and add FI support end-to-end:

Frontend routes: / landing, /us/* and /fi/*

Backend routes: /api/us/* and /api/fi/*

Shared UI components where possible; market-specific adapters for tickers, currency, exchanges, and trading hours.

1) Product/UX requirements
Landing page

Route: /

Two primary CTAs:

“US Markets (NYSE / NASDAQ / S&P 500)” → /us/dashboard

“Finland (Nasdaq Helsinki)” → /fi/dashboard

Remember last selection in localStorage (e.g. preferred_market=us|fi) and show a small “Continue” button if available.

Dashboards

/us/dashboard remains as it is.

Add /fi/dashboard with the same layout but Finland data:

list of top-ranked FI stocks (or watchlist)

quick filters: “Large cap”, “Dividend”, “High momentum”, etc. (can be minimal at first)

“View analysis” per ticker goes to /fi/stocks/{ticker}

Stock analysis page

/fi/stocks/{ticker} similar to US view:

OHLCV chart

key metrics (market cap, PE, etc.) if available

volatility/drawdown

a simple score/rank (can reuse existing scoring system with market normalization)

2) Data sources (MVP)

We prioritize low-cost/free sources first.

Price data (OHLCV)

Use yfinance:

Finland tickers use .HE suffix:

NOKIA.HE, KNEBV.HE, UPM.HE, FORTUM.HE, etc.

Implement:

daily OHLCV for last 1y/5y

optional: intraday if needed (but MVP can be daily only)

Fundamentals

Use yfinance fields where available:

marketCap, trailingPE, forwardPE, profitMargins, revenueGrowth, etc.
Fallback:

if a field is missing, return null and show “—” in UI.

News/sentiment (optional for MVP)

If already present for US, extend to FI with:

NewsAPI or RSS feeds (Nasdaq Helsinki releases, major Finnish business media RSS)

Keep this optional; do not block MVP.

3) Backend changes (FastAPI)
Routing structure

Create two routers:

backend/app/routers/us.py (existing, keep)

backend/app/routers/fi.py (new)

Mount:

/api/us/...

/api/fi/...

Endpoints required for FI

Implement at minimum:

GET /api/fi/universe

returns list of FI tickers (Nasdaq Helsinki universe)

For MVP: store a curated list in data/fi_tickers.json (or DB later)

GET /api/fi/quote/{ticker}

returns latest price + daily change if feasible

GET /api/fi/history/{ticker}?range=1y&interval=1d

returns OHLCV series (date, open, high, low, close, volume)

GET /api/fi/analysis/{ticker}

returns:

profile (name, exchange, currency)

fundamentals (best-effort)

risk metrics (volatility, max drawdown)

score (0-100) and explanation fields

GET /api/fi/rank?limit=50

returns top-ranked FI stocks by score

Implementation details

Add a module: backend/app/services/fi_data.py

get_fi_history(ticker, range, interval)

get_fi_fundamentals(ticker)

compute_fi_metrics(history)

compute_fi_score(metrics, fundamentals)

Use caching:

in-memory TTL cache or Redis if already in stack

cache history per ticker for 15–60 min

cache rank list for 30–60 min

Score (MVP)

Re-use an existing scoring approach but simplified:

Momentum: 3m and 12m return

Risk: annualized volatility and max drawdown

Fundamentals: trailingPE (if present), profitMargins (if present)
Output:

score_total (0–100)

score_components dict so UI can show breakdown

Important: score must be robust to missing fundamentals (do not crash; normalize and skip missing components).

4) Frontend changes (Next.js)
Routes and pages

Add new route group:

/app/us/dashboard/page.tsx (or existing structure)

/app/fi/dashboard/page.tsx

/app/fi/stocks/[ticker]/page.tsx
Create landing:

/app/page.tsx with the two buttons.

API client

Update API client to support market prefix:

apiGet(market, path)

US uses /api/us

FI uses /api/fi

Shared components

Keep shared components:

Chart component

Metric cards

Table/list

Market-specific:

ticker formatting, exchange labels, currency (EUR for FI)

optionally a small “MarketBadge” (US/FI)

UX requirements

If user enters FI ticker without .HE, auto-append .HE (optional but useful)

Show friendly error states (ticker not found, rate-limited, etc.)

5) Universe list for Finland (MVP approach)

Create a curated list (20–60 tickers) to ship quickly.
Store in:

backend/app/data/fi_tickers.json
Fields:

ticker

name

sector (optional)
The tool should also implement a future-proof interface so we can later replace it with a full Nasdaq Helsinki list ingestion job.

6) Acceptance criteria

Landing page exists with two buttons and working navigation.

/fi/dashboard loads and shows a list of FI tickers with scores.

Clicking a FI ticker opens /fi/stocks/{ticker} and renders:

chart from history

fundamentals (best-effort)

volatility/drawdown

score breakdown

No crashes when fundamentals are missing; UI shows placeholders.

Caching works (subsequent requests are faster).

7) Deliverables

Ask the AI tool to output:

File tree changes

Full code for new/modified files

Any environment variable changes

Minimal instructions to run locally:

backend uvicorn ...

frontend npm run dev

If Docker is used, update docker-compose.yml if required.

8) Constraints and notes

Keep MVP minimal: daily data + scoring + rank is enough.

Avoid paid APIs for now.

Ensure consistent response schema between US and FI endpoints where possible.

Do not refactor unrelated parts unless necessary.

Extra: Implementation hint for yfinance ticker conventions (Finland)

Most Nasdaq Helsinki tickers: TICKER.HE

Example: NOKIA.HE, KNEBV.HE, UPM.HE, FORTUM.HE, NESTE.HE, SAMPO.HE