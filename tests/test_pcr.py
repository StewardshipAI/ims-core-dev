import pytest
from src.core.pcr import RecommendationService, RecommendationRequest
from src.data.model_registry import ModelProfile, CapabilityTier

# Mock Registry
class MockRegistry:
    def filter_models(self):
        return [
            ModelProfile(
                model_id="gpt-4", vendor_id="OpenAI", 
                capability_tier=CapabilityTier.TIER_3,
                context_window=128000, cost_in_per_mil=10, cost_out_per_mil=30,
                is_active=True
            ),
            ModelProfile(
                model_id="gpt-3.5", vendor_id="OpenAI", 
                capability_tier=CapabilityTier.TIER_2,
                context_window=16000, cost_in_per_mil=0.5, cost_out_per_mil=1.5,
                is_active=True
            ),
            ModelProfile(
                model_id="claude-3-haiku", vendor_id="Anthropic", 
                capability_tier=CapabilityTier.TIER_2,
                context_window=200000, cost_in_per_mil=0.25, cost_out_per_mil=1.25,
                is_active=True
            )
        ]

def test_recommendation_strategy_cost():
    svc = RecommendationService(MockRegistry())
    req = RecommendationRequest(strategy="cost")
    
    results = svc.recommend(req)
    
    # Haiku should be first (Cheapest)
    assert results[0].model_id == "claude-3-haiku"
    assert results[1].model_id == "gpt-3.5"
    assert results[2].model_id == "gpt-4"

def test_recommendation_strategy_performance():
    svc = RecommendationService(MockRegistry())
    req = RecommendationRequest(strategy="performance")
    
    results = svc.recommend(req)
    
    # GPT-4 should be first (Tier 3)
    assert results[0].model_id == "gpt-4"
    # Haiku second (Tier 2, 200k ctx vs 16k)
    assert results[1].model_id == "claude-3-haiku"

def test_recommendation_hard_filters():
    svc = RecommendationService(MockRegistry())
    req = RecommendationRequest(
        min_capability_tier=CapabilityTier.TIER_3
    )
    results = svc.recommend(req)
    assert len(results) == 1
    assert results[0].model_id == "gpt-4"
