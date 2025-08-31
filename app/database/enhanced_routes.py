# app/auth/enhanced_routes.py (Updated routes with database integration)
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
