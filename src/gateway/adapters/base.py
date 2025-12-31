from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any

from src.gateway.schemas import ExecutionRequest, ExecutionResponse

@dataclass
class RateLimits:
    requests_per_minute: int
    tokens_per_minute: int

class VendorAdapter(ABC):
    @abstractmethod
    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """Execute API call and return normalized response"""
        pass
    
    @abstractmethod
    def supports_model(self, model_id: str) -> bool:
        """Check if adapter supports this model"""
        pass
    
    @abstractmethod
    async def validate_credentials(self) -> bool:
        """Verify API key is valid"""
        pass
    
    @abstractmethod
    def get_rate_limits(self) -> RateLimits:
        """Return rate limit configuration"""
        pass
