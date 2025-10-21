"""Configuration management for Recording Angel API."""

import os
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
DOTENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=DOTENV_PATH, override=False)


class Config:
    """Application configuration."""
    
    # API Keys
    ASSEMBLYAI_API_KEY: str = os.getenv("ASSEMBLYAI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # Simple API token for client authentication
    API_TOKEN: str = os.getenv("API_TOKEN", "")
    
    # Authentication configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # Database configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/recording_angel")
    
    # Paragraphizer configuration
    PARAGRAPHIZER_PROVIDER: str = os.getenv("PARAGRAPHIZER_PROVIDER", "gemini").lower()
    PARAGRAPHIZER_HTTP_URL: str = os.getenv("PARAGRAPHIZER_HTTP_URL", "")
    PARAGRAPHIZER_HTTP_AUTH_HEADER: str = os.getenv("PARAGRAPHIZER_HTTP_AUTH_HEADER", "")
    PARAGRAPHIZER_MODEL: str = os.getenv("PARAGRAPHIZER_MODEL", "gemini-2.5-flash-lite")
    PARAGRAPHIZER_COOLDOWN_SECONDS: int = int(os.getenv("PARAGRAPHIZER_COOLDOWN_SECONDS", "5"))
    PARAGRAPHIZER_RETRY_BACKOFF_SECONDS: int = int(os.getenv("PARAGRAPHIZER_RETRY_BACKOFF_SECONDS", "10"))
    
    # Text buffering configuration
    TEXT_BUFFER_SECONDS: int = 10
    
    # Translation configuration
    GOOGLE_TRANSLATE_API_KEY: str = os.getenv("GOOGLE_TRANSLATE_API_KEY", "")
    TRANSLATION_ENABLED: bool = os.getenv("TRANSLATION_ENABLED", "false").lower() == "true"
    TRANSLATION_DEFAULT_TARGET: str = os.getenv("TRANSLATION_DEFAULT_TARGET", "es")  # Spanish default
    TRANSLATION_RATE_LIMIT: int = int(os.getenv("TRANSLATION_RATE_LIMIT", "100"))  # requests per minute

    # New LLM-based translation configuration
    TRANSLATION_PROVIDER: str = os.getenv("TRANSLATION_PROVIDER", "gemini").lower()
    TRANSLATION_MODEL: str = os.getenv("TRANSLATION_MODEL", "gemini-2.5-flash-lite")
    TRANSLATION_CHUNK_SECONDS: int = int(os.getenv("TRANSLATION_CHUNK_SECONDS", "5"))
    TRANSLATION_HTTP_URL: str = os.getenv("TRANSLATION_HTTP_URL", "")
    TRANSLATION_HTTP_AUTH_HEADER: str = os.getenv("TRANSLATION_HTTP_AUTH_HEADER", "")
    
    # FastAPI configuration
    TITLE: str = "Recording Angel Python API"
    VERSION: str = "0.1.0"
    
    def __post_init__(self) -> None:
        """Post-initialization validation and setup."""
        self._validate_keys()
        self._configure_ai_providers()
    
    def _validate_keys(self) -> None:
        """Validate required API keys."""
        if not self.API_TOKEN:
            print("Warning: API_TOKEN not set - clients cannot authenticate")
        
        if not self.ASSEMBLYAI_API_KEY:
            print("Warning: ASSEMBLYAI_API_KEY not set")
        
        if self.PARAGRAPHIZER_PROVIDER == "gemini" and not self.GOOGLE_API_KEY:
            print("Warning: GOOGLE_API_KEY not set but Gemini provider selected")
        
        if self.TRANSLATION_ENABLED and not self.GOOGLE_TRANSLATE_API_KEY:
            print("Warning: TRANSLATION_ENABLED=true but GOOGLE_TRANSLATE_API_KEY not set")
        
        if self.SECRET_KEY == "your-secret-key-change-in-production":
            print("Warning: Using default SECRET_KEY - change in production")
    
    def _configure_ai_providers(self) -> None:
        """Configure AI providers based on settings."""
        # Configure Gemini for both paragraphizer and translation if either uses Gemini
        if (self.PARAGRAPHIZER_PROVIDER == "gemini" or self.TRANSLATION_PROVIDER == "gemini") and self.GOOGLE_API_KEY:
            genai.configure(api_key=self.GOOGLE_API_KEY)
            print(f"Gemini configured with API key for providers: paragraphizer={self.PARAGRAPHIZER_MODEL}, translation={self.TRANSLATION_MODEL}")


# Global configuration instance
config = Config()
config.__post_init__()
