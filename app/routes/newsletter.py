# app/routes/newsletter.py
from fastapi import APIRouter, HTTPException, Request, status
from typing import Dict, Any, Optional
import hashlib
import time
import json
import logging
from datetime import datetime, timedelta

from app.newsletter.security import (
    verify_security_token,
    validate_proof_of_work,
    generate_secure_token,
    validate_fingerprint,
    verify_request_signature
)
from app.newsletter.crypto import get_server_public_key, decrypt_payload
from app.newsletter.service import newsletter_service
from app.utils.rate_limiting import RateLimiter
from app.utils.validation import validate_email, sanitize_input

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Newsletter"])
rate_limiter = RateLimiter()

@router.post("/secure-token")
async def get_secure_token(request: Request, token_request: Dict[str, Any]):
    """Generate secure token with proof-of-work challenge"""
    try:
        client_ip = request.client.host
        logger.info(f"Secure token request from IP: {client_ip}")
        
        if not await rate_limiter.check_rate_limit(client_ip, max_requests=5, window=300):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many token requests"
            )
        
        fingerprint = token_request.get('fingerprint')
        if not fingerprint or not validate_fingerprint(fingerprint):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid browser fingerprint"
            )
        
        token_data = await generate_secure_token(fingerprint, client_ip)
        
        return {
            "token": token_data["token"],
            "challenge": token_data["challenge"],
            "expires_at": token_data["expires_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate secure token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate secure token"
        )

@router.get("/public-key")
async def get_public_key():
    """Get public key for X25519 key exchange"""
    try:
        public_key = get_server_public_key()
        return {"publicKey": public_key}
    except Exception as e:
        logger.error(f"Failed to retrieve public key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve public key"
        )

async def validate_subscription_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize subscription data"""
    email = data.get("email")
    if not email or not validate_email(email):
        raise ValueError("Invalid email address")
    
    # Check honeypot fields
    metadata = data.get("metadata", {})
    honeypot_fields = ['website', 'phone', 'company']
    for field in honeypot_fields:
        if metadata.get(field):
            logger.warning(f"Honeypot triggered for email: {email}")
            raise ValueError("Bot detected")
    
    return {
        "email": sanitize_input(email.lower().strip()),
        "name": sanitize_input(data.get("name")) if data.get("name") else None,
        "source": data.get("source", "website"),
        "metadata": metadata
    }

@router.post("/newsletter/subscribe")
async def subscribe_newsletter(request: Request, payload: Dict[str, Any]):
    """Secure newsletter subscription with full encryption and validation"""
    try:
        client_ip = request.client.host
        logger.info(f"Newsletter subscription attempt from IP: {client_ip}")
        
        # Extract security headers
        security_token = request.headers.get("X-Security-Token")
        fingerprint = request.headers.get("X-Fingerprint")
        challenge_solution = request.headers.get("X-Challenge-Solution")
        request_signature = request.headers.get("X-Request-Signature")
        request_id = request.headers.get("X-Request-ID")
        
        if not all([security_token, fingerprint, challenge_solution, request_signature]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing security headers"
            )
        
        # Rate limiting
        if not await rate_limiter.check_rate_limit(client_ip, max_requests=3, window=3600):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many subscription attempts"
            )
        
        # Security validations
        if not await verify_security_token(security_token, fingerprint):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid security token"
            )
        
        if not validate_proof_of_work(challenge_solution, security_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid proof-of-work solution"
            )
        
        encrypted_payload = payload.get("encryptedPayload")
        if not verify_request_signature(encrypted_payload, request_signature, security_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid request signature"
            )
        
        # Decrypt and validate
        decrypted_data = await decrypt_payload(encrypted_payload)
        subscription_data = await validate_subscription_data(decrypted_data)
        
        # Process subscription
        result = await newsletter_service.subscribe(
            email=subscription_data["email"],
            name=subscription_data.get("name"),
            source=subscription_data.get("source", "website"),
            metadata=subscription_data.get("metadata", {}),
            client_ip=client_ip,
            request_id=request_id
        )
        
        logger.info(f"Newsletter subscription successful for: {subscription_data['email']}")
        return {"success": True, "message": "Subscription successful", "result": result}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Newsletter subscription failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Subscription failed"
        )