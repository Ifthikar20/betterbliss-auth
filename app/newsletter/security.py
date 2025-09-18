# app/newsletter/security.py
import hashlib
import hmac
import time
import json
import secrets
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# In-memory token storage (use Redis in production)
active_tokens = {}

async def generate_secure_token(fingerprint: str, client_ip: str) -> Dict[str, Any]:
    """Generate secure token with proof-of-work challenge"""
    token = secrets.token_urlsafe(32)
    challenge_data = f"{token}:{fingerprint}:{int(time.time())}"
    challenge = {
        "data": challenge_data,
        "target": "0000",  # Require 4 leading zeros
        "difficulty": 4
    }
    
    expires_at = datetime.now() + timedelta(minutes=10)
    active_tokens[token] = {
        "fingerprint": fingerprint,
        "client_ip": client_ip,
        "created_at": datetime.now(),
        "expires_at": expires_at,
        "challenge": challenge,
        "used": False
    }
    
    logger.info(f"Generated secure token for fingerprint: {fingerprint[:8]}...")
    
    return {
        "token": token,
        "challenge": challenge,
        "expires_at": expires_at.isoformat()
    }

async def verify_security_token(token: str, fingerprint: str) -> bool:
    """Verify security token and fingerprint"""
    token_data = active_tokens.get(token)
    if not token_data:
        logger.warning(f"Token not found: {token[:8]}...")
        return False
    
    # Check expiry
    if datetime.now() > token_data["expires_at"]:
        del active_tokens[token]
        logger.warning(f"Token expired: {token[:8]}...")
        return False
    
    # Check fingerprint match
    if token_data["fingerprint"] != fingerprint:
        logger.warning(f"Fingerprint mismatch for token: {token[:8]}...")
        return False
    
    # Check if already used
    if token_data["used"]:
        logger.warning(f"Token already used: {token[:8]}...")
        return False
    
    return True

def validate_proof_of_work(solution: str, token: str) -> bool:
    """Validate proof-of-work solution"""
    token_data = active_tokens.get(token)
    if not token_data:
        return False
    
    challenge = token_data["challenge"]
    
    try:
        nonce = int(solution)
        attempt = f"{challenge['data']}{nonce}"
        hash_result = hashlib.sha256(attempt.encode()).hexdigest()
        
        if hash_result.startswith(challenge["target"]):
            # Mark token as used
            token_data["used"] = True
            logger.info(f"Proof-of-work validated for token: {token[:8]}...")
            return True
        
        logger.warning(f"Invalid proof-of-work for token: {token[:8]}...")
        return False
        
    except (ValueError, TypeError):
        logger.warning(f"Invalid proof-of-work solution format for token: {token[:8]}...")
        return False

def verify_request_signature(encrypted_payload: dict, signature: str, token: str) -> bool:
    """Verify request signature"""
    try:
        # Create consistent message for signature verification
        message = f"{json.dumps(encrypted_payload, sort_keys=True)}{token}{int(time.time() // 60)}"
        expected_signature = hashlib.sha256(message.encode()).hexdigest()
        
        # Use constant-time comparison to prevent timing attacks
        result = hmac.compare_digest(signature, expected_signature)
        if not result:
            logger.warning(f"Request signature verification failed for token: {token[:8]}...")
        
        return result
        
    except Exception as e:
        logger.error(f"Request signature verification error: {e}")
        return False

def validate_fingerprint(fingerprint: str) -> bool:
    """Validate browser fingerprint format"""
    if not fingerprint or len(fingerprint) != 64:
        return False
    
    # Check if it's a valid hex string
    try:
        int(fingerprint, 16)
        return True
    except ValueError:
        return False

def cleanup_expired_tokens():
    """Clean up expired tokens (call periodically)"""
    current_time = datetime.now()
    expired_tokens = [token for token, data in active_tokens.items() 
                     if current_time > data["expires_at"]]
    
    for token in expired_tokens:
        del active_tokens[token]
    
    if expired_tokens:
        logger.info(f"Cleaned up {len(expired_tokens)} expired tokens")