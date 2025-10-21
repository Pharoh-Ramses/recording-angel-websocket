#!/usr/bin/env python3
"""Test script for the new LLM-based translation system."""

import asyncio
import os
from app.services.translation_service_v2 import translation_service_v2
from app.config import config

async def test_translation():
    """Test the new translation service with different providers."""

    print("Testing LLM-based Translation System")
    print("=" * 40)

    # Test text
    test_text = "Hello, this is a test of the new translation system. We are testing real-time audio transcription translation."

    print(f"Original text: {test_text}")
    print()

    # Check available providers
    providers = translation_service_v2.get_available_providers()
    print("Available providers:")
    for provider, available in providers.items():
        status = "✓ Available" if available else "✗ Not available"
        print(f"  {provider}: {status}")
    print()

    # Test Gemini provider (if available)
    if providers.get("gemini", False):
        print("Testing Gemini provider...")
        try:
            translated = await translation_service_v2.translate_text(
                session_id="test_session",
                text=test_text,
                target_lang="es",
                source_lang="en"
            )
            print(f"Gemini translation to Spanish: {translated}")
        except Exception as e:
            print(f"Gemini translation failed: {e}")
        print()

    # Test Google provider (if available)
    if providers.get("google", False):
        print("Testing Google provider...")
        try:
            translated = await translation_service_v2.translate_text(
                session_id="test_session",
                text=test_text,
                target_lang="fr",
                source_lang="en"
            )
            print(f"Google translation to French: {translated}")
        except Exception as e:
            print(f"Google translation failed: {e}")
        print()

    # Test streaming (if Gemini is available)
    if providers.get("gemini", False):
        print("Testing streaming translation...")
        try:
            print("Streaming chunks:")
            async for chunk in translation_service_v2.translate_stream(
                session_id="test_session_stream",
                text=test_text,
                target_lang="de",
                source_lang="en"
            ):
                print(f"  Chunk: {chunk}")
        except Exception as e:
            print(f"Streaming translation failed: {e}")
        print()

    print("Translation system test completed!")

if __name__ == "__main__":
    # Set test environment variables
    os.environ["TRANSLATION_PROVIDER"] = "gemini"
    os.environ["TRANSLATION_MODEL"] = "gemini-2.5-flash-lite"
    os.environ["TRANSLATION_CHUNK_SECONDS"] = "5"

    # Note: You'll need to set GOOGLE_API_KEY in your environment
    # os.environ["GOOGLE_API_KEY"] = "your-api-key-here"

    asyncio.run(test_translation())