import sys
import os
import logging
from typing import List, Dict

# Add src to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.model_registry import ModelRegistry, ModelProfile, CapabilityTier, DuplicateModelError

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Sample Data
SAMPLE_MODELS: List[Dict] = [
    # --- Tier 3 (High Intelligence) ---
    {
        "model_id": "gpt-4-turbo",
        "vendor_id": "OpenAI",
        "capability_tier": CapabilityTier.TIER_3,
        "context_window": 128000,
        "cost_in_per_mil": 10.00,
        "cost_out_per_mil": 30.00,
        "function_call_support": True
    },
    {
        "model_id": "claude-3-opus",
        "vendor_id": "Anthropic",
        "capability_tier": CapabilityTier.TIER_3,
        "context_window": 200000,
        "cost_in_per_mil": 15.00,
        "cost_out_per_mil": 75.00,
        "function_call_support": True
    },
    # --- Tier 2 (Balanced) ---
    {
        "model_id": "claude-3-sonnet",
        "vendor_id": "Anthropic",
        "capability_tier": CapabilityTier.TIER_2,
        "context_window": 200000,
        "cost_in_per_mil": 3.00,
        "cost_out_per_mil": 15.00,
        "function_call_support": True
    },
    {
        "model_id": "gemini-1.5-pro",
        "vendor_id": "Google",
        "capability_tier": CapabilityTier.TIER_2,
        "context_window": 1000000,
        "cost_in_per_mil": 3.50,
        "cost_out_per_mil": 10.50,
        "function_call_support": True
    },
    # --- Tier 1 (Fast/Cheap) ---
    {
        "model_id": "gpt-3.5-turbo",
        "vendor_id": "OpenAI",
        "capability_tier": CapabilityTier.TIER_1,
        "context_window": 16385,
        "cost_in_per_mil": 0.50,
        "cost_out_per_mil": 1.50,
        "function_call_support": True
    },
    {
        "model_id": "mixtral-8x7b",
        "vendor_id": "Mistral AI",
        "capability_tier": CapabilityTier.TIER_1,
        "context_window": 32000,
        "cost_in_per_mil": 0.25,
        "cost_out_per_mil": 0.25,
        "function_call_support": False
    },
    # --- Local / Open Source ---
    {
        "model_id": "llama-3-8b-local",
        "vendor_id": "Meta",
        "capability_tier": CapabilityTier.TIER_1,
        "context_window": 8192,
        "cost_in_per_mil": 0.0,
        "cost_out_per_mil": 0.0,
        "function_call_support": False
    }
]

def populate():
    db_conn = os.getenv("DB_CONNECTION_STRING", "postgresql://user:pass@localhost:5432/ims_db")
    registry = ModelRegistry(db_conn)
    
    success_count = 0
    
    logger.info(f"Starting population of {len(SAMPLE_MODELS)} models...")

    for data in SAMPLE_MODELS:
        try:
            profile = ModelProfile(**data)
            registry.register_model(profile)
            logger.info(f"✔ Registered: {profile.model_id}")
            success_count += 1
        except DuplicateModelError:
            logger.warning(f"⚠ Skipped (Duplicate): {data['model_id']}")
        except Exception as e:
            logger.error(f"✘ Error registering {data['model_id']}: {e}")

    logger.info(f"Population complete. {success_count}/{len(SAMPLE_MODELS)} new models added.")

if __name__ == "__main__":
    populate()
