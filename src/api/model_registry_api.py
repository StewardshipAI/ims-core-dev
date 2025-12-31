# FastAPI Model Registry API - PRODUCTION READY (All Critical Fixes Applied)
# ✅ FIX #10: Fixed route ordering (/filter BEFORE /{model_id})

import os
import logging
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, status, Query
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
import redis.asyncio as redis

# Import our data layer
from src.data.model_registry import (
    ModelProfile, 
    CapabilityTier, 
    DuplicateModelError, 
    ValidationError,
    ModelRegistryError
)
from src.api.registry_singleton import registry # Import the singleton

# RabbitMQ Integration
from src.core.events import rabbitmq, get_event_publisher, EventPublisher
from src.schemas.events import CloudEvent

# Load environment variables
load_dotenv()

# --- Configuration & Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api")

# ✅ FIX #6: Enforce strong API key (no weak defaults)
DB_CONN = os.getenv("DB_CONNECTION_STRING")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
REDIS_URL = os.getenv("REDIS_URL")

# ✅ FIX #6: Validate critical environment variables
if not DB_CONN:
    raise ValueError("DB_CONNECTION_STRING must be set in environment")

if not ADMIN_API_KEY or ADMIN_API_KEY == "secret-admin-key":
    raise ValueError(
        "ADMIN_API_KEY must be set to a secure value (min 32 chars). "
        "Generate with: openssl rand -hex 32"
    )

if len(ADMIN_API_KEY) < 32:
    raise ValueError(
        f"ADMIN_API_KEY must be at least 32 characters (current: {len(ADMIN_API_KEY)}). "
        "Generate with: openssl rand -hex 32"
    )

# ✅ FIX #7: Restrict CORS to specific origins
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",")]

logger.info(f"Allowed CORS origins: {ALLOWED_ORIGINS}")

# Import PCR Router
from src.api.pcr_router import router as pcr_router
from src.api.auth_utils import verify_admin

# Rate Limiter Setup
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info("IMS Model Registry API starting up...")
    
    # Initialize RabbitMQ
    await rabbitmq.connect()
    
    logger.info(f"Database connection pool initialized")
    
    # Check health on startup
    health = registry.health_check()
    if health["status"] != "healthy":
        logger.error(f"Startup health check failed: {health}")
        raise RuntimeError("Database health check failed on startup")
    
    logger.info("Startup health check passed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await rabbitmq.close()
    registry.close_pool()
    logger.info("Connection pool closed")

app = FastAPI(
    title="IMS Model Registry API",
    description="REST API for managing the Intelligent Model Selector (IMS) registry.",
    version="1.0.0",
    lifespan=lifespan
)

# Register Rate Limit Exception Handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ✅ FIX #7: Restricted CORS (specific origins only)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # ✅ Whitelist only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],  # ✅ Explicit methods
    allow_headers=["X-Admin-Key", "Content-Type", "Authorization"],  # ✅ Explicit headers
    max_age=3600,  # Cache preflight requests for 1 hour
)

# ✅ FIX #8: Request body size limit middleware (1MB)
MAX_REQUEST_SIZE = 1_000_000  # 1MB

@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """
    ✅ FIX #8: Prevent DoS via large request bodies
    """
    if request.headers.get("content-length"):
        content_length = int(request.headers["content-length"])
        if content_length > MAX_REQUEST_SIZE:
            logger.warning(f"Request too large: {content_length} bytes from {request.client.host}")
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Request body too large. Maximum size: {MAX_REQUEST_SIZE} bytes"
            )
    return await call_next(request)

# --- Security ---
api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=True)

async def verify_admin(key: str = Depends(api_key_header)):
    """
    ✅ FIX #6: Secure API key validation (timing-attack resistant)
    """
    import hmac
    
    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(key, ADMIN_API_KEY):
        logger.warning(f"Invalid admin key attempt from unknown source")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Invalid Admin API Key"
        )
    return key

# --- Pydantic Models (DTOs) ---

class ModelBase(BaseModel):
    capability_tier: CapabilityTier = Field(..., description="Capability tier (Tier_1, Tier_2, Tier_3)")
    context_window: int = Field(..., gt=0, le=10_000_000, description="Max tokens (1-10M)")
    cost_in_per_mil: float = Field(..., ge=0, le=1000, description="Cost per 1M input tokens ($0-1000)")
    cost_out_per_mil: float = Field(..., ge=0, le=1000, description="Cost per 1M output tokens ($0-1000)")
    function_call_support: bool = False
    
    model_config = ConfigDict(use_enum_values=False, protected_namespaces=())

class ModelCreateRequest(ModelBase):
    model_id: str = Field(..., min_length=1, max_length=100, description="Unique Model ID")
    vendor_id: str = Field(..., min_length=1, max_length=50, description="Vendor Name")
    is_active: bool = True

class ModelUpdateRequest(BaseModel):
    # All fields optional for PATCH
    capability_tier: Optional[CapabilityTier] = Field(None, description="Capability tier (Tier_1, Tier_2, Tier_3)")
    context_window: Optional[int] = Field(None, gt=0, le=10_000_000)
    cost_in_per_mil: Optional[float] = Field(None, ge=0, le=1000)
    cost_out_per_mil: Optional[float] = Field(None, ge=0, le=1000)
    function_call_support: Optional[bool] = None
    is_active: Optional[bool] = None
    
    model_config = ConfigDict(use_enum_values=False, protected_namespaces=())

class ModelResponse(ModelBase):
    model_id: str
    vendor_id: str
    is_active: bool

class HealthResponse(BaseModel):
    status: str
    database: str
    cache: str
    pool_stats: Dict[str, Any] = {}

# --- Endpoints ---

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check endpoint"
)
async def health_check():
    """
    ✅ NEW: Health check for monitoring/orchestration
    
    Returns system health status including database, cache, and RabbitMQ.
    """
    try:
        health = registry.health_check()
        
        # Check RabbitMQ
        rmq_status = "connected" if rabbitmq.connection and not rabbitmq.connection.is_closed else "disconnected"
        health["rabbitmq"] = rmq_status
        
        return health
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Health check failed"
        )

@app.get(
    "/metrics",
    tags=["System"],
    summary="Get system metrics"
)
@limiter.limit("60/minute")
async def get_metrics(
    request: Request,
    _: str = Depends(verify_admin)
):
    """
    Retrieve system metrics collected via Telemetry Bus.
    
    **Requires Admin API Key**
    """
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        keys = await r.keys("metrics:*")
        metrics = {}
        if keys:
            values = await r.mget(keys)
            for k, v in zip(keys, values):
                clean_key = k.replace("metrics:", "")
                metrics[clean_key] = int(v) if v.isdigit() else v
        await r.close()
        return metrics
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch metrics")


@app.post(
    "/api/v1/models/register", 
    response_model=Dict[str, str], 
    status_code=status.HTTP_201_CREATED,
    tags=["Admin"],
    summary="Register a new model"
)
@limiter.limit("10/minute")
async def register_model(
    request: Request, 
    model: ModelCreateRequest, 
    _: str = Depends(verify_admin),
    publisher: EventPublisher = Depends(get_event_publisher)
):
    """
    Register a new AI model in the database.
    
    **Requires Admin API Key** (X-Admin-Key header)
    
    - Rate limited: 10 requests/minute
    - Max request size: 1MB
    """
    try:
        # Convert Pydantic model to Domain entity
        profile = ModelProfile(**model.model_dump())
        registered_id = registry.register_model(profile)
        
        # Publish Event
        from uuid import uuid4
        await publisher.publish(CloudEvent(
            source="/api/v1/models/register",
            type="model.registered",
            correlation_id=request.headers.get("X-Request-ID", str(uuid4())),
            data={"model_id": registered_id, "vendor_id": model.vendor_id}
        ))
        
        logger.info(f"Model registered: {registered_id} by admin")
        return {"model_id": registered_id, "status": "registered"}
    
    except DuplicateModelError as e:
        logger.warning(f"Duplicate model registration attempt: {model.model_id}")
        raise HTTPException(status_code=409, detail=str(e))
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except ModelRegistryError as e:
        logger.error(f"Registry error: {e}")
        raise HTTPException(status_code=500, detail="Internal registry error")
    except Exception as e:
        logger.error(f"Unexpected error in registration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# ✅ FIX #10: FILTER ENDPOINT MUST COME BEFORE PARAMETERIZED /{model_id}
@app.get(
    "/api/v1/models/filter", 
    response_model=List[ModelResponse],
    tags=["Public"],
    summary="Filter models by criteria"
)
@limiter.limit("50/minute")
async def filter_models(
    request: Request,
    capability_tier: Optional[CapabilityTier] = Query(None),
    vendor_id: Optional[str] = Query(None),
    function_call_support: Optional[bool] = Query(None),
    min_context: Optional[int] = Query(None, gt=0),
    max_cost_in: Optional[float] = Query(None, ge=0),
    include_inactive: bool = Query(False),
    publisher: EventPublisher = Depends(get_event_publisher)
):
    """
    Search for models matching specific criteria.
    
    - Uses Redis caching (1 min TTL for filter results)
    - Rate limited: 50 requests/minute
    - Returns only active models by default
    
    **Query Parameters:**
    - `capability_tier`: Filter by tier (Tier_1, Tier_2, Tier_3)
    - `vendor_id`: Filter by vendor (e.g., "OpenAI", "Anthropic")
    - `function_call_support`: Filter by tool support (true/false)
    - `min_context`: Minimum context window size
    - `max_cost_in`: Maximum input cost per million tokens
    - `include_inactive`: Include deactivated models (default: false)
    """
    filters = {}
    if capability_tier: filters['capability_tier'] = capability_tier
    if vendor_id: filters['vendor_id'] = vendor_id
    if function_call_support is not None: filters['function_call_support'] = function_call_support
    if min_context: filters['min_context'] = min_context
    if max_cost_in: filters['max_cost_in'] = max_cost_in
    if include_inactive: filters['include_inactive'] = True

    try:
        results = registry.filter_models(**filters)
        
        # Publish Event
        from uuid import uuid4
        await publisher.publish(CloudEvent(
            source="/api/v1/models/filter",
            type="filter.executed",
            correlation_id=request.headers.get("X-Request-ID", str(uuid4())),
            data={"filters": filters, "result_count": len(results)}
        ))
        
        logger.debug(f"Filter query returned {len(results)} results")
        return results
    except ModelRegistryError as e:
        logger.error(f"Registry error filtering models: {e}")
        raise HTTPException(status_code=500, detail="Internal registry error")
    except Exception as e:
        logger.error(f"Unexpected error filtering models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# ✅ GET BY ID COMES AFTER FILTER
@app.get(
    "/api/v1/models/{model_id}", 
    response_model=ModelResponse,
    tags=["Public"],
    summary="Get model by ID"
)
@limiter.limit("100/minute")
async def get_model(
    request: Request, 
    model_id: str,
    publisher: EventPublisher = Depends(get_event_publisher)
):
    """
    Retrieve details for a specific model by ID.
    
    - Uses Redis caching if available (5 min TTL)
    - Rate limited: 100 requests/minute
    """
    try:
        model = registry.get_model(model_id)
        if not model:
            raise HTTPException(
                status_code=404, 
                detail=f"Model '{model_id}' not found"
            )
        
        # Publish Event (Fire & Forget mostly, but here awaited)
        # Note: In high throughput, we might want to background this
        from uuid import uuid4
        await publisher.publish(CloudEvent(
            source=f"/api/v1/models/{model_id}",
            type="model.queried",
            correlation_id=request.headers.get("X-Request-ID", str(uuid4())),
            data={"model_id": model_id, "cached": False} # Registry doesn't expose cache hit status yet
        ))

        return model
    except ModelRegistryError as e:
        logger.error(f"Registry error fetching model: {e}")
        raise HTTPException(status_code=500, detail="Internal registry error")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.patch(
    "/api/v1/models/{model_id}", 
    tags=["Admin"],
    summary="Update model fields"
)
@limiter.limit("10/minute")
async def update_model(
    request: Request, 
    model_id: str, 
    updates: ModelUpdateRequest, 
    _: str = Depends(verify_admin),
    publisher: EventPublisher = Depends(get_event_publisher)
):
    """
    Update mutable fields of a model (costs, tier, capabilities).
    
    **Requires Admin API Key** (X-Admin-Key header)
    
    - Rate limited: 10 requests/minute
    - Cannot update: model_id, vendor_id, created_at, updated_at
    - Invalidates all caches after successful update
    """
    # Filter out None values to only update what was sent
    update_data = updates.model_dump(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(
            status_code=400, 
            detail="No fields provided for update"
        )

    try:
        success = registry.update_model(model_id, update_data)
        if not success:
            raise HTTPException(
                status_code=404, 
                detail=f"Model '{model_id}' not found"
            )
        
        # Publish Event
        from uuid import uuid4
        await publisher.publish(CloudEvent(
            source=f"/api/v1/models/{model_id}",
            type="model.updated",
            correlation_id=request.headers.get("X-Request-ID", str(uuid4())),
            data={"model_id": model_id, "updates": list(update_data.keys())}
        ))
        
        logger.info(f"Model updated: {model_id} by admin")
        return {
            "status": "updated", 
            "model_id": model_id,
            "updated_fields": list(update_data.keys())
        }
    except ValidationError as e:
        logger.warning(f"Validation error updating model: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except ModelRegistryError as e:
        logger.error(f"Registry error updating model: {e}")
        raise HTTPException(status_code=500, detail="Internal registry error")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete(
    "/api/v1/models/{model_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Admin"],
    summary="Deactivate model (soft delete)"
)
@limiter.limit("10/minute")
async def deactivate_model(
    request: Request, 
    model_id: str, 
    _: str = Depends(verify_admin),
    publisher: EventPublisher = Depends(get_event_publisher)
):
    """
    Soft-delete (deactivate) a model.
    
    **Requires Admin API Key** (X-Admin-Key header)
    
    - Rate limited: 10 requests/minute
    - Sets is_active=false (preserves data for audit trail)
    - Invalidates all caches after successful deactivation
    """
    try:
        success = registry.deactivate_model(model_id)
        if not success:
            raise HTTPException(
                status_code=404, 
                detail=f"Model '{model_id}' not found"
            )
        
        # Publish Event
        from uuid import uuid4
        await publisher.publish(CloudEvent(
            source=f"/api/v1/models/{model_id}",
            type="model.deactivated",
            correlation_id=request.headers.get("X-Request-ID", str(uuid4())),
            data={"model_id": model_id}
        ))
        
        logger.info(f"Model deactivated: {model_id} by admin")
        return None  # 204 response has no body
    except ModelRegistryError as e:
        logger.error(f"Registry error deactivating model: {e}")
        raise HTTPException(status_code=500, detail="Internal registry error")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deactivating model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# ✅ NEW: Batch registration endpoint for seed data
@app.post(
    "/api/v1/models/register/batch",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    tags=["Admin"],
    summary="Batch register multiple models"
)
@limiter.limit("5/hour")  # More restrictive for batch operations
async def register_models_batch(
    request: Request,
    models: List[ModelCreateRequest],
    _: str = Depends(verify_admin)
):
    """
    Register multiple models in a single transaction.
    
    **Requires Admin API Key** (X-Admin-Key header)
    
    - Rate limited: 5 requests/hour
    - Skips duplicates (ON CONFLICT DO NOTHING)
    - Useful for seed data population
    """
    if not models:
        raise HTTPException(status_code=400, detail="No models provided")
    
    if len(models) > 100:
        raise HTTPException(
            status_code=400, 
            detail="Maximum 100 models per batch request"
        )
    
    try:
        profiles = [ModelProfile(**m.model_dump()) for m in models]
        inserted_count = registry.register_models_batch(profiles)
        
        logger.info(f"Batch registration: {inserted_count}/{len(models)} models by admin")
        return {
            "status": "completed",
            "requested": len(models),
            "inserted": inserted_count,
            "skipped": len(models) - inserted_count
        }
    except ValidationError as e:
        logger.warning(f"Validation error in batch: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except ModelRegistryError as e:
        logger.error(f"Registry error in batch: {e}")
        raise HTTPException(status_code=500, detail="Internal registry error")
    except Exception as e:
        logger.error(f"Unexpected error in batch registration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

app.include_router(pcr_router)

from src.api.gateway_router import router as gateway_router
app.include_router(gateway_router)

from src.api.compliance_router import router as compliance_router
app.include_router(compliance_router)

if __name__ == "__main__":
    import uvicorn
    
    # ✅ Production-ready Uvicorn configuration
    uvicorn.run(
        "model_registry_api:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True,
        workers=4,  # Multiple workers for production
        limit_concurrency=100,  # Prevent overload
        timeout_keep_alive=30
    )
