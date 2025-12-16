# ✅ Docker Deployment Checklist

## Pre-Flight Checklist (Before First Run)

- [ ] Docker Desktop installed (`docker --version` returns version)
- [ ] Docker Compose installed (`docker-compose --version`)
- [ ] In correct directory: `/mnt/c/Users/natha/OneDrive/Documents/Claude-BuildsDocs/ims-core`
- [ ] `.env` file exists with `ADMIN_API_KEY` filled in
- [ ] `.env` is in `.gitignore` (won't be committed)
- [ ] No service running on ports 8000, 5432, 6379

## First Launch (Day 1)

```bash
# 1. Navigate to project
cd /mnt/c/Users/natha/OneDrive/Documents/Claude-BuildsDocs/ims-core

# 2. Start containers
./docker.sh start

# 3. Wait for services (30 seconds)
sleep 30

# 4. Verify health
curl http://localhost:8000/health

# 5. Load test data
./docker.sh populate

# 6. Test API
curl "http://localhost:8000/api/v1/models/filter?vendor_id=OpenAI"
```

## Daily Usage

```bash
# Morning: Start everything
./docker.sh start

# Evening: Stop everything
./docker.sh stop

# View logs while developing
./docker.sh logs api

# Run tests before committing
./docker.sh test
```

## Troubleshooting Commands

```bash
# Check container status
docker-compose ps

# View detailed logs
docker-compose logs -f api

# Restart a service
docker-compose restart api

# Connect to database
docker-compose exec postgres psql -U postgres -d ims_db

# Connect to Redis
docker-compose exec redis redis-cli

# Force rebuild
docker-compose build --no-cache

# Full reset (WARNING: deletes all data!)
./docker.sh clean
```

## Production Deployment

### Pre-Deployment

- [ ] All code committed and tested
- [ ] `.env.prod` created with production values
- [ ] Strong ADMIN_API_KEY (min 32 chars, random)
- [ ] Strong DB_PASSWORD (min 32 chars, random)
- [ ] ALLOWED_ORIGINS set to your domain only
- [ ] LOG_LEVEL set to "WARNING"
- [ ] SSL/TLS configured (nginx reverse proxy)
- [ ] Backups configured for PostgreSQL volume

### Deploy to Production

```bash
# Build production image
docker build -t ims-core:prod .

# Push to registry (e.g., Docker Hub, AWS ECR)
docker tag ims-core:prod <registry>/ims-core:prod
docker push <registry>/ims-core:prod

# Deploy
docker-compose -f docker-compose.prod.yml up -d

# Verify
curl https://your-domain.com/health
docker-compose logs -f api
```

## Files Created for Docker

```
✅ docker-compose.yml          # Development setup
✅ docker-compose.prod.yml     # Production setup
✅ Dockerfile                  # Container image definition
✅ .dockerignore               # Files to exclude from build
✅ docker.sh                   # Helper script (Linux/Mac)
✅ docker.cmd                  # Helper script (Windows)
✅ DOCKER_README.md            # Full documentation
✅ requirements.txt            # Updated with gunicorn
```

## What Gets Containerized

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| PostgreSQL | `postgres:14-alpine` | 5432 | Database |
| Redis | `redis:7-alpine` | 6379 | Cache |
| FastAPI | `python:3.12-slim` | 8000 | API |

## Environment Variables Set by docker-compose.yml

```
DB_CONNECTION_STRING=postgresql://postgres:postgres@postgres:5432/ims_db
REDIS_URL=redis://redis:6379/0
ADMIN_API_KEY=<from .env>
ALLOWED_ORIGINS=<from .env>
```

## Volumes (Data Persistence)

- `postgres_data` → PostgreSQL database files
- `redis_data` → Redis snapshots
- `.` → Your code (mounted for development)

## Networks

- `ims-network` → Private Docker network for inter-container communication

## Health Checks

All services have health checks configured:
- PostgreSQL: `pg_isready` every 10s
- Redis: `PING` command every 10s
- API: HTTP GET `/health` every 30s

## Security Features

✅ Non-root user in container (appuser:1000)
✅ No new privileges (cap_drop: ALL)
✅ Readonly root filesystem (production)
✅ Request size limits (1MB)
✅ CORS restricted to specific origins
✅ API key validation (timing-attack resistant)
✅ .env excluded from git

## Monitoring & Logs

```bash
# Real-time logs
./docker.sh logs api

# Logs from all services
docker-compose logs -f

# Specific service
./docker.sh logs postgres

# With timestamps
docker-compose logs -f --timestamps

# Last N lines
docker-compose logs --tail=100 api
```

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| Port 8000 in use | `lsof -i :8000` then `kill -9 <PID>` |
| DB won't connect | `docker-compose restart postgres` |
| Redis won't start | `docker-compose logs redis` |
| Old image running | `docker-compose build --no-cache` |
| Permission denied | `chmod +x docker.sh` |

## Next: Commit Docker Files

```bash
git add docker-compose.yml Dockerfile .dockerignore docker.sh DOCKER_README.md
git commit -m "feat: Add Docker containerization for dev/prod"
git push origin main
```

## Success Criteria

✅ `./docker.sh start` works without errors
✅ All containers pass health checks
✅ API responds at http://localhost:8000/health
✅ Swagger UI accessible at http://localhost:8000/docs
✅ Can register models and query them
✅ `./docker.sh stop` cleanly shuts down

**You're ready to go!** 🚀
