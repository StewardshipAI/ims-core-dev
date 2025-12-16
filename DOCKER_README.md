# 🐳 IMS Core - Docker Setup Guide

## Quick Start

### Prerequisites
- **Docker Desktop** (includes Docker & Docker Compose)
  - Download: https://www.docker.com/products/docker-desktop
  - For WSL2: Install Docker Desktop for Windows
- **.env file** (copy from `.env.example`)

### 1. Setup Environment

```bash
cd /mnt/c/Users/natha/OneDrive/Documents/Claude-BuildsDocs/ims-core

# Copy environment file
cp .env.example .env

# Verify .env has ADMIN_API_KEY
cat .env | grep ADMIN_API_KEY
```

### 2. Start All Services

**Linux/macOS/WSL2:**
```bash
chmod +x docker.sh
./docker.sh start
```

**Windows (PowerShell):**
```powershell
docker-compose up -d
# Or use the helper:
# .\docker.cmd start
```

**What gets started:**
- 🐘 **PostgreSQL 14** on `localhost:5432`
- 🔴 **Redis 7** on `localhost:6379`
- 🔗 **FastAPI** on `http://localhost:8000`

### 3. Check Status

```bash
docker-compose ps
```

Expected output:
```
NAME              IMAGE                PORTS
ims-postgres      postgres:14-alpine   0.0.0.0:5432->5432/tcp
ims-redis         redis:7-alpine       0.0.0.0:6379->6379/tcp
ims-api           ims-core:latest      0.0.0.0:8000->8000/tcp
```

### 4. Verify API is Running

```bash
curl http://localhost:8000/health

# Expected output:
# {"status":"healthy","database":"healthy","cache":"not_configured",...}
```

### 5. Load Test Data

```bash
# Linux/macOS/WSL2:
./docker.sh populate

# Windows:
docker-compose run --rm api python -m scripts.load_test_data
```

Or manually with curl:
```bash
ADMIN_KEY=$(grep ADMIN_API_KEY .env | cut -d= -f2)

curl -X POST http://localhost:8000/api/v1/models/register \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -d '{
    "model_id": "gpt-4-turbo",
    "vendor_id": "OpenAI",
    "capability_tier": "Tier_1",
    "context_window": 128000,
    "cost_in_per_mil": 10.0,
    "cost_out_per_mil": 30.0,
    "function_call_support": true,
    "is_active": true
  }'
```

---

## Common Commands

### View Logs
```bash
# API logs
./docker.sh logs api

# PostgreSQL logs
./docker.sh logs postgres

# Redis logs
./docker.sh logs redis

# All logs
docker-compose logs -f
```

### Stop Containers
```bash
./docker.sh stop
# or
docker-compose down
```

### Clean Everything (WARNING: Deletes all data!)
```bash
./docker.sh clean
# or
docker-compose down -v
```

### Run Tests
```bash
./docker.sh test
# or
docker-compose run --rm api pytest tests/ -v
```

### Access Databases

**PostgreSQL:**
```bash
docker-compose exec postgres psql -U postgres -d ims_db
```

**Redis:**
```bash
docker-compose exec redis redis-cli
```

---

## API Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/health` | ❌ | Health check |
| POST | `/api/v1/models/register` | ✅ | Register model |
| GET | `/api/v1/models/{model_id}` | ❌ | Get model |
| GET | `/api/v1/models/filter` | ❌ | Filter models |
| PATCH | `/api/v1/models/{model_id}` | ✅ | Update model |
| DELETE | `/api/v1/models/{model_id}` | ✅ | Deactivate model |

### Query Filter Examples

```bash
# Filter by vendor
curl "http://localhost:8000/api/v1/models/filter?vendor_id=OpenAI"

# Filter by minimum context window
curl "http://localhost:8000/api/v1/models/filter?min_context=100000"

# Filter by capability tier
curl "http://localhost:8000/api/v1/models/filter?capability_tier=Tier_1"

# Filter by tier AND vendor
curl "http://localhost:8000/api/v1/models/filter?capability_tier=Tier_1&vendor_id=OpenAI"

# Include function call support
curl "http://localhost:8000/api/v1/models/filter?function_call_support=true"
```

---

## Documentation

- **Swagger UI (Interactive):** http://localhost:8000/docs
- **ReDoc (Beautiful Docs):** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

---

## Environment Variables

Key variables in `.env`:

```env
# Database
DB_CONNECTION_STRING=postgresql://postgres:postgres@postgres:5432/ims_db
TEST_DB_CONNECTION_STRING=postgresql://postgres:postgres@postgres:5432/ims_test_db

# Redis
REDIS_URL=redis://redis:6379/0

# Security
ADMIN_API_KEY=<your-32-char-key>  # ⚠️ KEEP SECRET!

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Logging
LOG_LEVEL=INFO
```

### 🔒 IMPORTANT: Protect Your API Key!

**Never commit `.env` to git!**

```bash
# Check .gitignore includes .env
cat .gitignore | grep ".env"

# Should output:
# .env
# .env.local
# .env.*.local
```

---

## Troubleshooting

### Port Already in Use
```bash
# Check what's using the port
lsof -i :8000

# Use a different port in docker-compose.yml:
# ports:
#   - "8001:8000"  # Changed from 8000 to 8001
```

### Database Connection Error
```bash
# Wait for PostgreSQL to be ready
docker-compose logs postgres

# Restart just the database
docker-compose restart postgres
```

### Redis Connection Issues
```bash
# Test Redis connection
docker-compose exec redis redis-cli ping
# Should return: PONG
```

### API Won't Start
```bash
# Check API logs
./docker.sh logs api

# Rebuild the image
docker-compose build --no-cache

# Restart everything
docker-compose restart
```

### Permission Denied on docker.sh
```bash
chmod +x docker.sh
```

---

## Development Workflow

### 1. Start Everything
```bash
./docker.sh start
```

### 2. Code in Your Editor
The code is **mounted as a volume**, so changes appear live:
```yaml
volumes:
  - .:/app  # Local code syncs to container
```

### 3. Watch Logs
```bash
./docker.sh logs api
```

### 4. Test Changes
```bash
# API auto-reloads on file changes (--reload flag)
# Just save your file and test!

curl http://localhost:8000/health
```

### 5. Run Tests
```bash
./docker.sh test
```

### 6. Stop When Done
```bash
./docker.sh stop
```

---

## Production Deployment

For AWS/GCP/DigitalOcean:

```bash
# Build production image
docker build -t ims-core:prod .

# Push to registry
docker tag ims-core:prod <your-registry>/ims-core:prod
docker push <your-registry>/ims-core:prod

# Deploy with compose (update image name in compose file)
docker-compose -f docker-compose.prod.yml up -d
```

---

## File Structure

```
ims-core/
├── docker-compose.yml      # Container orchestration
├── Dockerfile              # API container image
├── docker.sh              # Helper script (Linux/Mac)
├── docker.cmd             # Helper script (Windows)
├── .env                   # Environment variables (SECRET!)
├── .env.example           # Template for .env
├── .dockerignore          # Files to exclude from build
├── src/
│   └── api/
│       └── model_registry_api.py
├── schemas/
│   └── *.sql              # Database migrations
└── requirements.txt       # Python dependencies
```

---

## Next Steps

1. ✅ Run `./docker.sh start`
2. ✅ Visit http://localhost:8000/docs
3. ✅ Register test models with `./docker.sh populate`
4. ✅ Try filter endpoint
5. ✅ Check logs with `./docker.sh logs api`

**Ready? Let's go!** 🚀
