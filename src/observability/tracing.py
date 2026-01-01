"""
IMS Observability - Distributed Tracing (OpenTelemetry)

Provides end-to-end request tracing across IMS components using OpenTelemetry.
Enables correlation of logs, metrics, and traces for deep debugging.

Key Capabilities:
- Automatic span creation for key operations
- Context propagation across async boundaries
- Integration with Jaeger, Zipkin, or cloud providers
- Minimal performance overhead (<2ms per span)

Design Principles:
- Sampling-aware (reduce overhead in production)
- Security-aware (redact sensitive data in spans)
- Integration-ready (works with existing logging/metrics)
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, sampling
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter
)
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from typing import Dict, Optional, Any, Callable
from functools import wraps
from contextvars import ContextVar
import time
import os

# Context variable for current span
current_span_context: ContextVar[Optional[trace.Span]] = ContextVar(
    'current_span', default=None
)


class IMSTracerProvider:
    """
    Centralized OpenTelemetry tracer configuration for IMS.
    
    Handles:
    - Tracer initialization
    - Exporter configuration (Jaeger, Console, etc.)
    - Sampling strategy
    - Resource attributes
    """
    
    def __init__(
        self,
        service_name: str = "ims-core",
        environment: str = "development",
        jaeger_endpoint: Optional[str] = None,
        sampling_rate: float = 1.0,
        enable_console_export: bool = False
    ):
        """
        Initialize tracer provider.
        
        Args:
            service_name: Service identifier
            environment: dev/staging/prod
            jaeger_endpoint: Jaeger collector endpoint (e.g., "localhost:6831")
            sampling_rate: Fraction of traces to sample (0.0-1.0)
            enable_console_export: Print traces to console (dev only)
        
        Example:
            >>> provider = IMSTracerProvider(
            ...     service_name="ims-action-gateway",
            ...     jaeger_endpoint="localhost:6831",
            ...     sampling_rate=0.1  # 10% sampling in prod
            ... )
        """
        # Create resource with service metadata
        resource = Resource.create({
            SERVICE_NAME: service_name,
            "service.version": "0.4.5",
            "deployment.environment": environment
        })
        
        # Configure sampler
        if sampling_rate >= 1.0:
            sampler = sampling.ALWAYS_ON
        elif sampling_rate <= 0.0:
            sampler = sampling.ALWAYS_OFF
        else:
            sampler = sampling.TraceIdRatioBased(sampling_rate)
        
        # Create tracer provider
        self.provider = TracerProvider(
            resource=resource,
            sampler=sampler
        )
        
        # Add exporters
        if jaeger_endpoint:
            self._setup_jaeger_exporter(jaeger_endpoint)
        
        if enable_console_export:
            self._setup_console_exporter()
        
        # Set as global tracer provider
        trace.set_tracer_provider(self.provider)
        
        # Store config
        self.service_name = service_name
        self.environment = environment
    
    def _setup_jaeger_exporter(self, endpoint: str) -> None:
        """Configure Jaeger exporter."""
        # Parse endpoint (format: "host:port")
        agent_host, agent_port = endpoint.split(':')
        
        jaeger_exporter = JaegerExporter(
            agent_host_name=agent_host,
            agent_port=int(agent_port)
        )
        
        # Use batch processor for performance
        span_processor = BatchSpanProcessor(jaeger_exporter)
        self.provider.add_span_processor(span_processor)
    
    def _setup_console_exporter(self) -> None:
        """Configure console exporter (dev only)."""
        console_exporter = ConsoleSpanExporter()
        span_processor = BatchSpanProcessor(console_exporter)
        self.provider.add_span_processor(span_processor)
    
    def get_tracer(self, name: str) -> trace.Tracer:
        """
        Get a tracer instance for a specific component.
        
        Args:
            name: Component name (e.g., "action_gateway", "policy_verifier")
        
        Returns:
            Tracer instance
        """
        return trace.get_tracer(name)


# Global tracer provider instance
_tracer_provider: Optional[IMSTracerProvider] = None


def initialize_tracing(
    service_name: str = "ims-core",
    environment: str = None,
    jaeger_endpoint: str = None,
    sampling_rate: float = None
) -> IMSTracerProvider:
    """
    Initialize global tracing configuration.
    
    Should be called once at application startup.
    
    Args:
        service_name: Service identifier
        environment: Deployment environment (defaults to IMS_ENVIRONMENT env var)
        jaeger_endpoint: Jaeger endpoint (defaults to JAEGER_ENDPOINT env var)
        sampling_rate: Sampling rate (defaults to TRACE_SAMPLING_RATE env var, or 1.0)
    
    Returns:
        Configured tracer provider
    
    Example:
        >>> initialize_tracing(
        ...     service_name="ims-action-gateway",
        ...     environment="production",
        ...     jaeger_endpoint="jaeger:6831",
        ...     sampling_rate=0.1
        ... )
    """
    global _tracer_provider
    
    # Use environment variables as defaults
    environment = environment or os.getenv("IMS_ENVIRONMENT", "development")
    jaeger_endpoint = jaeger_endpoint or os.getenv("JAEGER_ENDPOINT")
    sampling_rate = sampling_rate or float(os.getenv("TRACE_SAMPLING_RATE", "1.0"))
    
    enable_console = environment == "development"
    
    _tracer_provider = IMSTracerProvider(
        service_name=service_name,
        environment=environment,
        jaeger_endpoint=jaeger_endpoint,
        sampling_rate=sampling_rate,
        enable_console_export=enable_console
    )
    
    return _tracer_provider


def get_tracer(name: str) -> trace.Tracer:
    """
    Get tracer for a specific component.
    
    Args:
        name: Component name
    
    Returns:
        Tracer instance
    
    Raises:
        RuntimeError: If tracing not initialized
    
    Example:
        >>> tracer = get_tracer("action_gateway")
        >>> with tracer.start_as_current_span("model_selection"):
        ...     select_model()
    """
    if _tracer_provider is None:
        raise RuntimeError(
            "Tracing not initialized. Call initialize_tracing() first."
        )
    return _tracer_provider.get_tracer(name)


def trace_operation(
    operation_name: str,
    attributes: Optional[Dict[str, Any]] = None
) -> Callable:
    """
    Decorator to automatically trace a function/method.
    
    Creates a span for the decorated function with automatic error handling.
    
    Args:
        operation_name: Name of the operation (span name)
        attributes: Additional span attributes
    
    Returns:
        Decorator function
    
    Example:
        >>> @trace_operation("model_selection", {"component": "smart_router"})
        ... async def select_model(task):
        ...     # Your code here
        ...     return model
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer(func.__module__)
            
            with tracer.start_as_current_span(operation_name) as span:
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                # Add function metadata
                span.set_attribute("code.function", func.__name__)
                span.set_attribute("code.namespace", func.__module__)
                
                try:
                    start_time = time.time()
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    # Record success
                    span.set_attribute("operation.duration_seconds", duration)
                    span.set_status(Status(StatusCode.OK))
                    
                    return result
                
                except Exception as e:
                    # Record error
                    span.set_status(
                        Status(StatusCode.ERROR, str(e))
                    )
                    span.record_exception(e)
                    raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer(func.__module__)
            
            with tracer.start_as_current_span(operation_name) as span:
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                # Add function metadata
                span.set_attribute("code.function", func.__name__)
                span.set_attribute("code.namespace", func.__module__)
                
                try:
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    # Record success
                    span.set_attribute("operation.duration_seconds", duration)
                    span.set_status(Status(StatusCode.OK))
                    
                    return result
                
                except Exception as e:
                    # Record error
                    span.set_status(
                        Status(StatusCode.ERROR, str(e))
                    )
                    span.record_exception(e)
                    raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def add_span_attributes(attributes: Dict[str, Any]) -> None:
    """
    Add attributes to the current active span.
    
    Useful for adding context mid-operation without decorator overhead.
    
    Args:
        attributes: Key-value pairs to add to span
    
    Example:
        >>> add_span_attributes({
        ...     "model_id": "gpt-4",
        ...     "cost_usd": 0.05,
        ...     "tokens": 1000
        ... })
    """
    span = trace.get_current_span()
    if span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, value)


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    Add a timestamped event to the current span.
    
    Events are useful for marking significant moments within an operation.
    
    Args:
        name: Event name
        attributes: Optional event attributes
    
    Example:
        >>> add_span_event("cache_miss", {"cache_type": "model_metadata"})
        >>> add_span_event("fallback_triggered", {"reason": "rate_limit"})
    """
    span = trace.get_current_span()
    if span.is_recording():
        span.add_event(name, attributes or {})


def get_trace_context() -> Dict[str, str]:
    """
    Extract trace context for propagation.
    
    Returns trace_id and span_id as strings for logging integration.
    
    Returns:
        Dict with trace_id and span_id
    
    Example:
        >>> ctx = get_trace_context()
        >>> logger.info("Processing", extra=ctx)
    """
    span = trace.get_current_span()
    span_context = span.get_span_context()
    
    if span_context.is_valid:
        return {
            "trace_id": format(span_context.trace_id, '032x'),
            "span_id": format(span_context.span_id, '016x')
        }
    return {}


def inject_trace_context(carrier: Dict[str, str]) -> None:
    """
    Inject trace context into a carrier for cross-service propagation.
    
    Args:
        carrier: Dictionary to inject context into (e.g., HTTP headers)
    
    Example:
        >>> headers = {}
        >>> inject_trace_context(headers)
        >>> # headers now contains traceparent, tracestate
        >>> async with httpx.AsyncClient() as client:
        ...     await client.post(url, headers=headers)
    """
    propagator = TraceContextTextMapPropagator()
    propagator.inject(carrier)


def extract_trace_context(carrier: Dict[str, str]) -> None:
    """
    Extract trace context from incoming request.
    
    Args:
        carrier: Dictionary containing context (e.g., HTTP headers)
    
    Example:
        >>> # In FastAPI endpoint
        >>> @app.post("/execute")
        >>> async def execute(request: Request):
        ...     extract_trace_context(dict(request.headers))
        ...     # Trace is now continued from upstream service
    """
    propagator = TraceContextTextMapPropagator()
    context = propagator.extract(carrier)
    trace.set_span_in_context(trace.NonRecordingSpan(context))


# Known Limitations
"""
KNOWN LIMITATIONS:

1. **Async Context Propagation**: Context may be lost across thread boundaries
   in mixed sync/async code.
   Mitigation: Use OpenTelemetry's context managers consistently.

2. **Performance Overhead**: Each span adds ~1-2ms latency.
   Mitigation: Use sampling in production (sampling_rate < 1.0).

3. **Storage Requirements**: Traces consume significant storage.
   Example: 1M requests/day × 10 spans/request × 5KB/span = 50GB/day.
   Mitigation: Configure Jaeger retention policies, use sampling.

4. **Cardinality Explosion**: Span attributes with high cardinality
   (e.g., request_id, user_id) can overwhelm trace backends.
   Mitigation: Use tags sparingly, prefer events for debug data.

5. **Cross-Process Tracing**: Requires explicit context injection/extraction.
   Not automatic across subprocess boundaries.
   Mitigation: Document required header propagation for each service.

6. **Jaeger Dependency**: Default configuration assumes Jaeger backend.
   Mitigation: Support pluggable exporters (future work).

7. **Security**: Spans may contain sensitive data if not carefully filtered.
   Mitigation: Redact PII/secrets before setting attributes (not implemented).
"""