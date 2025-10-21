"""Simple API token authentication for Recording Angel API."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import config

# Security scheme for API token
security = HTTPBearer()

def verify_api_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    """Verify API token from Authorization header."""
    if not config.API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API token not configured"
        )
    
    if credentials.credentials != config.API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True

# Simple dependency for protected endpoints
def require_api_token() -> bool:
    """Dependency to require valid API token."""
    return Depends(verify_api_token)
