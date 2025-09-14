# app/auth/dependencies.py
from fastapi import Depends, HTTPException, Cookie, status
from typing import Optional
from app.auth.cognito import cognito_client
from app.auth.models import UserResponse

async def get_current_user(
    access_token: Optional[str] = Cookie(None)
) -> UserResponse:
    """Get current user from access token cookie - REQUIRED authentication"""
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        user = cognito_client.get_user_info(access_token)
        return user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

async def get_optional_user(
    access_token: Optional[str] = Cookie(None)
) -> Optional[UserResponse]:
    """Get current user if authenticated, otherwise None"""
    if not access_token:
        return None
    
    try:
        user = cognito_client.get_user_info(access_token)
        return user
    except Exception:
        return None