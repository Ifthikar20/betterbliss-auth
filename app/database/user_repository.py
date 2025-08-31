# app/database/user_repository.py
import asyncpg
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
from app.auth.models import UserRole, SubscriptionTier
import logging

logger = logging.getLogger(__name__)

class UserRepository:
    def __init__(self, connection: asyncpg.Connection):
        self.conn = connection
    
    async def create_user(
        self,
        cognito_sub: str,
        email: str,
        display_name: str,
        role: str = UserRole.FREE_USER,
        subscription_tier: str = SubscriptionTier.FREE
    ) -> Dict[str, Any]:
        """Create a new user in the database"""
        try:
            user_id = str(uuid.uuid4())
            
            query = """
                INSERT INTO users (id, cognito_sub, email, display_name, role, subscription_tier)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, cognito_sub, email, display_name, role, subscription_tier, 
                         status, created_at, updated_at
            """
            
            result = await self.conn.fetchrow(
                query, user_id, cognito_sub, email, display_name, role, subscription_tier
            )
            
            logger.info(f"Created user in database: {email} (cognito_sub: {cognito_sub})")
            return dict(result)
            
        except asyncpg.UniqueViolationError as e:
            logger.warning(f"User already exists: {email}")
            # Return existing user instead of failing
            return await self.get_user_by_cognito_sub(cognito_sub)
        except Exception as e:
            logger.error(f"Failed to create user {email}: {e}")
            raise
    
    async def get_user_by_cognito_sub(self, cognito_sub: str) -> Optional[Dict[str, Any]]:
        """Get user by Cognito sub ID"""
        try:
            query = """
                SELECT id, cognito_sub, email, display_name, avatar_url, 
                       subscription_tier, role, status, created_at, updated_at
                FROM users 
                WHERE cognito_sub = $1
            """
            
            result = await self.conn.fetchrow(query, cognito_sub)
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Failed to get user by cognito_sub {cognito_sub}: {e}")
            raise
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            query = """
                SELECT id, cognito_sub, email, display_name, avatar_url, 
                       subscription_tier, role, status, created_at, updated_at
                FROM users 
                WHERE email = $1
            """
            
            result = await self.conn.fetchrow(query, email)
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            raise
    
    async def update_user_last_login(self, cognito_sub: str):
        """Update user's last login timestamp"""
        try:
            query = """
                UPDATE users 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE cognito_sub = $1
            """
            
            await self.conn.execute(query, cognito_sub)
            logger.info(f"Updated last login for user: {cognito_sub}")
            
        except Exception as e:
            logger.error(f"Failed to update last login for {cognito_sub}: {e}")
            raise
    
    async def update_user_profile(
        self, 
        cognito_sub: str, 
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update user profile information"""
        try:
            updates = []
            params = []
            param_count = 1
            
            if display_name is not None:
                updates.append(f"display_name = ${param_count}")
                params.append(display_name)
                param_count += 1
            
            if avatar_url is not None:
                updates.append(f"avatar_url = ${param_count}")
                params.append(avatar_url)
                param_count += 1
            
            if not updates:
                # Nothing to update
                return await self.get_user_by_cognito_sub(cognito_sub)
            
            updates.append(f"updated_at = CURRENT_TIMESTAMP")
            params.append(cognito_sub)
            
            query = f"""
                UPDATE users 
                SET {', '.join(updates)}
                WHERE cognito_sub = ${param_count}
                RETURNING id, cognito_sub, email, display_name, avatar_url, 
                         subscription_tier, role, status, created_at, updated_at
            """
            
            result = await self.conn.fetchrow(query, *params)
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Failed to update user profile for {cognito_sub}: {e}")
            raise
    
    async def update_user_subscription(
        self, 
        cognito_sub: str, 
        subscription_tier: str,
        role: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update user subscription and role"""
        try:
            if role:
                query = """
                    UPDATE users 
                    SET subscription_tier = $1, role = $2, updated_at = CURRENT_TIMESTAMP
                    WHERE cognito_sub = $3
                    RETURNING id, cognito_sub, email, display_name, avatar_url, 
                             subscription_tier, role, status, created_at, updated_at
                """
                result = await self.conn.fetchrow(query, subscription_tier, role, cognito_sub)
            else:
                query = """
                    UPDATE users 
                    SET subscription_tier = $1, updated_at = CURRENT_TIMESTAMP
                    WHERE cognito_sub = $2
                    RETURNING id, cognito_sub, email, display_name, avatar_url, 
                             subscription_tier, role, status, created_at, updated_at
                """
                result = await self.conn.fetchrow(query, subscription_tier, cognito_sub)
            
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Failed to update subscription for {cognito_sub}: {e}")
            raise
