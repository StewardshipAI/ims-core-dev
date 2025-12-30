from fastapi import HTTPException, Header

# Simple placeholder admin check
async def verify_admin(x_admin_token: str = Header(None)):
    """
    Temporary admin verification until full auth is implemented.
    Accepts a header: X-Admin-Token
    """
    if x_admin_token != "secret-admin-token":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return "admin"
