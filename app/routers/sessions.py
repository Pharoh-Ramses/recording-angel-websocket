"""Sessions router for Recording Angel API."""

from typing import Any, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.auth import require_api_token
from app.database import get_db, get_session_by_id, get_session_by_code, create_session
from app.models import Session as SessionModel, SessionCreate, SessionParticipant

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("/", response_model=SessionModel)
async def create_transcription_session(
    session_data: SessionCreate,
    _: bool = require_api_token(),
    db: Session = Depends(get_db)
) -> Any:
    """
    Create a new transcription session.
    
    Creates a new session for real-time transcription.
    """
    # Check if session code already exists
    existing_session = get_session_by_code(db, session_data.code)
    if existing_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session code already exists"
        )
    
    # Create session data
    session_dict = session_data.dict()
    
    # Create session
    db_session = create_session(db, session_dict)
    
    return db_session


@router.get("/", response_model=List[SessionModel])
async def get_sessions(
    skip: int = Query(0, ge=0, description="Number of sessions to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of sessions to return"),
    _: bool = require_api_token(),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get list of sessions.
    
    Returns a paginated list of sessions.
    """
    from sqlalchemy.orm import Query as SQLQuery
    
    # Get all sessions
    query: SQLQuery = db.query(SessionModel)
    
    # Apply pagination
    sessions = query.offset(skip).limit(limit).all()
    
    return sessions


@router.get("/{session_id}", response_model=SessionModel)
async def get_session(
    session_id: str,
    _: bool = require_api_token(),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get session by ID.
    
    Returns session information.
    """
    session = get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return session


@router.get("/code/{session_code}", response_model=SessionModel)
async def get_session_by_code(
    session_code: str,
    _: bool = require_api_token(),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get session by code.
    
    Returns session information by session code.
    """
    session = get_session_by_code(db, session_code)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return session


@router.post("/{session_id}/join")
async def join_session(
    session_id: str,
    user_id: str,
    _: bool = require_api_token(),
    db: Session = Depends(get_db)
) -> dict:
    """
    Join a transcription session.
    
    Adds a user as a participant in the session.
    """
    # Check if session exists
    session = get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check if session is ended
    if session.ended_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session has already ended"
        )
    
    # Check if user is already a participant
    existing_participant = db.query(SessionParticipant).filter(
        SessionParticipant.session_id == session_id,
        SessionParticipant.user_id == user_id,
        SessionParticipant.left_at.is_(None)
    ).first()
    
    if existing_participant:
        return {"message": "Already joined this session"}
    
    # Add participant
    participant = SessionParticipant(
        session_id=session_id,
        user_id=user_id,
        joined_at=datetime.utcnow()
    )
    db.add(participant)
    db.commit()
    
    return {"message": "Successfully joined session"}


@router.post("/{session_id}/leave")
async def leave_session(
    session_id: str,
    user_id: str,
    _: bool = require_api_token(),
    db: Session = Depends(get_db)
) -> dict:
    """
    Leave a transcription session.
    
    Marks a user as having left the session.
    """
    # Check if session exists
    session = get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Find participant record
    participant = db.query(SessionParticipant).filter(
        SessionParticipant.session_id == session_id,
        SessionParticipant.user_id == user_id,
        SessionParticipant.left_at.is_(None)
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not a participant in this session"
        )
    
    # Mark as left
    participant.left_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Successfully left session"}


@router.post("/{session_id}/end")
async def end_session(
    session_id: str,
    _: bool = require_api_token(),
    db: Session = Depends(get_db)
) -> dict:
    """
    End a transcription session.
    
    Marks the session as ended.
    """
    # Check if session exists
    session = get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check if session is already ended
    if session.ended_at:
        return {"message": "Session already ended"}
    
    # End session
    session.ended_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Session ended successfully"}


@router.get("/{session_id}/participants", response_model=List[SessionParticipant])
async def get_session_participants(
    session_id: str,
    _: bool = require_api_token(),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get session participants.
    
    Returns list of participants in the session.
    """
    # Check if session exists
    session = get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Get participants
    participants = db.query(SessionParticipant).filter(
        SessionParticipant.session_id == session_id
    ).all()
    
    return participants
