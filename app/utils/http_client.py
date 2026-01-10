import httpx
from fastapi import HTTPException

from app.core.config import config


async def call_internal_api(endpoint: str, payload: dict) -> dict:
    """
    Викликає Internal API з переданим payload.
    Повертає JSON-відповідь або кидає HTTPException.
    """
    url = f"{config.INTERNAL_HOST}{endpoint}"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={"X-Service-Token": "super-secret-service-token"},
            json=payload,
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Internal API error: {response.text}"
        )

    try:
        return response.json()
    except ValueError:
        raise HTTPException(status_code=500, detail="Internal API did not return JSON")
