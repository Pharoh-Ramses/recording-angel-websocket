"""AI providers for paragraph refinement."""

import asyncio
from datetime import datetime
from typing import Dict, Optional

import httpx
import google.generativeai as genai

from app.config import config
from app.utils.time import now_utc
from app.services.session_manager import session_manager


# Paragraphizer throttling state
paragraphizer_last_call_at: Dict[str, datetime] = {}


async def refine_and_broadcast_paragraph(session_id: str, paragraph_data: dict) -> None:
    """Send paragraph text to AI provider to refine into a clean paragraph, then broadcast."""
    try:
        # Throttle per session to avoid hitting rate limits
        now = now_utc()
        last_call = paragraphizer_last_call_at.get(session_id)
        if last_call is not None:
            delta = (now - last_call).total_seconds()
            if delta < config.PARAGRAPHIZER_COOLDOWN_SECONDS:
                delay = config.PARAGRAPHIZER_COOLDOWN_SECONDS - delta
                print(f"Paragraphizer cooling down {delay:.1f}s for session {session_id}")
                asyncio.create_task(_refine_after_delay(session_id, paragraph_data, delay))
                return

        # Get buffered text directly (new approach) or fall back to verses (legacy)
        text = paragraph_data.get("buffered_text", "")
        if not text:
            # Legacy fallback for any remaining verse-based messages
            verses = paragraph_data.get("verses", [])
            text = "\n".join(v.get("text", "") for v in verses)
        if not text:
            return

        refined_text = None

        # Neutral instruction: no formatting/rewriting beyond grouping
        instruction = (
            "Group the provided lines into coherent paragraphs. "
            "Do not change, add, or remove any words or characters from the input. "
            "Return only the same text, with paragraph breaks inserted where appropriate."
        )

        if config.PARAGRAPHIZER_PROVIDER == "gemini":
            refined_text = await _refine_with_gemini(session_id, text, instruction)
        elif config.PARAGRAPHIZER_PROVIDER == "http":
            refined_text = await _refine_with_http(session_id, text, instruction, paragraph_data)
        else:
            # Default to LeMUR
            refined_text = await _refine_with_lemur(session_id, text, instruction)

        # If refinement succeeded, broadcast paragraph_refined
        if refined_text and refined_text.strip():
            paragraphizer_last_call_at[session_id] = now
            refined_message = {
                "type": "paragraph_refined",
                "data": {
                    "session_id": session_id,
                    "paragraph_number": paragraph_data.get("paragraph_number"),
                    "refined_text": refined_text.strip(),
                    "completed_at": now_utc().isoformat()
                }
            }
            print(f"Session {session_id}: Broadcasting paragraph_refined {refined_message['data']['paragraph_number']}")
            await session_manager.broadcast_to_session(session_id, refined_message)
    except Exception as e:
        print(f"Error refining paragraph with AI: {e}")


async def _refine_with_gemini(session_id: str, text: str, instruction: str) -> Optional[str]:
    """Refine text using Google Gemini."""
    if not config.GOOGLE_API_KEY:
        print("Gemini selected but GOOGLE_API_KEY not configured; skipping refinement")
        return None
    
    try:
        model = genai.GenerativeModel(config.PARAGRAPHIZER_MODEL)
        
        # Create the prompt for Gemini
        prompt = f"""Task: {instruction}

Text to organize:
{text}

Please return only the reorganized text with appropriate paragraph breaks."""

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=2000,
            )
        )
        
        if response.text:
            return response.text.strip()
        else:
            print(f"Gemini returned empty response for session {session_id}")
            return None
            
    except Exception as e:
        print(f"Gemini API error for session {session_id}: {e}")
        return None


async def _refine_with_http(session_id: str, text: str, instruction: str, paragraph_data: dict) -> Optional[str]:
    """Refine text using HTTP provider."""
    if not config.PARAGRAPHIZER_HTTP_URL:
        print("Paragraphizer HTTP URL not configured; skipping refinement")
        return None
    
    try:
        headers = {"Content-Type": "application/json"}
        if config.PARAGRAPHIZER_HTTP_AUTH_HEADER:
            # Expected format: "Authorization: Bearer xyz" or any header string "Header-Name: value"
            try:
                header_name, header_value = config.PARAGRAPHIZER_HTTP_AUTH_HEADER.split(":", 1)
                headers[header_name.strip()] = header_value.strip()
            except ValueError:
                print("PARAGRAPHIZER_HTTP_AUTH_HEADER is malformed; expected 'Header-Name: value'")

        payload = {
            "model": config.PARAGRAPHIZER_MODEL,
            "instruction": instruction,
            "text": text,
            "session_id": session_id,
            "paragraph_number": paragraph_data.get("paragraph_number")
        }

        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(config.PARAGRAPHIZER_HTTP_URL, headers=headers, json=payload)
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                try:
                    backoff = float(retry_after)
                except (TypeError, ValueError):
                    backoff = config.PARAGRAPHIZER_RETRY_BACKOFF_SECONDS
                print(f"HTTP paragraphizer rate limited; retrying in {backoff}s")
                asyncio.create_task(_refine_after_delay(session_id, paragraph_data, backoff))
                return None
            if resp.status_code < 400:
                data = resp.json()
                return data.get("refined_text") or data.get("text") or data.get("response")
            else:
                print(f"HTTP paragraphizer failed ({resp.status_code}): {resp.text}")
                return None
    except Exception as e:
        print(f"HTTP paragraphizer error for session {session_id}: {e}")
        return None


async def _refine_with_lemur(session_id: str, text: str, instruction: str) -> Optional[str]:
    """Refine text using AssemblyAI LeMUR."""
    try:
        url = "https://api.assemblyai.com/lemur/v3/generate/task"
        headers = {"Authorization": config.ASSEMBLYAI_API_KEY, "Content-Type": "application/json"}
        payload = {
            "final_model": config.PARAGRAPHIZER_MODEL,
            "input_text": text,
            "prompt": instruction,
            "temperature": 0,
            "max_output_size": 2000
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                try:
                    backoff = float(retry_after)
                except (TypeError, ValueError):
                    backoff = config.PARAGRAPHIZER_RETRY_BACKOFF_SECONDS
                print(f"LeMUR rate limited; retrying in {backoff}s")
                # Note: This would need paragraph_data parameter to retry properly
                return None
            if resp.status_code < 400:
                data = resp.json()
                return data.get("response") or data.get("responses") or data.get("result") or data.get("text")
            else:
                print(f"LeMUR refine failed ({resp.status_code}): {resp.text}")
                return None
    except Exception as e:
        print(f"LeMUR error for session {session_id}: {e}")
        return None


async def _refine_after_delay(session_id: str, paragraph_data: dict, delay_seconds: float) -> None:
    """Retry refinement after a delay."""
    try:
        await asyncio.sleep(max(0.0, delay_seconds))
        await refine_and_broadcast_paragraph(session_id, paragraph_data)
    except Exception as e:
        print(f"Error in delayed refine: {e}")
