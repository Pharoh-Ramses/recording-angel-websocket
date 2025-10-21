# Translation Feature Implementation

This document describes the real-time translation feature integrated into the Recording Angel API.

## Overview

The translation service provides real-time translation of live transcription using Google Cloud Translation API. Translation happens at Integration Point 1: immediately after AssemblyAI provides live transcription, before broadcasting to WebSocket clients.

## Setup

### 1. Install Dependencies

Add the Google Cloud Translation library:

```bash
cd python-api
uv add google-cloud-translate==3.15.3
```

Or update your requirements:
```
pip install google-cloud-translate==3.15.3
```

### 2. Configure API Keys

Add your Google Cloud Translation API key to your environment:

```bash
# In your .env file
GOOGLE_TRANSLATE_API_KEY=your_google_translate_api_key_here
TRANSLATION_ENABLED=true
TRANSLATION_DEFAULT_TARGET=es
TRANSLATION_RATE_LIMIT=100
```

### 3. Google Cloud Setup

1. Create a Google Cloud Project
2. Enable the Cloud Translation API
3. Create a service account and download the JSON key file
4. Set `GOOGLE_TRANSLATE_API_KEY` to the path of your service account JSON file, or configure Application Default Credentials

## Usage

### WebSocket Connection

Connect to the WebSocket endpoint with translation parameters:

```javascript
const ws = new WebSocket(`ws://localhost:8080/ws?session_id=test&user_id=user1&api_token=your-token&target_language=es`);
```

Supported languages: `es` (Spanish), `fr` (French), `de` (German), `zh` (Chinese), etc.
Use `disabled` to turn off translation for a session.

### Message Format

Live transcript messages now include translation data:

```json
{
  "type": "live_transcript",
  "data": {
    "text": "Hello everyone, welcome to our meeting",
    "text_translated": "Hola a todos, bienvenidos a nuestra reunión", 
    "target_language": "es",
    "source_language_detected": "en",
    "translation_status": "success",
    "timestamp": "2025-08-30T12:34:56.789Z",
    "session_id": "session-123456789",
    "is_final": false
  }
}
```

### Translation Status Values

- `success`: Translation completed successfully
- `failed`: Translation attempted but failed
- `disabled`: Translation is disabled for this session

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `TRANSLATION_ENABLED` | `false` | Enable/disable translation globally |
| `TRANSLATION_DEFAULT_TARGET` | `es` | Default target language |
| `TRANSLATION_RATE_LIMIT` | `100` | Max requests per minute |
| `GOOGLE_TRANSLATE_API_KEY` | `""` | Google Cloud Translation API key |

## Architecture

### Files Modified/Created

1. **`/app/services/translation.py`** - New translation service
2. **`/app/config.py`** - Added translation configuration
3. **`/app/services/session_manager.py`** - Added language tracking
4. **`/app/services/assemblyai.py`** - Integrated translation into live flow
5. **`/app/routers/websocket.py`** - Added language parameter
6. **`pyproject.toml`** - Added google-cloud-translate dependency

### Data Flow

```
Audio → AssemblyAI → Live Transcript → Translation Service → Enhanced Message → WebSocket Clients
```

### Performance Features

- **Language Detection Caching**: Avoids repeated detection API calls
- **Rate Limiting**: Prevents API quota exhaustion  
- **Async Processing**: Non-blocking translation calls
- **Error Handling**: Graceful fallbacks when translation fails
- **Session-level Control**: Per-session language configuration

## Cost Estimation

Google Cloud Translation API pricing:
- **$20 per million characters** (first 500K free monthly)
- **Input text only** (not charged for output)
- **Real-time optimized** for low latency

Example cost for a 1-hour meeting:
- ~50,000 characters of speech
- Cost: ~$1.00 per hour with translation enabled

## Testing

Test the translation feature:

```bash
# Start the API
cd python-api
uv run fastapi dev app/main.py

# Connect with translation enabled
wscat -c "ws://localhost:8080/ws?session_id=test&user_id=test&api_token=your-token&target_language=es"

# Send audio data and observe translated responses
```

## Next Integration Points

This implementation covers **Integration Point 1** (live transcript translation). Future enhancements:

- **Point 2**: Buffered text translation (every 10 seconds)
- **Point 3**: AI-refined paragraph translation
- **Frontend**: Translation toggle and language selection UI
- **Multiple Languages**: Simultaneous translation to multiple targets

## Troubleshooting

**Translation not working:**
1. Check `TRANSLATION_ENABLED=true` in environment
2. Verify `GOOGLE_TRANSLATE_API_KEY` is set correctly
3. Ensure Google Cloud Translation API is enabled
4. Check logs for authentication errors

**High latency:**
1. Reduce `TRANSLATION_RATE_LIMIT` if hitting quotas
2. Check Google Cloud region/latency
3. Monitor translation service performance

**Rate limiting:**
1. Increase `TRANSLATION_RATE_LIMIT` if needed
2. Monitor usage in Google Cloud Console
3. Consider upgrading Google Cloud quota