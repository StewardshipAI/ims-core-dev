-- =============================================================================
-- IMS POLICY ENFORCEMENT ENGINE - SEED POLICIES
-- Initial policy definitions for testing and production
-- =============================================================================
-- Version: 1.0.0
-- Date: 2025-12-31

-- =============================================================================
-- COST POLICIES - Budget Management & Cost Control
-- =============================================================================

INSERT INTO policies (name, category, enabled, priority, constraints, evaluation_type, action_on_violation, description, tags)
VALUES
    -- Critical: Free Tier Daily Budget
    (
        'free-tier-daily-budget',
        'cost',
        TRUE,
        95, -- Critical
        '{
            "max_daily_cost": 1.0,
            "max_cost_per_request": 0.01,
            "reset_hour_utc": 0
        }'::JSONB,
        'pre_flight',
        'block',
        'Enforce strict daily budget limit of $1.00 for free tier users. Blocks requests that would exceed limit.',
        ARRAY['free-tier', 'budget', 'critical']
    ),
    
    -- High: Expensive Model Warning
    (
        'expensive-model-threshold',
        'cost',
        TRUE,
        70, -- High
        '{
            "max_cost_per_mil_tokens": 10.0,
            "warn_threshold": 5.0
        }'::JSONB,
        'pre_flight',
        'warn',
        'Warn when using models that cost more than $10 per million tokens. Suggest cheaper alternatives.',
        ARRAY['cost-optimization', 'warnings']
    ),
    
    -- Medium: Monthly Budget Cap
    (
        'monthly-budget-cap',
        'cost',
        TRUE,
        60, -- Medium
        '{
            "max_monthly_cost": 100.0,
            "alert_threshold": 80.0
        }'::JSONB,
        'continuous',
        'warn',
        'Track monthly spending and alert when approaching $100 limit. Alert at 80% threshold.',
        ARRAY['budget', 'monthly', 'tracking']
    ),
    
    -- Medium: Cost Per Request Cap
    (
        'request-cost-limit',
        'cost',
        TRUE,
        65, -- Medium
        '{
            "max_cost_per_request": 0.05,
            "warn_threshold": 0.03
        }'::JSONB,
        'pre_flight',
        'degrade',
        'Cap individual request cost at $0.05. Attempt fallback to cheaper model before blocking.',
        ARRAY['cost-optimization', 'fallback']
    );

-- =============================================================================
-- VENDOR POLICIES - Provider Management & Compliance
-- =============================================================================

INSERT INTO policies (name, category, enabled, priority, constraints, evaluation_type, action_on_violation, description, tags)
VALUES
    -- High: Approved Vendors Only
    (
        'approved-vendors-only',
        'vendor',
        TRUE,
        80, -- High
        '{
            "allowed_vendors": ["google", "anthropic", "openai"],
            "require_approval": true
        }'::JSONB,
        'pre_flight',
        'block',
        'Only allow requests to pre-approved vendors: Google, Anthropic, OpenAI. Block all others.',
        ARRAY['security', 'compliance', 'vendor-management']
    ),
    
    -- Medium: Vendor Diversity
    (
        'vendor-diversity-requirement',
        'vendor',
        FALSE, -- Disabled by default
        50, -- Medium
        '{
            "min_vendor_count": 2,
            "evaluation_window_hours": 24
        }'::JSONB,
        'continuous',
        'warn',
        'Encourage using multiple vendors to avoid single-vendor dependency. Track vendor usage over 24h.',
        ARRAY['reliability', 'vendor-diversity']
    ),
    
    -- Low: Vendor Performance Tracking
    (
        'vendor-performance-baseline',
        'vendor',
        TRUE,
        40, -- Low
        '{
            "track_latency": true,
            "track_errors": true,
            "min_success_rate": 0.95
        }'::JSONB,
        'post_execution',
        'log',
        'Track vendor performance metrics. Log when success rate drops below 95%.',
        ARRAY['monitoring', 'performance']
    );

-- =============================================================================
-- PERFORMANCE POLICIES - SLA & Quality Guarantees
-- =============================================================================

INSERT INTO policies (name, category, enabled, priority, constraints, evaluation_type, action_on_violation, description, tags)
VALUES
    -- High: Latency SLA
    (
        'latency-sla-5-seconds',
        'performance',
        TRUE,
        75, -- High
        '{
            "max_latency_ms": 5000,
            "p95_threshold_ms": 3000,
            "consecutive_violations_to_alert": 3
        }'::JSONB,
        'post_execution',
        'warn',
        'Enforce 5-second latency SLA. Alert after 3 consecutive violations. Track p95 latency.',
        ARRAY['sla', 'latency', 'performance']
    ),
    
    -- Medium: Throughput Minimum
    (
        'minimum-throughput-requirement',
        'performance',
        FALSE, -- Disabled by default
        55, -- Medium
        '{
            "min_requests_per_minute": 60,
            "evaluation_window_minutes": 5
        }'::JSONB,
        'continuous',
        'log',
        'Ensure system can handle at least 60 requests per minute. Monitor over 5-minute windows.',
        ARRAY['throughput', 'capacity']
    );

-- =============================================================================
-- BEHAVIORAL POLICIES - Content Safety & Guardrails
-- =============================================================================

INSERT INTO policies (name, category, enabled, priority, constraints, evaluation_type, action_on_violation, description, tags)
VALUES
    -- Critical: Prompt Length Limit
    (
        'prompt-length-limit',
        'behavioral',
        TRUE,
        85, -- High
        '{
            "max_prompt_length": 50000,
            "max_tokens_estimated": 12500,
            "warn_threshold": 40000
        }'::JSONB,
        'pre_flight',
        'block',
        'Prevent excessively large prompts (50k chars max). Protects against memory issues and costs.',
        ARRAY['safety', 'resource-protection']
    ),
    
    -- High: Rate Limiting Per User
    (
        'user-rate-limit',
        'behavioral',
        TRUE,
        75, -- High
        '{
            "max_requests_per_minute": 20,
            "max_requests_per_hour": 200,
            "max_requests_per_day": 1000
        }'::JSONB,
        'pre_flight',
        'block',
        'Rate limit individual users to prevent abuse. 20/min, 200/hour, 1000/day.',
        ARRAY['rate-limiting', 'abuse-prevention']
    ),
    
    -- Medium: Output Length Control
    (
        'output-length-control',
        'behavioral',
        TRUE,
        60, -- Medium
        '{
            "max_output_tokens": 4096,
            "warn_threshold": 3000
        }'::JSONB,
        'pre_flight',
        'warn',
        'Control maximum output length to manage costs. Warn when requesting >3k tokens.',
        ARRAY['cost-optimization', 'output-control']
    );

-- =============================================================================
-- DATA RESIDENCY POLICIES - Geographic & Compliance
-- =============================================================================

INSERT INTO policies (name, category, enabled, priority, constraints, evaluation_type, action_on_violation, description, tags)
VALUES
    -- High: Data Locality Requirement
    (
        'data-locality-us-only',
        'data_residency',
        FALSE, -- Disabled by default (not all vendors support this)
        70, -- High
        '{
            "allowed_regions": ["us-east", "us-west", "us-central"],
            "blocked_regions": ["eu", "asia", "other"]
        }'::JSONB,
        'pre_flight',
        'block',
        'Ensure data stays within US regions. Required for certain compliance requirements (HIPAA, etc.).',
        ARRAY['compliance', 'data-residency', 'gdpr']
    );

-- =============================================================================
-- COMPLIANCE POLICIES - Audit & Regulatory
-- =============================================================================

INSERT INTO policies (name, category, enabled, priority, constraints, evaluation_type, action_on_violation, description, tags)
VALUES
    -- Critical: Audit Trail Required
    (
        'mandatory-audit-logging',
        'compliance',
        TRUE,
        90, -- Critical
        '{
            "require_correlation_id": true,
            "require_user_id": true,
            "log_all_requests": true,
            "retention_days": 90
        }'::JSONB,
        'pre_flight',
        'block',
        'Enforce complete audit trail for all requests. Required for compliance and incident investigation.',
        ARRAY['audit', 'compliance', 'security']
    ),
    
    -- High: PII Detection
    (
        'pii-detection-alert',
        'compliance',
        FALSE, -- Disabled (requires ML model)
        80, -- High
        '{
            "scan_for_pii": true,
            "pii_types": ["ssn", "credit_card", "email", "phone"],
            "action": "alert_and_redact"
        }'::JSONB,
        'pre_flight',
        'warn',
        'Detect and alert on potential PII in prompts. Helps prevent accidental data exposure.',
        ARRAY['pii', 'privacy', 'gdpr']
    );

-- =============================================================================
-- DEVELOPMENT & TESTING POLICIES
-- =============================================================================

INSERT INTO policies (name, category, enabled, priority, constraints, evaluation_type, action_on_violation, description, tags)
VALUES
    -- Low: Development Mode Override
    (
        'dev-mode-policy-bypass',
        'compliance',
        FALSE, -- Only enable in dev environments
        10, -- Low
        '{
            "bypass_policies": ["expensive-model-threshold", "prompt-length-limit"],
            "require_dev_flag": true,
            "log_all_bypasses": true
        }'::JSONB,
        'pre_flight',
        'log',
        'Allow policy bypasses in development environments. All bypasses are logged.',
        ARRAY['development', 'testing', 'non-production']
    );

-- =============================================================================
-- VERIFY SEED DATA
-- =============================================================================

-- Validation Query: Count policies by category
-- SELECT category, COUNT(*) as policy_count, 
--        COUNT(*) FILTER (WHERE enabled = TRUE) as enabled_count
-- FROM policies
-- GROUP BY category
-- ORDER BY category;

-- Validation Query: List all critical policies
-- SELECT name, category, priority, action_on_violation
-- FROM policies
-- WHERE priority >= 80 AND enabled = TRUE
-- ORDER BY priority DESC;

-- =============================================================================
-- END OF SEED DATA
-- =============================================================================
