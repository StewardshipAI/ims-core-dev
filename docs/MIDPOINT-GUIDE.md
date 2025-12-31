# 🎯 IMS MIDPOINT IMPLEMENTATION
## Complete Guide to Epic 2 Components

**Version:** 1.0  
**Status:** Ready for Deployment  
**Date:** December 30, 2025

---

## 📋 EXECUTIVE SUMMARY

This package contains all components needed to reach the **IMS Midpoint**—a production-ready model selection service that integrates with Gemini-CLI and provides:

✅ **Usage Tracking** - Monitor token consumption and costs  
✅ **Error Recovery** - Automatic fallback and retry logic  
✅ **State Machine** - Foundation for Epic 3 workflows  
✅ **Gemini-CLI Integration** - Smart model selection wrapper  
✅ **Health Monitoring** - Real-time status dashboard  
✅ **Model Seeding** - Auto-populate registry

---

## 🗂️ PACKAGE CONTENTS

```
IMS-MIDPOINT-IMPLEMENTATION/
├── src/
│   └── core/
│       ├── usage_tracker.py      # Token/cost tracking + telemetry
│       ├── error_recovery.py     # Fallback + retry logic
│       └── state_machine.py      # Agent workflow orchestration
│
├── scripts/
│   ├── ims-gemini.sh            # Gemini-CLI integration wrapper
│   ├── ims-status.sh            # Health monitoring dashboard
│   ├── seed-models.sh           # Auto-populate model registry
│   └── setup-midpoint.sh        # One-click installation
│
├── tests/
│   └── test_integration.py      # End-to-end integration tests
│
└── docs/
    └── MIDPOINT-GUIDE.md        # This file
```

---

## 🚀 QUICK START

### Option A: Automated Setup (RECOMMENDED)

```bash
# 1. Navigate to this directory
cd /mnt/c/Users/natha/OneDrive/Documents/Claude-BuildsDocs/IMS-MIDPOINT-IMPLEMENTATION

# 2. Make setup script executable
chmod +x scripts/setup-midpoint.sh

# 3. Run automated setup
./scripts/setup-midpoint.sh

# That's it! ✅
```

### Option B: Manual Setup

```bash
# 1. Copy components to ims-core-dev
TARGET="$HOME/projects/IMS-ECOSYSTEM/ims/ims-core-dev"

cp src/core/*.py "$TARGET/src/core/"
cp scripts/*.sh "$TARGET/scripts/"
cp tests/test_integration.py "$TARGET/tests/"

# 2. Make scripts executable
chmod +x "$TARGET/scripts"/*.sh

# 3. Seed models
cd "$TARGET"
./scripts/seed-models.sh

# 4. Test integration
./scripts/ims-gemini.sh "What is 2+2?"

# 5. Check status
./scripts/ims-status.sh --once
```

---

## 📦 COMPONENT DETAILS

### 1. Usage Tracker (`src/core/usage_tracker.py`)

**Purpose:** Track token consumption, costs, and performance metrics.

**Features:**
- Per-model token/cost tracking
- Session statistics
- Telemetry emission (RabbitMQ)
- Real-time cost calculation

**API:**
```python
from src.core.usage_tracker import UsageTracker

tracker = UsageTracker(publisher)

await tracker.log_execution(
    model_id="gemini-2.5-flash",
    vendor_id="Google",
    tokens_in=1000,
    tokens_out=500,
    cost_per_mil_in=0.075,
    cost_per_mil_out=0.30,
    latency_ms=1500,
    success=True
)

stats = tracker.get_session_stats()
# Returns: {requests, tokens, cost, failures, success_rate}
```

**Integration:**
- Emits `model.executed` events
- Stores metrics in Redis (via telemetry bus)
- Provides `/metrics` API endpoint data

---

### 2. Error Recovery (`src/core/error_recovery.py`)

**Purpose:** Intelligent error handling with automatic recovery.

**Features:**
- Error classification (rate limit, timeout, etc.)
- Strategy selection (fallback, retry, truncate)
- Circuit breaker pattern
- Exponential backoff

**Error Types:**
- `RATE_LIMIT` → Switch to different model
- `TIMEOUT` → Retry with backoff
- `OVERLOAD` → Use fallback model
- `CONTEXT_OVERFLOW` → Truncate input (TODO)
- `INVALID_REQUEST` → Fail fast
- `AUTHENTICATION` → Fail fast

**API:**
```python
from src.core.error_recovery import ErrorRecovery

recovery = ErrorRecovery(registry, recommendation_service)

# Wrap any async function
result = await recovery.execute_with_recovery(
    execution_fn=my_api_call,
    model_id="gemini-2.5-flash",
    prompt="..."
)

# Automatic fallback if primary fails!
```

**Circuit Breaker:**
- Opens after 3 consecutive failures
- Stays open for 60 seconds
- Automatically recovers
- Status available via `get_circuit_status()`

---

### 3. State Machine (`src/core/state_machine.py`)

**Purpose:** Orchestrate multi-step agentic workflows.

**States:**
```
IDLE → ANALYZING → SELECTING_MODEL → EXECUTING → VALIDATING → COMPLETED
                                                   ↓
                                              ROLLBACK → FAILED
```

**Features:**
- Finite state machine with valid transitions
- Transition history
- Context persistence
- Entry/exit callbacks
- Telemetry emission

**API:**
```python
from src.core.state_machine import StateMachine, AgentState, TransitionEvent

sm = StateMachine(workflow_id="abc123", publisher=publisher)

# Transition through workflow
sm.transition(TransitionEvent.START, {"task": "summarize doc"})
sm.transition(TransitionEvent.ANALYZED, {"complexity": "medium"})
sm.transition(TransitionEvent.MODEL_SELECTED, {"model": "gpt-4o-mini"})
sm.transition(TransitionEvent.EXECUTION_COMPLETED, {"tokens": 1500})
sm.transition(TransitionEvent.VALIDATION_PASSED)

# Get history
history = sm.get_history()

# Serialize for persistence
state_dict = sm.to_dict()

# Restore later
sm = StateMachine.from_dict(state_dict, publisher)
```

**Callbacks:**
```python
def on_execution_start(transition):
    print(f"Starting execution with {transition.context['model']}")

sm.register_entry_callback(AgentState.EXECUTING, on_execution_start)
```

---

### 4. Gemini-CLI Integration (`scripts/ims-gemini.sh`)

**Purpose:** Wrap gemini-cli with intelligent model selection.

**Workflow:**
1. Check IMS health
2. Query IMS for optimal model (based on prompt)
3. Execute with selected model
4. Log usage (TODO)

**Usage:**
```bash
# Simple query
./scripts/ims-gemini.sh "What is 2+2?"

# With strategy
IMS_STRATEGY=performance ./scripts/ims-gemini.sh "Analyze this code..."

# With minimum context
IMS_MIN_CONTEXT=50000 ./scripts/ims-gemini.sh "Summarize this doc..."

# Pass through gemini-cli options
./scripts/ims-gemini.sh "Generate code" --temperature 0.9
```

**Environment Variables:**
- `IMS_API_URL` - IMS endpoint (default: http://localhost:8000)
- `IMS_STRATEGY` - Selection strategy: cost|performance (default: cost)
- `IMS_MIN_CONTEXT` - Minimum context window (default: 10000)
- `ADMIN_API_KEY` - IMS admin API key (required)

---

### 5. Status Dashboard (`scripts/ims-status.sh`)

**Purpose:** Real-time monitoring and health checks.

**Features:**
- System health status
- Usage metrics
- Docker container status
- Interactive menu

**Usage:**
```bash
# Watch mode (auto-refresh every 5s)
./scripts/ims-status.sh

# Single snapshot
./scripts/ims-status.sh --once

# Interactive menu
./scripts/ims-status.sh --interactive

# Help
./scripts/ims-status.sh --help
```

**Dashboard Sections:**
```
╔════════════════════════════════════════╗
║       IMS CORE - STATUS DASHBOARD      ║
╚════════════════════════════════════════╝

═══════════════════ SYSTEM HEALTH ═══════════════════
  Overall Status: ● HEALTHY
  Database:       ● Connected
  Cache (Redis):  ● Connected
  RabbitMQ:       ● Connected
  Pool Config:    2-10 connections

═══════════════════ USAGE METRICS ═══════════════════
  Models Registered:     24
  Model Queries:         147
  Filter Queries:        83

  By Vendor:
    Google       6 models
    OpenAI       6 models
    Anthropic    5 models
    Meta         3 models

═══════════════════ DOCKER STATUS ═══════════════════
  ● postgres       Running (Up 2 hours)
  ● redis          Running (Up 2 hours)
  ● rabbitmq       Running (Up 2 hours)
  ● api            Running (Up 2 hours)
```

---

### 6. Model Seeding (`scripts/seed-models.sh`)

**Purpose:** Auto-populate registry with current models.

**Models Included:**
- **Google Gemini:** 2.0 Flash Exp, 2.5 Flash, 2.5 Flash-8b, 2.5 Pro, 1.5 Flash, 1.5 Pro
- **OpenAI:** GPT-4o, GPT-4o-mini, GPT-4 Turbo, GPT-3.5 Turbo, o1-preview, o1-mini
- **Anthropic Claude:** 3.5 Sonnet, 3.5 Haiku, 3 Opus, 3 Sonnet, 3 Haiku
- **Meta Llama:** 3.1 405B, 3.1 70B, 3.1 8B (local, inactive by default)

**Usage:**
```bash
# Seed all models
./scripts/seed-models.sh

# Verify
curl http://localhost:8000/api/v1/models/filter | jq '.[].model_id'
```

**Features:**
- Skips duplicates automatically
- Current pricing (as of Dec 2025)
- Organized by vendor
- Color-coded output

---

## 🧪 TESTING

### Integration Tests

```bash
cd ~/projects/IMS-ECOSYSTEM/ims/ims-core-dev

# Run all integration tests
pytest tests/test_integration.py -v

# Run specific test
pytest tests/test_integration.py::TestFullWorkflow::test_recommend_and_track_usage -v

# With coverage
pytest tests/test_integration.py --cov=src --cov-report=html
```

### Manual Testing

```bash
# 1. Test health check
curl http://localhost:8000/health | jq

# 2. Test recommendation
curl -X POST http://localhost:8000/api/v1/recommend \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: $ADMIN_API_KEY" \
  -d '{
    "strategy": "cost",
    "min_context_window": 50000
  }' | jq

# 3. Test Gemini-CLI integration
./scripts/ims-gemini.sh "What is the capital of France?"

# 4. Check metrics
curl http://localhost:8000/metrics \
  -H "X-Admin-Key: $ADMIN_API_KEY" | jq

# 5. Monitor dashboard
./scripts/ims-status.sh
```

---

## 🔧 TROUBLESHOOTING

### Issue: `ims-gemini.sh` fails with "API not responding"

**Solution:**
```bash
# Check if Docker containers are running
docker-compose ps

# If not running:
docker-compose up -d

# Wait 30 seconds for startup
sleep 30

# Verify health
curl http://localhost:8000/health
```

---

### Issue: `ADMIN_API_KEY` not set

**Solution:**
```bash
# Check .env file
cat .env | grep ADMIN_API_KEY

# If missing, add it:
echo "ADMIN_API_KEY=$(openssl rand -hex 32)" >> .env

# Reload environment
source .env
```

---

### Issue: Models not seeded

**Solution:**
```bash
# Run seed script manually
./scripts/seed-models.sh

# Check results
curl http://localhost:8000/api/v1/models/filter | jq length

# Should return: 24 (or more)
```

---

### Issue: `gemini-cli` not found

**Solution:**
```bash
# Install gemini-cli globally
npm install -g gemini-cli

# Or use npx
npx gemini-cli --version

# Update ims-gemini.sh to use npx if needed
```

---

### Issue: Redis not configured warning

**Solution:**
```python
# Edit src/api/model_registry_api.py
# Add Redis initialization:

from redis.asyncio import from_url

# After app creation:
redis_client = from_url(REDIS_URL, decode_responses=True)
registry = ModelRegistry(DB_CONN, redis_client=redis_client)
```

Then restart:
```bash
docker-compose restart api
```

---

## 📊 METRICS & MONITORING

### Available Metrics

**Via `/metrics` endpoint:**
```json
{
  "total_models_registered": 24,
  "total_model_queries": 147,
  "total_filter_queries": 83,
  "vendor_models:Google": 6,
  "vendor_models:OpenAI": 6,
  "vendor_models:Anthropic": 5,
  "model_queries:gemini-2.5-flash": 42,
  "model_queries:gpt-4o-mini": 28
}
```

**Via RabbitMQ events:**
- `model.registered`
- `model.updated`
- `model.queried`
- `filter.executed`
- `model.executed` (NEW - from usage tracker)
- `workflow.state_changed` (NEW - from state machine)

---

## 🎯 WHAT'S NEXT?

### Immediate (Today):
1. ✅ Run `setup-midpoint.sh`
2. ✅ Test Gemini-CLI integration
3. ✅ Verify all components working

### This Week:
1. Write usage tracking tests
2. Implement context truncation in error recovery
3. Add Redis caching configuration
4. Create CLI entrypoint (`ims` command)

### Next Week (Epic 3 Prep):
1. Extend state machine with Epic 3 states
2. Design Action Gateway interface
3. Create vendor adapter pattern
4. Write policy schema

---

## 📞 SUPPORT

**Issues:** File in GitHub under `ims-core-dev/issues`  
**Documentation:** See `docs/` folder  
**Logs:** `docker-compose logs -f api`  
**Health:** `./scripts/ims-status.sh`

---

## 🎉 SUCCESS CRITERIA

You've successfully reached the midpoint when:

✅ Health check returns all green  
✅ Models are seeded (24+ models)  
✅ Gemini-CLI integration works  
✅ Dashboard shows metrics  
✅ Usage tracking emits events  
✅ Error recovery triggers fallback  
✅ State machine transitions work  

---

**CONGRATULATIONS! 🎊**

You now have a production-ready model selection service!

Ready to start Epic 3 (Action Gateway) whenever you are! 🚀
