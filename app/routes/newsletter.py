# app/routes/newsletter.py
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
import logging
from datetime import datetime
import json
import os

router = APIRouter(prefix="/api/newsletter", tags=["newsletter"])

class SubscribeRequest(BaseModel):
    email: EmailStr
    name: str = None
    source: str = "unknown"

class SubscribeResponse(BaseModel):
    success: bool
    message: str

# Simple file-based storage for now (replace with your database later)
NEWSLETTER_FILE = "newsletter_subscribers.json"

def load_subscribers():
    """Load subscribers from JSON file"""
    if os.path.exists(NEWSLETTER_FILE):
        try:
            with open(NEWSLETTER_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_subscribers(subscribers):
    """Save subscribers to JSON file"""
    try:
        with open(NEWSLETTER_FILE, 'w') as f:
            json.dump(subscribers, f, indent=2, default=str)
        return True
    except Exception as e:
        logging.error(f"Failed to save subscribers: {e}")
        return False

@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe_newsletter(request: SubscribeRequest, req: Request):
    try:
        # Load existing subscribers
        subscribers = load_subscribers()
        
        # Check if already subscribed
        existing = next((s for s in subscribers if s['email'] == request.email.lower()), None)
        
        if existing:
            if existing.get('status') == 'active':
                return SubscribeResponse(
                    success=True,
                    message="You're already subscribed!"
                )
            else:
                # Reactivate subscription
                existing['status'] = 'active'
                existing['resubscribed_at'] = datetime.utcnow().isoformat()
        else:
            # Add new subscriber
            new_subscriber = {
                'email': request.email.lower(),
                'name': request.name,
                'source': request.source,
                'status': 'active',
                'subscribed_at': datetime.utcnow().isoformat(),
                'ip_address': req.client.host if req.client else None,
                'user_agent': req.headers.get("user-agent")
            }
            subscribers.append(new_subscriber)
        
        # Save subscribers
        if save_subscribers(subscribers):
            logging.info(f"Newsletter subscription: {request.email} from {request.source}")
            return SubscribeResponse(
                success=True,
                message="Successfully subscribed! Welcome to our wellness community."
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to save subscription")
            
    except Exception as e:
        logging.error(f"Newsletter subscription error: {e}")
        raise HTTPException(status_code=500, detail="Subscription failed")

@router.get("/subscribers")
async def get_subscribers():
    """Admin endpoint to view subscribers"""
    try:
        subscribers = load_subscribers()
        return {
            "total": len(subscribers),
            "active": len([s for s in subscribers if s.get('status') == 'active']),
            "subscribers": subscribers
        }
    except Exception as e:
        logging.error(f"Failed to load subscribers: {e}")
        raise HTTPException(status_code=500, detail="Failed to load subscribers")