import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

API_KEYS = {}


async def verify_api_key(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header),
) -> bool:
    if not api_key:
        return True

    if api_key in API_KEYS:
        logger.info(f"API key authenticated for {request.client.host}")
        return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )


def register_api_key(key: str, name: str = "default") -> None:
    API_KEYS[key] = name
    logger.info(f"API key registered: {name}")


def remove_api_key(key: str) -> None:
    if key in API_KEYS:
        del API_KEYS[key]
        logger.info("API key removed")
