"""Session management for WebSocket connections."""

import asyncio
from typing import Dict, Set, Optional

from fastapi import WebSocket

from app.utils.time import now_utc
from app.config import config


class SessionManager:
    """Manages WebSocket sessions and their metadata."""
    
    def __init__(self):
        # In-memory session management (replace with database later)
        self.active_sessions: Dict[str, Set[WebSocket]] = {}
        self.session_metadata: Dict[str, Dict] = {}
        
        # Time-based buffering for AI refinement
        self.session_text_buffers: Dict[str, str] = {}
        self.session_buffer_timers: Dict[str, asyncio.Task] = {}

        # Translation buffering for LLM-based translation
        self.translation_buffers: Dict[str, str] = {}
        self.translation_timers: Dict[str, asyncio.Task] = {}
    
    async def add_connection(self, session_id: str, websocket: WebSocket, user_id: str) -> None:
        """Add a WebSocket connection to a session."""
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = set()
            self.session_metadata[session_id] = {
                "created_at": now_utc().isoformat(),
                "paragraph_counter": 0,
            }
            # Initialize text buffer for this session
            self.session_text_buffers[session_id] = ""
        
        self.active_sessions[session_id].add(websocket)
        print(f"User {user_id} joined session {session_id}. Total connections: {len(self.active_sessions[session_id])}")
    
    async def remove_connection(self, session_id: str, websocket: WebSocket, user_id: str) -> None:
        """Remove a WebSocket connection from a session."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id].discard(websocket)
            if len(self.active_sessions[session_id]) == 0:
                # Clean up empty session
                del self.active_sessions[session_id]
                del self.session_metadata[session_id]
                
                # Clean up text buffer and timer
                if session_id in self.session_text_buffers:
                    del self.session_text_buffers[session_id]
                if session_id in self.session_buffer_timers:
                    self.session_buffer_timers[session_id].cancel()
                    del self.session_buffer_timers[session_id]

                # Clean up translation buffer and timer
                if session_id in self.translation_buffers:
                    del self.translation_buffers[session_id]
                if session_id in self.translation_timers:
                    self.translation_timers[session_id].cancel()
                    del self.translation_timers[session_id]
                    
                print(f"Session {session_id} cleaned up - no active connections")
            else:
                print(f"User {user_id} left session {session_id}. Remaining connections: {len(self.active_sessions[session_id])}")
    
    async def broadcast_to_session(self, session_id: str, message: dict, exclude_websocket: Optional[WebSocket] = None) -> None:
        """Broadcast a message to all connections in a session."""
        if session_id not in self.active_sessions:
            return
        
        # Create list of websockets to avoid set modification during iteration
        websockets_to_send = list(self.active_sessions[session_id])
        if exclude_websocket:
            websockets_to_send = [ws for ws in websockets_to_send if ws != exclude_websocket]
        
        # Send to all connections, removing any that are closed
        disconnected = []
        for websocket in websockets_to_send:
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"Failed to send to websocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected websockets
        for ws in disconnected:
            self.active_sessions[session_id].discard(ws)
    
    def get_session_metadata(self, session_id: str) -> Dict:
        """Get metadata for a session."""
        return self.session_metadata.get(session_id, {})
    
    def update_session_metadata(self, session_id: str, updates: Dict) -> None:
        """Update metadata for a session."""
        if session_id in self.session_metadata:
            self.session_metadata[session_id].update(updates)
    
    def get_text_buffer(self, session_id: str) -> str:
        """Get text buffer for a session."""
        return self.session_text_buffers.get(session_id, "")
    
    def add_to_text_buffer(self, session_id: str, text: str) -> None:
        """Add text to session buffer."""
        if session_id not in self.session_text_buffers:
            self.session_text_buffers[session_id] = ""
        
        # Add space if buffer already has content
        if self.session_text_buffers[session_id]:
            self.session_text_buffers[session_id] += " "
        self.session_text_buffers[session_id] += text
    
    def clear_text_buffer(self, session_id: str) -> str:
        """Clear and return text buffer for a session."""
        text = self.session_text_buffers.get(session_id, "")
        self.session_text_buffers[session_id] = ""
        return text
    
    def set_buffer_timer(self, session_id: str, timer_task: asyncio.Task) -> None:
        """Set buffer timer for a session."""
        # Cancel any existing timer
        if session_id in self.session_buffer_timers:
            self.session_buffer_timers[session_id].cancel()
        self.session_buffer_timers[session_id] = timer_task
    
    def cancel_buffer_timer(self, session_id: str) -> None:
        """Cancel buffer timer for a session."""
        if session_id in self.session_buffer_timers:
            self.session_buffer_timers[session_id].cancel()
            del self.session_buffer_timers[session_id]
    
    def get_target_language(self, session_id: str) -> str:
        """Get target language for translation for a session."""
        metadata = self.get_session_metadata(session_id)
        return metadata.get("target_language", config.TRANSLATION_DEFAULT_TARGET)

    def set_target_language(self, session_id: str, language: str):
        """Set target language for a session."""
        self.update_session_metadata(session_id, {"target_language": language})

    def get_translation_buffer(self, session_id: str) -> str:
        """Get translation buffer for a session."""
        return self.translation_buffers.get(session_id, "")

    def add_to_translation_buffer(self, session_id: str, text: str) -> None:
        """Add text to translation buffer."""
        if session_id not in self.translation_buffers:
            self.translation_buffers[session_id] = ""

        # Add space if buffer already has content
        if self.translation_buffers[session_id]:
            self.translation_buffers[session_id] += " "
        self.translation_buffers[session_id] += text.strip()

    def clear_translation_buffer(self, session_id: str) -> str:
        """Clear and return translation buffer for a session."""
        text = self.translation_buffers.get(session_id, "")
        self.translation_buffers[session_id] = ""
        return text

    def set_translation_timer(self, session_id: str, timer_task: asyncio.Task) -> None:
        """Set translation timer for a session."""
        # Cancel any existing timer
        if session_id in self.translation_timers:
            self.translation_timers[session_id].cancel()
        self.translation_timers[session_id] = timer_task

    def cancel_translation_timer(self, session_id: str) -> None:
        """Cancel translation timer for a session."""
        if session_id in self.translation_timers:
            self.translation_timers[session_id].cancel()
            del self.translation_timers[session_id]


# Global session manager instance
session_manager = SessionManager()
