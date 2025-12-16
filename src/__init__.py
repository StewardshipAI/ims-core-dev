"""
IMS Core - Intelligent Model Switching
"""

__version__ = "0.1.0"
__author__ = "Stewardship Solutions"
__email__ = "contact@stewardshipsolutions.com"

from src.data.model_registry import (
    ModelRegistry,
    ModelProfile,
    CapabilityTier,
    ModelRegistryError,
    DuplicateModelError,
    ValidationError,
)

__all__ = [
    "ModelRegistry",
    "ModelProfile",
    "CapabilityTier",
    "ModelRegistryError",
    "DuplicateModelError",
    "ValidationError",
]
