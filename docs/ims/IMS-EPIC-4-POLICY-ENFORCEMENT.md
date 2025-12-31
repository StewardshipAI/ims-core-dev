# 🛡️ EPIC 4: Policy Enforcement Engine

The **Policy Enforcement Engine** provides governance and cost control across the IMS platform. It ensures that every request complies with business rules before it reaches an AI vendor.

## 🎯 Overview

Epic 4 introduced the **Policy Verifier Engine (PVE)**, which acts as a technical gatekeeper. Unlike content filters, the PVE focuses on technical and financial intelligence.

### Key Features

1.  **No-Censorship Governance**:
    *   IMS intentionally excludes keyword and sentiment policing.
    *   Governance is limited to technical constraints (length, latency, vendor approval).
2.  **Smart Model Routing (SMR)**:
    *   If a request violates a cost policy (e.g., budget exceeded), the engine automatically searches for a cheaper alternative in the *same* `CapabilityTier`.
    *   This preserves the quality of work while staying within budget.
3.  **Permission-Based Overrides**:
    *   Users can include `"bypass_policies": true` in their execution requests.
    *   This allows a human-in-the-loop to approve expensive operations that would otherwise be blocked.
4.  **Audit & Compliance**:
    *   Every policy decision is logged to the `policy_violations` and `policy_executions` tables.
    *   A dedicated Compliance API allows for real-time reporting on system usage.

## 🏗️ Architecture

The engine is integrated directly into the `ActionGateway` request lifecycle:
1.  **Pre-Flight**: Evaluates request context against active policies.
2.  **Action Dispatch**:
    *   `BLOCK`: Request is rejected unless bypassed.
    *   `DEGRADE`: Smart Routing attempts to find a cheaper model.
    *   `WARN`: Request proceeds but violation is logged.
3.  **Audit**: Results are published to the Telemetry Bus.

## 🛠️ Implementation Details

*   **Logic Location**: `src/core/policy_verifier.py`
*   **Data Layer**: `src/data/policy_registry.py`
*   **API Layer**: `src/api/compliance_router.py`

---

*For technical specifications, see the root [README.md](../../README.md).*
