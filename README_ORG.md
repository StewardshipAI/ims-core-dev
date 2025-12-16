# 🤖 IMS Core - Intelligent Model Selector

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-0.1.0-green.svg)](#releases)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-Alpha-yellow.svg)](#status)

**Production-grade REST API for managing and selecting AI models based on capability, cost, and context requirements.**

---

## ✨ Features

- **🔗 REST API**: 6 endpoints for model management (register, retrieve, filter, update, delete)
- **🗄️ PostgreSQL**: Connection pooling (2-10 connections) for reliability
- **⚡ Redis Caching**: 5-minute model cache, 1-minute filter cache
- **🔐 Security**: API key authentication, rate limiting, CORS protection
- **📊 Health Monitoring**: Real-time health checks with pool statistics
- **🐳 Docker**: Production-ready containerization (dev & prod configs)
- **📚 Documentation**: Swagger UI + ReDoc auto-generated API docs
- **🧪 Tested**: All 6 endpoints verified with real test data

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Or: PostgreSQL 14+, Redis 7+, Python 3.12+

### Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/StewardshipSolutions/ims-core.git
cd ims-core

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Wait 30 seconds, then verify
curl http://localhost:8000/health

# Load test data
docker-compose run --rm api ./docker.sh populate

# View API documentation
# Open: http://localhost:8000/docs
```

### Manual Setup

```bash
# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL
createdb ims_db
psql ims_db < schemas/model_registry.sql

# Start Redis
redis-server

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run API
uvicorn src.api.model_registry_api:app --reload
```

---

## 📖 API Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| `GET` | `/health` | ❌ | System health check |
| `POST` | `/api/v1/models/register` | ✅ | Register new model |
| `GET` | `/api/v1/models/{model_id}` | ❌ | Get model details |
| `GET` | `/api/v1/models/filter` | ❌ | Search/filter models |
| `PATCH` | `/api/v1/models/{model_id}` | ✅ | Update model |
| `DELETE` | `/api/v1/models/{model_id}` | ✅ | Deactivate model |

### Example Usage

```bash
# Register a model
curl -X POST http://localhost:8000/api/v1/models/register \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR_API_KEY" \
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

# Filter models by capability tier
curl "http://localhost:8000/api/v1/models/filter?capability_tier=Tier_1"

# Get specific model
curl "http://localhost:8000/api/v1/models/gpt-4-turbo"
```

See [DOCKER_README.md](DOCKER_README.md) for complete documentation.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│          FastAPI REST API               │
│    (Port 8000, Swagger UI at /docs)     │
└──────────────┬──────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
    ┌───▼────┐   ┌──▼─────┐
    │PostgreSQL   Redis   │
    │(Database) (Cache)   │
    └──────────────────────┘
```

### Components
- **API Layer**: FastAPI with async/await
- **Data Layer**: PostgreSQL with connection pooling
- **Cache Layer**: Redis with TTL policies
- **Security**: API key auth, rate limiting, CORS
- **Deployment**: Docker Compose (dev & prod)

---

## 📊 Model Schema

```json
{
  "model_id": "gpt-4-turbo",
  "vendor_id": "OpenAI",
  "capability_tier": "Tier_1",
  "context_window": 128000,
  "cost_in_per_mil": 10.0,
  "cost_out_per_mil": 30.0,
  "function_call_support": true,
  "is_active": true
}
```

### Capability Tiers
- **Tier_1**: Fast, small models (great for simple tasks)
- **Tier_2**: Balanced models (good for most use cases)
- **Tier_3**: Advanced reasoning models (best for complex tasks)

---

## 🔐 Security

- ✅ API key authentication (32+ character minimum)
- ✅ Rate limiting (10/min admin, 50/min filter, 100/min read)
- ✅ CORS restricted to configured origins
- ✅ Request size limits (1MB max)
- ✅ Timing-attack resistant key comparison
- ✅ Connection pooling (prevents resource exhaustion)

See [DOCKER_README.md](DOCKER_README.md#security) for security details.

---

## 📦 Deployment

### Development
```bash
./docker.sh start          # Start containers
./docker.sh logs api       # View logs
./docker.sh stop           # Stop containers
```

### Production
```bash
docker-compose -f docker-compose.prod.yml up -d
# Configure with:
# - Strong ADMIN_API_KEY
# - Strong DB_PASSWORD
# - Reverse proxy (nginx) with SSL/TLS
# - Monitoring setup
```

See [DOCKER_CHECKLIST.md](DOCKER_CHECKLIST.md) for deployment checklist.

---

## 📋 Project Status

| Phase | Status | Target | Notes |
|-------|--------|--------|-------|
| **Phase 1: Core** | 🟢 In Progress | Jan 29 | Model Registry ✅, Telemetry Bus 🔄 |
| **Phase 2: Intelligence** | 🔵 Planned | Feb 2 | Pattern Completion, Recommendations |
| **Phase 3: Production** | 🔵 Planned | Feb 21 | Monitoring, Scaling, Security |
| **Phase 4: Launch** | 🔵 Planned | Feb 7 | Public API, Documentation |

### Completed ✅
- Epic 1.1: Model Registry Schema
- Epic 1.2: REST API (all endpoints)
- Docker setup (dev & production)

### In Progress 🔄
- Epic 1.3: Telemetry Bus (RabbitMQ)

### Planned 📋
- Epic 1.4: Pattern Completion & Recommendation
- Epic 2.x: Advanced features
- Epic 3.x: Production hardening
- Epic 4.x: Public launch

---

## 🧪 Testing

```bash
# Health check
curl http://localhost:8000/health

# Run pytest suite
docker-compose run --rm api pytest tests/ -v

# Load test data
docker-compose run --rm api ./docker.sh populate
```

---

## 📚 Documentation

- **[DOCKER_README.md](DOCKER_README.md)** - Complete Docker setup guide
- **[DOCKER_CHECKLIST.md](DOCKER_CHECKLIST.md)** - Deployment checklist
- **[Swagger UI](http://localhost:8000/docs)** - Interactive API documentation
- **[ReDoc](http://localhost:8000/redoc)** - Beautiful API docs

---

## 🤝 Contributing

This is an organization repository. For development and feature work:

1. Use the [development repository](https://github.com/StewardshipAI/ims-core-dev)
2. Test features thoroughly
3. Submit pull requests with test coverage
4. After review, features are merged here

---

## 📄 License

MIT License - See LICENSE file for details

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/StewardshipSolutions/ims-core/issues)
- **Documentation**: [DOCKER_README.md](DOCKER_README.md)
- **Roadmap**: [Project Board](https://github.com/StewardshipSolutions/ims-core/projects)

---

## 🎯 Next Phase: Telemetry Bus

Coming soon: Event streaming with RabbitMQ for real-time metrics and monitoring.

See [ROADMAP.md](ROADMAP.md) for full development roadmap.

---

**Built with ❤️ by StewardshipSolutions**
