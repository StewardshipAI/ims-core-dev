# 🧠 EPIC 2: Intelligence Layer

The **Intelligence Layer** is the decision-making core of IMS. It transforms static model data into dynamic, self-healing, and observable agent workflows.

## 🎯 Overview

Epic 2 introduced the logic required to intelligently select models, track their performance, and recover from failures automatically.

### Key Components

1.  **PCR (Pattern Completion & Recommendation)**:
    *   Dynamic model ranking based on strategy (`cost` vs `performance`).
    *   Heuristic-based filtering for context windows and capability tiers.
2.  **ACF State Machine**:
    *   A finite state machine that orchestrates the lifecycle of an AI request.
    *   States: `IDLE` → `ANALYZING` → `SELECTING_MODEL` → `EXECUTING` → `VALIDATING` → `COMPLETED`.
3.  **Usage Tracker**:
    *   Real-time token and cost monitoring.
    *   Emits telemetry events via RabbitMQ.
4.  **Error Recovery**:
    *   Circuit Breaker pattern for failing models.
    *   Automatic fallback to alternative models on 429 (Rate Limit) or 5xx errors.

## 🛠️ Implementation Details

*   **Logic Location**: `src/core/`
    *   `pcr.py`: Recommendation heuristics.
    *   `state_machine.py`: Workflow orchestration.
    *   `usage_tracker.py`: Telemetry and cost calculation.
    *   `error_recovery.py`: Fallback and retry logic.

## 📡 Telemetry Integration

Every execution in the Intelligence Layer emits a `CloudEvent` to the **Telemetry Bus**. This allows the system to build real-time metrics without slowing down the primary API response.

---

*For detailed setup instructions, see the [Midpoint Guide](../MIDPOINT-GUIDE.md).*
