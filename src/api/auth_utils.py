import os
import hmac
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=True)

async def verify_admin(key: str = Security(api_key_header)):
    """
    Secure admin verification using ADMIN_API_KEY from environment.
    """
    if not ADMIN_API_KEY:
         raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfiguration: ADMIN_API_KEY not set"
        )
        
    if not hmac.compare_digest(key, ADMIN_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Invalid Admin API Key"
        )
    return key

