import logging
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

from src.data.model_registry import ModelRegistry, ModelProfile, CapabilityTier

logger = logging.getLogger("ims.pcr")

class RecommendationRequest(BaseModel):
    """Criteria for model selection."""
    min_capability_tier: Optional[CapabilityTier] = None
    min_context_window: int = Field(0, ge=0)
    max_cost_per_mil: Optional[float] = None # Combined cost
    strategy: Literal["cost", "performance"] = "cost"

class RecommendationService:
    def __init__(self, registry: ModelRegistry):
        self.registry = registry

    def recommend(self, req: RecommendationRequest) -> List[ModelProfile]:
        """
        Rank models based on heuristics.
        """
        # 1. Fetch all candidates (active only)
        # Using filter_models with include_inactive=False (default)
        # Note: We need a method to get ALL active models efficiently or use filter
        # We'll use filter_models from registry with minimal args
        try:
            candidates = self.registry.filter_models()
        except Exception as e:
            logger.error(f"Failed to fetch candidates: {e}")
            return []

        filtered = []
        
        # 2. Hard Filters
        for model in candidates:
            # Check Tier
            if req.min_capability_tier:
                if not self._tier_gte(model.capability_tier, req.min_capability_tier):
                    continue
            
            # Check Context
            if model.context_window < req.min_context_window:
                continue
            
            # Check Cost (Avg of In/Out)
            avg_cost = (model.cost_in_per_mil + model.cost_out_per_mil) / 2
            if req.max_cost_per_mil is not None and avg_cost > req.max_cost_per_mil:
                continue
                
            filtered.append(model)

        # 3. Soft Ranking
        if req.strategy == "cost":
            # Cheapest first (Sum of costs)
            filtered.sort(key=lambda m: m.cost_in_per_mil + m.cost_out_per_mil)
        elif req.strategy == "performance":
            # Highest Tier first, then Largest Context
            filtered.sort(
                key=lambda m: (self._tier_value(m.capability_tier), m.context_window),
                reverse=True
            )

        return filtered[:5] # Return top 5

    def _tier_value(self, tier: CapabilityTier) -> int:
        mapping = {
            CapabilityTier.TIER_1: 1,
            CapabilityTier.TIER_2: 2,
            CapabilityTier.TIER_3: 3
        }
        return mapping.get(tier, 0)

    def _tier_gte(self, t1: CapabilityTier, t2: CapabilityTier) -> bool:
        return self._tier_value(t1) >= self._tier_value(t2)
