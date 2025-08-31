# app/auth/enhanced_routes.py
from fastapi import APIRouter, Response, HTTPException, Cookie, Depends, status
from fastapi.responses import RedirectResponse
from typing import Optional, Dict, Any
from app.auth.models import (
    LoginRequest, RegisterRequest, LoginResponse, 
    UserResponse
)
from app.auth.user_service import user_service
from app.auth.enhanced_dependencies import get_current_user_with_db, get_current_user_simple
from app.utils.cookies import set_auth_cookies, clear_auth_cookies
from app.auth.cognito import cognito_client
from app.config import settings
import traceback
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=LoginResponse)
async def register(request: RegisterRequest, response: Response):
    """Register a new user with full database integration"""
    logger.info(f"Registration request for email: {request.email}")
    
    try:
        # Register user (handles both Cognito and Database)
        registration_result = await user_service.register_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name
        )
        
        # Auto-login after registration
        auth_result = await user_service.authenticate_user(
            email=request.email,
            password=request.password
        )
        
        # Set cookies
        set_auth_cookies(
            response=response,
            access_token=auth_result['auth_tokens']['access_token'],
            refresh_token=auth_result['auth_tokens']['refresh_token']
        )
        
        logger.info(f"Registration and auto-login successful for: {request.email}")
        
        return LoginResponse(
            success=True,
            user=auth_result['user'],
            expires_in=auth_result['auth_tokens']['expires_in']
        )
        
    except ValueError as e:
        logger.warning(f"Registration validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, response: Response):
    """Login with email and password with database sync"""
    logger.info(f"Login request for email: {request.email}")
    
    try:
        # Authenticate user (handles both Cognito and Database)
        auth_result = await user_service.authenticate_user(
            email=request.email,
            password=request.password
        )
        
        # Set cookies
        set_auth_cookies(
            response=response,
            access_token=auth_result['auth_tokens']['access_token'],
            refresh_token=auth_result['auth_tokens']['refresh_token']
        )
        
        logger.info(f"Login successful for: {request.email}")
        
        return LoginResponse(
            success=True,
            user=auth_result['user'],
            expires_in=auth_result['auth_tokens']['expires_in']
        )
        
    except ValueError as e:
        logger.warning(f"Login validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: UserResponse = Depends(get_current_user_simple)
):
    """Get current user information"""
    return user

@router.get("/profile")
async def get_detailed_profile(
    user_data: Dict[str, Any] = Depends(get_current_user_with_db)
):
    """Get detailed user profile including database information"""
    return {
        "user": user_data["user"],
        "profile": user_data["db_user"],
        "subscription_info": {
            "tier": user_data["db_user"]["subscription_tier"],
            "role": user_data["db_user"]["role"],
            "status": user_data["db_user"]["status"]
        },
        "account_created": user_data["db_user"]["created_at"],
        "last_updated": user_data["db_user"]["updated_at"]
    }

@router.put("/profile")
async def update_profile(
    request: Dict[str, Any],
    user_data: Dict[str, Any] = Depends(get_current_user_with_db)
):
    """Update user profile"""
    try:
        updated_user = await user_service.update_user_profile(
            cognito_sub=user_data["cognito_user"].id,
            display_name=request.get("display_name"),
            avatar_url=request.get("avatar_url")
        )
        
        return {
            "success": True,
            "user": updated_user,
            "message": "Profile updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Profile update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

@router.post("/logout")
async def logout(
    response: Response,
    access_token: Optional[str] = Cookie(None)
):
    """Logout user"""
    # Sign out from Cognito if token exists
    if access_token:
        try:
            cognito_client.sign_out(access_token)
        except:
            pass
    
    # Clear cookies
    clear_auth_cookies(response)
    
    return {"success": True, "message": "Logged out successfully"}

@router.post("/refresh")
async def refresh_token(
    response: Response,
    refresh_token: Optional[str] = Cookie(None)
):
    """Refresh access token"""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found"
        )
    
    try:
        # Refresh tokens with Cognito
        new_tokens = cognito_client.refresh_tokens(refresh_token)
        
        # Update access token cookie
        response.set_cookie(
            key="access_token",
            value=new_tokens['access_token'],
            max_age=settings.access_token_expire_minutes * 60,
            domain=settings.cookie_domain,
            secure=settings.cookie_secure,
            httponly=settings.cookie_httponly,
            samesite=settings.cookie_samesite
        )
        
        return {"success": True, "message": "Token refreshed"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to refresh token"
        )

@router.get("/google")
async def google_login():
    """Initiate Google OAuth login"""
    google_url = cognito_client.initiate_google_auth()
    return RedirectResponse(url=google_url)

@router.get("/callback")
async def auth_callback(
    code: str,
    response: Response
):
    """Handle OAuth callback from Cognito"""
    try:
        # Exchange code for tokens
        tokens = cognito_client.exchange_code_for_tokens(code)
        
        # Get user info from Cognito and sync with database
        access_token = tokens['access_token']
        user_info = cognito_client.get_user_info(access_token)
        
        # Sync user with database (create if doesn't exist)
        auth_result = await user_service.sync_cognito_user_with_db(user_info)
        
        # Set cookies
        set_auth_cookies(
            response=response,
            access_token=access_token,
            refresh_token=tokens['refresh_token']
        )
        
        # Redirect to frontend
        return RedirectResponse(
            url=f"{settings.frontend_url}/browse",
            status_code=status.HTTP_302_FOUND
        )
        
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        # Redirect to login with error
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=oauth_failed",
            status_code=status.HTTP_302_FOUND
        )