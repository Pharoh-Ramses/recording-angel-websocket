"""Time utility functions."""

from datetime import datetime, timezone


def now_utc() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences for verse formatting."""
    import re
    if not text.strip():
        return []
    
    # Simple sentence splitting - matches the React app expectation
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if s.strip()]
