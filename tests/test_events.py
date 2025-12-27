import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.core.events import EventPublisher, rabbitmq
from src.schemas.events import CloudEvent
from aio_pika import DeliveryMode

@pytest.mark.asyncio
async def test_cloud_event_serialization():
    """Verify CloudEvent Pydantic model serialization."""
    event = CloudEvent(
        source="/test",
        type="test.event",
        correlation_id="123",
        data={"foo": "bar"}
    )
    
    json_str = event.model_dump_json()
    data = json.loads(json_str)
    
    assert data["specversion"] == "1.0"
    assert data["source"] == "/test"
    assert data["type"] == "test.event"
    assert data["data"] == {"foo": "bar"}
    assert "time" in data
    assert "id" in data

@pytest.mark.asyncio
async def test_publisher_routing():
    """Verify EventPublisher routes to correct exchanges."""
    mock_channel = AsyncMock()
    mock_exchange = AsyncMock()
    mock_channel.get_exchange.return_value = mock_exchange
    
    publisher = EventPublisher(mock_channel)
    
    # Test 1: Model Event -> models.events
    event1 = CloudEvent(source="/t", type="model.registered", data={})
    await publisher.publish(event1)
    
    mock_channel.get_exchange.assert_called_with("models.events")
    mock_exchange.publish.assert_called_once()
    
    # Verify persistence
    call_args = mock_exchange.publish.call_args
    message = call_args[0][0]
    assert message.delivery_mode == DeliveryMode.PERSISTENT
    assert message.headers is None or "app_id" in message.app_id

    # Test 2: Error Event -> errors.events
    mock_channel.reset_mock()
    event2 = CloudEvent(source="/t", type="api.error.500", data={})
    await publisher.publish(event2)
    mock_channel.get_exchange.assert_called_with("errors.events")

    # Test 3: Metric Event -> metrics.events (default)
    mock_channel.reset_mock()
    event3 = CloudEvent(source="/t", type="some.metric", data={})
    await publisher.publish(event3)
    mock_channel.get_exchange.assert_called_with("metrics.events")
