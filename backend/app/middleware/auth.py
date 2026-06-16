import secrets
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify the API key from the X-API-Key header.
    Returns 'unconfigured' if no API key is set, the provided key if valid.
    Raises HTTPException if key is missing or invalid.
    """
    if not settings.api_key:
        return "unconfigured"

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
        )

    if not secrets.compare_digest(api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )

    return api_key
