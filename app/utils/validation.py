# app/utils/validation.py
import re
import html
from typing import Optional

def validate_email(email: str) -> bool:
    """Validate email format with strict RFC compliance"""
    if not email or len(email) > 254:
        return False
    
    # More comprehensive email validation
    pattern = r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
    
    if not re.match(pattern, email):
        return False
    
    # Additional checks
    local, domain = email.rsplit('@', 1)
    if len(local) > 64 or len(domain) > 253:
        return False
    
    return True

def sanitize_input(text: Optional[str]) -> Optional[str]:
    """Sanitize text input to prevent XSS and injection"""
    if not text:
        return None
    
    # HTML escape
    text = html.escape(text.strip())
    
    # Remove potentially dangerous characters
    text = re.sub(r'[<>"\'\x00-\x1f\x7f-\x9f]', '', text)
    
    # Limit length
    text = text[:100]
    
    return text if text else None