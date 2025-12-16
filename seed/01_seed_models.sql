-- =============================================================================
-- IMS SEED DATA
-- Purpose: Populate registry with primary models for testing routing logic
-- =============================================================================

INSERT INTO models (model_id, vendor_id, capability_tier, context_window, cost_in_per_mil, cost_out_per_mil, function_call_support, is_active)
VALUES
    -- GOOGLE (The Backbone)
    ('gemini-2.0-flash-exp', 'google', 'Tier_1', 1000000, 0.000000, 0.000000, TRUE, TRUE), -- Free Tier King
    ('gemini-1.5-pro-latest', 'google', 'Tier_3', 2000000, 1.250000, 5.000000, TRUE, TRUE),
    ('gemini-1.5-flash-8b', 'google', 'Tier_1', 1000000, 0.037500, 0.150000, TRUE, TRUE),

    -- OPENAI (The Fallback)
    ('gpt-4o-mini', 'openai', 'Tier_1', 128000, 0.150000, 0.600000, TRUE, TRUE),
    ('gpt-4o', 'openai', 'Tier_2', 128000, 2.500000, 10.000000, TRUE, TRUE),
    ('o1-preview', 'openai', 'Tier_3', 128000, 15.000000, 60.000000, FALSE, TRUE),

    -- ANTHROPIC (The Specialist)
    ('claude-3-5-haiku-20241022', 'anthropic', 'Tier_1', 200000, 0.800000, 4.000000, TRUE, TRUE),
    ('claude-3-5-sonnet-20241022', 'anthropic', 'Tier_2', 200000, 3.000000, 15.000000, TRUE, TRUE),
    ('claude-3-opus-20240229', 'anthropic', 'Tier_3', 200000, 15.000000, 75.000000, TRUE, TRUE),
    
    -- LOCAL / OPEN SOURCE (The Future)
    ('llama-4-scout-local', 'meta', 'Tier_2', 128000, 0.000000, 0.000000, FALSE, FALSE) -- Inactive by default
ON CONFLICT (model_id) 
DO UPDATE SET 
    cost_in_per_mil = EXCLUDED.cost_in_per_mil,
    cost_out_per_mil = EXCLUDED.cost_out_per_mil,
    updated_at = CURRENT_TIMESTAMP;
