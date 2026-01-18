# TradeMaster Pro - Docker Deployment

Complete Docker-based deployment configuration for TradeMaster Pro trading platform.

## 📦 Services

This deployment includes 4 services:

1. **PostgreSQL 15** - Primary database
2. **Redis 7** - Caching and pub/sub
3. **Backend** - FastAPI application
4. **Frontend** - Next.js application (optional - can use Vercel)

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- At least 4GB RAM available for Docker

### 1. Clone Repository

```bash
git clone <your-repo-url>
cd pera/deployment
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API keys and passwords
nano .env
```

**Required Environment Variables:**

- `POSTGRES_PASSWORD` - Secure PostgreSQL password
- `REDIS_PASSWORD` - Secure Redis password
- `FRED_API_KEY` - Federal Reserve Economic Data API key
- `ALPHA_VANTAGE_API_KEY` - Stock data API key
- `REDDIT_CLIENT_ID` & `REDDIT_CLIENT_SECRET` - Reddit API credentials

### 3. Start Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 4. Verify Deployment

- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## 🔧 Common Commands

### Service Management

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart a specific service
docker-compose restart backend

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Execute commands in containers
docker-compose exec backend bash
docker-compose exec postgres psql -U trademaster -d trademaster
docker-compose exec redis redis-cli -a your_redis_password
```

### Database Management

```bash
# Access PostgreSQL
docker-compose exec postgres psql -U trademaster -d trademaster

# Run migrations (if you have them)
docker-compose exec backend alembic upgrade head

# Backup database
docker-compose exec postgres pg_dump -U trademaster trademaster > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T postgres psql -U trademaster -d trademaster
```

### Cache Management

```bash
# Access Redis CLI
docker-compose exec redis redis-cli -a your_redis_password

# Flush cache
docker-compose exec redis redis-cli -a your_redis_password FLUSHALL

# Monitor Redis
docker-compose exec redis redis-cli -a your_redis_password MONITOR
```

### Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove containers and volumes (⚠️ deletes all data)
docker-compose down -v

# Remove containers, volumes, and images
docker-compose down -v --rmi all

# Prune unused Docker resources
docker system prune -a
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                        │
│                  (trademaster-network)                   │
│                                                          │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐           │
│  │ Frontend │   │ Backend  │   │PostgreSQL│           │
│  │ Next.js  │◄──┤  FastAPI │◄──┤    15    │           │
│  │  :3000   │   │  :8000   │   │  :5432   │           │
│  └──────────┘   └─────┬────┘   └──────────┘           │
│                       │                                  │
│                       │        ┌──────────┐             │
│                       └────────┤  Redis 7 │             │
│                                │  :6379   │             │
│                                └──────────┘             │
└─────────────────────────────────────────────────────────┘
```

## 📊 Volumes

Persistent data is stored in Docker volumes:

- `postgres_data` - PostgreSQL database files
- `redis_data` - Redis persistence files
- `backend_cache` - Backend cache files

**Location**: `/var/lib/docker/volumes/`

## 🔐 Security Recommendations

### Production Deployment

1. **Change Default Passwords**
   - Update `POSTGRES_PASSWORD`
   - Update `REDIS_PASSWORD`
   - Generate strong `JWT_SECRET`

2. **Restrict Network Access**
   - Don't expose PostgreSQL/Redis ports publicly
   - Use firewall rules
   - Configure `CORS_ORIGINS` appropriately

3. **Use Secrets Management**
   - Docker Swarm secrets
   - Kubernetes secrets
   - HashiCorp Vault

4. **Enable SSL/TLS**
   - Use reverse proxy (nginx, Traefik)
   - Configure HTTPS certificates
   - Enable PostgreSQL SSL

5. **Resource Limits**
   ```yaml
   services:
     backend:
       deploy:
         resources:
           limits:
             cpus: '2'
             memory: 2G
   ```

## 🌐 Production Deployment Options

### Option 1: Frontend on Vercel, Backend on Docker

```bash
# Start only backend services
docker-compose up -d postgres redis backend

# Frontend deploys to Vercel with:
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

### Option 2: All Services on Docker with Nginx

```yaml
# Add nginx service to docker-compose.yml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf
    - ./ssl:/etc/nginx/ssl
```

### Option 3: Kubernetes

Convert docker-compose to Kubernetes manifests:

```bash
kompose convert
```

## 🐛 Troubleshooting

### Backend won't start

```bash
# Check logs
docker-compose logs backend

# Common issues:
# - Database not ready: Wait for postgres health check
# - Missing dependencies: Rebuild image
docker-compose build --no-cache backend
```

### Database connection errors

```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check connection
docker-compose exec backend python -c "import psycopg2; print('OK')"

# Reset database (⚠️ deletes data)
docker-compose down -v
docker-compose up -d
```

### Redis connection errors

```bash
# Test Redis
docker-compose exec redis redis-cli -a your_password ping

# Should return: PONG
```

### Port conflicts

```bash
# If ports are already in use, change in .env:
POSTGRES_PORT=5433
REDIS_PORT=6380
BACKEND_PORT=8001
FRONTEND_PORT=3001
```

## 📈 Monitoring

### Health Checks

All services include health checks:

```bash
# View service health
docker-compose ps

# Services should show (healthy) status
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Resource Usage

```bash
# Container stats
docker stats

# Specific service
docker stats trademaster-backend
```

## 🔄 Updates

### Update Backend

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose build backend
docker-compose up -d backend
```

### Update Frontend

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose build frontend
docker-compose up -d frontend
```

### Update Database Schema

```bash
# If using Alembic migrations
docker-compose exec backend alembic upgrade head

# Manual SQL update
docker-compose exec -T postgres psql -U trademaster -d trademaster < update.sql
```

## 📞 Support

For issues and questions:

- GitHub Issues: [Your repo URL]
- Documentation: [Your docs URL]
- Email: support@trademaster.pro

## 📄 License

[Your License]

---

**Made with ❤️ for TradeMaster Pro**
