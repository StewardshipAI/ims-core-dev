-- schemas/model_registry_extension.sql
-- Extension for Epic 5: Smart Routing & Quota Awareness

ALTER TABLE models 
ADD COLUMN IF NOT EXISTS quota_rpm INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS quota_tpm INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS regions TEXT[] DEFAULT '{global}',
ADD COLUMN IF NOT EXISTS p_success FLOAT DEFAULT 0.99;

-- Index for regional routing
CREATE INDEX IF NOT EXISTS idx_models_regions ON models USING GIN(regions);

COMMENT ON COLUMN models.quota_rpm IS 'Requests Per Minute limit for this model/key';
COMMENT ON COLUMN models.quota_tpm IS 'Tokens Per Minute limit for this model/key';
COMMENT ON COLUMN models.p_success IS 'Historical probability of success (0.0 to 1.0)';
