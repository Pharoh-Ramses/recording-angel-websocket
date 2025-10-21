"""Database models and connection for Recording Angel API."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.config import config

# Create database engine
engine = create_engine(
    config.DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


class User(Base):
    """User model for database."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    ward = Column(Integer, nullable=False)
    stake = Column(Integer, nullable=False)
    password_hash = Column(String(255), nullable=False)
    profile_picture = Column(String(500), nullable=True)
    status = Column(String(20), default="PENDING")  # PENDING, APPROVED, REJECTED
    role = Column(String(20), default="MEMBER")  # MEMBER, BISHOP, STAKEPRESIDENT, MISSIONARY, MISSIONPRESIDENT, ADMIN
    last_activity_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    sessions = relationship("Session", back_populates="host")
    participants = relationship("SessionParticipant", back_populates="user")


class Session(Base):
    """Transcription session model."""
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(10), unique=True, nullable=False, index=True)
    host_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)

    # Relationships
    host = relationship("User", back_populates="sessions")
    participants = relationship("SessionParticipant", back_populates="session")
    transcriptions = relationship("TranscriptionChunk", back_populates="session")


class SessionParticipant(Base):
    """Session participant model."""
    __tablename__ = "session_participants"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    left_at = Column(DateTime, nullable=True)

    # Relationships
    session = relationship("Session", back_populates="participants")
    user = relationship("User", back_populates="participants")


class TranscriptionChunk(Base):
    """Transcription chunk model."""
    __tablename__ = "transcription_chunks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    text = Column(Text, nullable=False)
    language = Column(String(10), default="en")
    timestamp = Column(DateTime, default=datetime.utcnow)
    speaker_id = Column(String, nullable=False)
    is_final = Column(Boolean, default=False)

    # Relationships
    session = relationship("Session", back_populates="transcriptions")


class RefreshToken(Base):
    """Refresh token model for JWT refresh."""
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_revoked = Column(Boolean, default=False)


# Database dependency
def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create tables
def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


# Database utilities
def get_user_by_email(db, email: str) -> Optional[User]:
    """Get user by email."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db, user_id: str) -> Optional[User]:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def create_user(db, user_data) -> User:
    """Create a new user."""
    db_user = User(**user_data)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db, user_id: str, update_data: dict) -> Optional[User]:
    """Update user data."""
    user = get_user_by_id(db, user_id)
    if user:
        for key, value in update_data.items():
            if hasattr(user, key):
                setattr(user, key, value)
        user.last_activity_date = datetime.utcnow()
        db.commit()
        db.refresh(user)
    return user


def get_session_by_code(db, code: str) -> Optional[Session]:
    """Get session by code."""
    return db.query(Session).filter(Session.code == code).first()


def get_session_by_id(db, session_id: str) -> Optional[Session]:
    """Get session by ID."""
    return db.query(Session).filter(Session.id == session_id).first()


def create_session(db, session_data) -> Session:
    """Create a new session."""
    db_session = Session(**session_data)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def save_refresh_token(db, user_id: str, token_hash: str, expires_at: datetime) -> RefreshToken:
    """Save refresh token to database."""
    db_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token


def get_refresh_token(db, token_hash: str) -> Optional[RefreshToken]:
    """Get refresh token by hash."""
    return db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.is_revoked == False,
        RefreshToken.expires_at > datetime.utcnow()
    ).first()


def revoke_refresh_token(db, token_hash: str) -> bool:
    """Revoke a refresh token."""
    token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if token:
        token.is_revoked = True
        db.commit()
        return True
    return False
