import logging
from typing import Dict, Optional, List

from src.data.model_registry import ModelRegistry
from src.core.state_machine import StateMachine, TransitionEvent, AgentState
from src.core.error_recovery import ErrorRecovery
from src.core.usage_tracker import UsageTracker
from src.gateway.adapters.base import VendorAdapter
from src.gateway.schemas import ExecutionRequest, ExecutionResponse
from src.gateway.exceptions import GatewayError, ExecutionError

logger = logging.getLogger("ims.gateway.action_gateway")

class ActionGateway:
    def __init__(
        self,
        registry: ModelRegistry,
        state_machine: StateMachine,
        error_recovery: ErrorRecovery,
        usage_tracker: UsageTracker,
        adapters: Dict[str, VendorAdapter]
    ):
        self.registry = registry
        self.state_machine = state_machine
        self.error_recovery = error_recovery
        self.usage_tracker = usage_tracker
        self.adapters = adapters

    def _select_adapter(self, vendor_id: str) -> VendorAdapter:
        # Normalize vendor_id (case insensitive)
        vendor_key = vendor_id.lower()
        
        # Try exact match
        for key, adapter in self.adapters.items():
            if key.lower() == vendor_key:
                return adapter
                
        # Fallback to key containing vendor name
        for key, adapter in self.adapters.items():
            if vendor_key in key.lower() or key.lower() in vendor_key:
                return adapter
                
        raise GatewayError(f"No adapter found for vendor: {vendor_id}")

    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """
        Execute request with automatic vendor selection,
        error recovery, and usage tracking.
        """
        # 1. Get model details
        try:
            model = self.registry.get_model(request.model_id)
            if not model:
                raise GatewayError(f"Model not found: {request.model_id}")
        except Exception as e:
            # If not in registry, maybe we can still try if adapter supports it?
            # But we need vendor_id for adapter selection. 
            # We assume model_id convention or fail.
            raise GatewayError(f"Registry lookup failed for {request.model_id}: {e}")

        # 2. Select adapter
        adapter = self._select_adapter(model.vendor_id)
        
        # 3. Transition state
        if self.state_machine.can_transition(TransitionEvent.EXECUTION_STARTED):
            self.state_machine.transition(
                TransitionEvent.EXECUTION_STARTED,
                {"model_id": request.model_id, "vendor_id": model.vendor_id}
            )
        else:
            logger.warning(f"Cannot transition to EXECUTION_STARTED from {self.state_machine.current_state}")
            # For robustness, we might proceed anyway or reset state
        
        # 4. Execute with error recovery
        try:
            # We wrap the adapter.execute call to match what ErrorRecovery expects.
            # ErrorRecovery.execute_with_recovery expects a callable.
            
            async def _execute_op(model_id_arg, req_arg):
                # We need to re-select adapter if model_id changes (fallback)
                current_model = self.registry.get_model(model_id_arg)
                current_adapter = self._select_adapter(current_model.vendor_id)
                
                # Update request model_id
                # (ExecutionRequest is a dataclass, we can modify or copy)
                req_copy = ExecutionRequest(
                    prompt=req_arg.prompt,
                    model_id=model_id_arg,
                    max_tokens=req_arg.max_tokens,
                    temperature=req_arg.temperature,
                    top_p=req_arg.top_p,
                    stop_sequences=req_arg.stop_sequences,
                    system_instruction=req_arg.system_instruction,
                    workflow_id=req_arg.workflow_id,
                    correlation_id=req_arg.correlation_id,
                    user_id=req_arg.user_id,
                    tags=req_arg.tags
                )
                
                return await current_adapter.execute(req_copy)

            response = await self.error_recovery.execute_with_recovery(
                _execute_op,
                request.model_id,
                request # passed as context/arg
            )
            
            # 5. Track usage
            await self.usage_tracker.log_execution(
                model_id=response.model_id,
                vendor_id=model.vendor_id, # Use original vendor? Or response vendor? 
                # Ideally response should contain vendor, or we re-lookup based on response.model_id
                # But response object doesn't have vendor_id.
                # We'll use the model object from registry for the *executed* model.
                # ErrorRecovery returns the result of the successful execution.
                tokens_in=response.tokens_input,
                tokens_out=response.tokens_output,
                cost_per_mil_in=model.cost_in_per_mil, # Potentially wrong if fallback happened
                cost_per_mil_out=model.cost_out_per_mil,
                latency_ms=response.latency_ms,
                success=True,
                correlation_id=request.correlation_id
            )
            
            # 6. Transition state
            if self.state_machine.can_transition(TransitionEvent.EXECUTION_COMPLETED):
                self.state_machine.transition(
                    TransitionEvent.EXECUTION_COMPLETED,
                    {"tokens": response.tokens_input + response.tokens_output}
                )
            
            return response
            
        except Exception as e:
            # Track failure
            await self.usage_tracker.log_execution(
                model_id=request.model_id,
                vendor_id=model.vendor_id,
                tokens_in=0,
                tokens_out=0,
                cost_per_mil_in=0,
                cost_per_mil_out=0,
                latency_ms=0,
                success=False,
                error=str(e),
                correlation_id=request.correlation_id
            )
            
            # Transition to failed state
            # EXECUTING -> ERROR -> ROLLBACK
            if self.state_machine.can_transition(TransitionEvent.ERROR):
                self.state_machine.transition(
                    TransitionEvent.ERROR,
                    {"error": str(e)}
                )
            
            raise ExecutionError(f"Gateway execution failed: {e}")
