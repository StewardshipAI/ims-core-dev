import asyncio
import json
import logging
import os
from typing import Optional

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractRobustConnection, DeliveryMode

from src.schemas.events import CloudEvent

logger = logging.getLogger("ims.events")

class RabbitMQ:
    """
    Singleton manager for RabbitMQ connection and channel.
    """
    connection: Optional[AbstractRobustConnection] = None
    channel: Optional[AbstractChannel] = None
    
    def __init__(self):
        self._url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

    async def connect(self):
        """Establish connection and channel."""
        if self.connection and not self.connection.is_closed:
            return

        logger.info(f"Connecting to RabbitMQ at {self._url}...")
        try:
            # automatic recovery is enabled by default with connect_robust
            self.connection = await aio_pika.connect_robust(self._url)
            self.channel = await self.connection.channel()
            
            # Declare exchanges to ensure they exist
            await self._setup_topology()
            
            logger.info("✅ RabbitMQ Connected.")
        except Exception as e:
            logger.error(f"❌ RabbitMQ connection failed: {e}")
            raise

    async def close(self):
        """Gracefully close connection."""
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()
        logger.info("RabbitMQ connection closed.")

    async def _setup_topology(self):
        """Declare the standard exchanges and DLQ infrastructure."""
        if not self.channel:
            return
            
        # 1. Setup Dead Letter Infrastructure
        # DLX (Dead Letter Exchange)
        await self.channel.declare_exchange("dlx", aio_pika.ExchangeType.DIRECT, durable=True)
        # DLQ (Dead Letter Queue)
        dlq = await self.channel.declare_queue("dlq.dead_letters", durable=True)
        # Bind DLQ to DLX
        await dlq.bind("dlx", routing_key="dlq.dead_letters")

        # 2. Setup Standard Domain Exchanges
        exchanges = ["models.events", "metrics.events", "errors.events"]
        for name in exchanges:
            await self.channel.declare_exchange(
                name, 
                aio_pika.ExchangeType.TOPIC, 
                durable=True
            )

    def get_channel(self) -> Optional[AbstractChannel]:
        return self.channel


# Global Singleton
rabbitmq = RabbitMQ()


class EventPublisher:
    """
    Service for publishing domain events.
    """
    def __init__(self, channel: AbstractChannel):
        self.channel = channel

    async def publish(self, event: CloudEvent):
        """
        Publish a CloudEvent to the appropriate exchange based on its type.
        """
        exchange_name = self._get_exchange_for_type(event.type)
        routing_key = event.type
        
        # Get exchange (we assume it exists from setup_topology)
        exchange = await self.channel.get_exchange(exchange_name)
        
        message = aio_pika.Message(
            body=event.model_dump_json().encode(),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            correlation_id=event.correlation_id,
            app_id="ims-core"
        )
        
        await exchange.publish(message, routing_key=routing_key)
        logger.debug(f"Published {event.type} to {exchange_name}")

    def _get_exchange_for_type(self, event_type: str) -> str:
        if event_type.startswith("model."):
            return "models.events"
        elif event_type.startswith("api.error"):
            return "errors.events"
        else:
            return "metrics.events"


async def get_event_publisher() -> EventPublisher:
    """FastAPI Dependency"""
    channel = rabbitmq.get_channel()
    if not channel:
        # In a real app we might want to retry or fail fast
        # For now, if RabbitMQ is down, we might raise 503
        raise RuntimeError("RabbitMQ channel not available")
    return EventPublisher(channel)
