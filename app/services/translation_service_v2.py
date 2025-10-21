"""LLM-based translation service with provider abstraction for real-time transcription translation."""

import asyncio
from datetime import datetime
from typing import Dict, Optional, AsyncGenerator, Any
from abc import ABC, abstractmethod

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from app.config import config
from app.utils.time import now_utc


class TranslationProvider(ABC):
    """Abstract base class for translation providers."""

    @abstractmethod
    async def translate_stream(self, session_id: str, text: str, target_lang: str, source_lang: str = "auto") -> AsyncGenerator[str, None]:
        """Stream translation chunks as they become available."""
        if False:  # This will never execute but makes this an async generator
            yield ""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available."""
        pass

    def cleanup_session(self, session_id: str, source_lang: str = "auto", target_lang: str = "es"):
        """Clean up provider-specific session data (optional)."""
        pass


class GoogleTranslateProvider(TranslationProvider):
    """Google Cloud Translation provider (legacy)."""

    def __init__(self):
        self.client = None
        # Skip Google Translate initialization for now since it requires ADC setup
        # This provider will be unavailable until proper credentials are configured

    async def translate_stream(self, session_id: str, text: str, target_lang: str, source_lang: str = "auto") -> AsyncGenerator[str, None]:
        if not self.client or not text.strip():
            return

        try:
            result = self.client.translate(
                text,
                target_language=target_lang,
                source_language=None if source_lang == "auto" else source_lang,
            )
            yield result["translatedText"]
        except Exception as e:
            print(f"Google Translate error for session {session_id}: {e}")

    def is_available(self) -> bool:
        return self.client is not None


class GeminiTranslateProvider(TranslationProvider):
    """Google Gemini provider for high-quality translation."""

    def __init__(self):
        self._chats: Dict[str, Any] = {}  # Store chat sessions per session_id + language pair

    def _get_chat_key(self, session_id: str, source_lang: str, target_lang: str) -> str:
        """Generate unique key for chat session."""
        return f"{session_id}_{source_lang}_{target_lang}"

    async def translate_stream(self, session_id: str, text: str, target_lang: str, source_lang: str = "auto") -> AsyncGenerator[str, None]:
        if not config.GOOGLE_API_KEY or not text.strip():
            return

        try:
            chat_key = self._get_chat_key(session_id, source_lang, target_lang)

            # Initialize or get existing chat session
            if chat_key not in self._chats:
                if GENAI_AVAILABLE:
                    model = genai.GenerativeModel(config.TRANSLATION_MODEL)
                    self._chats[chat_key] = model.start_chat(history=[])
                else:
                    return

                # Send system prompt to establish translator role
                system_prompt = f"""You are a professional translator specializing in {source_lang} to {target_lang} translation.
You will receive text in {source_lang} and must translate it accurately to {target_lang}.

Rules:
- Maintain the original meaning and tone
- Use natural, fluent {target_lang}
- Respond only with the translation, no explanations or additional text
- Preserve formatting and punctuation where appropriate
- For religious/church content, maintain respectful and appropriate language
- If the text appears incomplete or cut off, translate what's available without adding content
- Handle repetitive or similar text by providing consistent translations
- Maintain consistency in terminology throughout the conversation"""

                await self._chats[chat_key].send_message_async(system_prompt)

            # Send translation request with quality instructions
            prompt = f"""Translate this text to {target_lang}. If the text appears incomplete, translate what's available. If this is similar to previous text, maintain consistency.

Text to translate: {text}"""
            response = await self._chats[chat_key].send_message_async(prompt)

            if response.text:
                translated_text = response.text.strip()

                # Basic quality check - ensure translation is not too short compared to original
                if len(translated_text) < len(text) * 0.3 and len(text) > 10:
                    print(f"Warning: Translation suspiciously short for session {session_id}: '{text}' -> '{translated_text}'")
                    # Still yield it but log the issue

                # Check for common error responses
                if translated_text.lower() in ["error", "failed", "unable to translate", "translation failed"]:
                    print(f"Error response from translation service for session {session_id}: '{translated_text}'")
                    return

                yield translated_text

        except Exception as e:
            print(f"Gemini translation error for session {session_id}: {e}")

    def is_available(self) -> bool:
        return GENAI_AVAILABLE and bool(config.GOOGLE_API_KEY)

    def cleanup_session(self, session_id: str, source_lang: str = "auto", target_lang: str = "es"):
        """Clean up chat session for a specific session."""
        chat_key = self._get_chat_key(session_id, source_lang, target_lang)
        if chat_key in self._chats:
            del self._chats[chat_key]


class HTTPTranslateProvider(TranslationProvider):
    """HTTP provider for custom AI server integration."""

    async def translate_stream(self, session_id: str, text: str, target_lang: str, source_lang: str = "auto") -> AsyncGenerator[str, None]:
        if not config.TRANSLATION_HTTP_URL or not text.strip():
            return

        try:
            headers = {"Content-Type": "application/json"}
            if config.TRANSLATION_HTTP_AUTH_HEADER:
                # Expected format: "Authorization: Bearer xyz" or any header string "Header-Name: value"
                try:
                    header_name, header_value = config.TRANSLATION_HTTP_AUTH_HEADER.split(":", 1)
                    headers[header_name.strip()] = header_value.strip()
                except ValueError:
                    print("TRANSLATION_HTTP_AUTH_HEADER is malformed; expected 'Header-Name: value'")

            payload = {
                "text": text,
                "target_language": target_lang,
                "source_language": source_lang,
                "session_id": session_id,
                "model": config.TRANSLATION_MODEL
            }

            if HTTPX_AVAILABLE:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(config.TRANSLATION_HTTP_URL, headers=headers, json=payload)

                if resp.status_code == 200:
                    data = resp.json()
                    translated_text = data.get("translated_text") or data.get("translation") or data.get("text")
                    if translated_text:
                        yield translated_text
                else:
                    print(f"HTTP translation failed ({resp.status_code}): {resp.text}")

        except Exception as e:
            print(f"HTTP translation error for session {session_id}: {e}")

    def is_available(self) -> bool:
        return bool(config.TRANSLATION_HTTP_URL)


class TranslationServiceV2:
    """Main translation service with provider abstraction."""

    def __init__(self):
        self.providers: Dict[str, TranslationProvider] = {
            "google": GoogleTranslateProvider(),
            "gemini": GeminiTranslateProvider(),
            "http": HTTPTranslateProvider()
        }

        # Rate limiting
        self._request_count = 0
        self._last_reset = now_utc()

        # Translation cache to avoid redundant API calls
        self._translation_cache: Dict[str, str] = {}
        self._cache_max_size = 1000  # Maximum cache entries

    async def translate_stream(self, session_id: str, text: str, target_lang: str, source_lang: str = "auto") -> AsyncGenerator[str, None]:
        """Stream translation using configured provider."""
        provider_name = config.TRANSLATION_PROVIDER
        provider = self.providers.get(provider_name)

        if not provider or not provider.is_available():
            print(f"Translation provider '{provider_name}' not available")
            return

        if not text.strip():
            return

        try:
            # Rate limiting check
            await self._check_rate_limits()

            async for chunk in provider.translate_stream(session_id, text, target_lang, source_lang):
                self._request_count += 1
                yield chunk

        except Exception as e:
            print(f"Translation service error for session {session_id}: {e}")

    async def translate_text(self, session_id: str, text: str, target_lang: str, source_lang: str = "auto") -> Optional[str]:
        """Non-streaming translation for backward compatibility with caching."""
        # Normalize and clean the text for better caching
        clean_text = text.strip()
        if not clean_text:
            return None

        # Create a more robust cache key that handles minor variations
        cache_key = f"{clean_text.lower()}_{source_lang}_{target_lang}"

        # Check cache first with normalized key
        if cache_key in self._translation_cache:
            cached_result = self._translation_cache[cache_key]
            print(f"Cache hit for translation: '{clean_text[:30]}...' -> '{cached_result[:30]}...'")
            return cached_result

        # Also check for very similar texts in cache (basic fuzzy matching)
        for existing_key, cached_result in self._translation_cache.items():
            if existing_key.endswith(f"_{source_lang}_{target_lang}"):
                existing_text = existing_key[:-len(f"_{source_lang}_{target_lang}")]
                if self._texts_are_similar(clean_text.lower(), existing_text, threshold=0.9):
                    print(f"Fuzzy cache hit for translation: '{clean_text[:30]}...' -> '{cached_result[:30]}...'")
                    return cached_result

        # Not in cache, translate normally
        chunks = []
        async for chunk in self.translate_stream(session_id, text, target_lang, source_lang):
            chunks.append(chunk)

        result = " ".join(chunks) if chunks else None

        # Cache the result if successful and valid
        if result and self._is_valid_translation(result):
            # Implement LRU-style cache management
            if len(self._translation_cache) >= self._cache_max_size:
                # Remove oldest entries (simple approach - remove 10% of entries)
                cache_items = list(self._translation_cache.items())
                remove_count = max(1, len(cache_items) // 10)
                for i in range(remove_count):
                    del self._translation_cache[cache_items[i][0]]

            self._translation_cache[cache_key] = result
            print(f"Cached translation: '{clean_text[:30]}...' -> '{result[:30]}...' (cache size: {len(self._translation_cache)})")

        return result

    def cleanup_session(self, session_id: str, source_lang: str = "auto", target_lang: str = "es"):
        """Clean up provider-specific session data."""
        for provider in self.providers.values():
            if hasattr(provider, 'cleanup_session'):
                provider.cleanup_session(session_id, source_lang, target_lang)

    def get_available_providers(self) -> Dict[str, bool]:
        """Get availability status of all providers."""
        return {name: provider.is_available() for name, provider in self.providers.items()}

    def clear_cache(self):
        """Clear the translation cache."""
        cache_size = len(self._translation_cache)
        self._translation_cache.clear()
        print(f"Cleared translation cache ({cache_size} entries)")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "cache_size": len(self._translation_cache),
            "cache_max_size": self._cache_max_size,
            "cache_hit_rate": 0  # Could be implemented with hit/miss counters
        }

    def _texts_are_similar(self, text1: str, text2: str, threshold: float = 0.8) -> bool:
        """Check if two texts are similar enough to be considered the same for caching."""
        if text1 == text2:
            return True

        # Simple word-based similarity check
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return False

        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        if union == 0:
            return False

        similarity = intersection / union
        return similarity >= threshold

    def _is_valid_translation(self, translation: str) -> bool:
        """Check if a translation result is valid and worth caching."""
        if not translation or not translation.strip():
            return False

        # Check for common error patterns
        error_patterns = [
            "error", "failed", "unable", "sorry", "i cannot", "i'm sorry",
            "no translation", "translation failed", "api error"
        ]

        translation_lower = translation.lower().strip()
        if any(pattern in translation_lower for pattern in error_patterns):
            return False

        # Check minimum length (avoid caching very short/incomplete translations)
        if len(translation.strip()) < 3:
            return False

        return True

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


# Global translation service instance
translation_service_v2 = TranslationServiceV2()