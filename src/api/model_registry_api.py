# FastAPI Model Registry API - PRODUCTION READY (All Critical Fixes Applied)
# ✅ FIX #10: Fixed route ordering (/filter BEFORE /{model_id})

import os
import logging
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, status, Query
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
import redis.asyncio as redis

# Import our data layer
from src.data.model_registry import (
    ModelProfile, 
    CapabilityTier, 
    DuplicateModelError, 
    ValidationError,
    ModelRegistryError
)
from src.api.registry_singleton import registry # Import the singleton

# RabbitMQ Integration
from src.core.events import rabbitmq, get_event_publisher, EventPublisher
from src.schemas.events import CloudEvent

# Load environment variables
load_dotenv()

# --- Configuration & Setup ---

from src.observability.logging import setup_logging, get_logger

from src.observability.tracing import initialize_tracing



setup_logging(

    level="INFO",

    format_type="human", # Use json in production

    service_name="ims-core",

    environment="development"

)



logger = get_logger("api")



# ✅ FIX #6: Enforce strong API key (no weak defaults)

# ... (skipping env var checks)

# Import PCR Router

from src.api.pcr_router import router as pcr_router

from src.api.gateway_router import router as gateway_router

from src.api.compliance_router import router as compliance_router

from src.api.observability_router import router as observability_router

from src.api.auth_utils import verify_admin



# Rate Limiter Setup

limiter = Limiter(key_func=get_remote_address)



@asynccontextmanager

async def lifespan(app: FastAPI):

    """Application lifespan handler for startup/shutdown."""

    # Startup

    logger.info("IMS Model Registry API starting up...")

    

    # Initialize Tracing

    initialize_tracing(

        service_name="ims-core",

        environment="development",

        jaeger_endpoint="ims-jaeger:6831"

    )

    

    # Initialize RabbitMQ

    await rabbitmq.connect()

    # ... (skipping registry health check)

    logger.info("Startup health check passed")

    

    yield

    

    # Shutdown

    logger.info("Shutting down...")

    await rabbitmq.close()

    registry.close_pool()

    logger.info("Connection pool closed")



app = FastAPI(

# ... (skipping middle)

app.include_router(pcr_router)

app.include_router(gateway_router)

app.include_router(compliance_router)

app.include_router(observability_router)



if __name__ == "__main__":
    import uvicorn
    
    # ✅ Production-ready Uvicorn configuration
    uvicorn.run(
        "model_registry_api:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True,
        workers=4,  # Multiple workers for production
        limit_concurrency=100,  # Prevent overload
        timeout_keep_alive=30
    )
