ALTER TABLE model_registry
ADD COLUMN vendor TEXT,
ADD COLUMN access_tier TEXT,
ADD COLUMN quota_rpm INTEGER,
ADD COLUMN quota_tpm INTEGER,
ADD COLUMN billing_unit TEXT,
ADD COLUMN residency_regions TEXT[],
ADD COLUMN supports_tools BOOLEAN;
