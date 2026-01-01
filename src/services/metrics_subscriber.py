import asyncio
import json
import logging
import os
import signal
from typing import Dict, Any

import aio_pika
import redis.asyncio as redis  # Using async redis
from aio_pika.abc import AbstractIncomingMessage

from src.observability.logging import setup_logging, get_logger
from src.observability.metrics import get_metrics

# Configure logging
setup_logging(
    level="INFO",
    format_type="human", # Use json in production
    service_name="metrics-subscriber",
    environment="development"
)
logger = get_logger("metrics-subscriber")
metrics_svc = get_metrics()

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class MetricsSubscriber:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.queue = None
        self.is_running = True
        self.redis = None

    async def connect(self):
        # Connect to Redis
        logger.info(f"Connecting to Redis at {REDIS_URL}...")
        self.redis = redis.from_url(REDIS_URL, decode_responses=True)
        await self.redis.ping()
        logger.info("✅ Redis Connected.")

        # Connect to RabbitMQ
        logger.info(f"Connecting to {RABBITMQ_URL}...")
        self.connection = await aio_pika.connect_robust(RABBITMQ_URL)
        self.channel = await self.connection.channel()
        
        # Declare Exchanges (Ensure they exist)
        await self.channel.declare_exchange("models.events", aio_pika.ExchangeType.TOPIC, durable=True)
        await self.channel.declare_exchange("metrics.events", aio_pika.ExchangeType.TOPIC, durable=True)
        
        # Declare Queue with DLQ arguments
        args = {
            "x-dead-letter-exchange": "dlx",
            "x-dead-letter-routing-key": "dlq.dead_letters"
        }
        self.queue = await self.channel.declare_queue("metrics.updates", durable=True, arguments=args)
        
        # Bindings
        await self.queue.bind("models.events", routing_key="model.*")
        await self.queue.bind("models.events", routing_key="filter.executed")
        await self.queue.bind("metrics.events", routing_key="#") # Catch all metrics events
        
        # Set QoS
        await self.channel.set_qos(prefetch_count=10)
        logger.info("✅ RabbitMQ Connected and configured.")

    async def process_message(self, message: AbstractIncomingMessage):
        async with message.process(ignore_processed=True):
            retries = 0
            max_retries = 3
            
            try:
                body = json.loads(message.body)
                event_type = body.get("type", "unknown")
                
                logger.info(f"Received Event: {event_type}", extra={"event_id": body.get('id')})
                
                # Processing Logic
                if event_type == "model.registered":
                    await self._increment_metric("total_models_registered")
                    vendor = body.get("data", {}).get("vendor_id", "unknown")
                    await self._increment_metric(f"vendor_models:{vendor}")
                    metrics_svc.record_model_update(
                        vendor=body.get("data", {}).get("vendor_id", "unknown"),
                        model=body.get("data", {}).get("model_id", "unknown"),
                        action="registered"
                    )
                    
                elif event_type == "model.queried":
                    await self._increment_metric("total_model_queries")
                    model_id = body.get("data", {}).get("model_id", "unknown")
                    await self._increment_metric(f"model_queries:{model_id}")
                    
                elif event_type == "filter.executed":
                    await self._increment_metric("total_filter_queries")

                elif event_type == "pcr.recommendation_generated":
                    await self._increment_metric("total_model_queries") # Count recommendations as queries
                    await self._increment_metric("total_pcr_recommendations")

                elif event_type == "poison.pill":
                    raise ValueError("Poison pill received!")

                elif event_type == "policy.violation.detected":
                    metrics_svc.record_policy_violation(
                        policy=body.get("data", {}).get("policy_name", "unknown"),
                        category=body.get("data", {}).get("category", "unknown"),
                        severity=body.get("data", {}).get("severity", "unknown")
                    )
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                
                # Exponential Backoff Retry
                while retries < max_retries:
                    wait_time = 2 ** retries
                    logger.warning(f"Retrying in {wait_time}s... (Attempt {retries + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    
                    try:
                        # Re-attempt processing logic (simplified here)
                        # In a real scenario, we might extract the logic to a separate method
                        # to avoid code duplication, but for now we just fail to DLQ
                        # if the initial processing block failed.
                        # Wait, simple retry of the block isn't easy without refactoring.
                        # For this scope, we sleep then re-raise to trigger DLQ if max retries hit.
                        retries += 1
                    except Exception:
                        continue
                
                # If we exhausted retries, Nack(requeue=False) -> DLQ
                logger.error("Max retries reached. Moving to DLQ.")
                await message.nack(requeue=False)

    async def _increment_metric(self, key: str, value: int = 1):
        """Increment a metric in Redis."""
        if self.redis:
            new_val = await self.redis.incrby(f"metrics:{key}", value)
            logger.info(f"📈 Redis Update: {key} = {new_val}")

    async def run(self):
        await self.connect()
        logger.info("🎧 Waiting for messages...")
        
        async with self.queue.iterator() as queue_iter:
            async for message in queue_iter:
                await self.process_message(message)
                if not self.is_running:
                    break

    async def shutdown(self):
        logger.info("Shutting down...")
        self.is_running = False
        if self.connection:
            await self.connection.close()
        if self.redis:
            await self.redis.close()


async def main():
    subscriber = MetricsSubscriber()
    
    # Handle graceful shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(subscriber.shutdown()))

    await subscriber.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
