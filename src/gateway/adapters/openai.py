import time
import logging
from openai import AsyncOpenAI

from src.gateway.adapters.base import VendorAdapter, RateLimits
from src.gateway.schemas import ExecutionRequest, ExecutionResponse
from src.gateway.exceptions import ExecutionError

logger = logging.getLogger("ims.gateway.openai")

class OpenAIAdapter(VendorAdapter):
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    def supports_model(self, model_id: str) -> bool:
        return model_id.startswith("gpt-") or model_id.startswith("o1-")

    async def validate_credentials(self) -> bool:
        try:
            await self.client.models.list(limit=1)
            return True
        except Exception:
            return False

    def get_rate_limits(self) -> RateLimits:
        return RateLimits(requests_per_minute=500, tokens_per_minute=100000)

    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        try:
            start_time = time.time()
            
            response = await self.client.chat.completions.create(
                model=request.model_id,
                messages=[
                    {"role": "system", "content": request.system_instruction or "You are a helpful assistant."},
                    {"role": "user", "content": request.prompt}
                ],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
                stop=request.stop_sequences
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            usage = response.usage
            tokens_in = usage.prompt_tokens if usage else 0
            tokens_out = usage.completion_tokens if usage else 0
            
            return ExecutionResponse(
                content=response.choices[0].message.content or "",
                model_id=request.model_id,
                tokens_input=tokens_in,
                tokens_output=tokens_out,
                cost_input=0.0, # Calculated later
                cost_output=0.0,
                latency_ms=latency_ms,
                finish_reason=response.choices[0].finish_reason,
                workflow_id=request.workflow_id,
                correlation_id=request.correlation_id,
                raw_response=response.model_dump()
            )

        except Exception as e:
            logger.error(f"OpenAI execution failed: {e}")
            raise ExecutionError(f"OpenAI error: {str(e)}")
