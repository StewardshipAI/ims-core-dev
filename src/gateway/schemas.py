from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

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
    
    # Context
    workflow_id: str = field(default_factory=lambda: "")
    correlation_id: str = field(default_factory=lambda: "")
    
    # Metadata
    user_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    bypass_policies: bool = False

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
    raw_response: Optional[Dict[str, Any]] = None
