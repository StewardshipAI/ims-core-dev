# src/core/router.py

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from src.data.model_registry import ModelRegistry, ModelProfile, CapabilityTier
from src.observability.logging import get_logger
from src.observability.tracing import trace_operation, add_span_attributes

logger = get_logger("ims.router")

@dataclass
class RoutingDecision:
    selected_model: ModelProfile
    fallback_chain: List[str]
    score: float
    reason: str

class SmartRouter:
    """
    Advanced model selection service.
    Implements cost-aware, quota-sensitive routing heuristics.
    """
    
    def __init__(self, registry: ModelRegistry):
        self.registry = registry

    @trace_operation("router_select_model", {"component": "router"})
    def select_model(
        self, 
        capability_tier: CapabilityTier,
        min_context: int = 0,
        strategy: str = "cost",
        region: str = "global"
    ) -> Optional[RoutingDecision]:
        """
        Select the optimal model and build a fallback chain.
        """
        add_span_attributes({
            "tier": capability_tier.value,
            "strategy": strategy,
            "region": region
        })
        # 1. Fetch candidates from same tier
        candidates = self.registry.filter_models(
            capability_tier=capability_tier,
            min_context=min_context
        )
        
        if not candidates:
            logger.warning(f"No candidates found for tier {capability_tier.value}")
            return None

        # 2. Filter by region
        regional_candidates = [
            m for m in candidates 
            if region in m.regions or "global" in m.regions
        ]
        
        if not regional_candidates:
            regional_candidates = candidates # Fallback to any if regional is empty

        # 3. Score candidates
        scored_models = []
        for model in regional_candidates:
            score = self._calculate_score(model, strategy)
            scored_models.append((score, model))

        # Sort by score
        scored_models.sort(key=lambda x: x[0])

        if not scored_models:
            return None

        selected = scored_models[0][1]
        
        # 4. Build fallback chain (next best 2 models)
        fallback_chain = [m[1].model_id for m in scored_models[1:3]]

        return RoutingDecision(
            selected_model=selected,
            fallback_chain=fallback_chain,
            score=scored_models[0][0],
            reason=f"Optimal choice based on {strategy} strategy"
        )

    def _calculate_score(self, model: ModelProfile, strategy: str) -> float:
        """
        Calculate the 'Expected Cost of Success' (ECS).
        ECS = (Baseline Cost) / P(success)
        """
        avg_cost_per_mil = (float(model.cost_in_per_mil) + float(model.cost_out_per_mil)) / 2
        
        # Base probability of success from metadata
        p_success = getattr(model, 'p_success', 0.99)
        
        if strategy == "performance":
            # Penalize lower tiers more heavily when performance is priority
            # Tier 3 gets a 'bonus' reduction in effective cost score
            tier_bonus = 1.0
            if model.capability_tier == CapabilityTier.TIER_3: tier_bonus = 0.5
            elif model.capability_tier == CapabilityTier.TIER_2: tier_bonus = 0.8
            
            return (avg_cost_per_mil * tier_bonus) / p_success
        
        # Default 'cost' strategy: raw expected cost
        return avg_cost_per_mil / p_success
