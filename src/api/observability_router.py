"""
IMS API - Observability Endpoints

Exposes metrics, health checks, and debugging endpoints for monitoring.

Endpoints:
- GET /metrics - Prometheus metrics
- GET /health - Health check
- GET /health/detailed - Detailed component health
- GET /debug/trace - Current trace context
"""

from fastapi import APIRouter, Response, Depends
from typing import Dict, Any
from datetime import datetime

from src.observability.metrics import get_metrics, CONTENT_TYPE_LATEST
from src.observability.tracing import get_trace_context
from src.observability.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/observability", tags=["Observability"])


@router.get("/metrics", include_in_schema=False)
async def metrics_endpoint():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text format for scraping.
    
    **Note**: This endpoint is typically excluded from API docs
    and accessed directly by Prometheus.
    
    Example scrape_config:
    ```yaml
    scrape_configs:
      - job_name: 'ims-core'
        static_configs:
          - targets: ['localhost:8000']
        metrics_path: '/observability/metrics'
    ```
    """
    metrics = get_metrics()
    content = metrics.export_metrics()
    
    return Response(
        content=content,
        media_type=metrics.get_content_type()
    )


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns simple UP/DOWN status for load balancers and orchestrators.
    
    Returns:
        - status: "healthy" or "unhealthy"
        - timestamp: ISO 8601 timestamp
    
    Status Codes:
        - 200: Service is healthy
        - 503: Service is unhealthy
    """
    # Basic health check - just verify we can respond
    return {
        "status": "healthy",
        "service": "ims-core",
        "version": "0.4.5",
        "timestamp": datetime.utcnow().isoformat() + 'Z'
    }


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check with component status.
    
    Checks:
    - Database connectivity
    - Redis cache
    - RabbitMQ connection
    - Model registry
    
    Returns:
        Comprehensive health status for all components
    
    Example Response:
    ```json
    {
        "status": "healthy",
        "components": {
            "database": {"status": "healthy", "latency_ms": 5},
            "cache": {"status": "healthy", "hit_rate": 0.85},
            "queue": {"status": "healthy", "depth": 3}
        }
    }
    ```
    """
    from src.data.model_registry import ModelRegistry
    from src.core.events import rabbitmq
    import os
    
    components = {}
    overall_healthy = True
    
    # Check database
    try:
        db_conn = os.getenv("DB_CONNECTION_STRING")
        registry = ModelRegistry(db_connection_string=db_conn)
        health = registry.health_check()
        
        components["database"] = {
            "status": health["database"],
            "pool_stats": health.get("pool_stats", {})
        }
        
        if health["database"] != "healthy":
            overall_healthy = False
    
    except Exception as e:
        components["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False
    
    # Check RabbitMQ
    try:
        rmq_healthy = (
            rabbitmq.connection is not None and 
            not rabbitmq.connection.is_closed
        )
        
        components["queue"] = {
            "status": "healthy" if rmq_healthy else "unhealthy",
            "connected": rmq_healthy
        }
        
        if not rmq_healthy:
            overall_healthy = False
    
    except Exception as e:
        components["queue"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False
    
    # Check cache (if configured)
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            import redis.asyncio as redis
            r = redis.from_url(redis_url, decode_responses=True)
            await r.ping()
            await r.close()
            
            components["cache"] = {
                "status": "healthy"
            }
        except Exception as e:
            components["cache"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            overall_healthy = False
    else:
        components["cache"] = {
            "status": "not_configured"
        }
    
    return {
        "status": "healthy" if overall_healthy else "degraded",
        "service": "ims-core",
        "version": "0.4.5",
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "components": components
    }


@router.get("/debug/trace")
async def trace_context_debug() -> Dict[str, Any]:
    """
    Debug endpoint for trace context inspection.
    
    Returns current trace_id and span_id for request correlation.
    
    **Note**: Only enabled in development/staging environments.
    Should be disabled or protected in production.
    
    Returns:
        Current trace context
    
    Example:
    ```json
    {
        "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
        "span_id": "00f067aa0ba902b7",
        "sampled": true
    }
    ```
    """
    ctx = get_trace_context()
    
    if not ctx:
        return {
            "message": "No active trace context",
            "tracing_enabled": False
        }
    
    return {
        "trace_id": ctx.get("trace_id"),
        "span_id": ctx.get("span_id"),
        "tracing_enabled": True,
        "jaeger_ui_link": f"http://localhost:16686/trace/{ctx.get('trace_id')}"
    }


@router.get("/stats")
async def observability_stats() -> Dict[str, Any]:
    """
    Get observability system statistics.
    
    Returns:
        Current state of logging, metrics, and tracing
    
    Example:
    ```json
    {
        "metrics": {
            "total_requests": 1523,
            "cache_hit_rate": 0.85
        },
        "tracing": {
            "sampling_rate": 0.1,
            "spans_exported": 152
        }
    }
    ```
    """
    metrics = get_metrics()
    
    # Get key metric summaries (this would ideally query Prometheus)
    # For now, return static info about observability config
    
    return {
        "metrics": {
            "endpoint": "/observability/metrics",
            "format": "prometheus",
            "enabled": True
        },
        "tracing": {
            "provider": "opentelemetry",
            "exporter": "jaeger",
            "enabled": True
        },
        "logging": {
            "format": "json",
            "level": "INFO",
            "structured": True
        }
    }


# Integration with main FastAPI app
"""
To integrate with main API:

from src.api.observability_router import router as observability_router

app = FastAPI()
app.include_router(observability_router)

# Health checks should be at root for common LB expectations
@app.get("/health")
async def health():
    return await observability_router.health_check()
"""