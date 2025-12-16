-- =============================================================================
-- IMS MODEL REGISTRY SCHEMA - PRODUCTION READY (All Critical Fixes Applied)
-- =============================================================================

-- 1. UTILITY FUNCTIONS
-- Function to automatically update 'updated_at' timestamp
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. TABLE DEFINITION
CREATE TABLE IF NOT EXISTS models (
    -- Primary Identity
    model_id VARCHAR(100) PRIMARY KEY,
    
    -- Vendor Grouping
    vendor_id VARCHAR(50) NOT NULL,
    
    -- Capability & Routing Logic
    capability_tier VARCHAR(20) NOT NULL CHECK (capability_tier IN ('Tier_1', 'Tier_2', 'Tier_3')),
    
    -- Technical Specs
    context_window INTEGER NOT NULL CHECK (context_window > 0 AND context_window <= 10000000),
    function_call_support BOOLEAN DEFAULT FALSE,
    
    -- Economics (Cost per 1M tokens)
    cost_in_per_mil DECIMAL(10, 6) NOT NULL CHECK (cost_in_per_mil >= 0 AND cost_in_per_mil <= 1000),
    cost_out_per_mil DECIMAL(10, 6) NOT NULL CHECK (cost_out_per_mil >= 0 AND cost_out_per_mil <= 1000),
    
    -- Operational State
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Audit Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- ✅ Additional constraints for data integrity
    CONSTRAINT valid_model_id CHECK (LENGTH(model_id) > 0),
    CONSTRAINT valid_vendor_id CHECK (LENGTH(vendor_id) > 0)
);

-- 3. INDEXING STRATEGY (Original + ✅ FIX #4: Missing cost index)

-- Single Column Indexes
CREATE INDEX IF NOT EXISTS idx_vendor_id ON models(vendor_id);
CREATE INDEX IF NOT EXISTS idx_capability_tier ON models(capability_tier);
CREATE INDEX IF NOT EXISTS idx_is_active ON models(is_active);
CREATE INDEX IF NOT EXISTS idx_function_call ON models(function_call_support);

-- ✅ FIX #4: Add index for cost filtering queries
-- Partial index (only active models) for better performance
CREATE INDEX IF NOT EXISTS idx_cost_in_active ON models(cost_in_per_mil) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_cost_out_active ON models(cost_out_per_mil) WHERE is_active = TRUE;

-- Composite Indexes (Optimized for Router Queries)
-- Usage: "Get me all active Tier 1 models from Google"
CREATE INDEX IF NOT EXISTS idx_tier_vendor ON models(capability_tier, vendor_id);

-- Usage: "Get me any active model in Tier 1" (High frequency query)
CREATE INDEX IF NOT EXISTS idx_active_tier ON models(is_active, capability_tier);

-- ✅ NEW: Composite index for cost+tier filtering (common query pattern)
CREATE INDEX IF NOT EXISTS idx_tier_cost ON models(capability_tier, cost_in_per_mil) WHERE is_active = TRUE;

-- ✅ NEW: Index for context window filtering
CREATE INDEX IF NOT EXISTS idx_context_window ON models(context_window) WHERE is_active = TRUE;

-- 4. TRIGGERS
-- Auto-update updated_at on record modification
DROP TRIGGER IF EXISTS update_models_timestamp ON models;
CREATE TRIGGER update_models_timestamp
    BEFORE UPDATE ON models
    FOR EACH ROW
    EXECUTE PROCEDURE update_timestamp();

-- 5. COMMENTS (For auto-documentation and maintenance)
COMMENT ON TABLE models IS 'IMS Model Registry: Master table for all available LLM models';
COMMENT ON COLUMN models.model_id IS 'Unique identifier for the model (e.g., gpt-4-turbo)';
COMMENT ON COLUMN models.vendor_id IS 'Vendor/provider name (e.g., OpenAI, Anthropic, Google)';
COMMENT ON COLUMN models.capability_tier IS 'Model capability classification: Tier_1 (fast/cheap), Tier_2 (balanced), Tier_3 (advanced reasoning)';
COMMENT ON COLUMN models.context_window IS 'Maximum context window in tokens (1 to 10M)';
COMMENT ON COLUMN models.cost_in_per_mil IS 'Cost per 1 million input tokens in USD';
COMMENT ON COLUMN models.cost_out_per_mil IS 'Cost per 1 million output tokens in USD';
COMMENT ON COLUMN models.function_call_support IS 'Whether model supports function calling / tool use';
COMMENT ON COLUMN models.is_active IS 'Soft delete flag: false means deactivated but preserved for audit';

-- 6. INITIAL DATA VALIDATION VIEW (Optional but useful for monitoring)
CREATE OR REPLACE VIEW model_registry_stats AS
SELECT 
    capability_tier,
    COUNT(*) as total_models,
    COUNT(*) FILTER (WHERE is_active = TRUE) as active_models,
    COUNT(*) FILTER (WHERE is_active = FALSE) as inactive_models,
    AVG(cost_in_per_mil) as avg_input_cost,
    AVG(cost_out_per_mil) as avg_output_cost,
    MIN(context_window) as min_context,
    MAX(context_window) as max_context
FROM models
GROUP BY capability_tier
ORDER BY capability_tier;

COMMENT ON VIEW model_registry_stats IS 'Real-time statistics for monitoring registry health';

-- 7. PERFORMANCE ANALYSIS HELPER
-- Use this to check if indexes are being used efficiently
-- Run: EXPLAIN ANALYZE SELECT * FROM models WHERE is_active = TRUE AND capability_tier = 'Tier_1';

-- 8. ADMIN SAFETY: Prevent accidental hard deletes
-- Create a role with limited permissions (optional security hardening)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ims_readonly') THEN
        CREATE ROLE ims_readonly;
    END IF;
END
$$;

GRANT SELECT ON models TO ims_readonly;
GRANT SELECT ON model_registry_stats TO ims_readonly;

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================

-- 🎯 USAGE EXAMPLES FOR TESTING:

-- Example 1: Check if indexes are working
-- EXPLAIN ANALYZE SELECT * FROM models WHERE is_active = TRUE AND capability_tier = 'Tier_1';
-- Should show "Index Scan using idx_active_tier"

-- Example 2: Check cost filtering performance
-- EXPLAIN ANALYZE SELECT * FROM models WHERE cost_in_per_mil < 5.0 AND is_active = TRUE;
-- Should show "Index Scan using idx_cost_in_active"

-- Example 3: View registry statistics
-- SELECT * FROM model_registry_stats;

-- Example 4: Find all models that meet specific criteria
-- SELECT model_id, vendor_id, cost_in_per_mil 
-- FROM models 
-- WHERE capability_tier = 'Tier_2' 
--   AND cost_in_per_mil < 10.0 
--   AND is_active = TRUE
--   AND function_call_support = TRUE
-- ORDER BY cost_in_per_mil ASC;
