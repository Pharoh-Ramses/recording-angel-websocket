"""AssemblyAI transcription service."""

import asyncio
import json
import time
import websockets
from typing import Dict
from urllib.parse import urlencode

from app.config import config
from app.utils.time import now_utc
# from app.services.session_manager import session_manager  # Disabled for simplified testing
from app.services.ai_providers import refine_and_broadcast_paragraph
from app.services.translation_service_v2 import translation_service_v2


# AssemblyAI WebSocket connections
assembly_sessions: Dict[str, websockets.WebSocketClientProtocol] = {}

# Simple connection store for testing (replaces session_manager)
active_connections: Dict[str, websockets.WebSocketServerProtocol] = {}

# Translation deduplication cache per session
translated_texts: Dict[str, set] = {}

# Time-based deduplication to prevent rapid-fire translations
last_translation_times: Dict[str, float] = {}


def _is_text_complete_enough(text: str) -> bool:
    """Check if text appears complete enough to warrant translation."""
    if not text or not text.strip():
        return False

    text = text.strip()

    # Very short text is probably incomplete
    if len(text) < 5:
        return False

    # Check for sentence-ending punctuation
    if text.endswith(('.', '!', '?', ':')):
        return True

    # Check for common phrase endings in religious text
    religious_endings = ['amén', ' amén', 'jesús', 'cristo', 'espíritu', 'santo', 'padre']
    text_lower = text.lower()
    if any(text_lower.endswith(ending) for ending in religious_endings):
        return True

    # If text is long enough and has multiple words, consider it complete
    word_count = len(text.split())
    if word_count >= 3 and len(text) >= 15:
        return True

    # Default to incomplete for short, single-word, or fragment-like text
    return False


def _calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts using Jaccard similarity."""
    if text1 == text2:
        return 1.0

    # Normalize texts for better comparison
    text1_norm = _normalize_text(text1)
    text2_norm = _normalize_text(text2)

    if text1_norm == text2_norm:
        return 1.0

    # Simple word-based similarity check
    words1 = set(text1_norm.split())
    words2 = set(text2_norm.split())

    if not words1 or not words2:
        return 0.0

    # Calculate Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))

    if union == 0:
        return 0.0

    return intersection / union


def _normalize_text(text: str) -> str:
    """Normalize text for better deduplication."""
    if not text:
        return ""

    # Convert to lowercase
    text = text.lower()

    # Remove extra whitespace and normalize spaces
    text = ' '.join(text.split())

    # Remove common filler words and phrases that might vary
    filler_words = [
        'oh', 'um', 'ah', 'eh', 'er', 'uh', 'hmm', 'mm', 'wait', 'espera',
        'obtener', 'recibiendo', 'viendo', 'traduccion', 'traduction', 'ingles', 'inglés',
        'english', 'spanish', 'español', 'al', 'la', 'el', 'los', 'las', 'un', 'una',
        'de', 'del', 'y', 'o', 'pero', 'porque', 'que', 'como', 'cuando', 'donde'
    ]

    # Also remove punctuation and normalize
    import re
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation

    words = text.split()
    filtered_words = [word for word in words if word not in filler_words and len(word) > 2]

    return ' '.join(filtered_words)


async def setup_assemblyai_session(session_id: str, sample_rate: int) -> websockets.WebSocketClientProtocol:
    """Setup AssemblyAI v3 Universal-Streaming WebSocket connection for a session."""
    if not config.ASSEMBLYAI_API_KEY:
        raise Exception("ASSEMBLYAI_API_KEY not configured")

    # Build WebSocket URL with parameters
    params = {
        "sample_rate": sample_rate,
        "format_turns": "true",
        "encoding": "pcm_s16le",
        # Optimized turn detection for faster response
        "min_end_of_turn_silence_when_confident": "100",  # Faster turn detection
        "max_turn_silence": "800"  # Shorter max silence before forcing turn end
    }
    ws_url = f"wss://streaming.assemblyai.com/v3/ws?{urlencode(params)}"

    # Headers for authentication
    headers = {
        "Authorization": config.ASSEMBLYAI_API_KEY
    }

    try:
        # Connect to AssemblyAI WebSocket
        websocket = await websockets.connect(ws_url, extra_headers=headers)

        # Store the connection
        assembly_sessions[session_id] = websocket

        # Start listening for messages in background
        asyncio.create_task(listen_to_assemblyai(session_id, websocket))

        print(f"AssemblyAI v3 WebSocket connected for {session_id}")
        return websocket

    except Exception as e:
        print(f"Failed to connect to AssemblyAI: {e}")
        raise


async def listen_to_assemblyai(session_id: str, websocket: websockets.WebSocketClientProtocol):
    """Listen for messages from AssemblyAI WebSocket."""
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                await handle_assemblyai_message(session_id, data)
            except json.JSONDecodeError as e:
                print(f"Failed to parse AssemblyAI message for {session_id}: {e}")
            except Exception as e:
                print(f"Error handling AssemblyAI message for {session_id}: {e}")
    except websockets.exceptions.ConnectionClosed:
        print(f"AssemblyAI WebSocket closed for session {session_id}")
    except Exception as e:
        print(f"AssemblyAI WebSocket error for session {session_id}: {e}")
    finally:
        # Cleanup on disconnect
        if session_id in assembly_sessions:
            del assembly_sessions[session_id]


async def handle_assemblyai_message(session_id: str, data: dict):
    """Handle messages from AssemblyAI WebSocket."""
    msg_type = data.get("type")

    if msg_type == "Begin":
        print(f"AssemblyAI session {data.get('id')} began for {session_id}")

    elif msg_type == "Turn":
        transcript = data.get("transcript", "")
        end_of_turn = data.get("end_of_turn", False)
        turn_is_formatted = data.get("turn_is_formatted", False)

        print(f"Turn for session {session_id}: '{transcript}' (end_of_turn: {end_of_turn})")

        if not transcript or not transcript.strip():
            return

        transcript_text = transcript.strip()

        # Send live transcript immediately (without waiting for translation)
        live_message = {
            "type": "live_transcript",
            "data": {
                "text": transcript_text,
                "text_translated": None,  # Will be updated asynchronously
                "target_language": "es" if config.TRANSLATION_ENABLED else None,
                "translation_status": "translating" if (config.TRANSLATION_ENABLED and not end_of_turn) else ("disabled" if not config.TRANSLATION_ENABLED else "ready"),
                "timestamp": now_utc().isoformat(),
                "session_id": session_id,
                "is_final": end_of_turn and (turn_is_formatted or "turn_is_formatted" in data)
            }
        }

        # Send transcript immediately to WebSocket
        if session_id in active_connections:
            try:
                await active_connections[session_id].send_json(live_message)
            except Exception as e:
                print(f"Failed to send message to WebSocket: {e}")

        # Start translation asynchronously only when turn is complete (fire-and-forget)
        if config.TRANSLATION_ENABLED and transcript_text and end_of_turn:
            # Only translate if the text appears to be a complete thought/sentence
            if _is_text_complete_enough(transcript_text):
                print(f"🚀 Starting final translation for session {session_id}: '{transcript_text[:50]}...'")
                asyncio.create_task(translate_and_broadcast_async(
                    session_id, transcript_text, "es", live_message
                ))
            else:
                print(f"⏳ Skipping translation for session {session_id} - incomplete text: '{transcript_text[:50]}...'")

    elif msg_type == "Termination":
        audio_duration = data.get("audio_duration_seconds", 0)
        print(f"AssemblyAI session terminated for {session_id}: {audio_duration}s audio")

    else:
        # Handle errors or unknown message types
        print(f"Unknown AssemblyAI message type for {session_id}: {data}")

        if "error" in data:
            error_message = {
                "type": "error",
                "message": f"Transcription error: {data.get('error', 'Unknown error')}"
            }
            if session_id in active_connections:
                try:
                    await active_connections[session_id].send_json(error_message)
                except Exception as e:
                    print(f"Failed to send error message to WebSocket: {e}")


async def cleanup_assemblyai_session(session_id: str):
    """Cleanup AssemblyAI v3 WebSocket session."""
    if session_id in assembly_sessions:
        try:
            websocket = assembly_sessions[session_id]

            # Send termination message
            termination_msg = {"type": "SessionTermination"}
            await websocket.send(json.dumps(termination_msg))

            # Close the WebSocket
            await websocket.close()
            del assembly_sessions[session_id]
            print(f"Cleaned up AssemblyAI v3 session for {session_id}")
        except Exception as e:
            print(f"Error cleaning up AssemblyAI session {session_id}: {e}")

    # Clean up translation deduplication caches
    if session_id in translated_texts:
        cache_size = len(translated_texts[session_id])
        del translated_texts[session_id]
        print(f"Cleaned up translation cache for session {session_id}: {cache_size} entries")

    if session_id in last_translation_times:
        del last_translation_times[session_id]
        print(f"Cleaned up translation timing cache for session {session_id}")


async def translate_and_broadcast_async(session_id: str, transcript_text: str, target_language: str, original_message: dict):
    """Translate text asynchronously and broadcast the result."""
    try:
        current_time = time.time()

        # Time-based throttling - prevent translations too close together
        if session_id in last_translation_times:
            time_since_last = current_time - last_translation_times[session_id]
            if time_since_last < 1.0:  # Minimum 1 second between translations
                print(f"Throttling translation for session {session_id}: too soon after last translation ({time_since_last:.2f}s)")
                return

        # Clean and normalize the text for deduplication
        clean_text = _normalize_text(transcript_text)

        # Initialize session's translated texts set if not exists
        if session_id not in translated_texts:
            translated_texts[session_id] = set()

        # Check if we've already translated this exact normalized text
        if clean_text in translated_texts[session_id]:
            print(f"Skipping exact duplicate translation for session {session_id}: '{transcript_text[:50]}...'")
            return

        # Check for very similar text (lower threshold for better deduplication)
        for existing_text in translated_texts[session_id]:
            similarity = _calculate_similarity(clean_text, existing_text)
            if similarity > 0.6:  # Lower threshold to catch more duplicates
                print(f"Skipping similar translation for session {session_id}: '{transcript_text[:50]}...' (similarity: {similarity:.2f})")
                return

        # Update last translation time
        last_translation_times[session_id] = current_time

        # Add to translated set before attempting translation
        translated_texts[session_id].add(clean_text)

        # Limit the size of the deduplication cache per session
        if len(translated_texts[session_id]) > 100:
            # Remove oldest entries (simple FIFO)
            translated_texts[session_id] = set(list(translated_texts[session_id])[-50:])

        print(f"🚀 Translating for session {session_id}: '{transcript_text[:50]}...'")

        # Use the real Gemini translation service
        translated_text = await translation_service_v2.translate_text(
            session_id=session_id,
            text=transcript_text,
            target_lang=target_language,
            source_lang="auto"
        )

        translation_status = "success" if translated_text else "failed"
        print(f"✅ Translation complete for session {session_id}: '{translated_text[:50] if translated_text else 'FAILED'}...'")

        # Send translation update
        translation_message = {
            "type": "translation_update",
            "data": {
                "original_text": transcript_text,
                "text_translated": translated_text,
                "target_language": target_language,
                "translation_status": translation_status,
                "timestamp": now_utc().isoformat(),
                "session_id": session_id,
                "is_final": True  # Mark this as a final translation
            }
        }

        # Send translation update to WebSocket
        if session_id in active_connections:
            try:
                await active_connections[session_id].send_json(translation_message)
            except Exception as e:
                print(f"Failed to send translation update to WebSocket: {e}")

    except Exception as e:
        print(f"Async translation error for session {session_id}: {e}")
        # Send error update
        error_message = {
            "type": "translation_update",
            "data": {
                "original_text": transcript_text,
                "text_translated": None,
                "target_language": target_language,
                "translation_status": "failed",
                "timestamp": now_utc().isoformat(),
                "session_id": session_id,
                "error": str(e)
            }
        }
        if session_id in active_connections:
            try:
                await active_connections[session_id].send_json(error_message)
            except Exception as send_error:
                print(f"Failed to send translation error to WebSocket: {send_error}")


async def process_audio_chunk(session_id: str, audio_data: bytes, user_id: str) -> None:
    """Forward audio chunk to AssemblyAI v3 WebSocket for real transcription."""
    if len(audio_data) < 100:  # Skip very small chunks
        return

    # Debug: Log audio data reception
    print(f"Received audio chunk for {session_id}: {len(audio_data)} bytes")

    # Get AssemblyAI WebSocket for this session
    if session_id not in assembly_sessions:
        print(f"No AssemblyAI session found for {session_id}, this shouldn't happen")
        return

    websocket = assembly_sessions[session_id]

    try:
        # Send audio data as binary to AssemblyAI v3 WebSocket
        await websocket.send(audio_data)
        print(f"Sent {len(audio_data)} bytes to AssemblyAI for {session_id}")
    except Exception as e:
        print(f"Error sending audio to AssemblyAI for session {session_id}: {e}")
        # Send error directly to connected WebSocket
        error_message = {
            "type": "error",
            "message": f"Failed to process audio: {str(e)}"
        }
        if session_id in active_connections:
            try:
                await active_connections[session_id].send_json(error_message)
            except Exception as send_error:
                print(f"Failed to send error message: {send_error}")


def clear_translation_caches():
    """Clear all translation deduplication caches (for debugging)."""
    global translated_texts, last_translation_times
    cache_count = len(translated_texts)
    timing_count = len(last_translation_times)
    translated_texts.clear()
    last_translation_times.clear()
    print(f"Cleared {cache_count} translation caches and {timing_count} timing caches")


def get_cache_stats(session_id: str = None) -> dict:
    """Get statistics about the translation caches."""
    if session_id:
        return {
            "session_id": session_id,
            "translated_texts_count": len(translated_texts.get(session_id, set())),
            "last_translation_time": last_translation_times.get(session_id, None)
        }
    else:
        return {
            "total_sessions": len(translated_texts),
            "total_cache_entries": sum(len(cache) for cache in translated_texts.values()),
            "sessions_with_timing": len(last_translation_times)
        }