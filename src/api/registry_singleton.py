import os
from src.data.model_registry import ModelRegistry

# Get DB connection from environment
DB_CONN = os.getenv("DB_CONNECTION_STRING")
if not DB_CONN:
    raise ValueError("DB_CONNECTION_STRING must be set in environment for registry singleton")

# Create the global registry instance here
registry = ModelRegistry(db_connection_string=DB_CONN)
