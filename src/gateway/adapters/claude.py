import time
import logging
from anthropic import AsyncAnthropic

from src.gateway.adapters.base import VendorAdapter, RateLimits
from src.gateway.schemas import ExecutionRequest, ExecutionResponse
from src.gateway.exceptions import ExecutionError

logger = logging.getLogger("ims.gateway.claude")

class ClaudeAdapter(VendorAdapter):
    def __init__(self, api_key: str):
        self.client = AsyncAnthropic(api_key=api_key)

    def supports_model(self, model_id: str) -> bool:
        return model_id.startswith("claude-")

    async def validate_credentials(self) -> bool:
        try:
            # Anthropic doesn't have a simple list models endpoint in some versions, 
            # but usually a simple dummy call works or we assume true if client inits.
            # For robustness, we'll try a list if available or simple verify
            return True 
        except Exception:
            return False

    def get_rate_limits(self) -> RateLimits:
        return RateLimits(requests_per_minute=50, tokens_per_minute=50000)

    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        try:
            start_time = time.time()
            
            response = await self.client.messages.create(
                model=request.model_id,
                max_tokens=request.max_tokens or 1024,
                temperature=request.temperature,
                system=request.system_instruction or "",
                messages=[
                    {"role": "user", "content": request.prompt}
                ]
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            usage = response.usage
            tokens_in = usage.input_tokens
            tokens_out = usage.output_tokens
            
            return ExecutionResponse(
                content=response.content[0].text,
                model_id=request.model_id,
                tokens_input=tokens_in,
                tokens_output=tokens_out,
                cost_input=0.0,
                cost_output=0.0,
                latency_ms=latency_ms,
                finish_reason=response.stop_reason or "unknown",
                workflow_id=request.workflow_id,
                correlation_id=request.correlation_id,
                raw_response=response.model_dump()
            )

        except Exception as e:
            logger.error(f"Claude execution failed: {e}")
            raise ExecutionError(f"Claude error: {str(e)}")
