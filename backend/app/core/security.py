from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
import secrets
from typing import Optional

from app.core.config import settings

# For future implementation if needed
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

def check_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> bool:
    """
    Validate API key if API security is enabled
    Currently a placeholder for future implementation
    """
    return True