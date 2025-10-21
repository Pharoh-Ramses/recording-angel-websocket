"""Simple authentication router for Recording Angel API."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/auth", tags=["authentication"])

@router.get("/health")
async def auth_health() -> dict:
    """Simple health check for authentication system."""
    return {"status": "ok", "auth_type": "api_token"}
