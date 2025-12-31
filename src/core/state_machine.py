"""
IMS Agent Control Flow State Machine
=====================================
Implements a finite state machine for orchestrating multi-step workflows.
Provides state persistence, transition logging, and rollback capabilities.
"""

import logging
from typing import Optional, Dict, Any, List, Callable, Awaitable
from enum import Enum
from datetime import datetime
from uuid import uuid4
import json

from src.core.events import EventPublisher, CloudEvent

logger = logging.getLogger("ims.state_machine")


class AgentState(Enum):
    """Valid agent states"""
    IDLE = "idle"                      # No active workflow
    ANALYZING = "analyzing"            # Analyzing request requirements
    SELECTING_MODEL = "selecting"      # Choosing optimal model
    EXECUTING = "executing"            # Model execution in progress
    VALIDATING = "validating"          # Checking policy compliance
    COMPLETED = "completed"            # Workflow completed successfully
    FAILED = "failed"                  # Workflow failed
    ROLLBACK = "rollback"              # Rolling back changes


class TransitionEvent(Enum):
    """Events that trigger state transitions"""
    START = "start"
    ANALYZED = "analyzed"
    MODEL_SELECTED = "model_selected"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    VALIDATION_PASSED = "validation_passed"
    ERROR = "error"
    RETRY = "retry"
    ABORT = "abort"
    ROLLBACK_COMPLETE = "rollback_complete"


class StateTransition:
    """Record of a state transition"""
    
    def __init__(
        self,
        from_state: AgentState,
        to_state: AgentState,
        event: TransitionEvent,
        context: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ):
        self.id = str(uuid4())
        self.from_state = from_state
        self.to_state = to_state
        self.event = event
        self.context = context
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from": self.from_state.value,
            "to": self.to_state.value,
            "event": self.event.value,
            "context": self.context,
            "timestamp": self.timestamp.isoformat()
        }


class StateMachine:
    """
    Finite State Machine for agent workflows.
    
    Features:
    - Valid transition enforcement
    - State persistence
    - Transition history
    - Rollback capability
    - Telemetry emission
    """
    
    # Valid state transitions
    VALID_TRANSITIONS = {
        AgentState.IDLE: {
            TransitionEvent.START: AgentState.ANALYZING
        },
        AgentState.ANALYZING: {
            TransitionEvent.ANALYZED: AgentState.SELECTING_MODEL,
            TransitionEvent.ERROR: AgentState.FAILED
        },
        AgentState.SELECTING_MODEL: {
            TransitionEvent.MODEL_SELECTED: AgentState.EXECUTING,
            TransitionEvent.ERROR: AgentState.FAILED,
            TransitionEvent.RETRY: AgentState.ANALYZING
        },
        AgentState.EXECUTING: {
            TransitionEvent.EXECUTION_COMPLETED: AgentState.VALIDATING,
            TransitionEvent.ERROR: AgentState.ROLLBACK,
            TransitionEvent.RETRY: AgentState.SELECTING_MODEL
        },
        AgentState.VALIDATING: {
            TransitionEvent.VALIDATION_PASSED: AgentState.COMPLETED,
            TransitionEvent.ERROR: AgentState.ROLLBACK
        },
        AgentState.COMPLETED: {
            TransitionEvent.START: AgentState.ANALYZING
        },
        AgentState.FAILED: {
            TransitionEvent.START: AgentState.ANALYZING,
            TransitionEvent.RETRY: AgentState.ANALYZING
        },
        AgentState.ROLLBACK: {
            TransitionEvent.ROLLBACK_COMPLETE: AgentState.FAILED,
            TransitionEvent.RETRY: AgentState.ANALYZING
        }
    }
    
    def __init__(
        self,
        workflow_id: Optional[str] = None,
        publisher: Optional[EventPublisher] = None
    ):
        self.workflow_id = workflow_id or str(uuid4())
        self.publisher = publisher
        
        # State tracking
        self.current_state = AgentState.IDLE
        self.history: List[StateTransition] = []
        self.context: Dict[str, Any] = {}
        
        # Callbacks for state entry/exit
        self._entry_callbacks: Dict[AgentState, List[Callable]] = {}
        self._exit_callbacks: Dict[AgentState, List[Callable]] = {}
        
        logger.info(f"StateMachine initialized: {self.workflow_id}")
    
    def transition(
        self,
        event: TransitionEvent,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Attempt a state transition.
        
        Args:
            event: Event triggering the transition
            context: Additional context data
            
        Returns:
            True if transition successful, False otherwise
        """
        # Check if transition is valid
        valid_transitions = self.VALID_TRANSITIONS.get(self.current_state, {})
        new_state = valid_transitions.get(event)
        
        if new_state is None:
            logger.warning(
                f"Invalid transition: {self.current_state.value} "
                f"--({event.value})--> ???"
            )
            return False
        
        # Update context
        if context:
            self.context.update(context)
        
        # Create transition record
        transition = StateTransition(
            from_state=self.current_state,
            to_state=new_state,
            event=event,
            context=dict(self.context)  # Snapshot of context
        )
        
        # Execute exit callbacks
        self._execute_callbacks(
            self._exit_callbacks.get(self.current_state, []),
            transition
        )
        
        # Perform transition
        old_state = self.current_state
        self.current_state = new_state
        self.history.append(transition)
        
        logger.info(
            f"Transition: {old_state.value} "
            f"--({event.value})--> {new_state.value}"
        )
        
        # Execute entry callbacks
        self._execute_callbacks(
            self._entry_callbacks.get(new_state, []),
            transition
        )
        
        # Emit telemetry
        if self.publisher:
            self._emit_transition_event(transition)
        
        return True
    
    def _execute_callbacks(
        self,
        callbacks: List[Callable],
        transition: StateTransition
    ) -> None:
        """Execute state callbacks"""
        for callback in callbacks:
            try:
                callback(transition)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    async def _emit_transition_event(self, transition: StateTransition) -> None:
        """Emit transition event to telemetry"""
        try:
            event = CloudEvent(
                source="/state-machine",
                type="workflow.state_changed",
                correlation_id=self.workflow_id,
                data={
                    "workflow_id": self.workflow_id,
                    "transition": transition.to_dict()
                }
            )
            
            await self.publisher.publish(event)
        except Exception as e:
            logger.error(f"Failed to emit transition event: {e}")
    
    def register_entry_callback(
        self,
        state: AgentState,
        callback: Callable[[StateTransition], None]
    ) -> None:
        """Register callback for state entry"""
        if state not in self._entry_callbacks:
            self._entry_callbacks[state] = []
        
        self._entry_callbacks[state].append(callback)
    
    def register_exit_callback(
        self,
        state: AgentState,
        callback: Callable[[StateTransition], None]
    ) -> None:
        """Register callback for state exit"""
        if state not in self._exit_callbacks:
            self._exit_callbacks[state] = []
        
        self._exit_callbacks[state].append(callback)
    
    def get_state(self) -> AgentState:
        """Get current state"""
        return self.current_state
    
    def get_context(self) -> Dict[str, Any]:
        """Get current context"""
        return dict(self.context)
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get transition history"""
        return [t.to_dict() for t in self.history]
    
    def can_transition(self, event: TransitionEvent) -> bool:
        """Check if transition is valid from current state"""
        valid_transitions = self.VALID_TRANSITIONS.get(self.current_state, {})
        return event in valid_transitions
    
    def reset(self) -> None:
        """Reset state machine to IDLE"""
        self.current_state = AgentState.IDLE
        self.context.clear()
        self.history.clear()
        
        logger.info(f"StateMachine reset: {self.workflow_id}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize state machine to dictionary"""
        return {
            "workflow_id": self.workflow_id,
            "current_state": self.current_state.value,
            "context": self.context,
            "history": self.get_history()
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        publisher: Optional[EventPublisher] = None
    ) -> "StateMachine":
        """Restore state machine from dictionary"""
        sm = cls(
            workflow_id=data["workflow_id"],
            publisher=publisher
        )
        
        sm.current_state = AgentState(data["current_state"])
        sm.context = data.get("context", {})
        
        # Restore history
        for t in data.get("history", []):
            transition = StateTransition(
                from_state=AgentState(t["from"]),
                to_state=AgentState(t["to"]),
                event=TransitionEvent(t["event"]),
                context=t["context"],
                timestamp=datetime.fromisoformat(t["timestamp"])
            )
            sm.history.append(transition)
        
        logger.info(f"StateMachine restored: {sm.workflow_id}")
        
        return sm


class WorkflowOrchestrator:
    """
    High-level workflow orchestration using StateMachine.
    """
    
    def __init__(self, publisher: Optional[EventPublisher] = None):
        self.publisher = publisher
        self.active_workflows: Dict[str, StateMachine] = {}
    
    def create_workflow(self, workflow_id: Optional[str] = None) -> StateMachine:
        """Create new workflow"""
        sm = StateMachine(workflow_id=workflow_id, publisher=self.publisher)
        self.active_workflows[sm.workflow_id] = sm
        
        logger.info(f"Workflow created: {sm.workflow_id}")
        
        return sm
    
    def get_workflow(self, workflow_id: str) -> Optional[StateMachine]:
        """Get existing workflow"""
        return self.active_workflows.get(workflow_id)
    
    def complete_workflow(self, workflow_id: str) -> None:
        """Mark workflow as complete and archive"""
        if workflow_id in self.active_workflows:
            del self.active_workflows[workflow_id]
            logger.info(f"Workflow completed: {workflow_id}")
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all active workflows"""
        return [
            {
                "workflow_id": wf_id,
                "state": sm.current_state.value,
                "transitions": len(sm.history)
            }
            for wf_id, sm in self.active_workflows.items()
        ]
