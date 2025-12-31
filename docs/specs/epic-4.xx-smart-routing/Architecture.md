# Architecture Overview

## Execution Flow

Agent / CLI / API
  → Agent Control Flow (ACF)
    → Policy Enforcement Engine (Epic 4)
      → Smart Model Router (Epic 4.XX)
        → Vendor Adapter
          → External Model API

## Design Constraints

- Router MUST NOT override policy decisions
- Policy evaluation MUST be logged
- Routing MUST be deterministic given the same inputs
- Escalation paths MUST be explicit

## Failure Handling

- Policy rejection → hard fail
- Model failure → fallback if allowed
- Exhausted candidates → escalation or fail
