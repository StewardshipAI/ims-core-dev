# 🧠 IMS Core Dev. - Intelligent Model Switching

**Project:** Intelligent Model Selector (IMS) Core Service  
**Status:** EPIC-2 (Agent Control Flow) Complete  
**Next Epic:** EPIC-3 (Action Gateway Integration)

---

## 🚀 Overview

This repository contains the core backend services for the Intelligent Model Selector (IMS) ecosystem. It includes the Model Registry API, the Pattern Completion & Recommendation (PCR) service, and the new EPIC-2 Agent Control Flow (ACF) for policy-driven request management.

---

## ✨ Features

- **Model Registry API**: Manage and query model profiles and capabilities.
- **PCR Service**: Get model recommendations based on constraints.
- **Agent Control Flow (EPIC-2)**: A state machine to enforce policy gates and orchestrate the request lifecycle.
- **Telemetry Bus**: Emits events for system monitoring and analytics.
- **Dockerized Environment**: Fully containerized for consistent development and deployment.

---

## 🏁 Getting Started

### Prerequisites
- Docker and Docker Compose
- Python 3.12+
- An environment file (`.env`) based on `.env.example`.

### Running the Application

1.  **Build and start the services:**
    ```bash
    docker-compose up -d --build
    ```

2.  **Check the health of the API:**
    ```bash
    curl http://localhost:8000/health
    ```

3.  **View the logs:**
    ```bash
    docker-compose logs -f api
    ```

---

## 🏛️ Project Structure

```
IMS Core v1.0.0 (Target: Week 10)
├── Model Registry (Epic 1.1) ✅
├── Metrics Store (Epic 1.2) - EMA calculations ✅
├── Telemetry Bus (Epic 1.3) - RabbitMQ event system  ✅
├── Policy & Constraint Repository (Epic 1.4) - Business rules ✅
├── Agent Control Flow (Epic 2.1) - State machine orchestration ✅
├── Scoring Algorithm (Epic 2.2) - S_model optimization ✅
├── Policy Verifier Engine (Epic 2.3) - Constraint checking ✅
├── Behavioral Constraint Processor (Epic 2.4) - Guardrails ✅
└── Action Gateway (Epic 3.1) - Vendor API adapters (In Progress)
```

---

## 🤝 Contributors & Auditing

This project is developed and tested with the assistance of advanced AI models.

- **Auditing & Initial Implementation**: The initial code and documentation for EPIC-2 were audited and implemented with assistance from **Claude 4.5 Sonnet, Gemini 2.5 Pro, and Chat-GPT 5**.
- **Testing & Refinement**: The code was tested, debugged, and refined by **gemini-2.5-pro (Google)**, which included fixing syntax errors, resolving dependencies, and writing unit tests.

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

### Running Tests

Tests are run inside the `api` container to ensure the environment is consistent.

1.  **Run all tests:**
    ```bash
    docker-compose exec api pytest
    ```

2.  **Run a specific test file:**
    ```bash
    docker-compose exec api pytest tests/test_acf.py
    ```

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
- [x] Epic 1.4: PCR (Week 4) - ***FINISHED***
- [x] Epic 2.1: ACF State Machine (Week 5-6) - ***FINISHED***
- [x] Epic 2.2: S_model Algorithm (Week 6) - ***FINISHED***
- [x] Epic 2.3: Policy Verifier Engine - ***FINISHED***
- [x] Epic 2.4: Behavioral Constraint Processor - ***FINISHED***
- [ ] Epic 3: Action Gateway (Week 7) - **IN PROGRESS**
- [ ] Epic 4-7: Governance, Observability, Testing, Deployment (Week 8-10)

**Target Launch**: Week 10 (Public v1.0.0)
