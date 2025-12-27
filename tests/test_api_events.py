import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from src.api.model_registry_api import app, get_event_publisher

client = TestClient(app)

# Mock Data
VALID_API_KEY = "test-admin-key-must-be-32-chars-long!!"
MOCK_MODEL = {
    "model_id": "gpt-4-test",
    "vendor_id": "OpenAI",
    "capability_tier": "Tier_1",
    "context_window": 128000,
    "cost_in_per_mil": 10.0,
    "cost_out_per_mil": 30.0,
    "function_call_support": True,
    "is_active": True
}

@pytest.fixture
def mock_publisher():
    publisher = AsyncMock()
    publisher.publish = AsyncMock()
    return publisher

@pytest.fixture
def override_deps(mock_publisher):
    app.dependency_overrides[get_event_publisher] = lambda: mock_publisher
    yield
    app.dependency_overrides = {}

def test_register_model_emits_event(override_deps, mock_publisher):
    """Test that registering a model emits a 'model.registered' event."""
    
    # We also need to mock the registry to avoid DB calls
    with patch("src.api.model_registry_api.registry") as mock_registry:
        mock_registry.register_model.return_value = "gpt-4-test"
        
        # Override env var for key check (or just mock verify_admin)
        with patch("src.api.model_registry_api.ADMIN_API_KEY", VALID_API_KEY):
            response = client.post(
                "/api/v1/models/register",
                json=MOCK_MODEL,
                headers={"X-Admin-Key": VALID_API_KEY}
            )
            
            assert response.status_code == 201
            assert response.json()["model_id"] == "gpt-4-test"
            
            # Verify Event Publish
            assert mock_publisher.publish.called
            event = mock_publisher.publish.call_args[0][0]
            assert event.type == "model.registered"
            assert event.data["model_id"] == "gpt-4-test"
