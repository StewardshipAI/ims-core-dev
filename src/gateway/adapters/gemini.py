import time
import logging
from typing import Optional, List
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from src.gateway.adapters.base import VendorAdapter, RateLimits
from src.gateway.schemas import ExecutionRequest, ExecutionResponse
from src.gateway.exceptions import AuthenticationError, ExecutionError

logger = logging.getLogger("ims.gateway.gemini")

class GeminiAdapter(VendorAdapter):
    def __init__(self, api_key: str):
        self.api_key = api_key
        try:
            genai.configure(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to configure Gemini: {e}")

    def supports_model(self, model_id: str) -> bool:
        return model_id.startswith("gemini-")

    async def validate_credentials(self) -> bool:
        try:
            # List models to verify key
            list(genai.list_models(limit=1))
            return True
        except Exception:
            return False

    def get_rate_limits(self) -> RateLimits:
        # Simplified default limits
        return RateLimits(requests_per_minute=60, tokens_per_minute=100000)

    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        try:
            # Ensure model_id has models/ prefix
            model_id = request.model_id
            if not model_id.startswith("models/"):
                model_id = f"models/{model_id}"
                
            model = genai.GenerativeModel(model_id)
            
            # Convert config
            generation_config = genai.types.GenerationConfig(
                temperature=request.temperature,
                top_p=request.top_p,
                max_output_tokens=request.max_tokens,
                stop_sequences=request.stop_sequences
            )

            start_time = time.time()
            
            # Execute
            response = await model.generate_content_async(
                request.prompt,
                generation_config=generation_config
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Extract usage (Gemini might not return usage in all responses, handle gracefully)
            # usage_metadata is available in newer versions
            prompt_tokens = 0
            candidate_tokens = 0
            if hasattr(response, "usage_metadata"):
                prompt_tokens = response.usage_metadata.prompt_token_count
                candidate_tokens = response.usage_metadata.candidates_token_count
            
            # Cost estimation (simplified placeholders)
            # In real system, fetch from Registry based on model_id
            cost_in = 0.0
            cost_out = 0.0

            return ExecutionResponse(
                content=response.text,
                model_id=request.model_id,
                tokens_input=prompt_tokens,
                tokens_output=candidate_tokens,
                cost_input=cost_in,
                cost_output=cost_out,
                latency_ms=latency_ms,
                finish_reason="stop", # Gemini doesn't always expose finish reason easily in top level
                workflow_id=request.workflow_id,
                correlation_id=request.correlation_id,
                raw_response={"text": response.text}
            )

        except Exception as e:
            logger.error(f"Gemini execution failed: {e}")
            raise ExecutionError(f"Gemini error: {str(e)}")
