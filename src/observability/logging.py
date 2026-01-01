"""
IMS Observability - Structured Logging

Provides JSON-formatted logging with context propagation for distributed tracing.
Supports both human-readable (dev) and machine-parseable (prod) formats.

Design Principles:
- Structured logs (JSON) for production
- Human-readable for development
- Context propagation (trace_id, span_id)
- Security-aware (redact sensitive data)
- Performance-aware (async logging)
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar
from pythonjsonlogger import jsonlogger

# Context variables for distributed tracing
trace_context: ContextVar[Dict[str, str]] = ContextVar('trace_context', default={})


class SecurityRedactingFilter(logging.Filter):
    """
    Redact sensitive information from logs.
    
    CRITICAL: Prevents API keys, tokens, and PII from appearing in logs.
    """
    
    REDACT_KEYS = {
        'api_key', 'apikey', 'api-key',
        'password', 'passwd', 'pwd',
        'secret', 'token', 'auth',
        'credit_card', 'ssn', 'email'
    }
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Redact sensitive fields from log record."""
        if hasattr(record, 'msg') and isinstance(record.msg, dict):
            record.msg = self._redact_dict(record.msg)
        
        if hasattr(record, 'args') and isinstance(record.args, dict):
            record.args = self._redact_dict(record.args)
        
        return True
    
    def _redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact sensitive keys."""
        redacted = {}
        for key, value in data.items():
            if any(pattern in key.lower() for pattern in self.REDACT_KEYS):
                redacted[key] = "***REDACTED***"
            elif isinstance(value, dict):
                redacted[key] = self._redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [
                    self._redact_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                redacted[key] = value
        return redacted


class IMSJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter with IMS-specific fields.
    
    Adds:
    - timestamp (ISO 8601)
    - trace_id (from context)
    - span_id (from context)
    - service_name
    - environment
    """
    
    def __init__(self, *args, service_name: str = "ims-core", 
                 environment: str = "development", **kwargs):
        self.service_name = service_name
        self.environment = environment
        super().__init__(*args, **kwargs)
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, 
                   message_dict: Dict[str, Any]) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # Add service metadata
        log_record['service'] = self.service_name
        log_record['environment'] = self.environment
        
        # Add trace context
        ctx = trace_context.get()
        if ctx:
            log_record['trace_id'] = ctx.get('trace_id')
            log_record['span_id'] = ctx.get('span_id')
        
        # Add level name (not just number)
        log_record['level'] = record.levelname
        
        # Add source location
        log_record['source'] = {
            'file': record.pathname,
            'line': record.lineno,
            'function': record.funcName
        }


class HumanReadableFormatter(logging.Formatter):
    """
    Development-friendly formatter with color and structure.
    
    Example output:
    2025-12-31 10:30:45 | INFO | action_gateway | Model selected: gpt-4 | trace_id=abc123
    """
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors and structure."""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Base format
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        base = f"{timestamp} | {color}{record.levelname:8}{reset} | {record.name:20} | {record.getMessage()}"
        
        # Add trace context if available
        ctx = trace_context.get()
        if ctx and ctx.get('trace_id'):
            base += f" | trace_id={ctx['trace_id'][:8]}"
        
        # Add exception info if present
        if record.exc_info:
            base += f"\n{self.formatException(record.exc_info)}"
        
        return base


def setup_logging(
    level: str = "INFO",
    format_type: str = "json",
    service_name: str = "ims-core",
    environment: str = "development"
) -> logging.Logger:
    """
    Configure root logger with IMS observability standards.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: "json" for production, "human" for development
        service_name: Service identifier for distributed systems
        environment: dev/staging/prod
    
    Returns:
        Configured root logger
    
    Example:
        >>> logger = setup_logging(level="INFO", format_type="json")
        >>> logger.info("Service started", extra={"version": "0.4.5"})
    """
    
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    
    # Add security filter
    console_handler.addFilter(SecurityRedactingFilter())
    
    # Set formatter based on environment
    if format_type == "json":
        formatter = IMSJsonFormatter(
            service_name=service_name,
            environment=environment
        )
    else:
        formatter = HumanReadableFormatter()
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def set_trace_context(trace_id: str, span_id: Optional[str] = None) -> None:
    """
    Set distributed tracing context for current execution.
    
    This context propagates through all log messages in the current
    async context, enabling correlation across services.
    
    Args:
        trace_id: Unique identifier for the entire request trace
        span_id: Unique identifier for this specific operation
    
    Example:
        >>> set_trace_context(trace_id="abc123", span_id="span-001")
        >>> logger.info("Processing request")  # Will include trace_id
    """
    ctx = {'trace_id': trace_id}
    if span_id:
        ctx['span_id'] = span_id
    trace_context.set(ctx)


def clear_trace_context() -> None:
    """Clear distributed tracing context."""
    trace_context.set({})


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Module name (typically __name__)
    
    Returns:
        Logger instance
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Module initialized")
    """
    return logging.getLogger(name)


# Convenience functions for structured logging
def log_model_selection(logger: logging.Logger, model_id: str, 
                        reason: str, score: float) -> None:
    """
    Log model selection with structured data.
    
    Example:
        >>> log_model_selection(logger, "gpt-4", "highest_score", 0.95)
    """
    logger.info(
        "Model selected",
        extra={
            "event_type": "model_selection",
            "model_id": model_id,
            "reason": reason,
            "score": score
        }
    )


def log_policy_violation(logger: logging.Logger, policy: str, 
                         action: str, details: Dict[str, Any]) -> None:
    """
    Log policy violation with structured data.
    
    Example:
        >>> log_policy_violation(logger, "cost_limit", "block", {"cost": 10.5})
    """
    logger.warning(
        f"Policy violation: {policy}",
        extra={
            "event_type": "policy_violation",
            "policy": policy,
            "action": action,
            "details": details
        }
    )


def log_api_call(logger: logging.Logger, vendor: str, model: str, 
                 latency_ms: float, tokens: int, success: bool) -> None:
    """
    Log API call metrics.
    
    Example:
        >>> log_api_call(logger, "openai", "gpt-4", 1234, 500, True)
    """
    level = logging.INFO if success else logging.ERROR
    logger.log(
        level,
        f"API call: {vendor}/{model}",
        extra={
            "event_type": "api_call",
            "vendor": vendor,
            "model": model,
            "latency_ms": latency_ms,
            "tokens": tokens,
            "success": success
        }
    )


# Known Limitations
"""
KNOWN LIMITATIONS:

1. **Log Volume**: High-traffic deployments may generate 100k+ log lines/hour.
   Mitigation: Use sampling for DEBUG level, filter noisy endpoints.

2. **Performance**: JSON serialization adds ~0.5ms per log call.
   Mitigation: Use async logging for high-throughput paths (not implemented yet).

3. **Context Propagation**: ContextVars work per-thread. Multi-process workers
   require explicit trace_id passing.
   Mitigation: Future work - integrate OpenTelemetry context propagation.

4. **Storage**: Structured logs are 3-5x larger than plain text.
   Mitigation: Use log aggregation with retention policies (Loki recommended).

5. **Redaction**: Pattern-based redaction may miss creative key naming.
   Mitigation: Manual audit of logs, add patterns as discovered.
"""