# Codex Handoff - TradeMaster Pro

## 2026-01-01 Update: FI disclosures/news + LLM analysis

Summary of changes for the next coding agent:
- Implemented Finnish disclosure/news ingestion + LLM analysis pipeline (OpenAI + Claude) and wired it into FI analysis output + API + scheduler.
- Added Finnish fundamentals snapshots + AI insights (LLM only on significant deltas) and surfaced on FI stock analysis page.
- Added new DB model for Finnish events; auto-created via SQLAlchemy `init_db()` on startup (no migration added to `database/init.sql` yet).
- Added frontend rendering of recent FI disclosures on `/fi/stocks/[ticker]`.

Backend changes:
- New model: `FiNewsEvent` in `backend/app/models/database.py`.
- New services:
  - `backend/app/services/fi_event_service.py` (ingest Nasdaq RSS + disclosure HTML, optional FIVA shorts, optional yfinance per-ticker news).
  - `backend/app/services/fi_llm_service.py` (Claude summary/reasoning + OpenAI structured extraction/impact; Finnish output).
  - `backend/app/services/fi_ticker_lookup.py` (ticker/company inference from `fi_tickers.json`).
- `backend/app/services/fi_data.py`: adds `newsEvents` + `eventSummary` to FI analysis response.
- `backend/app/routers/fi.py`: new endpoints:
  - `GET /api/fi/events`
  - `POST /api/fi/events/refresh` (admin key required via `x-admin-key` or Bearer; optional yfinance ingest).
- `backend/app/services/scheduler_service.py`: added scheduled FI tasks:
  - Nasdaq RSS every 5 min
  - FIVA shorts daily at 06:00 Europe/Helsinki
  - Fundamentals AI insights daily at 07:00 Europe/Helsinki
- `backend/requirements.txt`: added `openai` + `anthropic`.
 - New models in `backend/app/models/database.py`:
   - `FiFundamentalSnapshot` (daily snapshot with hash)
   - `FiAiInsight` (LLM insight records)
 - New service: `backend/app/services/fi_insight_service.py`
   - stores snapshots
   - computes diffs + thresholds
   - LLM insight generation with daily budget
 - `backend/app/services/fi_data.py`: adds `fundamentalInsight` to FI analysis output.
 - `backend/app/routers/fi.py`: new endpoints:
   - `GET /api/fi/insights`
   - `POST /api/fi/insights/refresh` (admin key required)

Frontend changes:
- `frontend/lib/api.ts`: added FI event types + `getFiEvents` helper; extended `FiAnalysis` with `newsEvents` & `eventSummary`.
- `frontend/lib/api.ts`: added `FiInsight` type and `fundamentalInsight` on `FiAnalysis`.
- `frontend/app/fi/stocks/[ticker]/page.tsx`: new “Tiedotteet & uutiset” section + “AI‑tulkinta (fundamentit)” card.
- `frontend/app/fi/dashboard/page.tsx`: new “Tiedotteet & sisäpiiri” latest events card.

Env (new variables, add to VPS `/opt/trademaster-pro/deployment/.env`):
- `OPENAI_API_KEY`, `OPENAI_MODEL` (default `gpt-4.1-mini`)
- `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` (default `claude-3-5-sonnet-latest`)
- `FI_NASDAQ_RSS_URLS` (comma-separated RSS feed URLs)
- `FI_FIVA_SHORTS_URL` (FIVA shorts page)
- `FI_NEWS_ANALYSIS_BATCH_LIMIT` (default 5)
- `FI_LLM_DAILY_LIMIT` (default 30)
- `FI_FUNDAMENTAL_INSIGHTS_PER_RUN` (default 20)

Files to deploy (SCP):
Backend:
- backend/requirements.txt
- backend/app/models/database.py
- backend/app/services/fi_ticker_lookup.py
- backend/app/services/fi_llm_service.py
- backend/app/services/fi_event_service.py
- backend/app/services/fi_insight_service.py
- backend/app/services/fi_data.py
- backend/app/routers/fi.py
- backend/app/services/scheduler_service.py
- backend/.env.example (optional, reference only)

Frontend:
- frontend/lib/api.ts
- frontend/app/fi/stocks/[ticker]/page.tsx (copy folder `frontend/app/fi/stocks` to preserve [ticker])
- frontend/app/fi/dashboard/page.tsx

After deploy:
- add env keys to `/opt/trademaster-pro/deployment/.env`
- rebuild: `docker compose build backend scheduler frontend` and restart

Mapping to `uutistiedotymsanalyysi.md` (implemented items):
1) Ingest → normalize → analyze → cache → serve:
   - Implemented in `FiEventService` + DB storage (`fi_news_events`) + API endpoints + FI analysis integration.
2) OpenAI + Claude combined:
   - `FiLLMAnalyzer` uses Claude for summary/what-changed/bullets and OpenAI for structured extraction/impact.
3) Sources:
   - Nasdaq RSS + disclosure HTML: implemented.
   - FIVA shorts: implemented (requires `FI_FIVA_SHORTS_URL`).
   - yfinance news: optional per-ticker ingestion via admin refresh.
4) Cache strategy:
   - Stored in Postgres (`fi_news_events`, `fi_fundamental_snapshots`, `fi_ai_insights`); Redis only for LLM daily budget.
5) UI:
   - FI stock analysis page shows recent events + impact badge + summary.

Known gaps / next steps:
- Add DB migration/init SQL for `fi_news_events` if you rely on `database/init.sql` only.
- Confirm FIVA page URL and/or use official CSV/Excel if available.
- Optional: add FI dashboard “latest disclosures” and per-ticker ingestion triggers.
- Add IR site scraping (not implemented).
- Optional: expose fundamentals snapshots for UI charts.

 

As of this session, we added auth + account watchlists + alert sync, and moved earnings to yfinance only.

Current user intent:
- Use Postgres (production-friendly). Docker is not installed yet; user will reboot to finish install.

Where we left off:
- backend/.env currently uses SQLite and a generated SECRET_KEY. Needs update to Postgres once Docker is ready.
- Docker command failed because docker is not recognized (not installed / PATH).

Next steps after reboot (Docker Desktop installed):
1) Verify Docker: `docker --version`
2) Start Postgres:
   docker run --name trademaster-postgres -e POSTGRES_DB=trademaster -e POSTGRES_USER=trademaster -e POSTGRES_PASSWORD=YOUR_PASS -p 5432:5432 -v trademaster_pg:/var/lib/postgresql/data -d postgres:15-alpine
3) Update backend/.env:
   DATABASE_URL=postgresql://trademaster:YOUR_PASS@localhost:5432/trademaster
4) Restart backend.

Key code changes (backend):
- backend/app/services/earnings_service.py: now yfinance-only earnings calendar data.
- backend/app/services/finnhub_service.py: added get_insider_transactions.
- backend/app/services/insider_trading_service.py: uses Finnhub insider transactions + SEC EDGAR fallback; added cache.
- backend/app/services/short_interest_service.py: yfinance-based short interest; added cache.
- backend/app/services/options_flow_service.py: yfinance options chain analysis; added cache.
- backend/app/services/enhanced_predictor.py: hidden gems scan over full universe with shortlist + scoring; quick wins uses use_advanced_data=False.
- backend/app/services/auth_service.py: custom HMAC token auth + password hashing (PBKDF2).
- backend/app/routers/auth.py: register/login/me endpoints.
- backend/app/routers/watchlist.py: watchlist CRUD + alerts/summary endpoints.
- backend/app/models/database.py: Watchlist model + get_db helper + SQLite connect args.
- backend/app/config/settings.py: SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, PASSWORD_HASH_ITERATIONS.
- backend/main.py: include auth/watchlist routers + init_db on startup.

Key code changes (frontend):
- frontend/lib/auth.ts and frontend-nordic/lib/auth.ts: token/user storage helpers.
- frontend/lib/api.ts and frontend-nordic/lib/api.ts: adds Authorization header, auth + watchlist endpoints.
- frontend/components/SmartAlerts.tsx (+ nordic): login/register UI; watchlist synced to server when logged in; fallback to local storage for guests; alerts fetched from server watchlist if logged in.
- frontend/app/stocks/[ticker]/page.tsx (+ nordic): watchlist toggle uses server when logged in, local storage otherwise; shows source + error state.

Storage details:
- Auth token stored in localStorage key `tm_auth_token`, user in `tm_auth_user`.
- Guest watchlist stored in localStorage `tm_watchlist`.
- Account watchlist stored in DB table `watchlists`.

Notes / Known gaps:
- No JWT library; custom HMAC token. Tokens expire by timestamp.
- No migrations; SQLAlchemy creates tables on startup.
- backend/.env currently set to SQLite; must update to Postgres after Docker install.

Files likely to continue editing:
- backend/.env
- backend/app/services/auth_service.py
- backend/app/routers/auth.py
- backend/app/routers/watchlist.py
- frontend/components/SmartAlerts.tsx
- frontend/app/stocks/[ticker]/page.tsx
