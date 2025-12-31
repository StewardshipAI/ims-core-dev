# ADR-0005: Policy Enforcement Engine Architecture

**Status:** Accepted  
**Date:** 2025-12-31  
**Deciders:** IMS-Apex, StewardshipAI Team  
**Epic:** 4 - Policy Enforcement Engine

---

## Context and Problem Statement

The IMS system needs a way to enforce business rules, cost constraints, vendor restrictions, and behavioral guardrails **before** executing AI requests. Without policy enforcement:

- Users can accidentally exceed budgets
- Prohibited vendors might be used
- Excessively large/expensive requests aren't blocked
- No audit trail for compliance
- No automatic fallback mechanisms

We need a **Policy Enforcement Engine (PVE)** that:
1. Evaluates requests against defined policies
2. Blocks, warns, or logs violations
3. Provides automatic fallback to cheaper alternatives
4. Maintains complete audit trail
5. Integrates seamlessly with Action Gateway

---

## Decision Drivers

* **Cost Control**: Must prevent budget overruns
* **Compliance**: Must provide audit trail for governance
* **Performance**: Must not add significant latency
* **Flexibility**: Must support multiple policy types
* **Honesty**: Must surface limitations explicitly
* **Auditability**: Every decision must be traceable

---

## Considered Options

### Option 1: Ad-hoc Checks in Action Gateway
**Pros:**
- Simple to implement
- No additional components

**Cons:**
- ❌ Not scalable (hardcoded logic)
- ❌ No centralized policy management
- ❌ Difficult to audit
- ❌ Cannot handle complex rules

### Option 2: External Policy Engine (OPA, Cedar)
**Pros:**
- Industry-standard tools
- Powerful policy language

**Cons:**
- ❌ Additional infrastructure (free tier violated)
- ❌ Learning curve for policy language
- ❌ Overkill for current needs
- ❌ Integration complexity

### Option 3: Custom Policy Verifier Engine (Chosen)
**Pros:**
- ✅ Full control over logic
- ✅ Database-backed (PostgreSQL)
- ✅ Python-native (matches stack)
- ✅ Integrated with telemetry
- ✅ No external dependencies
- ✅ Easy to extend

**Cons:**
- Requires initial development effort
- Need to maintain custom code

---

## Decision Outcome

Chosen option: **Option 3 - Custom Policy Verifier Engine**

### Why This is the Right Choice

1. **Free Tier Compliance**: Uses existing PostgreSQL, no paid tools
2. **Tight Integration**: Works seamlessly with existing IMS components
3. **Flexibility**: Can implement any policy type we need
4. **Performance**: Optimized for our specific use cases
5. **Transparency**: All logic is auditable and understandable
6. **Extensibility**: Easy to add new policy categories

---

## Architecture Design

### High-Level Flow

```
┌─────────────────────┐
│  API Request        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Action Gateway     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────┐
│  Policy Verifier Engine         │
│  ┌──────────────────────────┐   │
│  │ Evaluation Context       │   │
│  │ - model_id               │   │
│  │ - estimated_tokens       │   │
│  │ - vendor_id              │   │
│  │ - prompt                 │   │
│  └──────────────────────────┘   │
│           │                      │
│           ▼                      │
│  ┌────────────────────────────┐ │
│  │ Fetch Active Policies      │ │
│  │ (from policy_registry)     │ │
│  └────────┬───────────────────┘ │
│           │                      │
│           ▼                      │
│  ┌────────────────────────────┐ │
│  │ Category-Specific          │ │
│  │ Evaluators                 │ │
│  │ - Cost Evaluator          │ │
│  │ - Vendor Evaluator        │ │
│  │ - Behavioral Evaluator    │ │
│  └────────┬───────────────────┘ │
│           │                      │
│           ▼                      │
│  ┌────────────────────────────┐ │
│  │ Violation Detection        │ │
│  └────────┬───────────────────┘ │
│           │                      │
│           ▼                      │
│  ┌────────────────────────────┐ │
│  │ Determine Action           │ │
│  │ - BLOCK                    │ │
│  │ - WARN                     │ │
│  │ - LOG                      │ │
│  │ - DEGRADE (fallback)       │ │
│  └────────────────────────────┘ │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────┐
│  Policy Result      │
│  - passed: bool     │
│  - violations: []   │
│  - warnings: []     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────┐
│  If Blocked: HTTP 403   │
│  If Degraded: Fallback  │
│  If Passed: Continue    │
└─────────────────────────┘
```

### Database Schema

**Three Core Tables:**

1. **`policies`** - Policy definitions
   - Constraints (JSON)
   - Evaluation type (pre_flight, runtime, post_execution)
   - Action on violation (block, warn, log, degrade)
   - Priority (0-100, higher = more critical)

2. **`policy_violations`** - Audit log
   - Violation details (JSON)
   - Severity (low, medium, high, critical)
   - Action taken
   - Resolution tracking

3. **`policy_executions`** - Performance tracking
   - Evaluation time
   - Pass/fail status
   - Input/output snapshots

### Policy Categories

1. **Cost** - Budget and spending control
2. **Vendor** - Provider restrictions
3. **Behavioral** - Content safety, rate limits
4. **Performance** - SLA enforcement
5. **Data Residency** - Geographic restrictions
6. **Compliance** - Audit requirements

### Evaluator Pattern

Each category has a dedicated evaluator:

```python
async def _evaluate_cost_policy(policy, context) -> dict:
    """
    Returns:
    {
        "passed": bool,
        "details": {...},
        "warnings": [...]
    }
    """
```

This allows:
- Category-specific logic
- Easy testing
- Clear separation of concerns
- Independent evolution

---

## Consequences

### Positive ✅

1. **Cost Control**: Can enforce strict budget limits
2. **Governance**: Complete audit trail for compliance
3. **Safety**: Behavioral guardrails prevent abuse
4. **Flexibility**: Easy to add new policy types
5. **Performance**: < 50ms evaluation time
6. **Transparency**: All decisions are logged and explainable

### Negative ❌

1. **Maintenance Burden**: Custom code to maintain
2. **Initial Effort**: ~40 hours to implement fully
3. **Testing Complexity**: Need comprehensive test coverage
4. **Missing Features**: Some advanced features not yet implemented:
   - Daily cost tracking requires metrics integration
   - Rate limiting requires Redis integration
   - Content filtering is basic (not ML-based)

### Mitigations

1. **Comprehensive Tests**: 90%+ coverage target
2. **Clear Documentation**: Operator manuals and ADRs
3. **Phased Rollout**: Enable policies gradually
4. **Monitoring**: Track policy effectiveness via telemetry
5. **Fail-Open**: Policy evaluation errors don't block requests

---

## Implementation Details

### Priority-to-Severity Mapping

```
Priority 90-100 → CRITICAL (always block)
Priority 70-89  → HIGH (block or degrade)
Priority 40-69  → MEDIUM (warn)
Priority 0-39   → LOW (log)
```

### Action Determination Logic

1. Check policy's explicit `action_on_violation` field
2. If not set, use severity-based default:
   - CRITICAL → BLOCK
   - HIGH (cost category) → DEGRADE
   - HIGH (other) → BLOCK
   - MEDIUM → WARN
   - LOW → LOG

### Fallback Mechanism

When a cost policy triggers DEGRADE action:

1. Query model registry for cheaper alternatives
2. Filter by same capability tier or lower
3. Select cheapest option that meets requirements
4. Re-evaluate with new model
5. If still fails, BLOCK

### Performance Optimization

1. **Indexed Queries**: All filter columns indexed
2. **Async Operations**: Violation logging is async
3. **Early Exit**: Stop on first BLOCK violation
4. **Cached Pricing**: Model costs cached from registry

---

## Research Foundation

This design is informed by:

1. **FrugalGPT** (arXiv:2305.05176)
   - Model cascading concept
   - Cost optimization strategies

2. **RouteLLM** (arXiv:2406.18665)
   - Intelligent routing patterns
   - Quality vs cost tradeoffs

3. **Industry Practices**
   - Open Policy Agent (OPA) patterns
   - AWS IAM policy evaluation
   - Kubernetes admission controllers

---

## Testing Strategy

### Unit Tests (15+ tests)
- Each evaluator tested independently
- Severity mapping verified
- Action determination logic tested
- Edge cases covered

### Integration Tests
- End-to-end policy enforcement
- Database operations
- Event emission
- API responses

### Load Tests
- 1000 req/s throughput target
- < 50ms p95 latency
- No memory leaks
- Concurrent evaluation handling

---

## Migration Path

### Phase 1: Foundation (Week 1) ✅
- Database schema
- Data layer
- Core engine

### Phase 2: Integration (Week 2)
- Action Gateway integration
- Compliance API
- Event emission

### Phase 3: Production (Week 3)
- Daily cost tracking
- Rate limiting
- ML content filtering
- Operator training

---

## Success Metrics

1. **Cost Savings**: 30%+ reduction in token spend
2. **Policy Effectiveness**: <1% false positives
3. **Performance**: <50ms evaluation time (p95)
4. **Compliance**: 100% audit trail coverage
5. **Adoption**: 100% of requests evaluated
6. **Reliability**: 99.9%+ uptime for policy checks

---

## Alternatives Considered (Detailed)

### Cedar (AWS Policy Language)

**Rejected because:**
- Requires running Cedar service (not free tier)
- Learning curve for policy syntax
- Overkill for current needs
- Limited Python integration

### Open Policy Agent (OPA)

**Rejected because:**
- Additional infrastructure (Docker container)
- Rego language learning curve
- Heavier than needed
- Not Python-native

### Rule Engine (Drools, etc.)

**Rejected because:**
- Java-based (different stack)
- Complexity for our use case
- Limited Python support

---

## Links

- **Epic Document**: `IMS-EPIC-4-POLICY-ENFORCEMENT.md`
- **Implementation**: `EPIC-4-POLICY-ENFORCEMENT-ENGINE/`
- **Tests**: `tests/test_policy_verifier.py`
- **API Docs**: `/api/v1/compliance` endpoints

---

## Follow-Up ADRs

- ADR-0006: Smart Model Router (in progress)
- ADR-0007: Usage Tracking & Metrics Store
- ADR-0008: ML-Based Content Filtering

---

**Decision Date:** 2025-12-31  
**Review Date:** 2026-01-31 (1 month after deployment)  
**Status:** Accepted ✅

---

## Appendix: Policy Examples

### Example 1: Free Tier Budget
```json
{
  "name": "free-tier-daily-budget",
  "category": "cost",
  "priority": 95,
  "constraints": {
    "max_daily_cost": 1.0,
    "max_cost_per_request": 0.01
  },
  "evaluation_type": "pre_flight",
  "action_on_violation": "block"
}
```

### Example 2: Approved Vendors
```json
{
  "name": "approved-vendors-only",
  "category": "vendor",
  "priority": 80,
  "constraints": {
    "allowed_vendors": ["google", "anthropic", "openai"]
  },
  "evaluation_type": "pre_flight",
  "action_on_violation": "block"
}
```

### Example 3: Prompt Length Limit
```json
{
  "name": "prompt-length-limit",
  "category": "behavioral",
  "priority": 85,
  "constraints": {
    "max_prompt_length": 50000,
    "warn_threshold": 40000
  },
  "evaluation_type": "pre_flight",
  "action_on_violation": "block"
}
```

---

**Approved by:** IMS-Apex Architecture Team  
**Implemented by:** Claude Sonnet 4.5  
**Deployed to:** ims-core-dev
