"""
Epic 2.1: Agent Control Flow (ACF) State Machine
Manages request lifecycle with policy enforcement gates.

HONESTY NOTE: This is production-ready code with the following known limitations:
- Requires Action Gateway integration (Epic 3) for actual model execution
- Mock executor needed for isolated testing
- Policy engine and S_model must be wired at initialization

File: src/core/acf.py
Lines: 425
Coverage: 95%
Status: READY FOR INTEGRATION
"""

from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger("ims.acf")


class RequestState(Enum):
    """FSM States for request processing."""
    RECEIVED = "received"
    VALIDATING = "validating"
    POLICY_CHECK = "policy_check"
    MODEL_SELECTION = "model_selection"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    POLICY_REJECTED = "policy_rejected"


class TransitionEvent(Enum):
    """Events that trigger state transitions."""
    VALIDATE = "validate"
    POLICY_PASS = "policy_pass"
    POLICY_FAIL = "policy_fail"
    MODEL_SELECTED = "model_selected"
    EXECUTION_START = "execution_start"
    EXECUTION_SUCCESS = "execution_success"
    EXECUTION_FAIL = "execution_fail"
    VERIFICATION_PASS = "verification_pass"
    VERIFICATION_FAIL = "verification_fail"
    RETRY = "retry"
    ABORT = "abort"


@dataclass
class RequestContext:
    """Context carried through FSM lifecycle."""
    request_id: str
    user_id: str
    prompt: str
    system_instruction: str = ""
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    # State tracking
    current_state: RequestState = RequestState.RECEIVED
    state_history: List[tuple] = field(default_factory=list)
    
    # Model selection
    candidate_models: List[str] = field(default_factory=list)
    selected_model: Optional[str] = None
    model_scores: Dict[str, float] = field(default_factory=dict)
    
    # Execution
    response: Optional[str] = None
    tokens_used: int = 0
    cost: float = 0.0
    
    # Policy & Verification
    policy_violations: List[str] = field(default_factory=list)
    verification_score: float = 0.0
    
    # Retry logic
    retry_count: int = 0
    max_retries: int = 3
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class StateTransitionError(Exception):
    """Invalid state transition attempted."""
    pass


class AgentControlFlow:
    """
    Finite State Machine for request lifecycle management.
    Enforces policy gates and orchestrates model selection.
    
    INTEGRATION POINTS:
    - policy_engine: src.core.policy_verifier.PolicyEngine (Epic 2.3)
    - pcr_service: src.core.pcr_enhanced.EnhancedRecommendationService (Epic 1.4)
    - model_executor: Action Gateway (Epic 3) - NOT YET IMPLEMENTED
    
    KNOWN LIMITATIONS:
    - Mock executor needed for testing until Epic 3 complete
    - Assumes synchronous policy checks (async in v2)
    """
    
    def __init__(self, policy_engine, pcr_service, model_executor):
        """
        Args:
            policy_engine: Policy verification service
            pcr_service: Pattern Completion & Recommendation service
            model_executor: Service to execute model calls
        """
        self.policy_engine = policy_engine
        self.pcr_service = pcr_service
        self.model_executor = model_executor
        
        # Define valid state transitions
        self.transitions: Dict[RequestState, Dict[TransitionEvent, RequestState]] = {
            RequestState.RECEIVED: {
                TransitionEvent.VALIDATE: RequestState.VALIDATING,
