# 📊 Epic 1.3: Telemetry Bus (RabbitMQ + Event Streaming)

## Overview

The **Telemetry Bus** is a real-time event streaming system that captures metrics, logs, and events from the API and routes them for processing, monitoring, and analysis.

**Status**: Planning Phase
**Priority**: High
**Timeline**: Dec 16 - Jan 5 (3 weeks)
**Effort**: 40-50 hours

---

## 🎯 Goals

1. **Event Publishing**: Emit events when models are registered, updated, or queried
2. **Message Queue**: RabbitMQ for reliable event delivery
3. **Event Subscribers**: Multiple consumers (metrics, logging, analytics)
4. **Real-time Monitoring**: Track API performance and usage
5. **Error Handling**: Dead-letter queues and retry logic
6. **Observability**: Full event audit trail

---

## 📋 Sub-Epics

### **1.3.1: RabbitMQ Setup & Configuration**
- [ ] RabbitMQ container setup (Docker)
- [ ] Queue/Exchange definitions
- [ ] Connection pooling
- [ ] Health checks
- [ ] Docker integration

**Acceptance Criteria:**
- RabbitMQ running on port 5672 (AMQP) + 15672 (management UI)
- 3 exchanges: `models.events`, `metrics.events`, `errors.events`
- 6 queues with appropriate bindings
- Health check endpoint returns queue stats
- Docker compose includes RabbitMQ service

**Effort**: 8 hours

---

### **1.3.2: Event Publisher (API Integration)**
- [ ] Event emitter utility/service
- [ ] Model lifecycle events:
  - `model.registered`
  - `model.updated`
  - `model.deactivated`
  - `model.queried`
  - `filter.executed`
- [ ] Request/response metrics
- [ ] Error event emission
- [ ] Event schema definition (JSON)
- [ ] Async publishing (non-blocking)

**Acceptance Criteria:**
- Publisher emits events without blocking API responses
- All 6 event types working
- Event schema includes: timestamp, source, event_type, data, correlation_id
- API latency not affected (< 1ms overhead)
- Graceful handling of RabbitMQ downtime

**Effort**: 12 hours

---

### **1.3.3: Metrics Subscriber**
- [ ] Metrics collector service
- [ ] Event processing pipeline
- [ ] Metrics stored (PostgreSQL or Redis):
  - Model registration rate
  - Query frequency by vendor/tier
  - Average response time
  - Error rates
  - Peak usage times
- [ ] Metrics API endpoint (`GET /metrics`)
- [ ] Health monitoring

**Acceptance Criteria:**
- Metrics updated in real-time
- Metrics endpoint returns JSON with usage stats
- Handles 1000+ events/second
- No event loss
- Metrics queryable by time range

**Effort**: 10 hours

---

### **1.3.4: Error Handling & Dead-Letter Queue**
- [ ] Dead-letter queue setup
- [ ] Retry logic (exponential backoff)
- [ ] Error event tracking
- [ ] Alert mechanism (log errors)
- [ ] Error recovery procedures

**Acceptance Criteria:**
- Failed messages moved to DLQ after 3 retries
- Exponential backoff: 1s, 5s, 30s
- DLQ events logged with stack traces
- Recovery endpoint to replay DLQ messages
- Manual intervention documented

**Effort**: 8 hours

---

### **1.3.5: Integration & Testing**
- [ ] End-to-end tests (API → Queue → Subscriber)
- [ ] Load testing (1000 events/sec)
- [ ] Failover testing (RabbitMQ down)
- [ ] Event ordering verification
- [ ] Performance benchmarks

**Acceptance Criteria:**
- All integration tests passing
- Load test: 1000 events/sec without errors
- RabbitMQ downtime handled gracefully
- Events processed in order (per model_id)
- Latency < 100ms (p95)

**Effort**: 12 hours

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│           FastAPI REST API                          │
│  (Model Registry - Epic 1.2)                        │
└────────────────┬────────────────────────────────────┘
                 │
                 │ emit events
                 ▼
┌─────────────────────────────────────────────────────┐
│      Event Publisher (1.3.2)                        │
│  - model.registered                                 │
│  - model.updated                                    │
│  - model.deactivated                                │
│  - model.queried                                    │
│  - filter.executed                                  │
│  - api.error                                        │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│      RabbitMQ (1.3.1)                               │
│  ┌─────────────────────────────────────────────┐   │
│  │ Exchange: models.events                     │   │
│  │ Exchange: metrics.events                    │   │
│  │ Exchange: errors.events                     │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │ Queue: metrics.updates                      │   │
│  │ Queue: analytics.events                     │   │
│  │ Queue: logging.errors                       │   │
│  │ Queue: audit.trail                          │   │
│  │ Queue: dlq.dead_letters                     │   │
│  └─────────────────────────────────────────────┘   │
└────────┬──────────────┬──────────────┬──────────────┘
         │              │              │
         ▼              ▼              ▼
    ┌─────────┐  ┌─────────┐  ┌─────────────┐
    │Metrics  │  │Logging  │  │Error Handler│
    │Consumer │  │Consumer │  │ (1.3.4)     │
    │(1.3.3)  │  │(logs)   │  └─────────────┘
    └────┬────┘  └─────────┘       │
         │                         │
         ▼                         ▼
    ┌─────────┐           ┌──────────────┐
    │PostgreSQL           │Dead-Letter   │
    │Metrics Table        │Queue         │
    └─────────┘           └──────────────┘
         │
         ▼
    ┌─────────────────┐
    │Metrics API      │
    │GET /metrics     │
    └─────────────────┘
```

---

## 📊 Event Schema

```json
{
  "event_id": "uuid",
  "event_type": "model.registered|model.updated|model.deactivated|model.queried|filter.executed|api.error",
  "timestamp": "2025-01-01T12:00:00Z",
  "source": "api|scheduler|admin",
  "correlation_id": "request-uuid",
  "user_id": "api-key-hash",
  
  "data": {
    "model_id": "gpt-4-turbo",
    "vendor_id": "OpenAI",
    "capability_tier": "Tier_1",
    "context_window": 128000,
    "cost_in_per_mil": 10.0,
    "cost_out_per_mil": 30.0,
    "function_call_support": true,
    "is_active": true
  },
  
  "metadata": {
    "request_duration_ms": 45,
    "response_code": 201,
    "user_agent": "curl/7.68.0",
    "ip_address": "127.0.0.1"
  },
  
  "error": {
    "type": null,
    "message": null,
    "stack_trace": null
  }
}
```

---

## 🔄 Event Types

### **model.registered**
Fired when a new model is registered

### **model.updated**
Fired when a model is updated

### **model.deactivated**
Fired when a model is deactivated

### **model.queried**
Fired when a model is retrieved

### **filter.executed**
Fired when a filter query is executed

### **api.error**
Fired when an API error occurs

---

## 📈 Metrics to Track

- Models registered (total, 24h, by vendor, by tier)
- API queries (total, 24h, by endpoint)
- API latency (p50, p95, p99)
- Error rates
- Cache hit rates
- Event processing latency

---

## 🧪 Testing Strategy

### **Unit Tests**
- Event publisher (emits correct events)
- Event schema validation
- Metrics calculation
- Retry logic

### **Integration Tests**
- Event → Queue → Subscriber flow
- End-to-end model registration → event → metrics
- Error handling (RabbitMQ down)
- Dead-letter queue behavior

### **Load Tests**
- 1000 events/second throughput
- Memory usage under load
- CPU usage monitoring
- Event ordering verification

---

## 📦 Dependencies

```
pika==1.3.2              # RabbitMQ client
aio-pika==9.2.4          # Async RabbitMQ
python-json-logger==2.0.7  # JSON logging
prometheus-client==0.19.0  # Metrics export
```

---

## 📅 Timeline

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| **1.3.1 RabbitMQ Setup** | 1 week | Dec 16 | Dec 22 |
| **1.3.2 Event Publisher** | 1.5 weeks | Dec 23 | Jan 5 |
| **1.3.3 Metrics Subscriber** | 1 week | Jan 6 | Jan 12 |
| **1.3.4 Error Handling** | 3 days | Jan 13 | Jan 15 |
| **1.3.5 Testing & Polish** | 1 week | Jan 16 | Jan 22 |

---

## ✅ Acceptance Criteria

- [ ] RabbitMQ running and healthy
- [ ] All 6 event types emitted correctly
- [ ] Metrics collected in real-time
- [ ] Metrics API endpoint working
- [ ] Dead-letter queue functional
- [ ] All integration tests passing
- [ ] Load test: 1000 events/sec
- [ ] Documentation complete

---

## 🚀 Success Metrics

| Metric | Target |
|--------|--------|
| Event Throughput | 1000+ events/sec |
| Event Latency | < 10ms (p95) |
| API Impact | < 1ms overhead |
| Error Rate | < 0.1% |

---

## 🔗 Related

- **Epic 1.2**: Model Registry (✅ Complete)
- **Epic 1.4**: Pattern Completion & Recommendation (depends on 1.3)
