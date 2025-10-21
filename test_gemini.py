#!/usr/bin/env python3
"""Quick test to verify Gemini translation is working."""

import asyncio
import os
from app.services.translation_service_v2 import translation_service_v2

async def test_gemini():
    """Test Gemini translation directly."""
    print("Testing Gemini Translation...")

    # Test text
    test_text = "Hello, this is a test of the Gemini translation system."

    try:
        # Test translation
        translated = await translation_service_v2.translate_text(
            session_id="test",
            text=test_text,
            target_lang="es",
            source_lang="en"
        )

        if translated:
            print(f"✅ Gemini translation working!")
            print(f"Original: {test_text}")
            print(f"Spanish: {translated}")
        else:
            print("❌ Gemini translation returned None")

    except Exception as e:
        print(f"❌ Gemini translation error: {e}")
        print("Make sure GOOGLE_API_KEY is set in your .env file")

if __name__ == "__main__":
    asyncio.run(test_gemini())