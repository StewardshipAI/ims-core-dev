# 📘 EPIC 3: ACTION GATEWAY - COMPLETE SPECIFICATION

**Version:** 1.0.0  
**Status:** Implementation Ready  
**Target Release:** v0.3.0  
**Estimated Effort:** 40-50 hours

---

## 🎯 EXECUTIVE SUMMARY

The **Action Gateway** is the execution layer of IMS that transforms recommendations into real API calls. It provides a unified interface across multiple vendors (Google, OpenAI, Anthropic) with automatic normalization, error handling, and usage tracking.

### What This Epic Delivers

✅ **Vendor Adapter Pattern** - Pluggable architecture for API providers  
✅ **Unified Interface** - Single API regardless of vendor  
✅ **Request Normalization** - Convert between vendor formats  
✅ **Response Normalization** - Consistent output structure  
✅ **Error Handling** - Integrated with Epic 2 error recovery  
✅ **Usage Tracking** - Real token/cost monitoring  
✅ **State Integration** - Hooks into workflow state machine  

---

## 🏗️ ARCHITECTURE

### Component Hierarchy

```
Action Gateway (Orchestrator)
├── Vendor Adapter Interface (Abstract Base)
│   ├── Google Gemini Adapter
│   ├── OpenAI GPT Adapter
│   └── Anthropic Claude Adapter
├── Request Normalizer
├── Response Normalizer
└── Execution Context Manager
```

### Data Flow

```
User Request
    ↓
[ State Machine: SELECTING_MODEL → EXECUTING ]
    ↓
Action Gateway
    ├─> Select Adapter (based on model_id)
    ├─> Normalize Request
    ├─> Execute API Call
    ├─> Handle Errors (Circuit Breaker, Retry)
    ├─> Normalize Response
    ├─> Track Usage
    └─> Update State Machine
    ↓
[ State Machine: EXECUTING → VALIDATING → COMPLETED ]
    ↓
Return Response to User
```

---

## 📋 DETAILED REQUIREMENTS

### 1. Vendor Adapter Interface

**Purpose:** Abstract base class that all vendor adapters implement.

**Methods:**
```python
class VendorAdapter(ABC):
    @abstractmethod
    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """Execute API call and return normalized response"""
        pass
    
    @abstractmethod
    def supports_model(self, model_id: str) -> bool:
        """Check if adapter supports this model"""
        pass
    
    @abstractmethod
    async def validate_credentials(self) -> bool:
        """Verify API key is valid"""
        pass
    
    @abstractmethod
    def get_rate_limits(self) -> RateLimits:
        """Return rate limit configuration"""
        pass
```

---

### 2. Google Gemini Adapter

**Implementation:**
```python
class GeminiAdapter(VendorAdapter):
    def __init__(self, api_key: str):
        self.client = genai.GenerativeModel()
        self.api_key = api_key
    
    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        # Convert IMS request → Gemini format
        gemini_request = self._to_gemini_format(request)
        
        # Execute API call
        response = await self.client.generate_content(gemini_request)
        
        # Convert Gemini response → IMS format
        ims_response = self._from_gemini_format(response)
        
        return ims_response
```

**Supported Models:**
- gemini-2.0-flash-exp
- gemini-2.5-flash
- gemini-2.5-flash-8b
- gemini-2.5-pro
- gemini-1.5-flash
- gemini-1.5-pro

---

### 3. OpenAI GPT Adapter

**Implementation:**
```python
class OpenAIAdapter(VendorAdapter):
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        # Convert IMS request → OpenAI format
        openai_request = self._to_openai_format(request)
        
        # Execute API call
        response = await self.client.chat.completions.create(**openai_request)
        
        # Convert OpenAI response → IMS format
        ims_response = self._from_openai_format(response)
        
        return ims_response
```

**Supported Models:**
- gpt-4o
- gpt-4o-mini
- gpt-4-turbo
- gpt-3.5-turbo
- o1-preview
- o1-mini

---

### 4. Anthropic Claude Adapter

**Implementation:**
```python
class ClaudeAdapter(VendorAdapter):
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
    
    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        # Convert IMS request → Claude format
        claude_request = self._to_claude_format(request)
        
        # Execute API call
        response = await self.client.messages.create(**claude_request)
        
        # Convert Claude response → IMS format
        ims_response = self._from_claude_format(response)
        
        return ims_response
```

**Supported Models:**
- claude-3-5-sonnet-20241022
- claude-3-5-haiku-20241022
- claude-3-opus-20240229
- claude-3-sonnet-20240229
- claude-3-haiku-20240307

---

### 5. Unified Request/Response Schema

**ExecutionRequest:**
```python
@dataclass
class ExecutionRequest:
    """Unified request format across all vendors"""
    prompt: str
    model_id: str
    max_tokens: Optional[int] = None
    temperature: float = 1.0
    top_p: float = 1.0
    stop_sequences: Optional[List[str]] = None
    system_instruction: Optional[str] = None
    tools: Optional[List[Tool]] = None
    
    # Context
    workflow_id: str
    correlation_id: str
    
    # Metadata
    user_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
```

**ExecutionResponse:**
```python
@dataclass
class ExecutionResponse:
    """Unified response format across all vendors"""
    content: str
    model_id: str
    
    # Usage
    tokens_input: int
    tokens_output: int
    cost_input: float
    cost_output: float
    
    # Performance
    latency_ms: int
    
    # Metadata
    finish_reason: str
    workflow_id: str
    correlation_id: str
    
    # Raw response (for debugging)
    raw_response: Optional[Dict] = None
```

---

### 6. Action Gateway Orchestrator

**Purpose:** Main class that coordinates execution across adapters.

**Implementation:**
```python
class ActionGateway:
    def __init__(
        self,
        registry: ModelRegistry,
        state_machine: StateMachine,
        error_recovery: ErrorRecovery,
        usage_tracker: UsageTracker,
        adapters: Dict[str, VendorAdapter]
    ):
        self.registry = registry
        self.state_machine = state_machine
        self.error_recovery = error_recovery
        self.usage_tracker = usage_tracker
        self.adapters = adapters
    
    async def execute(
        self,
        request: ExecutionRequest
    ) -> ExecutionResponse:
        \"\"\"
        Execute request with automatic vendor selection,
        error recovery, and usage tracking.
        \"\"\"
        # 1. Get model details
        model = self.registry.get_model(request.model_id)
        
        # 2. Select adapter
        adapter = self._select_adapter(model.vendor_id)
        
        # 3. Transition state
        self.state_machine.transition(
            TransitionEvent.EXECUTION_STARTED,
            {"model_id": request.model_id}
        )
        
        # 4. Execute with error recovery
        try:
            response = await self.error_recovery.execute_with_recovery(
                adapter.execute,
                request.model_id,
                request
            )
            
            # 5. Track usage
            await self.usage_tracker.log_execution(
                model_id=response.model_id,
                vendor_id=model.vendor_id,
                tokens_in=response.tokens_input,
                tokens_out=response.tokens_output,
                cost_per_mil_in=model.cost_in_per_mil,
                cost_per_mil_out=model.cost_out_per_mil,
                latency_ms=response.latency_ms,
                success=True
            )
            
            # 6. Transition state
            self.state_machine.transition(
                TransitionEvent.EXECUTION_COMPLETED,
                {"tokens": response.tokens_input + response.tokens_output}
            )
            
            return response
            
        except Exception as e:
            # Track failure
            await self.usage_tracker.log_execution(
                model_id=request.model_id,
                vendor_id=model.vendor_id,
                tokens_in=0,
                tokens_out=0,
                cost_per_mil_in=0,
                cost_per_mil_out=0,
                latency_ms=0,
                success=False,
                error=str(e)
            )
            
            # Transition to failed state
            self.state_machine.transition(
                TransitionEvent.ERROR,
                {"error": str(e)}
            )
            
            raise
```

---

## 🔌 API INTEGRATION

### New Endpoint: `/api/v1/execute`

**Purpose:** Execute a prompt with a selected model.

**Request:**
```json
POST /api/v1/execute
Content-Type: application/json
X-Admin-Key: <key>

{
  "prompt": "Explain quantum computing in simple terms",
  "model_id": "gemini-2.5-flash",
  "max_tokens": 1000,
  "temperature": 0.7,
  "system_instruction": "You are a helpful AI assistant."
}
```

**Response:**
```json
{
  "content": "Quantum computing is...",
  "model_id": "gemini-2.5-flash",
  "tokens": {
    "input": 125,
    "output": 487,
    "total": 612
  },
  "cost": {
    "input": 0.000009,
    "output": 0.000146,
    "total": 0.000155
  },
  "latency_ms": 1847,
  "finish_reason": "stop",
  "workflow_id": "wf_abc123",
  "correlation_id": "req_xyz789"
}
```

---

## 🧪 TESTING STRATEGY

### Unit Tests

**Test Adapters:**
```python
def test_gemini_adapter_execute():
    """Test Gemini adapter execution"""
    adapter = GeminiAdapter(api_key="test")
    request = ExecutionRequest(
        prompt="Test",
        model_id="gemini-2.5-flash"
    )
    
    response = await adapter.execute(request)
    
    assert response.content is not None
    assert response.tokens_input > 0
    assert response.tokens_output > 0
```

**Test Normalization:**
```python
def test_request_normalization():
    """Test IMS → Gemini format conversion"""
    request = ExecutionRequest(
        prompt="Test",
        temperature=0.7,
        max_tokens=100
    )
    
    gemini_format = adapter._to_gemini_format(request)
    
    assert "generation_config" in gemini_format
    assert gemini_format["generation_config"]["temperature"] == 0.7
```

### Integration Tests

**Test End-to-End Flow:**
```python
@pytest.mark.asyncio
async def test_full_execution_flow():
    \"\"\"Test complete execution: recommend → execute → track\"\"\"
    # 1. Get recommendation
    recommendation = await client.post("/api/v1/recommend", ...)
    model_id = recommendation.json()[0]["model_id"]
    
    # 2. Execute
    execution = await client.post("/api/v1/execute", json={
        "prompt": "Test prompt",
        "model_id": model_id
    })
    
    assert execution.status_code == 200
    result = execution.json()
    
    # 3. Verify tracking
    metrics = await client.get("/metrics", ...)
    assert metrics.json()["total_model_queries"] > 0
```

---

## 📊 MONITORING & OBSERVABILITY

### Telemetry Events

**New Events:**
- `gateway.execution_started`
- `gateway.execution_completed`
- `gateway.execution_failed`
- `gateway.adapter_selected`

**Event Schema:**
```json
{
  "type": "gateway.execution_completed",
  "source": "/action-gateway",
  "data": {
    "model_id": "gemini-2.5-flash",
    "vendor_id": "Google",
    "tokens": 612,
    "cost": 0.000155,
    "latency_ms": 1847,
    "success": true
  }
}
```

### Metrics

**New Metrics:**
- `total_executions`
- `executions_by_vendor`
- `executions_by_model`
- `total_tokens_consumed`
- `total_cost_spent`
- `average_latency_ms`

---

## 🔐 SECURITY CONSIDERATIONS

### API Key Management

**Storage:**
```python
# .env
GOOGLE_API_KEY=<key>
OPENAI_API_KEY=<key>
ANTHROPIC_API_KEY=<key>

# Never log API keys
# Never expose in responses
# Rotate regularly
```

**Validation:**
```python
async def validate_all_adapters():
    \"\"\"Validate all API keys on startup\"\"\"
    for name, adapter in adapters.items():
        try:
            valid = await adapter.validate_credentials()
            if not valid:
                logger.error(f"{name} adapter: Invalid API key")
        except Exception as e:
            logger.error(f"{name} adapter: {e}")
```

---

## 📁 FILE STRUCTURE

```
src/gateway/
├── __init__.py
├── action_gateway.py       # Main orchestrator
├── adapters/
│   ├── __init__.py
│   ├── base.py             # VendorAdapter base class
│   ├── gemini.py           # Google Gemini adapter
│   ├── openai.py           # OpenAI GPT adapter
│   └── claude.py           # Anthropic Claude adapter
├── normalization.py        # Request/response normalizers
├── schemas.py              # ExecutionRequest/Response
└── exceptions.py           # Gateway-specific exceptions
```

---

## 🚀 IMPLEMENTATION PLAN

### Phase 1: Foundation 
- ✅ Create base adapter interface
- ✅ Define unified schemas
- ✅ Implement request/response normalizers
- ✅ Write unit tests

### Phase 2: Adapters 
- ✅ Implement Gemini adapter
- ✅ Implement OpenAI adapter
- ✅ Implement Claude adapter
- ✅ Write adapter tests

### Phase 3: Gateway 
- ✅ Implement ActionGateway orchestrator
- ✅ Integrate with state machine
- ✅ Integrate with error recovery
- ✅ Integrate with usage tracker

### Phase 4: API Integration 
- ✅ Add `/api/v1/execute` endpoint
- ✅ Update FastAPI dependencies
- ✅ Write integration tests
- ✅ Update documentation

### Phase 5: Testing & Polish 
- ✅ End-to-end testing
- ✅ Load testing
- ✅ Security audit
- ✅ Documentation review

---

## ✅ ACCEPTANCE CRITERIA

Epic 3 is complete :

- ✅ All 3 adapters implemented (Gemini, OpenAI, Claude)
- ✅ Unified interface works across all vendors
- ✅ Request/response normalization functional
- ✅ Integration with state machine works
- ✅ Usage tracking captures all executions
- ✅ Error recovery triggers fallback
- ✅ API endpoint `/api/v1/execute` operational
- ✅ All tests passing (unit + integration)
- ✅ Documentation complete
- ✅ Security audit passed

---

## 📈 SUCCESS METRICS

| Metric | Target |
|--------|--------|
| Adapter Coverage | 100% (Google, OpenAI, Anthropic) |
| Test Coverage | >90% |
| Execution Success Rate | >98% |
| Average Latency | <2s (p95) |
| Error Recovery Success | >95% |
| API Uptime | >99.9% |

---

**READY FOR IMPLEMENTATION! 🚀**

See `src/gateway/` for complete implementation code.
