"""Health check router."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import HealthResponse
from app.utils.time import now_utc

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(db: Session = Depends(get_db)):
    """Health check endpoint with database connectivity."""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "time": now_utc().isoformat(),
        "version": "0.1.0",
        "database": db_status
    }


@router.get("/health/auth")
async def auth_health():
    """Authentication health check endpoint."""
    return {
        "status": "healthy",
        "auth_system": "api_token",
        "description": "Simple API token authentication",
        "note": "No user management or JWT tokens"
    }
