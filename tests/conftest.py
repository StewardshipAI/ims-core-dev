import pytest
import os
import psycopg2
from src.data.model_registry import ModelRegistry, ModelProfile, CapabilityTier

# Use a separate test database or connection string for safety
TEST_DB_CONN = os.getenv("TEST_DB_CONNECTION_STRING", "postgresql://user:pass@localhost:5432/ims_test_db")

@pytest.fixture(scope="session")
def db_connection():
    """
    Creates a single database connection for the test session
    to set up the schema.
    """
    conn = psycopg2.connect(TEST_DB_CONN)
    conn.autocommit = True
    
    # Ensure schema exists
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS models (
                model_id VARCHAR(255) PRIMARY KEY,
                vendor_id VARCHAR(255) NOT NULL,
                capability_tier VARCHAR(50) NOT NULL,
                context_window INTEGER NOT NULL,
                cost_in_per_mil FLOAT NOT NULL,
                cost_out_per_mil FLOAT NOT NULL,
                function_call_support BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    
    yield conn
    conn.close()

@pytest.fixture(scope="function")
def registry(db_connection):
    """
    Provides a fresh ModelRegistry instance for each test.
    Cleans up the table before running.
    """
    # Truncate table before each test to ensure isolation
    with db_connection.cursor() as cur:
        cur.execute("TRUNCATE TABLE models;")
    
    return ModelRegistry(TEST_DB_CONN)

@pytest.fixture
def sample_model_tier_1():
    return ModelProfile(
        model_id="test-gpt-mini",
        vendor_id="TestVendor",
        capability_tier=CapabilityTier.TIER_1,
        context_window=10000,
        cost_in_per_mil=0.5,
        cost_out_per_mil=1.5,
        function_call_support=True
    )

@pytest.fixture
def sample_model_tier_3():
    return ModelProfile(
        model_id="test-gpt-mega",
        vendor_id="TestVendor",
        capability_tier=CapabilityTier.TIER_3,
        context_window=100000,
        cost_in_per_mil=10.0,
        cost_out_per_mil=30.0,
        function_call_support=True
    )
