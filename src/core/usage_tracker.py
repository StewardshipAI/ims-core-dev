"""
IMS Usage Tracker
=================
Tracks token usage, costs, and performance metrics for model executions.
Emits telemetry events to RabbitMQ for observability.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import uuid4

from src.core.events import EventPublisher, CloudEvent

logger = logging.getLogger("ims.usage_tracker")


class UsageMetrics:
    """Container for usage metrics"""
    
    def __init__(
        self,
        model_id: str,
        vendor_id: str,
        tokens_in: int,
        tokens_out: int,
        cost_in: float,
        cost_out: float,
        latency_ms: int,
        success: bool,
        error: Optional[str] = None
    ):
        self.model_id = model_id
        self.vendor_id = vendor_id
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.cost_in = cost_in
        self.cost_out = cost_out
        self.latency_ms = latency_ms
        self.success = success
        self.error = error
        self.timestamp = datetime.utcnow()
    
    @property
    def total_tokens(self) -> int:
        return self.tokens_in + self.tokens_out
    
    @property
    def total_cost(self) -> float:
        return self.cost_in + self.cost_out
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "vendor_id": self.vendor_id,
            "tokens": {
                "input": self.tokens_in,
                "output": self.tokens_out,
                "total": self.total_tokens
            },
            "cost": {
                "input": self.cost_in,
                "output": self.cost_out,
                "total": self.total_cost
            },
            "latency_ms": self.latency_ms,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }


class UsageTracker:
    """
    Tracks and logs model usage metrics.
    Emits telemetry events for observability.
    """
    
    def __init__(self, publisher: EventPublisher):
        self.publisher = publisher
        self._session_stats = {
            "requests": 0,
            "tokens": 0,
            "cost": 0.0,
            "failures": 0
        }
    
    async def log_execution(
        self,
        model_id: str,
        vendor_id: str,
        tokens_in: int,
        tokens_out: int,
        cost_per_mil_in: float,
        cost_per_mil_out: float,
        latency_ms: int,
        success: bool = True,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Log a model execution and emit telemetry.
        
        Args:
            model_id: Model identifier
            vendor_id: Vendor/provider name
            tokens_in: Input tokens consumed
            tokens_out: Output tokens generated
            cost_per_mil_in: Cost per 1M input tokens
            cost_per_mil_out: Cost per 1M output tokens
            latency_ms: Request latency in milliseconds
            success: Whether execution succeeded
            error: Error message if failed
            correlation_id: Optional correlation ID for tracing
        """
        # Calculate costs
        cost_in = (tokens_in / 1_000_000) * cost_per_mil_in
        cost_out = (tokens_out / 1_000_000) * cost_per_mil_out
        
        # Create metrics object
        metrics = UsageMetrics(
            model_id=model_id,
            vendor_id=vendor_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_in=cost_in,
            cost_out=cost_out,
            latency_ms=latency_ms,
            success=success,
            error=error
        )
        
        # Update session stats
        self._session_stats["requests"] += 1
        self._session_stats["tokens"] += metrics.total_tokens
        self._session_stats["cost"] += metrics.total_cost
        
        if not success:
            self._session_stats["failures"] += 1
        
        # Log locally
        logger.info(
            f"Model execution: {model_id} | "
            f"Tokens: {metrics.total_tokens} | "
            f"Cost: ${metrics.total_cost:.6f} | "
            f"Latency: {latency_ms}ms | "
            f"Success: {success}"
        )
        
        # Emit telemetry event
        event = CloudEvent(
            source="/usage-tracker",
            type="model.executed",
            correlation_id=correlation_id or str(uuid4()),
            data=metrics.to_dict()
        )
        
        try:
            await self.publisher.publish(event)
            logger.debug(f"Usage event emitted for {model_id}")
        except Exception as e:
            logger.error(f"Failed to emit usage event: {e}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get cumulative stats for current session"""
        return {
            **self._session_stats,
            "success_rate": (
                (self._session_stats["requests"] - self._session_stats["failures"]) 
                / self._session_stats["requests"]
            ) if self._session_stats["requests"] > 0 else 1.0
        }
    
    def reset_session_stats(self) -> None:
        """Reset session statistics"""
        self._session_stats = {
            "requests": 0,
            "tokens": 0,
            "cost": 0.0,
            "failures": 0
        }
        logger.info("Session stats reset")


# FastAPI Dependency
_tracker_instance: Optional[UsageTracker] = None

def get_usage_tracker(publisher: EventPublisher) -> UsageTracker:
    """Get or create singleton UsageTracker instance"""
    global _tracker_instance
    
    if _tracker_instance is None:
        _tracker_instance = UsageTracker(publisher)
        logger.info("UsageTracker initialized")
    
    return _tracker_instance
