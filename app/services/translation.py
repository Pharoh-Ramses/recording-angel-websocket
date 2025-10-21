"""Google Cloud Translation service for real-time transcription translation."""

import asyncio
from datetime import datetime
from typing import Dict, Optional

try:
    from google.cloud import translate_v2 as translate

    GOOGLE_TRANSLATE_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_AVAILABLE = False
    print("Warning: google-cloud-translate not installed. Translation will be disabled.")

from app.config import config
from app.utils.time import now_utc


class TranslationService:
    """Service for translating transcription text using Google Cloud Translation."""

    def __init__(self):
        self.client = None
        self._init_client()

        # Cache for language detection to avoid repeated API calls
        self._language_cache: dict[str, str] = {}

        # Rate limiting
        self._request_count = 0
        self._last_reset = now_utc()

    def _init_client(self):
        """Initialize Google Translate client if API key is available."""
        if not GOOGLE_TRANSLATE_AVAILABLE:
            print("Google Cloud Translation library not available")
            return

        if config.GOOGLE_TRANSLATE_API_KEY:
            try:
                # Initialize with API key
                self.client = (
                    translate.Client.from_service_account_json(config.GOOGLE_TRANSLATE_API_KEY)
                    if config.GOOGLE_TRANSLATE_API_KEY.endswith(".json")
                    else translate.Client()
                )
                print("Google Cloud Translation initialized")
            except Exception as e:
                print(f"Failed to initialize Google Translate client: {e}")
        else:
            print("Warning: GOOGLE_TRANSLATE_API_KEY not configured")

    async def translate_text(
        self, text: str, target_language: str, source_language: str = "auto"
    ) -> Optional[str]:
        """
        Translate text using Google Cloud Translation API.

        Args:
            text: Text to translate
            target_language: Target language code (e.g., 'es', 'fr', 'de')
            source_language: Source language code or 'auto' for detection

        Returns:
            Translated text or None if translation fails
        """
        if not self.client or not text.strip():
            return None

        try:
            # Rate limiting check
            await self._check_rate_limits()

            # Use cached source language detection if available
            if source_language == "auto":
                source_language = self._get_cached_language(
                    text[:100]
                )  # First 100 chars for detection

            # Translate
            result = self.client.translate(
                text,
                target_language=target_language,
                source_language=source_language if source_language != "auto" else None,
            )

            # Cache detected language
            if "detectedSourceLanguage" in result:
                self._cache_language(text[:100], result["detectedSourceLanguage"])

            self._request_count += 1
            return result["translatedText"]

        except Exception as e:
            print(f"Translation error: {e}")
            return None

    async def detect_language(self, text: str) -> Optional[str]:
        """
        Detect the language of the given text.

        Args:
            text: Text to analyze

        Returns:
            Language code or None if detection fails
        """
        if not self.client or not text.strip():
            return None

        try:
            # Check cache first
            cached_lang = self._get_cached_language(text[:100])
            if cached_lang != "auto":
                return cached_lang

            # Rate limiting check
            await self._check_rate_limits()

            result = self.client.detect_language(text)
            if result and "language" in result:
                language = result["language"]
                self._cache_language(text[:100], language)
                self._request_count += 1
                return language

        except Exception as e:
            print(f"Language detection error: {e}")

        return None

    def _get_cached_language(self, text_sample: str) -> str:
        """Get cached language detection result."""
        return self._language_cache.get(text_sample, "auto")

    def _cache_language(self, text_sample: str, language: str):
        """Cache language detection result."""
        # Keep cache size manageable
        if len(self._language_cache) > 100:
            # Remove oldest entries (simple FIFO)
            oldest_keys = list(self._language_cache.keys())[:20]
            for key in oldest_keys:
                del self._language_cache[key]

        self._language_cache[text_sample] = language

    async def _check_rate_limits(self):
        """Simple rate limiting to avoid hitting API limits."""
        current_time = now_utc()

        # Reset counter every minute
        if (current_time - self._last_reset).total_seconds() > 60:
            self._request_count = 0
            self._last_reset = current_time

        # Limit to reasonable requests per minute
        if self._request_count > config.TRANSLATION_RATE_LIMIT:
            await asyncio.sleep(0.1)  # Brief pause

    def is_available(self) -> bool:
        """Check if translation service is available."""
        return self.client is not None

    def get_supported_languages(self) -> dict[str, str]:
        """Get list of supported languages."""
        if not self.client:
            return {}

        try:
            languages = self.client.get_languages()
            return {lang["language"]: lang["name"] for lang in languages}
        except Exception as e:
            print(f"Error getting supported languages: {e}")
            return {}


# Global translation service instance
translation_service = TranslationService()
