-- =============================================================================
-- IMS POLICY ENFORCEMENT ENGINE - DATABASE SCHEMA
-- Epic 4: Policy Verification Engine (PVE) & Behavioral Constraint Processor (BCP)
-- =============================================================================
-- Version: 1.0.0
-- Date: 2025-12-31
-- Author: IMS-Apex (Claude Sonnet 4.5)

-- =============================================================================
-- 1. POLICIES TABLE - Core Policy Definitions
-- =============================================================================

CREATE TABLE IF NOT EXISTS policies (
    -- Primary Identity
    policy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    
    -- Classification
    category VARCHAR(50) NOT NULL CHECK (category IN 
        ('cost', 'performance', 'vendor', 'data_residency', 'behavioral', 'compliance')),
    
    -- Operational State
    enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0 CHECK (priority >= 0 AND priority <= 100), -- Higher = more critical
    
    -- Constraint Definition (JSON)
    -- Examples:
    -- Cost: {"max_cost_per_mil": 5.0, "max_daily_cost": 100.0, "max_cost_per_request": 0.01}
    -- Performance: {"min_accuracy": 0.95, "max_latency_ms": 1000, "min_throughput": 100}
    -- Vendor: {"allowed_vendors": ["google", "anthropic"], "blocked_vendors": ["openai"]}
    -- Behavioral: {"max_prompt_length": 50000}
    -- Data Residency: {"allowed_regions": ["us-east", "eu-west"]}
    constraints JSONB NOT NULL,
    
    -- Evaluation Logic
    evaluation_type VARCHAR(50) NOT NULL CHECK (evaluation_type IN 
        ('pre_flight', 'runtime', 'post_execution', 'continuous')),
    
    -- Action on Violation
    action_on_violation VARCHAR(50) DEFAULT 'warn' CHECK (action_on_violation IN
        ('block', 'warn', 'log', 'degrade')),
    
    -- Audit Trail
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255) DEFAULT 'system',
    
    -- Metadata
    description TEXT,
    tags TEXT[] DEFAULT '{}',
    
    -- Soft Delete
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_policies_category ON policies(category);
CREATE INDEX IF NOT EXISTS idx_policies_enabled ON policies(enabled) WHERE enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_policies_priority ON policies(priority DESC);
CREATE INDEX IF NOT EXISTS idx_policies_eval_type ON policies(evaluation_type);
CREATE INDEX IF NOT EXISTS idx_policies_tags ON policies USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_policies_active ON policies(enabled, deleted_at) 
    WHERE enabled = TRUE AND deleted_at IS NULL;

-- Comments for documentation
COMMENT ON TABLE policies IS 'Policy definitions for IMS enforcement engine';
COMMENT ON COLUMN policies.category IS 'Policy classification: cost, performance, vendor, data_residency, behavioral, compliance';
COMMENT ON COLUMN policies.priority IS 'Priority level 0-100 (higher = more critical)';
COMMENT ON COLUMN policies.constraints IS 'JSON object defining policy-specific constraints';
COMMENT ON COLUMN policies.evaluation_type IS 'When policy is evaluated: pre_flight, runtime, post_execution, continuous';
COMMENT ON COLUMN policies.action_on_violation IS 'Action to take: block, warn, log, degrade';

-- =============================================================================
-- 2. POLICY VIOLATIONS TABLE - Violation Log
-- =============================================================================

CREATE TABLE IF NOT EXISTS policy_violations (
    -- Primary Identity
    violation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID REFERENCES policies(policy_id) ON DELETE CASCADE,
    
    -- Request Context
    correlation_id VARCHAR(255), -- Links to specific request/workflow
    request_id VARCHAR(255),
    user_id VARCHAR(255),
    
    -- Violation Details
    violation_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    
    -- What happened
    violation_details JSONB NOT NULL,
    -- Example: {"estimated_cost": 0.05, "limit": 0.01, "violation": "cost_per_request_exceeded"}
    
    action_taken VARCHAR(50) NOT NULL CHECK (action_taken IN 
        ('blocked', 'warned', 'logged', 'degraded')),
    
    -- Fallback Info (if degradation occurred)
    fallback_model VARCHAR(100),
    original_model VARCHAR(100),
    
    -- Timestamps
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Resolution Tracking
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(255),
    resolution_notes TEXT,
    
    -- Impact Assessment
    impact_score INTEGER CHECK (impact_score >= 0 AND impact_score <= 10),
    cost_impact DECIMAL(10, 6),
    
    -- Metadata
    metadata JSONB DEFAULT '{}'
);

-- Indexes for violation queries
CREATE INDEX IF NOT EXISTS idx_violations_policy ON policy_violations(policy_id);
CREATE INDEX IF NOT EXISTS idx_violations_correlation ON policy_violations(correlation_id);
CREATE INDEX IF NOT EXISTS idx_violations_severity ON policy_violations(severity);
CREATE INDEX IF NOT EXISTS idx_violations_unresolved ON policy_violations(resolved) 
    WHERE resolved = FALSE;
CREATE INDEX IF NOT EXISTS idx_violations_detected ON policy_violations(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_violations_user ON policy_violations(user_id);
CREATE INDEX IF NOT EXISTS idx_violations_action ON policy_violations(action_taken);

-- Composite index for common query patterns
CREATE INDEX IF NOT EXISTS idx_violations_policy_time ON policy_violations(policy_id, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_violations_severity_time ON policy_violations(severity, detected_at DESC);

COMMENT ON TABLE policy_violations IS 'Log of all policy violations detected by PVE';
COMMENT ON COLUMN policy_violations.correlation_id IS 'Links violation to specific request/workflow';
COMMENT ON COLUMN policy_violations.action_taken IS 'Action taken: blocked, warned, logged, degraded';
COMMENT ON COLUMN policy_violations.impact_score IS 'Business impact severity (0-10)';

-- =============================================================================
-- 3. POLICY EXECUTIONS TABLE - Performance & Analytics
-- =============================================================================

CREATE TABLE IF NOT EXISTS policy_executions (
    -- Primary Identity
    execution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID REFERENCES policies(policy_id) ON DELETE CASCADE,
    
    -- Request Context
    correlation_id VARCHAR(255),
    request_id VARCHAR(255),
    
    -- Evaluation Result
    passed BOOLEAN NOT NULL,
    evaluation_time_ms INTEGER NOT NULL CHECK (evaluation_time_ms >= 0),
    
    -- Context Snapshot
    evaluation_input JSONB NOT NULL,
    -- Example: {"model_id": "gemini-2.5-flash", "estimated_tokens": 1000, "vendor_id": "google"}
    
    evaluation_output JSONB NOT NULL,
    -- Example: {"result": "passed", "details": {"estimated_cost": 0.005}, "warnings": []}
    
    -- Timestamps
    evaluated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Performance Metrics
    cache_hit BOOLEAN DEFAULT FALSE,
    retry_count INTEGER DEFAULT 0
);

-- Indexes for analytics
CREATE INDEX IF NOT EXISTS idx_executions_policy ON policy_executions(policy_id);
CREATE INDEX IF NOT EXISTS idx_executions_correlation ON policy_executions(correlation_id);
CREATE INDEX IF NOT EXISTS idx_executions_result ON policy_executions(passed);
CREATE INDEX IF NOT EXISTS idx_executions_time ON policy_executions(evaluated_at DESC);
CREATE INDEX IF NOT EXISTS idx_executions_policy_result ON policy_executions(policy_id, passed);

-- Partial index for failed executions (faster queries)
CREATE INDEX IF NOT EXISTS idx_executions_failed ON policy_executions(policy_id, evaluated_at DESC)
    WHERE passed = FALSE;

COMMENT ON TABLE policy_executions IS 'Performance tracking for all policy evaluations';
COMMENT ON COLUMN policy_executions.evaluation_time_ms IS 'Time taken to evaluate policy (milliseconds)';
COMMENT ON COLUMN policy_executions.cache_hit IS 'Whether evaluation used cached result';

-- =============================================================================
-- 4. UTILITY FUNCTIONS
-- =============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_policy_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update timestamps
DROP TRIGGER IF EXISTS update_policies_timestamp ON policies;
CREATE TRIGGER update_policies_timestamp
    BEFORE UPDATE ON policies
    FOR EACH ROW
    EXECUTE PROCEDURE update_policy_timestamp();

-- =============================================================================
-- 5. VIEWS FOR ANALYTICS & REPORTING
-- =============================================================================

-- Policy Performance View
CREATE OR REPLACE VIEW policy_performance_stats AS
SELECT 
    p.policy_id,
    p.name,
    p.category,
    COUNT(pe.execution_id) as total_evaluations,
    COUNT(pe.execution_id) FILTER (WHERE pe.passed = TRUE) as passed_count,
    COUNT(pe.execution_id) FILTER (WHERE pe.passed = FALSE) as failed_count,
    ROUND(AVG(pe.evaluation_time_ms), 2) as avg_evaluation_ms,
    MAX(pe.evaluation_time_ms) as max_evaluation_ms,
    MIN(pe.evaluation_time_ms) as min_evaluation_ms,
    COUNT(pe.execution_id) FILTER (WHERE pe.cache_hit = TRUE) as cache_hits,
    ROUND(
        (COUNT(pe.execution_id) FILTER (WHERE pe.cache_hit = TRUE)::DECIMAL / 
         NULLIF(COUNT(pe.execution_id), 0)) * 100, 
        2
    ) as cache_hit_rate_pct
FROM policies p
LEFT JOIN policy_executions pe ON p.policy_id = pe.policy_id
WHERE p.enabled = TRUE AND p.deleted_at IS NULL
GROUP BY p.policy_id, p.name, p.category;

COMMENT ON VIEW policy_performance_stats IS 'Performance statistics for each policy';

-- Violation Summary View
CREATE OR REPLACE VIEW policy_violation_summary AS
SELECT 
    p.policy_id,
    p.name,
    p.category,
    p.priority,
    COUNT(pv.violation_id) as total_violations,
    COUNT(pv.violation_id) FILTER (WHERE pv.severity = 'critical') as critical_violations,
    COUNT(pv.violation_id) FILTER (WHERE pv.severity = 'high') as high_violations,
    COUNT(pv.violation_id) FILTER (WHERE pv.severity = 'medium') as medium_violations,
    COUNT(pv.violation_id) FILTER (WHERE pv.severity = 'low') as low_violations,
    COUNT(pv.violation_id) FILTER (WHERE pv.resolved = TRUE) as resolved_violations,
    COUNT(pv.violation_id) FILTER (WHERE pv.action_taken = 'blocked') as blocked_count,
    COUNT(pv.violation_id) FILTER (WHERE pv.action_taken = 'degraded') as degraded_count,
    MAX(pv.detected_at) as last_violation_at
FROM policies p
LEFT JOIN policy_violations pv ON p.policy_id = pv.policy_id
WHERE p.enabled = TRUE AND p.deleted_at IS NULL
GROUP BY p.policy_id, p.name, p.category, p.priority;

COMMENT ON VIEW policy_violation_summary IS 'Summary of violations per policy';

-- Daily Compliance Report View
CREATE OR REPLACE VIEW daily_compliance_report AS
SELECT 
    DATE(pv.detected_at) as date,
    COUNT(DISTINCT pv.policy_id) as policies_violated,
    COUNT(pv.violation_id) as total_violations,
    COUNT(pv.violation_id) FILTER (WHERE pv.action_taken = 'blocked') as requests_blocked,
    COUNT(pv.violation_id) FILTER (WHERE pv.severity = 'critical') as critical_violations,
    ROUND(AVG(pv.impact_score), 2) as avg_impact_score,
    SUM(pv.cost_impact) as total_cost_impact
FROM policy_violations pv
WHERE pv.detected_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(pv.detected_at)
ORDER BY date DESC;

COMMENT ON VIEW daily_compliance_report IS 'Daily compliance metrics for the last 30 days';

-- =============================================================================
-- 6. EXAMPLE QUERIES FOR TESTING
-- =============================================================================

-- Query 1: Check active policies by category
-- SELECT * FROM policies WHERE enabled = TRUE AND category = 'cost';

-- Query 2: Recent violations
-- SELECT * FROM policy_violations ORDER BY detected_at DESC LIMIT 10;

-- Query 3: Policy effectiveness
-- SELECT * FROM policy_performance_stats ORDER BY total_evaluations DESC;

-- Query 4: Unresolved critical violations
-- SELECT * FROM policy_violations 
-- WHERE resolved = FALSE AND severity = 'critical'
-- ORDER BY detected_at DESC;

-- Query 5: Daily compliance trends
-- SELECT * FROM daily_compliance_report ORDER BY date DESC;

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================
