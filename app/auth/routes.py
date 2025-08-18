from fastapi import APIRouter, Response, HTTPException, Cookie, Depends, status
from fastapi.responses import RedirectResponse
from typing import Optional
from app.auth.models import (
    LoginRequest, RegisterRequest, LoginResponse, 
    UserResponse
)
from app.auth.cognito import cognito_client
from app.auth.dependencies import get_current_user, get_optional_user
from app.utils.cookies import set_auth_cookies, clear_auth_cookies
from app.config import settings
import traceback

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=LoginResponse)
async def register(request: RegisterRequest, response: Response):
    """Register a new user"""
    print(f"🔍 DEBUG: Registration request received for email: {request.email}")
    print(f"🔍 DEBUG: Full name: {request.full_name}")
    
    try:
        # Register with Cognito
        print(f"🔍 DEBUG: Calling cognito_client.register_user...")
        cognito_response = cognito_client.register_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name
        )
        print(f"✅ DEBUG: Registration successful: {cognito_response}")
        
        # Auto-login after registration
        print(f"🔍 DEBUG: Attempting auto-login...")
        auth_response = cognito_client.authenticate_user(
            email=request.email,
            password=request.password
        )
        print(f"✅ DEBUG: Auto-login successful")
        
        # Get user info
        user_info = cognito_client.get_user_info(auth_response['access_token'])
        print(f"✅ DEBUG: Got user info: {user_info.email}")
        
        # Set cookies
        set_auth_cookies(
            response=response,
            access_token=auth_response['access_token'],
            refresh_token=auth_response['refresh_token']
        )
        
        return LoginResponse(
            success=True,
            user=user_info,
            expires_in=auth_response['expires_in']
        )
        
    except ValueError as e:
        print(f"❌ DEBUG: ValueError in registration: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ DEBUG: Unexpected error in registration: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, response: Response):
    """Login with email and password"""
    print(f"🔍 DEBUG: Login request received for email: {request.email}")
    
    try:
        # Authenticate with Cognito
        print(f"🔍 DEBUG: Calling cognito_client.authenticate_user...")
        auth_response = cognito_client.authenticate_user(
            email=request.email,
            password=request.password
        )
        print(f"✅ DEBUG: Authentication successful")
        
        # Get user info
        user_info = cognito_client.get_user_info(auth_response['access_token'])
        print(f"✅ DEBUG: Got user info: {user_info.email}")
        
        # Set cookies
        set_auth_cookies(
            response=response,
            access_token=auth_response['access_token'],
            refresh_token=auth_response['refresh_token']
        )
        
        return LoginResponse(
            success=True,
            user=user_info,
            expires_in=auth_response['expires_in']
        )
        
    except ValueError as e:
        print(f"❌ DEBUG: ValueError in login: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ DEBUG: Unexpected error in login: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.post("/logout")
async def logout(
    response: Response,
    access_token: Optional[str] = Cookie(None),
    user: Optional[UserResponse] = Depends(get_optional_user)
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

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: UserResponse = Depends(get_current_user)
):
    """Get current user information"""
    return user

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
        
        # Get user info
        user_info = cognito_client.get_user_info(tokens['access_token'])
        
        # Set cookies
        set_auth_cookies(
            response=response,
            access_token=tokens['access_token'],
            refresh_token=tokens['refresh_token']
        )
        
        # Redirect to frontend
        return RedirectResponse(
            url=f"{settings.frontend_url}/browse",
            status_code=status.HTTP_302_FOUND
        )
        
    except Exception as e:
        # Redirect to login with error
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=oauth_failed",
            status_code=status.HTTP_302_FOUND
        )