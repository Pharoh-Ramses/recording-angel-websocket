"""Pydantic models for Recording Angel API."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


class TokenRequest(BaseModel):
    """Request model for WebRTC token creation."""
    expires_in: Optional[int] = 60  # Expiry in seconds


class UserBase(BaseModel):
    """Base user model."""
    full_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    ward: int = Field(..., ge=1)
    stake: int = Field(..., ge=1)
    profile_picture: Optional[str] = None


class UserCreate(UserBase):
    """Model for user registration."""
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """Model for user profile updates."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    ward: Optional[int] = Field(None, ge=1)
    stake: Optional[int] = Field(None, ge=1)
    profile_picture: Optional[str] = None


class User(UserBase):
    """Complete user model."""
    id: str
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED
    role: str = "MEMBER"  # MEMBER, BISHOP, STAKEPRESIDENT, MISSIONARY, MISSIONPRESIDENT, ADMIN
    last_activity_date: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserInDB(User):
    """User model with password hash."""
    password_hash: str


class Token(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token payload data."""
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request model."""
    email: EmailStr
    password: str


class PasswordChangeRequest(BaseModel):
    """Password change request model."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class SessionCreate(BaseModel):
    """Model for creating transcription sessions."""
    code: str = Field(..., min_length=3, max_length=10)
    host_id: str


class Session(SessionCreate):
    """Complete session model."""
    id: str
    created_at: datetime
    ended_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SessionParticipant(BaseModel):
    """Session participant model."""
    id: str
    session_id: str
    user_id: str
    joined_at: datetime
    left_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TranscriptionChunk(BaseModel):
    """Transcription chunk model."""
    id: str
    session_id: str
    text: str
    language: str = "en"
    timestamp: datetime
    speaker_id: str
    is_final: bool = False
    
    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    time: str
    version: str
    database: str = "connected"
