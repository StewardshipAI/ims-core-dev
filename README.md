# IMS Core Developer Environment

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
    You should see a response with `"status": "healthy"`.

3.  **View the logs:**
    ```bash
    docker-compose logs -f api
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

## 🏛️ Project Structure

```
ims-core-dev/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
│
├── src/
│   ├── api/         # FastAPI endpoints and routers
│   ├── core/        # Core application logic (PCR, ACF)
│   ├── data/        # Data access layer (ModelRegistry)
│   └── services/    # Background services (e.g., metrics subscriber)
│
└── tests/           # Pytest unit and integration tests
```

---

## 🎯 Next Steps (EPIC-3)

The next major development effort is **EPIC-3: Action Gateway Integration**.

The primary goals are:
1.  **Implement the Action Gateway**: A new service responsible for making the actual calls to external model APIs (e.g., OpenAI, Anthropic).
2.  **Integrate ACF with Action Gateway**: Wire the `model_executor` in the `AgentControlFlow` to the new Action Gateway.
3.  **Secure Credential Management**: Implement a secure way to store and access API keys for the Action Gateway.
4.  **End-to-End Testing**: Create tests that cover the full request lifecycle, from API ingress to model execution and response.

---

## 🤝 Contributors & Auditing

This project is developed and tested with the assistance of advanced AI models.

- **Auditing & Initial Implementation**: The initial code and documentation for EPIC-2 were audited and implemented with assistance from **Claude 4.5 Sonnet, Gemini 2.5 Pro, and Chat-GPT 5**.
- **Testing & Refinement**: The code was tested, debugged, and refined by **gemini-2.5-pro (Google)**, which included fixing syntax errors, resolving dependencies, and writing unit tests.

---

## 📞 Contact

**Repository:** https://github.com/StewardshipAI/ims-core-dev  
**Maintainer:** StewardshipAI
