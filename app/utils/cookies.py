from fastapi import Response
from datetime import datetime, timedelta
from app.config import settings

def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    """Set HTTP-only cookies for authentication"""
    
    # Access token cookie (15 minutes)
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.access_token_expire_minutes * 60,
        expires=datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes),
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        httponly=settings.cookie_httponly,
        samesite=settings.cookie_samesite
    )
    
    # Refresh token cookie (7 days)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        expires=datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days),
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        httponly=settings.cookie_httponly,
        samesite=settings.cookie_samesite
    )

def clear_auth_cookies(response: Response):
    """Clear authentication cookies"""
    response.delete_cookie(
        key="access_token",
        domain=settings.cookie_domain
    )
    response.delete_cookie(
        key="refresh_token",
        domain=settings.cookie_domain
    )