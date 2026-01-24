# Prelaunch Checklist (VPS + Docker + Redis)

Scope: run these checks before choosing a VPS/domain and before public launch.

Critical fixes
- Backend Docker entrypoint uses socket_app (Socket.IO enabled).
- No startup errors in backend logs.

Configuration
- backend/.env uses production values:
  - ENVIRONMENT=production
  - DEBUG=false
  - DATABASE_URL uses "postgres" service host (not localhost)
  - REDIS_* values set
  - CORS_ORIGINS includes planned domains
- deployment/.env set:
  - POSTGRES_* and REDIS_PASSWORD
  - NEXT_PUBLIC_API_URL and NEXT_PUBLIC_WS_URL (will be updated when domain is chosen)

Smoke tests (local or staging)
- docker compose up -d --build (from deployment/)
- Backend health: http://localhost:8000/health
- API docs: http://localhost:8000/docs
- Frontend loads: http://localhost:3000
- Register/login works and persists in DB
- Watchlist add/remove persists across refresh
- News Bombs tab shows high-impact items (no obvious off-topic news)
- Stock news analysis for a ticker returns relevant items
- WebSockets connect and update (news/price events)

Operational checks
- Logs: docker compose logs -f backend
- Container status: docker compose ps
- Database reachable: psql inside postgres container

Go/No-Go
- All smoke tests pass
- No critical errors in logs after 15-30 minutes
- API rate limits are not tripping on normal usage

