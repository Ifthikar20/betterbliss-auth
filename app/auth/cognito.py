import boto3
import hmac
import hashlib
import base64
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError
from app.config import settings
from app.auth.models import UserRole, SubscriptionTier, UserResponse
import json
from jose import jwt, JWTError
from datetime import datetime, timedelta

class CognitoClient:
    def __init__(self):
        self.client = boto3.client('cognito-idp', region_name=settings.aws_region)
        self.user_pool_id = settings.cognito_user_pool_id
        self.client_id = settings.cognito_client_id
        self.client_secret = settings.cognito_client_secret
        
    def _get_secret_hash(self, username: str) -> str:
        """Generate SECRET_HASH for Cognito"""
        message = bytes(username + self.client_id, 'utf-8')
        key = bytes(self.client_secret, 'utf-8')
        secret_hash = base64.b64encode(
            hmac.new(key, message, digestmod=hashlib.sha256).digest()
        ).decode()
        return secret_hash
    
    def register_user(self, email: str, password: str, full_name: str) -> Dict[str, Any]:
        """Register a new user in Cognito"""
        try:
            response = self.client.sign_up(
                ClientId=self.client_id,
                SecretHash=self._get_secret_hash(email),
                Username=email,
                Password=password,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'name', 'Value': full_name},
                    {'Name': 'custom:role', 'Value': UserRole.FREE_USER},
                    {'Name': 'custom:subscription_tier', 'Value': SubscriptionTier.FREE},
                    {'Name': 'custom:permissions', 'Value': json.dumps([])}
                ]
            )
            
            # Auto-confirm user in development
            if settings.environment == "development":
                self.client.admin_confirm_sign_up(
                    UserPoolId=self.user_pool_id,
                    Username=email
                )
            
            return {
                "success": True,
                "user_sub": response['UserSub'],
                "email": email
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UsernameExistsException':
                raise ValueError("An account with this email already exists")
            elif error_code == 'InvalidPasswordException':
                raise ValueError("Password does not meet requirements")
            else:
                raise ValueError(f"Registration failed: {e.response['Error']['Message']}")
    
    def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user with Cognito"""
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': email,
                    'PASSWORD': password,
                    'SECRET_HASH': self._get_secret_hash(email)
                }
            )
            
            if 'ChallengeName' in response:
                # Handle MFA or other challenges
                raise ValueError(f"Authentication challenge required: {response['ChallengeName']}")
            
            return {
                "access_token": response['AuthenticationResult']['AccessToken'],
                "refresh_token": response['AuthenticationResult']['RefreshToken'],
                "id_token": response['AuthenticationResult']['IdToken'],
                "expires_in": response['AuthenticationResult']['ExpiresIn']
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NotAuthorizedException':
                raise ValueError("Invalid email or password")
            elif error_code == 'UserNotConfirmedException':
                raise ValueError("Please confirm your email before signing in")
            else:
                raise ValueError(f"Authentication failed: {e.response['Error']['Message']}")
    
    def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': refresh_token
                }
            )
            
            return {
                "access_token": response['AuthenticationResult']['AccessToken'],
                "id_token": response['AuthenticationResult']['IdToken'],
                "expires_in": response['AuthenticationResult']['ExpiresIn']
            }
            
        except ClientError as e:
            raise ValueError("Token refresh failed")
    
    def get_user_info(self, access_token: str) -> UserResponse:
        """Get user information from access token"""
        try:
            response = self.client.get_user(AccessToken=access_token)
            
            # Parse user attributes
            attributes = {attr['Name']: attr['Value'] for attr in response['UserAttributes']}
            
            # Get custom attributes with defaults
            role = attributes.get('custom:role', UserRole.FREE_USER)
            subscription_tier = attributes.get('custom:subscription_tier', SubscriptionTier.FREE)
            permissions = json.loads(attributes.get('custom:permissions', '[]'))
            
            return UserResponse(
                id=attributes.get('sub', ''),
                email=attributes.get('email', ''),
                name=attributes.get('name', ''),
                role=role,
                subscription_tier=subscription_tier,
                permissions=permissions
            )
            
        except ClientError as e:
            raise ValueError("Failed to get user information")
    
    def sign_out(self, access_token: str):
        """Sign out user from Cognito"""
        try:
            self.client.global_sign_out(AccessToken=access_token)
        except ClientError:
            # Even if sign out fails, we'll clear cookies
            pass
    
    def initiate_google_auth(self) -> str:
        """Generate Google OAuth URL"""
        google_oauth_url = (
            f"https://{settings.cognito_domain}/oauth2/authorize?"
            f"client_id={self.client_id}&"
            f"response_type=code&"
            f"scope=email+openid+profile&"
            f"redirect_uri={settings.backend_url}/auth/callback&"
            f"identity_provider=Google"
        )
        return google_oauth_url
    
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        import httpx
        
        token_url = f"https://{settings.cognito_domain}/oauth2/token"
        
        data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': f"{settings.backend_url}/auth/callback"
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        response = httpx.post(token_url, data=data, headers=headers)
        
        if response.status_code != 200:
            raise ValueError("Failed to exchange code for tokens")
        
        return response.json()

cognito_client = CognitoClient()