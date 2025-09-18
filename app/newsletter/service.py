# app/newsletter/service.py
import uuid
import time
import json
import logging
from typing import Dict, Any, Optional
from app.database.connection import get_db_connection, release_db_connection

logger = logging.getLogger(__name__)

class NewsletterService:
    async def subscribe(
        self,
        email: str,
        name: Optional[str] = None,
        source: str = "website",
        metadata: Dict[str, Any] = None,
        client_ip: str = None,
        request_id: str = None
    ) -> Dict[str, Any]:
        """Process secure newsletter subscription"""
        
        connection = None
        try:
            # Validate timing (prevent too-fast submissions)
            if metadata and metadata.get('timestamp'):
                time_on_page = time.time() * 1000 - metadata['timestamp']
                if time_on_page < 5000:  # Less than 5 seconds
                    logger.warning(f"Suspicious fast submission: {email}")
                    raise ValueError("Submission too fast")
            
            # Behavioral validation
            if metadata and metadata.get('interactions'):
                interactions = metadata['interactions']
                if len(interactions) < 2:
                    logger.warning(f"Suspicious low interaction count: {email}")
                    raise ValueError("Insufficient user interaction")
            
            connection = await get_db_connection()
            
            # Check if already subscribed
            existing = await connection.fetchrow(
                "SELECT id, status FROM newsletter_subscribers WHERE email = $1",
                email
            )
            
            if existing:
                if existing['status'] == 'active':
                    logger.info(f"User already subscribed: {email}")
                    return {"status": "already_subscribed"}
                else:
                    # Reactivate subscription
                    await connection.execute(
                        "UPDATE newsletter_subscribers SET status = 'active', updated_at = CURRENT_TIMESTAMP WHERE email = $1",
                        email
                    )
                    logger.info(f"Reactivated subscription: {email}")
                    return {"status": "reactivated"}
            
            # Create new subscription
            subscription_id = str(uuid.uuid4())
            
            await connection.execute("""
                INSERT INTO newsletter_subscribers (
                    id, email, name, source, status, metadata, 
                    client_ip, request_id, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_TIMESTAMP)
            """, 
                subscription_id, email, name, source, 'pending',
                json.dumps(metadata) if metadata else None,
                client_ip, request_id
            )
            
            # Send confirmation email (implement separately)
            await self._send_confirmation_email(email, subscription_id)
            
            logger.info(f"Newsletter subscription created: {email}")
            
            return {
                "status": "subscribed",
                "subscription_id": subscription_id,
                "requires_confirmation": True
            }
            
        except ValueError as e:
            # These are validation errors we want to surface
            raise e
        except Exception as e:
            logger.error(f"Newsletter subscription failed for {email}: {e}")
            raise Exception("Subscription processing failed")
        finally:
            if connection:
                await release_db_connection(connection)
    
    async def _send_confirmation_email(self, email: str, subscription_id: str):
        """Send double opt-in confirmation email"""
        try:
            # Implement email sending logic here
            # For now, just log
            logger.info(f"Confirmation email queued for: {email}")
            pass
        except Exception as e:
            logger.error(f"Failed to send confirmation email to {email}: {e}")

newsletter_service = NewsletterService()