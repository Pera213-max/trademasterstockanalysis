# VPS Deploy Plan (Docker + Redis)

Goal: Deploy TradeMaster Pro on a single VPS (20-30 EUR/month) using Docker
Compose, with Redis running as a container. This is the most stable and
cost-effective option for this app.

Key notes
- Redis is included via Docker Compose. No external Redis service needed.
- Use a single VPS: backend, frontend, Postgres, Redis, scheduler, Socket.IO.
- Scheduler runs as a separate container; backend API runs without background jobs.
- IMPORTANT: WebSocket support is currently wired to socket_app, but the Docker
  image runs main:app. This must be fixed before go-live.

Must verify before go-live
- Backend Docker entrypoint uses socket_app so WebSockets work.
  Current: backend/Dockerfile -> main:socket_app (Gunicorn UvicornWorker)

Recommended VPS
- Ubuntu 22.04 LTS
- 4 vCPU / 8 GB RAM / 80+ GB SSD
- Budget fits ~20-30 EUR/month from most providers

Pre-flight checklist
- Domain name ready (optional but recommended)
- API keys ready (Finnhub, NewsAPI, FRED, Reddit, etc)
- Strong secrets prepared (SECRET_KEY, DB password, Redis password)

Step 1: Provision VPS
- Create VPS, note public IP
- Add your SSH key
- Optional: create DNS A record (app.yourdomain.com -> VPS IP)

Step 2: Server bootstrap (SSH)
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl ca-certificates
```

Step 3: Install Docker + Compose
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
docker --version
docker compose version
```

Step 4: Get the code
```bash
git clone <your_repo_url> trademaster-pro
cd trademaster-pro
```

Step 5: Configure env files
1) backend/.env (production values)
   - DATABASE_URL must use the service name "postgres" (not localhost)
     DATABASE_URL=postgresql://trademaster:<DB_PASS>@postgres:5432/trademaster
   - ENVIRONMENT=production
   - DEBUG=false
   - CORS_ORIGINS should include your domain(s)

2) deployment/.env (for docker-compose)
```bash
POSTGRES_DB=trademaster
POSTGRES_USER=trademaster
POSTGRES_PASSWORD=<DB_PASS>
REDIS_PASSWORD=<REDIS_PASS>
BACKEND_PORT=8000
FRONTEND_PORT=3000
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_WS_URL=wss://api.yourdomain.com
ADMIN_API_KEY=<ADMIN_KEY>  # Required for force_refresh endpoints
```

Step 6: Fix WebSocket entrypoint (required)
- Change backend/Dockerfile CMD to use main:socket_app
  (We will do this before production run.)

Step 7: Build + start
```bash
cd deployment
docker compose up -d --build
docker compose ps
```

Step 8: Reverse proxy + TLS
Option A (recommended): Caddy
- Run Caddy on the VPS and proxy to frontend + backend.
- Example Caddyfile:
  - app.yourdomain.com -> frontend:3000
  - api.yourdomain.com -> backend:8000

Option B: Nginx (manual TLS via certbot)

Step 9: Smoke tests
- Backend health: https://api.yourdomain.com/health
- Docs: https://api.yourdomain.com/docs
- Frontend: https://app.yourdomain.com
- Login/register flow
- Watchlist add/remove persists
- Check WebSocket events (news/price update UI)

Step 10: Monitoring + backups
- Log tail: docker compose logs -f backend
- DB backup: pg_dump to a nightly file + offsite copy
- Uptime monitor (UptimeRobot) on /health

Step 11: Updates and rollback
```bash
git pull
docker compose up -d --build
```
Rollback: `git checkout <tag>` then rebuild.

Before public launch
- Run the smoke tests above
- Confirm CORS origins in backend/.env
- Confirm WebSockets work (socket_app)
- Ensure API rate limits and caching are stable
