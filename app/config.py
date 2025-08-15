from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # AWS Cognito
    aws_region: str
    cognito_user_pool_id: str
    cognito_client_id: str
    cognito_client_secret: str
    cognito_domain: str
    
    # App Settings
    frontend_url: str
    backend_url: str
    jwt_secret_key: str
    cookie_domain: str
    environment: str = "development"
    
    # Cookie Settings
    cookie_secure: bool = False  # Set to True in production with HTTPS
    cookie_samesite: str = "lax"
    cookie_httponly: bool = True
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    
    class Config:
        env_file = ".env"

settings = Settings()