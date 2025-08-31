# app/auth/enhanced_dependencies.py
from fastapi import Depends, HTTPException, Cookie, status
from typing import Optional, Dict, Any
from app.auth.cognito import cognito_client
from app.auth.models import UserResponse, UserRole, SubscriptionTier
from app.auth.user_service import user_service
from app.database.connection import get_db_connection, release_db_connection
from app.database.user_repository import UserRepository

async def get_current_user_with_db(
    access_token: Optional[str] = Cookie(None)
) -> Dict[str, Any]:
    """Get current user from Cognito with database sync"""
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        # Get user from Cognito
        cognito_user = cognito_client.get_user_info(access_token)
        
        # Get user from database
        db_user = await user_service.get_user_profile(cognito_user.id)
        
        if not db_user:
            # Create user in database if missing
            connection = await get_db_connection()
            try:
                user_repo = UserRepository(connection)
                db_user = await user_repo.create_user(
                    cognito_sub=cognito_user.id,
                    email=cognito_user.email,
                    display_name=cognito_user.name,
                    role=cognito_user.role,
                    subscription_tier=cognito_user.subscription_tier
                )
            finally:
                await release_db_connection(connection)
        
        # Return combined user data
        return {
            "cognito_user": cognito_user,
            "db_user": db_user,
            "user": UserResponse(
                id=cognito_user.id,
                email=cognito_user.email,
                name=cognito_user.name,
                role=UserRole(db_user['role']),
                subscription_tier=SubscriptionTier(db_user['subscription_tier']),
                permissions=cognito_user.permissions
            )
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

async def get_current_user_simple(
    access_token: Optional[str] = Cookie(None)
) -> UserResponse:
    """Get current user (simple version for backward compatibility)"""
    user_data = await get_current_user_with_db(access_token)
    return user_data["user"]