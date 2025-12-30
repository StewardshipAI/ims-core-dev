"""
Unit tests for the Agent Control Flow (ACF) state machine.
"""

import pytest
from unittest.mock import Mock
from src.core.acf import AgentControlFlow, RequestContext, RequestState, StateTransitionError

# Mock dependencies for initialization
@pytest.fixture
def mock_policy_engine():
    return Mock()

@pytest.fixture
def mock_pcr_service():
    return Mock()

@pytest.fixture
def mock_model_executor():
    return Mock()

def test_acf_initialization(mock_policy_engine, mock_pcr_service, mock_model_executor):
    """
    Tests if the AgentControlFlow class can be initialized without errors.
    This is a basic smoke test to ensure the file is syntactically correct and importable.
    """
    try:
        acf = AgentControlFlow(
            policy_engine=mock_policy_engine,
            pcr_service=mock_pcr_service,
            model_executor=mock_model_executor
        )
        assert acf is not None, "ACF instance should not be None"
    except Exception as e:
        pytest.fail(f"AgentControlFlow initialization failed: {e}")

def test_request_context_creation():
    """
    Tests if the RequestContext can be created with default values.
    """
    context = RequestContext(request_id="test-req-123", user_id="test-user", prompt="Hello")
    assert context.request_id == "test-req-123"
    assert context.current_state == RequestState.RECEIVED
    assert context.retry_count == 0

# A more advanced test to show transition logic could be added later
# For now, this confirms the file is operational enough for a basic import and instantiation.
