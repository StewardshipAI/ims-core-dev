# 🤖 IMS Core - Intelligent Model Selector

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.0.0--alpha-green.svg)](#releases)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-Midpoint_Complete-success.svg)](#status)

**The central nervous system for AI model orchestration. IMS intelligently routes prompts to the most cost-effective and capable model for the task.**

---

## 🚀 Overview

The **Intelligent Model Selector (IMS)** is a production-grade service that decouples applications from specific AI providers. Instead of hardcoding `gpt-4` or `claude-3`, applications query IMS for a recommendation based on:
- **Cost constraints** (e.g., "max $0.01 per query")
- **Capability requirements** (e.g., "needs complex reasoning")
- **Context window** (e.g., "needs 100k+ tokens")
- **Policy rules** (e.g., "no data sent to Vendor X")

IMS handles the complexity of model selection, usage tracking, and error recovery, providing a unified "Action Gateway" for your AI ecosystem.

---

## ✨ Key Features

### 🧠 Intelligent Routing (PCR)
- **Pattern Completion & Recommendation (PCR)** engine.
- Dynamically selects models based on strategy (`cost` vs `performance`).
- Filters by context window, capabilities, and active status.

### 🛡️ Robust Registry
- **Centralized Model Management**: Register/update models via API.
- **Dynamic Updates**: Change model status/costs without deploying code.
- **Seeded Database**: Comes pre-loaded with 24+ models (Gemini, OpenAI, Anthropic, Llama).

### ⚡ Agent Control Flow (ACF)
- **State Machine**: Enforces policy gates and request lifecycles.
- **Error Recovery**: Automatic fallback logic (e.g., if Primary fails, try Fallback).
- **Usage Tracking**: Real-time telemetry for tokens, latency, and cost.

### 🔌 Integration Ready
- **Telemetry Bus**: RabbitMQ-based event streaming for observability.
- **Health Dashboard**: Real-time CLI dashboard for system monitoring.
- **CLI Tools**: Drop-in wrapper for `gemini-cli` (and others).

---

## 🏗️ Architecture

```mermaid
graph TD
    Client[Client App / CLI] -->|1. Request Recommendation| API[IMS Core API]
    API -->|2. Query| Registry[Model Registry DB]
    API -->|3. Optimize| PCR[Recommendation Engine]
    
    Client -->|4. Execute| Provider[AI Provider (Gemini/OpenAI)]
    
    Client -.->|5. Log Usage| API
    API -->|6. Publish Event| Bus[Telemetry Bus (RabbitMQ)]
    Bus -->|7. Process| Subscriber[Metrics Service]
    Subscriber -->|8. Store| Redis[Metrics Cache]
```

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/StewardshipAI/ims-core-dev.git
cd ims-core-dev

# Run the automated setup (deploys DB, Redis, RabbitMQ, API)
chmod +x scripts/setup-midpoint.sh
./scripts/setup-midpoint.sh
```

### 2. Verify Deployment

```bash
# Check system health and metrics
./scripts/ims-status.sh
```

### 3. Usage Example (CLI)

Use the provided wrapper to intelligently route your prompts:

```bash
# Ask IMS to select the best model for a query
./scripts/ims-gemini.sh "Explain quantum computing in simple terms"
```

### 4. Usage Example (API)

```bash
# Get a model recommendation
curl -X POST http://localhost:8000/api/v1/recommend \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY" \
  -d '{ 
    "strategy": "cost",
    "min_context_window": 10000,
    "min_capability_tier": "Tier_1"
  }'
```

---

## 📊 Project Status

| Milestone | Component | Status | Description |
|-----------|-----------|--------|-------------|
| **Epic 1** | Model Registry | ✅ Complete | Database, API, Caching |
| **Epic 1** | Telemetry Bus | ✅ Complete | RabbitMQ, Event Publishers |
| **Epic 1** | Metrics Store | ✅ Complete | Redis-backed usage stats |
| **Epic 2** | PCR Engine | ✅ Complete | Recommendation logic |
| **Epic 2** | ACF Core | ✅ Complete | State machine, Error recovery |
| **Epic 2** | Integration | ✅ Complete | CLI wrappers, Health dashboard |
| **Epic 3** | Action Gateway | 🔄 Pending | Unified API Proxy |

---

## 📚 Documentation

Detailed documentation is available in the `docs/` directory:

- **[Implementation Guide](docs/MIDPOINT-GUIDE.md)**: Comprehensive guide to the architecture and components.
- **[API Documentation](http://localhost:8000/docs)**: Interactive Swagger UI (when running).
- **[Deployment Guide](DEPLOYMENT-PACKAGE.md)**: Production deployment instructions.

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/StewardshipAI/ims-core-dev/issues)
- **Organization**: StewardshipAI

---

**Built with ❤️ by StewardshipAI**