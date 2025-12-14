import pytest
from src.data.model_registry import (
    ModelRegistry, 
    ModelProfile, 
    CapabilityTier, 
    DuplicateModelError, 
    ValidationError
)

class TestModelRegistryCRUD:

    # --- Register Tests ---

    def test_register_model_success(self, registry, sample_model_tier_1):
        """Test successful registration of a valid model."""
        model_id = registry.register_model(sample_model_tier_1)
        assert model_id == sample_model_tier_1.model_id
        
        # Verify in DB
        fetched = registry.get_model(model_id)
        assert fetched is not None
        assert fetched.vendor_id == "TestVendor"
        assert fetched.is_active is True

    def test_register_duplicate_error(self, registry, sample_model_tier_1):
        """Test that registering a duplicate ID raises DuplicateModelError."""
        registry.register_model(sample_model_tier_1)
        
        with pytest.raises(DuplicateModelError):
            registry.register_model(sample_model_tier_1)

    def test_register_validation_negative_cost(self, registry, sample_model_tier_1):
        """Test validation for negative costs."""
        sample_model_tier_1.cost_in_per_mil = -1.0
        with pytest.raises(ValidationError):
            registry.register_model(sample_model_tier_1)

    # --- Get Tests ---

    def test_get_model_found(self, registry, sample_model_tier_1):
        """Test retrieving an existing model."""
        registry.register_model(sample_model_tier_1)
        result = registry.get_model(sample_model_tier_1.model_id)
        assert result.model_id == sample_model_tier_1.model_id

    def test_get_model_not_found(self, registry):
        """Test retrieving a non-existent model returns None."""
        result = registry.get_model("non-existent-id")
        assert result is None

    # --- Filter Tests ---

    def test_filter_models_single_filter(self, registry, sample_model_tier_1, sample_model_tier_3):
        """Test filtering by a single criteria (Tier)."""
        registry.register_model(sample_model_tier_1)
        registry.register_model(sample_model_tier_3)
        
        results = registry.filter_models(capability_tier=CapabilityTier.TIER_3)
        assert len(results) == 1
        assert results[0].model_id == sample_model_tier_3.model_id

    def test_filter_models_multiple_filters(self, registry, sample_model_tier_1, sample_model_tier_3):
        """Test filtering by multiple criteria (Tier + Cost)."""
        registry.register_model(sample_model_tier_1)
        registry.register_model(sample_model_tier_3)
        
        # Filter: Tier 1 AND Max Cost Input < 1.0
        results = registry.filter_models(
            capability_tier=CapabilityTier.TIER_1, 
            max_cost_in=1.0
        )
        assert len(results) == 1
        assert results[0].model_id == sample_model_tier_1.model_id

    def test_filter_models_no_matches(self, registry, sample_model_tier_1):
        """Test filter returns empty list when no models match."""
        registry.register_model(sample_model_tier_1)
        results = registry.filter_models(vendor_id="NonExistentVendor")
        assert results == []

    # --- Update Tests ---

    def test_update_model_success(self, registry, sample_model_tier_1):
        """Test updating mutable fields."""
        registry.register_model(sample_model_tier_1)
        
        updates = {"cost_in_per_mil": 99.99, "function_call_support": False}
        success = registry.update_model(sample_model_tier_1.model_id, updates)
        
        assert success is True
        updated = registry.get_model(sample_model_tier_1.model_id)
        assert updated.cost_in_per_mil == 99.99
        assert updated.function_call_support is False

    def test_update_model_immutable_fields(self, registry, sample_model_tier_1):
        """Test that updating immutable fields raises ValidationError."""
        registry.register_model(sample_model_tier_1)
        
        with pytest.raises(ValidationError):
            registry.update_model(sample_model_tier_1.model_id, {"vendor_id": "NewVendor"})

    def test_update_non_existent_model(self, registry):
        """Test updating a model that doesn't exist."""
        success = registry.update_model("fake-id", {"cost_in_per_mil": 10})
        assert success is False

    # --- Deactivate Tests ---

    def test_deactivate_model(self, registry, sample_model_tier_1):
        """Test soft deletion."""
        registry.register_model(sample_model_tier_1)
        
        success = registry.deactivate_model(sample_model_tier_1.model_id)
        assert success is True
        
        # Verify it is marked inactive
        model = registry.get_model(sample_model_tier_1.model_id)
        assert model.is_active is False
        
        # Verify default filter excludes it
        results = registry.filter_models()
        assert sample_model_tier_1.model_id not in [m.model_id for m in results]
        
        # Verify explicit include_inactive includes it
        results_all = registry.filter_models(include_inactive=True)
        assert sample_model_tier_1.model_id in [m.model_id for m in results_all]
