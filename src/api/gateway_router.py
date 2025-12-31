import os
import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.core.events import EventPublisher, get_event_publisher
from src.core.state_machine import StateMachine, WorkflowOrchestrator
from src.core.error_recovery import ErrorRecovery
from src.core.usage_tracker import UsageTracker, get_usage_tracker
from src.core.pcr import RecommendationService
from src.data.model_registry import ModelRegistry
from src.api.registry_singleton import registry

from src.gateway.action_gateway import ActionGateway
from src.gateway.schemas import ExecutionRequest as GatewayRequest, ExecutionResponse
from src.gateway.adapters.gemini import GeminiAdapter
from src.gateway.adapters.openai import OpenAIAdapter
from src.gateway.adapters.claude import ClaudeAdapter
from src.api.auth_utils import verify_admin

logger = logging.getLogger("ims.api.gateway")

router = APIRouter(prefix="/api/v1/execute", tags=["Gateway"])

# Pydantic model for input (GatewayRequest is dataclass, need Pydantic for API)
class ExecuteRequestDTO(BaseModel):
    prompt: str
    model_id: str
    max_tokens: int = 1024
    temperature: float = 0.7
    system_instruction: str = "You are a helpful AI assistant."

# Dependency to get Action Gateway
async def get_action_gateway(
    publisher = Depends(get_event_publisher),
    usage_tracker = Depends(get_usage_tracker)
):
    
    # Initialize Adapters
    adapters = {}
    
    # Gemini
    gemini_key = os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        adapters["Google"] = GeminiAdapter(gemini_key)
        
    # OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        adapters["OpenAI"] = OpenAIAdapter(openai_key)
        
    # Claude
    claude_key = os.getenv("ANTHROPIC_API_KEY")
    if claude_key:
        adapters["Anthropic"] = ClaudeAdapter(claude_key)
        
    if not adapters:
        logger.warning("No vendor adapters configured!")
        
    # Dependencies
    state_machine = StateMachine(publisher=publisher)
    
    # Error Recovery needs RecommendationService
    pcr_service = RecommendationService(registry)
    error_recovery = ErrorRecovery(registry, pcr_service)
    
    return ActionGateway(
        registry=registry,
        state_machine=state_machine,
        error_recovery=error_recovery,
        usage_tracker=usage_tracker,
        adapters=adapters
    )

@router.post(
    "",
    response_model=Dict[str, Any],
    summary="Execute prompt with selected model"
)
async def execute_prompt(
    request: ExecuteRequestDTO,
    gateway = Depends(get_action_gateway),
    _ = Depends(verify_admin)
):
    """
    Execute a prompt using the Action Gateway.
    
    - Handles vendor selection
    - Normalizes request/response
    - Tracks usage and cost
    - Recovers from errors automatically
    """
    try:
        # Convert Pydantic -> Gateway Request (Dataclass)
        gw_request = GatewayRequest(
            prompt=request.prompt,
            model_id=request.model_id,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system_instruction=request.system_instruction
        )
        
        response = await gateway.execute(gw_request)
        
        # Convert Gateway Response (Dataclass) -> Dict
        return {
            "content": response.content,
            "model_id": response.model_id,
            "tokens": {
                "input": response.tokens_input,
                "output": response.tokens_output,
                "total": response.tokens_input + response.tokens_output
            },
            "cost": {
                "input": response.cost_input,
                "output": response.cost_output,
                "total": response.cost_input + response.cost_output
            },
            "latency_ms": response.latency_ms,
            "finish_reason": response.finish_reason,
            "workflow_id": response.workflow_id,
            "correlation_id": response.correlation_id
        }
        
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=str(e)
        )
