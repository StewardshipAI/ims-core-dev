# 🧠 IMS Core Dev. - Intelligent Model Switching

**Status**: 🚧 Development Version (v0.1.0)

Enterprise-grade AI orchestration platform for intelligent model switching, cost optimization, and automatic failover across multiple LLM vendors.

---

## 📊 Project Status

### Epic 1.1: Model Registry (100% Complete) ✅
- ✅ PostgreSQL schema with optimized indexes
- ✅ Data layer with connection pooling
- ✅ Secure REST API (CORS, authentication)
- ✅ Comprehensive test suite
- ✅ Environment setup for testing
- ✅ Metrics Store (EMA calculations)
- ✅ Telemetry Bus (RabbitMQ) 
- ✅ Policy & Constraint Repository
-    Agent Control Flow (State Machine) **IN PROGRESS**
     
### Epic 3-4: Not Started ❌ 
- Action Gateway (Vendor adapters)
- Production deployment

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Git

### Installation

```bash
# Clone repository
git clone https://github.com/StewardshipAI/ims-core-dev.git
cd ims-core-dev

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your actual configuration

# Set up database
psql -U postgres
CREATE DATABASE ims_db;
CREATE DATABASE ims_test_db;
\q

# Run migrations
psql -U postgres -d ims_db -f schemas/model_registry.sql

# Seed initial data
psql -U postgres -d ims_db -f seed/01_seed_models.sql

# Or use Python script:
python scripts/populate_model_registry.py
```

### Running the API

```bash
# Development server (with auto-reload)
uvicorn src.api.model_registry_api:app --reload --port 8000

# Production server (multiple workers)
uvicorn src.api.model_registry_api:app --host 0.0.0.0 --port 8000 --workers 4
```

### API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=html

# Run specific test file
pytest tests/test_model_registry.py -v

# Run with markers
pytest tests/ -v -m "not slow"
```

---

## 🏗️ Architecture

### Components (Current)

```
IMS Core v0.1.0
└── Epic 1.1: Model Registry ✅
    ├── PostgreSQL Database (models table) ✅
    ├── Data Layer (ModelRegistry class) ✅
    ├── REST API (FastAPI) ✅
    └── Redis Cache (optional) ✅
```

### Components (Planned)

```
IMS Core v1.0.0 (Target: Week 10)
├── Model Registry (Epic 1.1) ✅
├── Metrics Store (Epic 1.2) - EMA calculations ✅
├── Telemetry Bus (Epic 1.3) - RabbitMQ event system  ✅
├── Policy & Constraint Repository (Epic 1.4) - Business rules ✅
├── Agent Control Flow (Epic 2.1) - State machine orchestration (In Progress)
├── Scoring Algorithm (Epic 2.2) - S_model optimization
├── Policy Verifier Engine (Epic 2.3) - Constraint checking
├── Behavioral Constraint Processor (Epic 2.4) - Guardrails
└── Action Gateway (Epic 3.1) - Vendor API adapters
```

---

## 📚 Documentation

- [Architecture Overview](docs/architecture.md) _(coming soon)_
- [API Reference](http://localhost:8000/docs) _(when running)_
- [Development Guide](docs/development.md) _(coming soon)_
- [Deployment Guide](docs/deployment.md) _(coming soon)_

---

## 🔒 Security

### Implemented Fixes (v0.1.0)

This version includes **8 critical security fixes**:

1. ✅ **Connection Pooling** - Prevents resource exhaustion
2. ✅ **CORS Whitelist** - Restricts cross-origin requests
3. ✅ **Strong API Keys** - Enforces 32+ character keys
4. ✅ **Request Size Limits** - Prevents DoS attacks (1MB max)
5. ✅ **Cache Race Conditions** - Fixed invalidation timing
6. ✅ **Transaction Isolation** - SERIALIZABLE for consistency
7. ✅ **SQL Injection Prevention** - Parameterized queries
8. ✅ **Timing Attack Resistance** - Constant-time auth comparison

### Security Checklist

- [ ] ⚠️ **NEVER commit `.env` file** (contains secrets)
- [ ] ⚠️ **Generate strong API keys**: `openssl rand -hex 32`
- [ ] ⚠️ **Restrict CORS origins** (no `*` wildcards in production)
- [ ] ⚠️ **Use HTTPS in production** (TLS/SSL certificates)
- [ ] ⚠️ **Rotate API keys regularly** (every 90 days)
- [ ] ⚠️ **Run security scans**: `bandit -r src/`

---

## 🛠️ Development

### Code Style

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint
flake8 src/ tests/

# Type check
mypy src/
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## 📈 Performance

### Benchmarks (Target)

- **Model Lookup**: <10ms (P95) with Redis cache
- **Filter Query**: <50ms (P95) without cache
- **API Latency**: <100ms (P95) for model selection
- **Throughput**: >1000 requests/second (with 4 workers)

### Load Testing

```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load_test.py --host=http://localhost:8000
```

---

## 🐛 Known Issues

1. ⚠️ **Tests not yet run** - (Testing in Progress)
2. ⚠️ **No Docker setup** - Coming in v0.2.0
3. ⚠️ **No CI/CD pipeline** - Coming in v0.2.0

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file

---

## 👥 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Development Status**: Private alpha (not accepting external contributions yet)

---

## 📧 Contact

- **Organization**: Stewardship Solutions
- **Website**: https://stewardshipsolutions.github.io
- **Issues**: https://github.com/StewardshipSolutions/ims-core/issues

---

## 🗺️ Roadmap

- [x] Epic 1.1: Model Registry (Week 1-2) - ***FINISHED***
- [x] Epic 1.2: Metrics Store (Week 2-3) - ***FINISHED***
- [x] Epic 1.3: Telemetry Bus (Week 3-4) - ***FINISHED***
- [X] Epic 1.4: PCR (Week 4) - ***FINISHED***
- [ ] Epic 2.1: ACF State Machine (Week 5-6) - **IN PROGRESS**
- [ ] Epic 2.2: S_model Algorithm (Week 6)
- [ ] Epic 3: Action Gateway (Week 7)
- [ ] Epic 4-7: Governance, Observability, Testing, Deployment (Week 8-10)

**Target Launch**: Week 10 (Public v1.0.0)

---

**Built with ❤️ by Stewardship Solutions**
