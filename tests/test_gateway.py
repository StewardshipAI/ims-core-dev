import pytest
from unittest.mock import AsyncMock, MagicMock
from src.gateway.adapters.gemini import GeminiAdapter
from src.gateway.schemas import ExecutionRequest
from src.data.model_registry import CapabilityTier

@pytest.mark.asyncio
async def test_gemini_adapter_structure():
    """Test that adapter can be instantiated and has correct methods"""
    adapter = GeminiAdapter("fake-key")
    assert adapter.supports_model("gemini-2.0-flash-exp")
    assert not adapter.supports_model("gpt-4")

@pytest.mark.asyncio
async def test_gateway_flow(mocker):
    """Test the full gateway flow with mocked adapter"""
    # Mock dependencies
    registry = MagicMock()
    model = MagicMock()
    model.model_id = "gemini-fake"
    model.vendor_id = "Google"
    model.capability_tier = CapabilityTier.TIER_1
    model.cost_in_per_mil = 0.1
    model.cost_out_per_mil = 0.2
    model.regions = ["global"]
    model.p_success = 0.99
    
    registry.get_model.return_value = model
    registry.filter_models.return_value = [model]
    
    sm = MagicMock()
    sm.can_transition.return_value = True
    
    er = AsyncMock()
    # execute_with_recovery just calls the operation
    async def side_effect(op, mid, ctx, **kwargs):
        return await op(mid, ctx)
    er.execute_with_recovery.side_effect = side_effect
    
    tracker = AsyncMock()
    
    # Mock Adapter
    adapter = AsyncMock()
    adapter.execute.return_value.content = "Mocked Response"
    adapter.execute.return_value.model_id = "gemini-fake"
    adapter.execute.return_value.tokens_input = 10
    adapter.execute.return_value.tokens_output = 20
    
    adapters = {"Google": adapter}
    
    from src.gateway.action_gateway import ActionGateway
    gateway = ActionGateway(registry, sm, er, tracker, adapters)
    
    request = ExecutionRequest(
        prompt="Test",
        model_id="gemini-fake"
    )
    
    response = await gateway.execute(request)
    
    assert response.content == "Mocked Response"
    # Verify state machine transition
    sm.transition.assert_called()
    # Verify tracking
    tracker.log_execution.assert_called_with(
        model_id="gemini-fake",
        vendor_id="Google",
        tokens_in=10,
        tokens_out=20,
        cost_per_mil_in=mocker.ANY,
        cost_per_mil_out=mocker.ANY,
        latency_ms=mocker.ANY,
        success=True,
        correlation_id=mocker.ANY
    )
