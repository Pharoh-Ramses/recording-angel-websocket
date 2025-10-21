"""API Token management router for Recording Angel API."""

import json
import secrets
from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import AuthService, get_current_active_user
from app.database import get_db, create_api_token, get_user_api_tokens, deactivate_api_token
from app.models import ApiTokenCreate, ApiToken, ApiTokenResponse, User

router = APIRouter(prefix="/api/tokens", tags=["api-tokens"])


@router.post("/", response_model=ApiTokenResponse)
async def create_token(
    token_data: ApiTokenCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Create a new API token.
    
    Creates a new API token for the current user with specified permissions.
    """
    # Generate a secure token
    token = f"ra_{secrets.token_urlsafe(32)}"
    token_prefix = token[:8]
    
    # Hash the token for storage
    token_hash = AuthService.hash_refresh_token(token)
    
    # Prepare token data
    db_token_data = {
        "name": token_data.name,
        "description": token_data.description,
        "token_hash": token_hash,
        "token_prefix": token_prefix,
        "created_by": current_user.id,
        "expires_at": token_data.expires_at,
        "permissions": json.dumps(token_data.permissions),
    }
    
    # Create token in database
    db_token = create_api_token(db, db_token_data)
    
    # Return response with full token (only shown once)
    return ApiTokenResponse(
        id=db_token.id,
        name=db_token.name,
        description=db_token.description,
        token=token,  # Full token (only shown once)
        token_prefix=db_token.token_prefix,
        created_at=db_token.created_at,
        expires_at=db_token.expires_at,
        permissions=json.loads(db_token.permissions),
    )


@router.get("/", response_model=List[ApiToken])
async def list_tokens(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    List all API tokens for the current user.
    
    Returns a list of all active API tokens created by the current user.
    """
    tokens = get_user_api_tokens(db, current_user.id)
    return tokens


@router.delete("/{token_id}")
async def deactivate_token(
    token_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Deactivate an API token.
    
    Deactivates an API token created by the current user.
    """
    success = deactivate_api_token(db, token_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found or not owned by current user"
        )
    
    return {"message": "Token deactivated successfully"}
