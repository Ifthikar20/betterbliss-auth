from pydantic import BaseModel, EmailStr
from typing import Optional, List
from enum import Enum

class UserRole(str, Enum):
    FREE_USER = "free_user"
    PREMIUM_USER = "premium_user"
    ADMIN = "admin"

class SubscriptionTier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    subscription_tier: SubscriptionTier
    permissions: List[str]

class LoginResponse(BaseModel):
    success: bool
    user: UserResponse
    token_type: str = "Bearer"
    expires_in: int

class TokenData(BaseModel):
    sub: str
    email: str
    role: UserRole
    subscription_tier: SubscriptionTier
    permissions: List[str]
    exp: Optional[int] = None