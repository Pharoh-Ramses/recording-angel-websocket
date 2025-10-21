"""WebSocket transcription router."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.config import config
from app.database import get_db, get_session_by_id, create_session
from app.services.session_manager import session_manager
from app.services.assemblyai import (
    setup_assemblyai_session,
    cleanup_assemblyai_session,
    process_audio_chunk,
    assembly_sessions,
    active_connections
)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str = Query("test_session", description="Session ID (optional)"),
    user_id: str = Query("test_user", description="User ID (optional)"),
    sample_rate: int = Query(16000, description="Audio sample rate"),
    encoding: str = Query("pcm_s16le", description="Audio encoding"),
    target_language: str = Query("disabled", description="Translation target language (e.g., 'es', 'fr', 'disabled')")
):
    """
    WebSocket endpoint for real-time audio transcription.
    Simplified for testing - no authentication or session validation required.
    """
    await websocket.accept()

    # Use default values if not provided
    if not session_id:
        session_id = "test_session"
    if not user_id:
        user_id = "test_user"

    try:
        # Store WebSocket connection for direct messaging
        active_connections[session_id] = websocket

        # Setup AssemblyAI session immediately
        if session_id not in assembly_sessions:
            try:
                await setup_assemblyai_session(session_id, sample_rate)
                print(f"AssemblyAI session created for {session_id}")
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Failed to setup AssemblyAI: {str(e)}"
                })
                return

        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to simplified transcription service",
            "config": {
                "sample_rate": sample_rate,
                "encoding": encoding,
                "session_id": session_id,
                "user_id": user_id,
                "assemblyai_enabled": True,
                "translation_enabled": config.TRANSLATION_ENABLED,
                "target_language": target_language if target_language != "disabled" else None
            }
        })

        print(f"WebSocket connected: session={session_id}, user={user_id}, sample_rate={sample_rate}, encoding={encoding}")

        # Listen for audio data
        while True:
            try:
                # Receive binary audio data
                audio_data = await websocket.receive_bytes()

                # Forward audio to AssemblyAI for real transcription
                await process_audio_chunk(session_id, audio_data, user_id)

            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"Error processing audio data: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"Error processing audio: {str(e)}"
                })
                break

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Clean up connection
        if session_id in active_connections:
            del active_connections[session_id]

        # Clean up AssemblyAI session
        if session_id in assembly_sessions:
            await cleanup_assemblyai_session(session_id)

        print(f"WebSocket disconnected: session={session_id}, user={user_id}")
