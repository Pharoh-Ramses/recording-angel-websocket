"""WebRTC token router."""

import httpx
from fastapi import APIRouter, HTTPException, Depends

from app.config import config
from app.auth import require_api_token
from app.models import TokenRequest

router = APIRouter(prefix="/api/webrtc", tags=["webrtc"])


@router.post("/token")
async def create_webrtc_token(
    body: TokenRequest,
    _: bool = require_api_token()
):
    """
    Create an ephemeral realtime token for the browser to initialize a WebRTC
    connection to AssemblyAI from a React app.
    """
    if not config.ASSEMBLYAI_API_KEY:
        raise HTTPException(status_code=500, detail="ASSEMBLYAI_API_KEY is not set")

    expires_in_seconds = body.expires_in or 60

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://streaming.assemblyai.com/v3/token",
                headers={"Authorization": config.ASSEMBLYAI_API_KEY},
                params={"expires_in_seconds": expires_in_seconds}
            )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach AssemblyAI: {e}")

    if response.status_code >= 400:
        try:
            err_json = response.json()
        except Exception:
            err_json = {"message": response.text}
        raise HTTPException(status_code=response.status_code, detail=err_json)

    return response.json()
