# app/auth/user_service.py
from typing import Optional, Dict, Any
from app.database.connection import get_db_connection, release_db_connection
from app.database.user_repository import UserRepository
from app.auth.cognito import cognito_client
from app.auth.models import UserResponse, UserRole, SubscriptionTier
import logging

logger = logging.getLogger(__name__)

class UserService:
    """Service for managing users across Cognito and Database"""
    
    async def register_user(
        self, 
        email: str, 
        password: str, 
        full_name: str
    ) -> Dict[str, Any]:
        """Register user in both Cognito and Database"""
        connection = None
        try:
            # Step 1: Register in Cognito first
            cognito_response = cognito_client.register_user(
                email=email,
                password=password,
                full_name=full_name
            )
            
            # Step 2: Create user in database
            connection = await get_db_connection()
            user_repo = UserRepository(connection)
            
            db_user = await user_repo.create_user(
                cognito_sub=cognito_response['user_sub'],
                email=email,
                display_name=full_name,
                role=UserRole.FREE_USER,
                subscription_tier=SubscriptionTier.FREE
            )
            
            logger.info(f"User registered successfully: {email}")
            
            return {
                "success": True,
                "cognito_sub": cognito_response['user_sub'],
                "db_user": db_user
            }
            
        except Exception as e:
            logger.error(f"Registration failed for {email}: {e}")
            # If database creation fails but Cognito succeeded, 
            # we might want to clean up Cognito user here
            raise
        finally:
            if connection:
                await release_db_connection(connection)
    
    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user and sync with database"""
        connection = None
        try:
            # Step 1: Authenticate with Cognito
            auth_response = cognito_client.authenticate_user(email, password)
            
            # Step 2: Get user info from Cognito
            user_info = cognito_client.get_user_info(auth_response['access_token'])
            
            # Step 3: Sync with database
            connection = await get_db_connection()
            user_repo = UserRepository(connection)
            
            # Check if user exists in database
            db_user = await user_repo.get_user_by_cognito_sub(user_info.id)
            
            if not db_user:
                # Create user in database if doesn't exist
                logger.info(f"Creating missing database user for: {email}")
                db_user = await user_repo.create_user(
                    cognito_sub=user_info.id,
                    email=user_info.email,
                    display_name=user_info.name,
                    role=user_info.role,
                    subscription_tier=user_info.subscription_tier
                )
            else:
                # Update last login
                await user_repo.update_user_last_login(user_info.id)
            
            # Step 4: Create enhanced user response with database data
            enhanced_user = UserResponse(
                id=user_info.id,
                email=user_info.email,
                name=user_info.name,
                role=UserRole(db_user['role']),
                subscription_tier=SubscriptionTier(db_user['subscription_tier']),
                permissions=user_info.permissions
            )
            
            return {
                "auth_tokens": auth_response,
                "user": enhanced_user,
                "db_user": db_user
            }
            
        except Exception as e:
            logger.error(f"Authentication failed for {email}: {e}")
            raise
        finally:
            if connection:
                await release_db_connection(connection)
    
    async def get_user_profile(self, cognito_sub: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive user profile from database"""
        connection = None
        try:
            connection = await get_db_connection()
            user_repo = UserRepository(connection)
            
            return await user_repo.get_user_by_cognito_sub(cognito_sub)
            
        except Exception as e:
            logger.error(f"Failed to get user profile for {cognito_sub}: {e}")
            raise
        finally:
            if connection:
                await release_db_connection(connection)
    
    async def update_user_profile(
        self, 
        cognito_sub: str, 
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update user profile in database"""
        connection = None
        try:
            connection = await get_db_connection()
            user_repo = UserRepository(connection)
            
            return await user_repo.update_user_profile(
                cognito_sub=cognito_sub,
                display_name=display_name,
                avatar_url=avatar_url
            )
            
        except Exception as e:
            logger.error(f"Failed to update user profile for {cognito_sub}: {e}")
            raise
        finally:
            if connection:
                await release_db_connection(connection)

user_service = UserService()
