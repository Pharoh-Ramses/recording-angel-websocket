# Recording Angel Python API

**Recording Angel** is a comprehensive real-time audio transcription platform designed specifically for religious organizations and meeting environments. This Python-based API provides seamless real-time audio transcription with intelligent AI-powered text organization, secure authentication, and role-based access control.

## What is Recording Angel?

Recording Angel transforms live meetings, conferences, and religious gatherings by providing:

- **Real-time Transcription**: Live audio-to-text conversion with minimal latency
- **AI-Powered Organization**: Intelligent paragraph structuring and text refinement using Google Gemini
- **Religious Organization Ready**: Built-in role hierarchy for church leadership structures
- **Session Management**: Create, join, and manage transcription sessions with ease
- **Secure Architecture**: Enterprise-grade authentication with JWT tokens and refresh mechanisms

Perfect for stake conferences, ward meetings, missionary training, and any religious gathering where accurate, real-time transcription is needed.

## Technology Stack

- **Framework**: FastAPI (Python 3.8+)
- **Database**: PostgreSQL/SQLite with SQLAlchemy ORM
- **Authentication**: JWT tokens with BCrypt password hashing
- **Real-time Communication**: WebSockets
- **Audio Transcription**: AssemblyAI API
- **AI Text Processing**: Google Gemini API
- **Package Management**: UV (ultra-fast Python package installer)
- **Deployment**: Uvicorn ASGI server

## Architecture Overview

The Recording Angel API follows a modern, scalable architecture:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client App    │◄──►│  FastAPI Server  │◄──►│   Database      │
│  (Web/Mobile)   │    │                  │    │ (PostgreSQL)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  External APIs   │
                       │ • AssemblyAI     │
                       │ • Google Gemini  │
                       └──────────────────┘
```

## Features

- **Real-time Audio Transcription** - WebSocket-based transcription using AssemblyAI
- **AI Paragraph Organization** - Intelligent text refinement using Google Gemini
- **JWT Authentication** - Secure token-based authentication with refresh tokens
- **Role-based Access Control** - User roles: MEMBER, BISHOP, STAKEPRESIDENT, MISSIONARY, MISSIONPRESIDENT, ADMIN
- **Session Management** - Create, join, and manage transcription sessions
- **Database Integration** - PostgreSQL/SQLite support with SQLAlchemy ORM

## Quick Start

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the example environment file and configure your settings:

```bash
cp env.example .env
```

Edit `.env` with your configuration:

```env
# API Keys
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here
GOOGLE_API_KEY=your_google_api_key_here

# Authentication
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
DATABASE_URL=postgresql://user:password@localhost/recording_angel
# For development with SQLite:
# DATABASE_URL=sqlite:///./recording_angel.db
```

### 3. Run the API

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## API Endpoints

### Authentication

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login with email/password
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/auth/logout` - Logout and revoke token
- `GET /api/auth/me` - Get current user info
- `PUT /api/auth/me` - Update current user profile
- `POST /api/auth/change-password` - Change password

### Users

- `GET /api/users/` - List users (leadership only)
- `GET /api/users/{user_id}` - Get user by ID
- `PUT /api/users/{user_id}` - Update user (leadership only)
- `PATCH /api/users/{user_id}/status` - Update user status (admin only)
- `PATCH /api/users/{user_id}/role` - Update user role (admin only)
- `DELETE /api/users/{user_id}` - Delete user (admin only)

### Sessions

- `POST /api/sessions/` - Create transcription session
- `GET /api/sessions/` - List sessions
- `GET /api/sessions/{session_id}` - Get session by ID
- `GET /api/sessions/code/{session_code}` - Get session by code
- `POST /api/sessions/{session_id}/join` - Join session
- `POST /api/sessions/{session_id}/leave` - Leave session
- `POST /api/sessions/{session_id}/end` - End session
- `GET /api/sessions/{session_id}/participants` - Get session participants

### WebRTC

- `POST /api/webrtc/token` - Generate AssemblyAI WebRTC token

### WebSocket

- `WS /ws` - Real-time audio transcription

### Health

- `GET /health` - Health check with database status
- `GET /health/auth` - Authentication system health

## Authentication Flow

### 1. Registration

```bash
curl -X POST "http://localhost:8080/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "email": "john@example.com",
    "password": "securepassword123",
    "ward": 1,
    "stake": 1
  }'
```

### 2. Login

```bash
curl -X POST "http://localhost:8080/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "securepassword123"
  }'
```

### 3. Using Access Token

```bash
curl -X GET "http://localhost:8080/api/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## WebSocket Connection

Connect to the WebSocket with authentication:

```javascript
const ws = new WebSocket(
  `ws://localhost:8080/ws?session_id=${sessionId}&user_id=${userId}&access_token=${accessToken}&sample_rate=16000&encoding=pcm_s16le`
);
```

## User Roles & Permissions

- **MEMBER** - Basic user access, can join sessions
- **BISHOP** - Ward-level management, can create sessions
- **STAKEPRESIDENT** - Stake-level oversight, can manage all ward sessions
- **MISSIONARY** - Mission-specific access
- **MISSIONPRESIDENT** - Mission leadership
- **ADMIN** - Full system access, can manage users and roles

## Database Schema

The API automatically creates the following tables:

- `users` - User accounts and profiles
- `sessions` - Transcription sessions
- `session_participants` - Session participation tracking
- `transcription_chunks` - Stored transcription data
- `refresh_tokens` - JWT refresh token storage

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black app/
isort app/
```

### Type Checking

```bash
mypy app/
```

## Production Deployment

1. Set a strong `SECRET_KEY`
2. Use PostgreSQL for production database
3. Configure proper CORS origins
4. Set up SSL/TLS termination
5. Use environment variables for all sensitive configuration

## Security Features

- **Password Hashing** - BCrypt with salt
- **JWT Tokens** - Access and refresh token rotation
- **Role-based Access Control** - Granular permissions
- **Input Validation** - Pydantic models for all requests
- **SQL Injection Protection** - SQLAlchemy ORM
- **CORS Protection** - Configurable cross-origin policies

## License

This project is part of the Recording Angel system.
