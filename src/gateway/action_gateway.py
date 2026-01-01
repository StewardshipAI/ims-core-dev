import logging
from typing import Dict, Optional, List

from src.data.model_registry import ModelRegistry
from src.core.state_machine import StateMachine, TransitionEvent, AgentState
from src.core.error_recovery import ErrorRecovery
from src.core.usage_tracker import UsageTracker
from src.core.policy_verifier import PolicyVerifierEngine, EvaluationContext, PolicyAction
from src.core.router import SmartRouter, RoutingDecision
from src.gateway.adapters.base import VendorAdapter
from src.gateway.schemas import ExecutionRequest, ExecutionResponse
from src.gateway.exceptions import GatewayError, ExecutionError
import time
from src.observability.logging import get_logger, log_api_call
from src.observability.metrics import get_metrics
from src.observability.tracing import trace_operation, add_span_attributes, add_span_event

logger = get_logger("ims.gateway.action_gateway")
metrics = get_metrics()

class ActionGateway:
    def __init__(
        self,
        registry: ModelRegistry,
        state_machine: StateMachine,
        error_recovery: ErrorRecovery,
        usage_tracker: UsageTracker,
        adapters: Dict[str, VendorAdapter],
        policy_engine: Optional[PolicyVerifierEngine] = None,
        router: Optional[SmartRouter] = None
    ):
        self.registry = registry
        self.state_machine = state_machine
        self.error_recovery = error_recovery
        self.usage_tracker = usage_tracker
        self.adapters = adapters
        self.policy_engine = policy_engine
        self.router = router or SmartRouter(registry)

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

    @trace_operation("gateway_execute", {"component": "action_gateway"})
    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """
        Execute request with smart routing, policy enforcement,
        and automatic fallback.
        """
        start_time = time.time()
        # 1. Get model details
        try:
            model = self.registry.get_model(request.model_id)
            if not model:
                raise GatewayError(f"Model not found: {request.model_id}")
        except Exception as e:
            raise GatewayError(f"Registry lookup failed for {request.model_id}: {e}")

        # 2. Policy Enforcement
        if self.policy_engine and not request.bypass_policies:
            context = EvaluationContext(
                model_id=request.model_id,
                vendor_id=model.vendor_id,
                estimated_tokens=request.max_tokens or 1000, 
                prompt=request.prompt,
                user_id=request.user_id,
                correlation_id=request.correlation_id,
                request_id=getattr(request, 'request_id', None),
                system_instruction=request.system_instruction,
                temperature=request.temperature,
                max_output_tokens=request.max_tokens
            )
            policy_result = await self.policy_engine.evaluate_pre_flight(context)
            add_span_attributes({"policy_passed": policy_result.passed})
            
            if not policy_result.passed:
                # Handle BLOCK
                if any(v.action == PolicyAction.BLOCK for v in policy_result.violations):
                    reasons = [v.policy_name for v in policy_result.violations if v.action == PolicyAction.BLOCK]
                    metrics.record_error("policy_blocked", "action_gateway")
                    raise GatewayError(
                        f"Blocked by policies: {', '.join(reasons)}. "
                        "To proceed with this expensive option, set 'bypass_policies': true"
                    )
                
                if any(v.action == PolicyAction.DEGRADE for v in policy_result.violations):
                    add_span_event("policy_degrade_triggered")
                    logger.info("Policy DEGRADE triggered: Invoking SmartRouter")
                    decision = self.router.select_model(
                        capability_tier=model.capability_tier,
                        strategy="cost"
                    )
                    if decision:
                        logger.info(f"SmartRouter selected alternative: {decision.selected_model.model_id}")
                        request.model_id = decision.selected_model.model_id
                        model = decision.selected_model

        # 3. Select Initial Adapter
        adapter = self._select_adapter(model.vendor_id)
        
        # 4. Transition state
        if self.state_machine.can_transition(TransitionEvent.EXECUTION_STARTED):
            self.state_machine.transition(
                TransitionEvent.EXECUTION_STARTED,
                {"model_id": request.model_id, "vendor_id": model.vendor_id}
            )
        
        # 5. Build Smart Fallback Chain
        decision = self.router.select_model(
            capability_tier=model.capability_tier,
            strategy="cost"
        )
        fallback_models = decision.fallback_chain if decision else []

        # 6. Execute with Error Recovery
        try:
            async def _execute_op(model_id_arg, req_arg):
                current_model = self.registry.get_model(model_id_arg)
                current_adapter = self._select_adapter(current_model.vendor_id)
                
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
                    tags=req_arg.tags,
                    bypass_policies=req_arg.bypass_policies
                )
                
                return await current_adapter.execute(req_copy)

            response = await self.error_recovery.execute_with_recovery(
                _execute_op,
                request.model_id,
                request,
                fallback_chain=fallback_models
            )
            
            duration = time.time() - start_time
            # 7. Track usage
            await self.usage_tracker.log_execution(
                model_id=response.model_id,
                vendor_id=model.vendor_id, 
                tokens_in=response.tokens_input,
                tokens_out=response.tokens_output,
                cost_per_mil_in=model.cost_in_per_mil,
                cost_per_mil_out=model.cost_out_per_mil,
                latency_ms=response.latency_ms,
                success=True,
                correlation_id=request.correlation_id
            )
            
            # Record Metrics
            metrics.record_request(
                service="action_gateway",
                vendor=model.vendor_id,
                model=response.model_id,
                duration_seconds=duration,
                success=True
            )
            metrics.record_tokens(
                vendor=model.vendor_id,
                model=response.model_id,
                input_tokens=response.tokens_input,
                output_tokens=response.tokens_output
            )
            
            # Trace attributes
            add_span_attributes({
                "model_id": response.model_id,
                "vendor_id": model.vendor_id,
                "tokens_total": response.tokens_input + response.tokens_output
            })
            
            # Log structured
            log_api_call(
                logger,
                vendor=model.vendor_id,
                model=response.model_id,
                latency_ms=duration * 1000,
                tokens=response.tokens_input + response.tokens_output,
                success=True
            )
            
            # 8. Transition state
            if self.state_machine.can_transition(TransitionEvent.EXECUTION_COMPLETED):
                self.state_machine.transition(
                    TransitionEvent.EXECUTION_COMPLETED,
                    {"tokens": response.tokens_input + response.tokens_output}
                )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
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
            
            metrics.record_request(
                service="action_gateway",
                vendor=model.vendor_id if 'model' in locals() else "unknown",
                model=request.model_id,
                duration_seconds=duration,
                success=False
            )
            metrics.record_error(type(e).__name__, "action_gateway")
            
            # Transition to failed state
            if self.state_machine.can_transition(TransitionEvent.ERROR):
                self.state_machine.transition(
                    TransitionEvent.ERROR,
                    {"error": str(e)}
                )
            
            raise ExecutionError(f"Gateway execution failed: {e}")