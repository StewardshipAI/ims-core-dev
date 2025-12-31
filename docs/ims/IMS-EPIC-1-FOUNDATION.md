# 🏗️ EPIC 1: Foundation

The **Foundation Layer** provides the core infrastructure for the IMS platform, including data persistence, caching, and the primary communication bus.

## 🎯 Overview

Epic 1 established the "backbone" of IMS, ensuring high availability, performance, and scalability.

### Key Components

1.  **Model Registry**:
    *   PostgreSQL-backed database for model metadata.
    *   Tracks vendor info, capabilities, context windows, and pricing.
2.  **REST API**:
    *   FastAPI-based interface for managing models.
    *   Endpoints for registration, filtering, and updates.
3.  **Redis Cache Layer**:
    *   Connection pooling for low-latency lookups.
    *   Caching for model profiles and filter results.
4.  **Telemetry Bus**:
    *   RabbitMQ-based asynchronous event system.
    *   Decouples primary execution from side effects like logging and metrics.

## 🗄️ Data Schema

The foundation uses a relational schema to ensure data integrity:
*   `models`: Main registry table.
*   `capability_tier`: Enum for model power levels.

## 🚀 Deployment

The foundation is fully containerized using Docker, allowing for consistent environments across development and production.

---

*See the root [README.md](../../README.md) for quick start instructions.*
