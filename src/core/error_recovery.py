"""
IMS Error Recovery Handler
===========================
Implements intelligent error recovery patterns:
- Rate limit fallback (switch models)
- Timeout retry (with exponential backoff)
- Context truncation (reduce input size)
- Graceful degradation
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from datetime import datetime, timedelta

from src.data.model_registry import ModelRegistry, ModelProfile, CapabilityTier
from src.core.pcr import RecommendationService, RecommendationRequest

logger = logging.getLogger("ims.error_recovery")


class ErrorType(Enum):
    """Classification of error types"""
    RATE_LIMIT = "rate_limit"          # 429 Too Many Requests
    TIMEOUT = "timeout"                 # Request timeout
    OVERLOAD = "overload"              # 503 Service Unavailable
    INVALID_REQUEST = "invalid"        # 400 Bad Request
    AUTHENTICATION = "auth"            # 401/403 Auth errors
    CONTEXT_OVERFLOW = "context"       # Context window exceeded
    UNKNOWN = "unknown"                # Unclassified errors


class RecoveryStrategy(Enum):
    """Available recovery strategies"""
    FALLBACK_MODEL = "fallback"        # Switch to different model
    RETRY_BACKOFF = "retry"            # Retry with exponential backoff
    TRUNCATE_CONTEXT = "truncate"      # Reduce input size
    DEGRADE_TIER = "degrade"           # Use lower-tier model
    FAIL_FAST = "fail"                 # Don't retry, fail immediately


class ErrorRecovery:
    """
    Handles error recovery for model execution failures.
    """
    
    def __init__(
        self,
        registry: ModelRegistry,
        recommendation_service: RecommendationService,
        max_retries: int = 3,
        base_backoff_ms: int = 1000
    ):
        self.registry = registry
        self.recommendation_service = recommendation_service
        self.max_retries = max_retries
        self.base_backoff_ms = base_backoff_ms
        
        # Track failures per model (for circuit breaker pattern)
        self._failure_counts: Dict[str, int] = {}
        self._circuit_open_until: Dict[str, datetime] = {}
    
    def classify_error(self, error: Exception) -> ErrorType:
        """
        Classify error type based on exception details.
        
        Args:
            error: The exception that occurred
            
        Returns:
            ErrorType classification
        """
        error_str = str(error).lower()
        
        if "429" in error_str or "rate limit" in error_str:
            return ErrorType.RATE_LIMIT
        elif "timeout" in error_str:
            return ErrorType.TIMEOUT
        elif "503" in error_str or "overload" in error_str:
            return ErrorType.OVERLOAD
        elif "400" in error_str or "invalid" in error_str:
            return ErrorType.INVALID_REQUEST
        elif "401" in error_str or "403" in error_str or "auth" in error_str:
            return ErrorType.AUTHENTICATION
        elif "context" in error_str or "token limit" in error_str:
            return ErrorType.CONTEXT_OVERFLOW
        else:
            return ErrorType.UNKNOWN
    
    def choose_strategy(self, error_type: ErrorType) -> RecoveryStrategy:
        """
        Choose appropriate recovery strategy based on error type.
        
        Args:
            error_type: Classification of the error
            
        Returns:
            Recommended recovery strategy
        """
        strategy_map = {
            ErrorType.RATE_LIMIT: RecoveryStrategy.FALLBACK_MODEL,
            ErrorType.TIMEOUT: RecoveryStrategy.RETRY_BACKOFF,
            ErrorType.OVERLOAD: RecoveryStrategy.FALLBACK_MODEL,
            ErrorType.CONTEXT_OVERFLOW: RecoveryStrategy.TRUNCATE_CONTEXT,
            ErrorType.INVALID_REQUEST: RecoveryStrategy.FAIL_FAST,
            ErrorType.AUTHENTICATION: RecoveryStrategy.FAIL_FAST,
            ErrorType.UNKNOWN: RecoveryStrategy.RETRY_BACKOFF
        }
        
        return strategy_map.get(error_type, RecoveryStrategy.FAIL_FAST)
    
    async def get_fallback_model(
        self,
        failed_model_id: str,
        original_requirements: Optional[RecommendationRequest] = None
    ) -> Optional[ModelProfile]:
        """
        Get alternative model when primary fails.
        
        Args:
            failed_model_id: Model that failed
            original_requirements: Original selection criteria
            
        Returns:
            Alternative model or None if none available
        """
        # Get failed model details
        failed_model = self.registry.get_model(failed_model_id)
        
        if not failed_model:
            logger.error(f"Failed model {failed_model_id} not found in registry")
            return None
        
        # Build fallback requirements
        if original_requirements:
            # Use original requirements but exclude failed model
            req = original_requirements
        else:
            # Create reasonable defaults based on failed model
            req = RecommendationRequest(
                min_capability_tier=failed_model.capability_tier,
                min_context_window=failed_model.context_window,
                strategy="cost"
            )
        
        # Get recommendations
        candidates = self.recommendation_service.recommend(req)
        
        # Filter out failed model and circuit-broken models
        now = datetime.utcnow()
        available = [
            m for m in candidates
            if m.model_id != failed_model_id
            and not self._is_circuit_open(m.model_id, now)
        ]
        
        if not available:
            logger.warning("No fallback models available")
            return None
        
        fallback = available[0]
        logger.info(f"Fallback: {failed_model_id} → {fallback.model_id}")
        
        return fallback
    
    async def execute_with_recovery(
        self,
        execution_fn: Callable,
        model_id: str,
        *args,
        fallback_chain: Optional[List[str]] = None,
        **kwargs
    ) -> Any:
        """
        Execute function with automatic error recovery.
        
        Args:
            execution_fn: Async function to execute
            model_id: Model being used
            *args: Positional args for execution_fn
            fallback_chain: Optional list of model IDs to try in order
            **kwargs: Keyword args for execution_fn
        """
        attempt = 0
        current_model_id = model_id
        last_error = None
        
        # Track models we've already tried to avoid loops
        tried_models = {current_model_id}
        
        # Local copy of fallback chain
        remaining_fallbacks = list(fallback_chain) if fallback_chain else []
        
        while attempt < self.max_retries:
            try:
                # Check circuit breaker
                if self._is_circuit_open(current_model_id):
                    logger.warning(f"Circuit open for {current_model_id}, switching to fallback")
                    
                    if remaining_fallbacks:
                        current_model_id = remaining_fallbacks.pop(0)
                    else:
                        fallback = await self.get_fallback_model(current_model_id)
                        if not fallback:
                            raise Exception("No fallback available and circuit is open")
                        current_model_id = fallback.model_id
                    
                    tried_models.add(current_model_id)
                
                # Attempt execution
                result = await execution_fn(current_model_id, *args, **kwargs)
                
                # Success! Reset failure count
                self._failure_counts[current_model_id] = 0
                
                return result
                
            except Exception as e:
                last_error = e
                attempt += 1
                
                # Increment failure count
                self._failure_counts[current_model_id] = (
                    self._failure_counts.get(current_model_id, 0) + 1
                )
                
                # Open circuit if too many failures
                if self._failure_counts[current_model_id] >= 3:
                    self._open_circuit(current_model_id)
                
                # Classify error and choose strategy
                error_type = self.classify_error(e)
                strategy = self.choose_strategy(error_type)
                
                logger.warning(
                    f"Attempt {attempt}/{self.max_retries} failed: "
                    f"{error_type.value} | Strategy: {strategy.value}"
                )
                
                # Execute recovery strategy
                if strategy == RecoveryStrategy.FAIL_FAST:
                    raise
                
                elif strategy == RecoveryStrategy.FALLBACK_MODEL:
                    if remaining_fallbacks:
                        current_model_id = remaining_fallbacks.pop(0)
                        logger.info(f"Using next model from fallback chain: {current_model_id}")
                    else:
                        fallback = await self.get_fallback_model(current_model_id)
                        if not fallback:
                            if attempt >= self.max_retries:
                                raise
                            strategy = RecoveryStrategy.RETRY_BACKOFF
                        else:
                            current_model_id = fallback.model_id
                    
                    tried_models.add(current_model_id)
                    continue  # Try with new model immediately
                
                if strategy == RecoveryStrategy.RETRY_BACKOFF:
                    # Exponential backoff
                    backoff_ms = self.base_backoff_ms * (2 ** (attempt - 1))
                    logger.info(f"Backing off for {backoff_ms}ms")
                    await asyncio.sleep(backoff_ms / 1000)
                
                elif strategy == RecoveryStrategy.TRUNCATE_CONTEXT:
                    # TODO: Implement context truncation
                    # For now, just retry with backoff
                    logger.warning("Context truncation not yet implemented, using backoff")
                    backoff_ms = self.base_backoff_ms * (2 ** (attempt - 1))
                    await asyncio.sleep(backoff_ms / 1000)
        
        # All retries exhausted
        raise Exception(
            f"All {self.max_retries} recovery attempts failed. "
            f"Last error: {last_error}"
        )
    
    def _is_circuit_open(
        self,
        model_id: str,
        now: Optional[datetime] = None
    ) -> bool:
        """Check if circuit breaker is open for model"""
        if now is None:
            now = datetime.utcnow()
        
        open_until = self._circuit_open_until.get(model_id)
        
        if not open_until:
            return False
        
        if now >= open_until:
            # Circuit has recovered
            del self._circuit_open_until[model_id]
            self._failure_counts[model_id] = 0
            logger.info(f"Circuit recovered for {model_id}")
            return False
        
        return True
    
    def _open_circuit(self, model_id: str, duration_seconds: int = 60) -> None:
        """Open circuit breaker for model"""
        open_until = datetime.utcnow() + timedelta(seconds=duration_seconds)
        self._circuit_open_until[model_id] = open_until
        
        logger.warning(
            f"Circuit opened for {model_id} "
            f"(will retry after {duration_seconds}s)"
        )
    
    def get_circuit_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status for all models"""
        now = datetime.utcnow()
        
        return {
            model_id: {
                "failures": self._failure_counts.get(model_id, 0),
                "circuit_open": self._is_circuit_open(model_id, now),
                "open_until": (
                    self._circuit_open_until[model_id].isoformat()
                    if model_id in self._circuit_open_until
                    else None
                )
            }
            for model_id in set(
                list(self._failure_counts.keys()) + 
                list(self._circuit_open_until.keys())
            )
        }
