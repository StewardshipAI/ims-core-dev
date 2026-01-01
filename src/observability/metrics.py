"""
IMS Observability - Prometheus Metrics

Exposes application metrics in Prometheus format for monitoring and alerting.

Key Metrics:
- Request latency histograms (by model, vendor)
- Error rates (by type, service)
- Model usage counters (by tier, vendor)
- Cost tracking (actual vs estimated)
- Cache hit rates
- Queue depths

Design Principles:
- Standard Prometheus naming conventions
- Cardinality awareness (avoid label explosion)
- Performance-first (metrics add <1ms overhead)
"""

from prometheus_client import (
    Counter, Histogram, Gauge, Summary,
    CollectorRegistry, generate_latest,
    CONTENT_TYPE_LATEST
)
from typing import Dict, List, Optional
from enum import Enum


# Standard Prometheus label sets
VENDOR_LABELS = ['vendor', 'model']
TIER_LABELS = ['capability_tier']
ERROR_LABELS = ['error_type', 'service']
POLICY_LABELS = ['policy_name', 'action']


class MetricsRegistry:
    """
    Centralized metrics registry for IMS observability.
    
    Provides type-safe metric definitions and helper methods for recording
    common IMS operations.
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialize metrics registry.
        
        Args:
            registry: Custom Prometheus registry (defaults to global)
        """
        self.registry = registry or CollectorRegistry()
        
        # === Request Metrics ===
        self.request_duration = Histogram(
            'ims_request_duration_seconds',
            'Request duration in seconds',
            ['service', 'vendor', 'model'],
            registry=self.registry,
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )
        
        self.request_total = Counter(
            'ims_requests_total',
            'Total number of requests',
            ['service', 'vendor', 'model', 'status'],
            registry=self.registry
        )
        
        # === Model Selection Metrics ===
        self.model_selections = Counter(
            'ims_model_selections_total',
            'Total model selections by Smart Router',
            ['model_id', 'capability_tier', 'reason'],
            registry=self.registry
        )
        
        self.model_fallbacks = Counter(
            'ims_model_fallbacks_total',
            'Total model fallback attempts',
            ['from_model', 'to_model', 'reason'],
            registry=self.registry
        )
        
        # === Error Metrics ===
        self.errors_total = Counter(
            'ims_errors_total',
            'Total errors by type and service',
            ERROR_LABELS,
            registry=self.registry
        )
        
        self.api_errors = Counter(
            'ims_api_errors_total',
            'Total API errors by vendor',
            ['vendor', 'model', 'error_code'],
            registry=self.registry
        )
        
        # === Cost Tracking ===
        self.cost_actual = Counter(
            'ims_cost_actual_usd',
            'Actual cost incurred (USD)',
            ['vendor', 'model', 'cost_type'],
            registry=self.registry
        )
        
        self.cost_estimated = Counter(
            'ims_cost_estimated_usd',
            'Estimated cost (USD)',
            ['vendor', 'model'],
            registry=self.registry
        )
        
        self.cost_drift = Histogram(
            'ims_cost_drift_percentage',
            'Cost estimation drift (actual - estimated) / estimated * 100',
            ['vendor', 'model'],
            registry=self.registry,
            buckets=[-50, -25, -10, -5, 0, 5, 10, 25, 50, 100]
        )
        
        # === Token Metrics ===
        self.tokens_processed = Counter(
            'ims_tokens_processed_total',
            'Total tokens processed',
            ['vendor', 'model', 'token_type'],
            registry=self.registry
        )
        
        # === Cache Metrics ===
        self.cache_hits = Counter(
            'ims_cache_hits_total',
            'Total cache hits',
            ['cache_type'],
            registry=self.registry
        )
        
        self.cache_misses = Counter(
            'ims_cache_misses_total',
            'Total cache misses',
            ['cache_type'],
            registry=self.registry
        )
        
        self.cache_size = Gauge(
            'ims_cache_size_bytes',
            'Current cache size in bytes',
            ['cache_type'],
            registry=self.registry
        )
        
        # === Policy Enforcement Metrics ===
        self.policy_evaluations = Counter(
            'ims_policy_evaluations_total',
            'Total policy evaluations',
            POLICY_LABELS,
            registry=self.registry
        )
        
        self.policy_violations = Counter(
            'ims_policy_violations_total',
            'Total policy violations',
            ['policy_name', 'action', 'bypass_used'],
            registry=self.registry
        )
        
        # === Queue Metrics ===
        self.queue_depth = Gauge(
            'ims_queue_depth',
            'Current queue depth',
            ['queue_name'],
            registry=self.registry
        )
        
        self.queue_processing_time = Histogram(
            'ims_queue_processing_seconds',
            'Time spent processing queue items',
            ['queue_name'],
            registry=self.registry,
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
        )
        
        # === Health Metrics ===
        self.health_status = Gauge(
            'ims_health_status',
            'Service health status (1=healthy, 0=unhealthy)',
            ['service'],
            registry=self.registry
        )
        
        # === Model Performance Metrics ===
        self.model_success_rate = Gauge(
            'ims_model_success_rate',
            'Model success rate (0-1)',
            ['vendor', 'model'],
            registry=self.registry
        )
    
    # === Helper Methods ===
    
    def record_request(self, service: str, vendor: str, model: str, 
                      duration_seconds: float, success: bool) -> None:
        """
        Record a request with duration and status.
        
        Args:
            service: Service name (e.g., "action_gateway")
            vendor: Vendor name (e.g., "openai")
            model: Model ID (e.g., "gpt-4")
            duration_seconds: Request duration
            success: Whether request succeeded
        """
        status = "success" if success else "error"
        self.request_duration.labels(
            service=service, vendor=vendor, model=model
        ).observe(duration_seconds)
        
        self.request_total.labels(
            service=service, vendor=vendor, model=model, status=status
        ).inc()
    
    def record_model_selection(self, model_id: str, tier: str, reason: str) -> None:
        """Record a model selection by Smart Router."""
        self.model_selections.labels(
            model_id=model_id,
            capability_tier=tier,
            reason=reason
        ).inc()
    
    def record_fallback(self, from_model: str, to_model: str, reason: str) -> None:
        """Record a model fallback attempt."""
        self.model_fallbacks.labels(
            from_model=from_model,
            to_model=to_model,
            reason=reason
        ).inc()
    
    def record_error(self, error_type: str, service: str) -> None:
        """Record an error occurrence."""
        self.errors_total.labels(
            error_type=error_type,
            service=service
        ).inc()
    
    def record_api_error(self, vendor: str, model: str, error_code: str) -> None:
        """Record an API-specific error."""
        self.api_errors.labels(
            vendor=vendor,
            model=model,
            error_code=error_code
        ).inc()
    
    def record_cost(self, vendor: str, model: str, actual_cost: float, 
                   estimated_cost: float, cost_type: str = "combined") -> None:
        """
        Record cost metrics with drift calculation.
        
        Args:
            vendor: Vendor name
            model: Model ID
            actual_cost: Actual cost incurred (USD)
            estimated_cost: Pre-calculated estimated cost (USD)
            cost_type: "input", "output", or "combined"
        """
        # Record actual cost
        self.cost_actual.labels(
            vendor=vendor,
            model=model,
            cost_type=cost_type
        ).inc(actual_cost)
        
        # Record estimated cost
        self.cost_estimated.labels(
            vendor=vendor,
            model=model
        ).inc(estimated_cost)
        
        # Calculate and record drift
        if estimated_cost > 0:
            drift_pct = ((actual_cost - estimated_cost) / estimated_cost) * 100
            self.cost_drift.labels(
                vendor=vendor,
                model=model
            ).observe(drift_pct)
    
    def record_tokens(self, vendor: str, model: str, input_tokens: int, 
                     output_tokens: int) -> None:
        """Record token usage."""
        self.tokens_processed.labels(
            vendor=vendor,
            model=model,
            token_type="input"
        ).inc(input_tokens)
        
        self.tokens_processed.labels(
            vendor=vendor,
            model=model,
            token_type="output"
        ).inc(output_tokens)
    
    def record_cache_access(self, cache_type: str, hit: bool) -> None:
        """Record cache hit or miss."""
        if hit:
            self.cache_hits.labels(cache_type=cache_type).inc()
        else:
            self.cache_misses.labels(cache_type=cache_type).inc()
    
    def set_cache_size(self, cache_type: str, size_bytes: int) -> None:
        """Update cache size gauge."""
        self.cache_size.labels(cache_type=cache_type).set(size_bytes)
    
    def record_policy_evaluation(self, policy_name: str, action: str, 
                                 violation: bool, bypass_used: bool = False) -> None:
        """
        Record policy evaluation and potential violation.
        
        Args:
            policy_name: Name of evaluated policy
            action: Action taken (ALLOW, BLOCK, DEGRADE, WARN)
            violation: Whether policy was violated
            bypass_used: Whether user used bypass flag
        """
        self.policy_evaluations.labels(
            policy_name=policy_name,
            action=action
        ).inc()
        
        if violation:
            self.policy_violations.labels(
                policy_name=policy_name,
                action=action,
                bypass_used=str(bypass_used).lower()
            ).inc()
    
    def set_queue_depth(self, queue_name: str, depth: int) -> None:
        """Update queue depth gauge."""
        self.queue_depth.labels(queue_name=queue_name).set(depth)
    
    def record_queue_processing(self, queue_name: str, duration_seconds: float) -> None:
        """Record queue item processing time."""
        self.queue_processing_time.labels(queue_name=queue_name).observe(duration_seconds)
    
    def set_health(self, service: str, healthy: bool) -> None:
        """Update service health status."""
        self.health_status.labels(service=service).set(1 if healthy else 0)
    
    def update_model_success_rate(self, vendor: str, model: str, rate: float) -> None:
        """
        Update model success rate (0-1).
        
        Should be called periodically based on recent request history.
        """
        self.model_success_rate.labels(vendor=vendor, model=model).set(rate)
    
    def export_metrics(self) -> bytes:
        """
        Export metrics in Prometheus text format.
        
        Returns:
            Prometheus-formatted metrics
        """
        return generate_latest(self.registry)
    
    def get_content_type(self) -> str:
        """Get Prometheus content type for HTTP response."""
        return CONTENT_TYPE_LATEST


# Global metrics instance (singleton pattern)
_metrics_instance: Optional[MetricsRegistry] = None


def get_metrics() -> MetricsRegistry:
    """
    Get global metrics registry instance.
    
    Returns:
        MetricsRegistry singleton
    
    Example:
        >>> metrics = get_metrics()
        >>> metrics.record_request("gateway", "openai", "gpt-4", 1.5, True)
    """
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MetricsRegistry()
    return _metrics_instance


def reset_metrics() -> None:
    """Reset global metrics instance (useful for testing)."""
    global _metrics_instance
    _metrics_instance = None


# Cardinality Warnings
"""
CARDINALITY MANAGEMENT:

High-cardinality labels can cause memory issues in Prometheus. Guidelines:

LOW CARDINALITY (Safe - <100 unique values):
- service, vendor, capability_tier, error_type, policy_name, action

MEDIUM CARDINALITY (Monitor - 100-1000 values):
- model (tracked in registry, ~50-200 models expected)
- error_code (HTTP codes, API errors)

HIGH CARDINALITY (DANGEROUS - >1000 values):
- trace_id, request_id, user_id (NEVER use as labels)
- timestamps, UUIDs, session IDs (NEVER use as labels)

For high-cardinality data, use:
1. Logs (with trace_id)
2. Traces (OpenTelemetry)
3. Aggregated metrics (e.g., count by hour, not by request)

Current implementation is safe (<10k unique label combinations expected).
"""


# Known Limitations
"""
KNOWN LIMITATIONS:

1. **Memory Usage**: Each unique label combination creates a new time series.
   With 50 models × 5 vendors × 4 tiers = 1000 series baseline.
   Mitigation: Periodic cleanup of unused series (not implemented).

2. **Performance**: Metric recording adds ~0.1ms overhead per operation.
   Mitigation: Use counters/gauges (fast) over summaries (slower).

3. **Prometheus Scraping**: Metrics endpoint must be exposed via HTTP.
   Current implementation returns raw bytes - integration needed.
   Mitigation: Add /metrics endpoint in FastAPI app (Epic 5 task).

4. **Historical Data**: Prometheus default retention is 15 days.
   Mitigation: Configure longer retention or use Thanos/Cortex for long-term storage.

5. **Cost Drift Calculation**: Assumes cost is deterministic. Real-world costs
   may vary due to dynamic pricing, rate limit refunds, etc.
   Mitigation: Treat drift as directional signal, not absolute truth.

6. **No Exemplars**: Current implementation doesn't link metrics to traces.
   Mitigation: Future work - add exemplar support for detailed debugging.
"""