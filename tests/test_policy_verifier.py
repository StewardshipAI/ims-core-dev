"""
IMS Policy Enforcement Engine - Unit Tests
Tests for Policy Verifier Engine core logic.
"""

import pytest
from datetime import datetime
from src.core.policy_verifier import (
    PolicyVerifierEngine,
    EvaluationContext,
    PolicyCategory,
    PolicyAction,
    ViolationSeverity,
    PolicyResult
)

# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_registry():
    """Mock PolicyRegistry for testing."""
    class MockRegistry:
        async def get_active_policies(self, evaluation_type=None, category=None):
            """Return sample test policies."""
            policies = [
                {
                    "policy_id": "cost-001",
                    "name": "free-tier-budget",
                    "category": "cost",
                    "priority": 90,
                    "constraints": {"max_cost_per_request": 0.01},
                    "evaluation_type": "pre_flight",
                    "action_on_violation": "block"
                },
                {
                    "policy_id": "vendor-001",
                    "name": "approved-vendors-only",
                    "category": "vendor",
                    "priority": 80,
                    "constraints": {"allowed_vendors": ["google", "anthropic"]},
                    "evaluation_type": "pre_flight",
                    "action_on_violation": "block"
                },
                {
                    "policy_id": "behavioral-001",
                    "name": "prompt-length-limit",
                    "category": "behavioral",
                    "priority": 85,
                    "constraints": {"max_prompt_length": 50000},
                    "evaluation_type": "pre_flight",
                    "action_on_violation": "block"
                }
            ]
            
            # Filter by evaluation_type if provided
            if evaluation_type:
                policies = [p for p in policies if p["evaluation_type"] == evaluation_type]
            
            # Filter by category if provided
            if category:
                policies = [p for p in policies if p["category"] == category]
            
            return policies
        
        async def get_model(self, model_id):
            """Return mock model data."""
            models = {
                "gemini-2.5-flash": MockModel(
                    model_id="gemini-2.5-flash",
                    vendor_id="google",
                    cost_in_per_mil=0.075,
                    cost_out_per_mil=0.30
                ),
                "gpt-4": MockModel(
                    model_id="gpt-4",
                    vendor_id="openai",
                    cost_in_per_mil=30.0,
                    cost_out_per_mil=60.0
                )
            }
            return models.get(model_id)
        
        async def log_violation(self, violation):
            """Mock violation logging."""
            return "mock-violation-id"
    
    return MockRegistry()

@pytest.fixture
def mock_publisher():
    """Mock EventPublisher for testing."""
    class MockPublisher:
        async def publish(self, event):
            """Mock event publishing."""
            pass
    
    return MockPublisher()

class MockModel:
    """Mock model for testing."""
    def __init__(self, model_id, vendor_id, cost_in_per_mil, cost_out_per_mil):
        self.model_id = model_id
        self.vendor_id = vendor_id
        self.cost_in_per_mil = cost_in_per_mil
        self.cost_out_per_mil = cost_out_per_mil

# ============================================================================
# COST POLICY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_cost_policy_pass(mock_registry, mock_publisher):
    """Test that a low-cost request passes."""
    engine = PolicyVerifierEngine(mock_registry, mock_publisher)
    
    context = EvaluationContext(
        model_id="gemini-2.5-flash",
        vendor_id="google",
        estimated_tokens=100,  # Very small, ~$0.00002
        prompt="Hello, world!",
        user_id="test-user",
        correlation_id="test-123"
    )
    
    result = await engine.evaluate_pre_flight(context)
    
    assert result.passed is True
    assert len(result.violations) == 0
    assert result.policies_evaluated > 0

@pytest.mark.asyncio
async def test_cost_policy_fail_expensive_request(mock_registry, mock_publisher):
    """Test that an expensive request is blocked."""
    engine = PolicyVerifierEngine(mock_registry, mock_publisher)
    
    context = EvaluationContext(
        model_id="gemini-2.5-flash",
        vendor_id="google",
        estimated_tokens=1_000_000,  # Large request, ~$0.1875
        prompt="A" * 100000,
        user_id="test-user",
        correlation_id="test-456"
    )
    
    result = await engine.evaluate_pre_flight(context)
    
    assert result.passed is False
    assert len(result.violations) > 0
    
    # Check violation details
    violation = result.violations[0]
    assert violation.policy_name == "free-tier-budget"
    assert violation.action == PolicyAction.BLOCK
    assert violation.severity == ViolationSeverity.CRITICAL
    assert "cost_per_request_exceeded" in violation.details.get("violation", "")

@pytest.mark.asyncio
async def test_cost_policy_expensive_model(mock_registry, mock_publisher):
    """Test policy with an expensive model (GPT-4)."""
    engine = PolicyVerifierEngine(mock_registry, mock_publisher)
    
    context = EvaluationContext(
        model_id="gpt-4",
        vendor_id="openai",
        estimated_tokens=1000,
        prompt="Test prompt",
        user_id="test-user",
        correlation_id="test-789"
    )
    
    result = await engine.evaluate_pre_flight(context)
    
    # Should fail due to high cost
    assert result.passed is False

# ============================================================================
# VENDOR POLICY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_vendor_policy_pass_allowed(mock_registry, mock_publisher):
    """Test that an allowed vendor passes."""
    engine = PolicyVerifierEngine(mock_registry, mock_publisher)
    
    context = EvaluationContext(
        model_id="gemini-2.5-flash",
        vendor_id="google",
        estimated_tokens=100,
        prompt="Hello",
        correlation_id="test-vendor-1"
    )
    
    result = await engine.evaluate_pre_flight(context)
    
    assert result.passed is True

@pytest.mark.asyncio
async def test_vendor_policy_fail_blocked(mock_registry, mock_publisher):
    """Test that a blocked vendor is rejected."""
    engine = PolicyVerifierEngine(mock_registry, mock_publisher)
    
    context = EvaluationContext(
        model_id="some-model",
        vendor_id="openai",  # Not in allowed list
        estimated_tokens=100,
        prompt="Hello",
        correlation_id="test-vendor-2"
    )
    
    result = await engine.evaluate_pre_flight(context)
    
    # Should fail vendor policy
    violations = [v for v in result.violations if v.category == PolicyCategory.VENDOR]
    assert len(violations) > 0
    assert violations[0].details.get("violation") == "vendor_not_allowed"

# ============================================================================
# BEHAVIORAL POLICY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_behavioral_policy_pass_normal_prompt(mock_registry, mock_publisher):
    """Test that a normal-length prompt passes."""
    engine = PolicyVerifierEngine(mock_registry, mock_publisher)
    
    context = EvaluationContext(
        model_id="gemini-2.5-flash",
        vendor_id="google",
        estimated_tokens=100,
        prompt="A" * 1000,  # 1k chars, well below 50k limit
        correlation_id="test-behav-1"
    )
    
    result = await engine.evaluate_pre_flight(context)
    
    assert result.passed is True

@pytest.mark.asyncio
async def test_behavioral_policy_fail_long_prompt(mock_registry, mock_publisher):
    """Test that an excessively long prompt is blocked."""
    engine = PolicyVerifierEngine(mock_registry, mock_publisher)
    
    context = EvaluationContext(
        model_id="gemini-2.5-flash",
        vendor_id="google",
        estimated_tokens=100000,
        prompt="A" * 60000,  # 60k chars, exceeds 50k limit
        correlation_id="test-behav-2"
    )
    
    result = await engine.evaluate_pre_flight(context)
    
    # Should fail behavioral policy
    violations = [v for v in result.violations if v.category == PolicyCategory.BEHAVIORAL]
    assert len(violations) > 0
    assert "prompt_too_long" in violations[0].details.get("violation", "")

# ============================================================================
# SEVERITY & ACTION MAPPING TESTS
# ============================================================================

def test_severity_mapping():
    """Test priority-to-severity mapping."""
    engine = PolicyVerifierEngine(None, None)
    
    # Critical (90-100)
    assert engine._determine_severity({"priority": 95}) == ViolationSeverity.CRITICAL
    assert engine._determine_severity({"priority": 90}) == ViolationSeverity.CRITICAL
    
    # High (70-89)
    assert engine._determine_severity({"priority": 80}) == ViolationSeverity.HIGH
    assert engine._determine_severity({"priority": 70}) == ViolationSeverity.HIGH
    
    # Medium (40-69)
    assert engine._determine_severity({"priority": 50}) == ViolationSeverity.MEDIUM
    assert engine._determine_severity({"priority": 40}) == ViolationSeverity.MEDIUM
    
    # Low (0-39)
    assert engine._determine_severity({"priority": 20}) == ViolationSeverity.LOW
    assert engine._determine_severity({"priority": 0}) == ViolationSeverity.LOW

# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_multiple_violations(mock_registry, mock_publisher):
    """Test handling multiple policy violations simultaneously."""
    engine = PolicyVerifierEngine(mock_registry, mock_publisher)
    
    context = EvaluationContext(
        model_id="gpt-4",  # Expensive, not in allowed vendors
        vendor_id="openai",
        estimated_tokens=1_000_000,  # Expensive request
        prompt="A" * 60000,  # Too long
        correlation_id="test-multi-1"
    )
    
    result = await engine.evaluate_pre_flight(context)
    
    # Should fail multiple policies
    assert result.passed is False
    assert len(result.violations) >= 2  # Cost, vendor, and/or behavioral
    
    # Verify different violation types
    categories = {v.category for v in result.violations}
    assert PolicyCategory.COST in categories or PolicyCategory.VENDOR in categories

@pytest.mark.asyncio
async def test_warning_handling(mock_registry, mock_publisher):
    """Test that warnings are collected even when policies pass."""
    engine = PolicyVerifierEngine(mock_registry, mock_publisher)
    
    context = EvaluationContext(
        model_id="gemini-2.5-flash",
        vendor_id="google",
        estimated_tokens=5000,  # Medium size
        prompt="Medium prompt",
        correlation_id="test-warn-1"
    )
    
    result = await engine.evaluate_pre_flight(context)
    
    # Should pass but may have warnings
    assert result.passed is True
    # Warnings might be present depending on thresholds
    # Just verify structure
    assert isinstance(result.warnings, list)
