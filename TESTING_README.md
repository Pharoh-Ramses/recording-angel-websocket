# Simplified Testing Setup

This version of the API has been simplified for fast testing by removing authentication and session management requirements.

## Quick Start

### 1. Set Environment Variables

Create a `.env` file with required settings:

```env
# Required for AssemblyAI transcription
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here

# Required for Gemini translation
GOOGLE_API_KEY=your_google_api_key_here

# Translation settings
TRANSLATION_ENABLED=true
TRANSLATION_PROVIDER=gemini
TRANSLATION_MODEL=gemini-2.5-flash-lite
```

### 2. Run the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### 3. Test the WebSocket

```bash
python test_websocket.py
```

## What's Simplified

### ✅ Removed Requirements
- **API Token Authentication**: WebSocket connects without tokens
- **Session Management**: No database sessions or user validation
- **Complex Translation**: Using real Gemini translation (not placeholder)

### ✅ What's Working
- **Real-time Transcription**: AssemblyAI integration still works
- **WebSocket Communication**: Direct connection to transcription service
- **Audio Processing**: Binary audio data forwarding to AssemblyAI

## WebSocket Usage

### Connect
```javascript
const ws = new WebSocket('ws://localhost:8080/ws');
```

### Send Audio Data
```javascript
// Send PCM audio data as binary
ws.send(audioBuffer);
```

### Receive Transcriptions
```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'live_transcript') {
        console.log('Transcription:', data.data.text);
        if (data.data.text_translated) {
            console.log('Translation:', data.data.text_translated);
        }
    }
};
```

## Message Format

### Connection
```json
{
    "type": "connected",
    "message": "Connected to simplified transcription service",
    "config": {
        "sample_rate": 16000,
        "encoding": "pcm_s16le",
        "session_id": "test_session",
        "assemblyai_enabled": true,
        "translation_enabled": true
    }
}
```

### Live Transcription
```json
{
    "type": "live_transcript",
    "data": {
        "text": "Hello, this is a test transcription",
        "text_translated": "Hola, esta es una transcripción de prueba",
        "target_language": "es",
        "translation_status": "success",
        "timestamp": "2024-01-01T12:00:00.000Z",
        "session_id": "test_session",
        "is_final": true
    }
}
```

## Next Steps

Once testing is complete, you can:

1. **Re-enable Authentication**: Uncomment session management code
2. **Add Real Translation**: Integrate the full LLM translation system
3. **Enable Session Persistence**: Add database session storage
4. **Add User Management**: Implement proper user authentication

## Files Modified for Testing

- `app/routers/websocket.py`: Removed authentication requirements
- `app/services/assemblyai.py`: Simplified to direct WebSocket communication
- `test_websocket.py`: Simple test client for verification

The core transcription functionality remains intact - only the authentication and session layers have been simplified for faster testing.