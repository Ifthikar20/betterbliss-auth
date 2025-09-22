from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # AWS Cognito
    aws_region: str
    cognito_user_pool_id: str
    cognito_client_id: str
    cognito_client_secret: str
    cognito_domain: str
    
    # Email Settings (ADD THESE)
    from_email: str
    support_email: str
    ses_configuration_set: Optional[str] = None
    
    # Database Settings
    database_url: Optional[str] = None
    db_host: Optional[str] = None
    db_port: Optional[int] = None
    db_name: Optional[str] = None
    db_username: Optional[str] = None
    db_password: Optional[str] = None
    db_ssl_mode: str = "require"
    
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
        extra = "ignore"  # This line allows extra env vars without errors

settings = Settings()