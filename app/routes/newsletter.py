# app/routes/newsletter.py - Updated with email integration
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, EmailStr
import logging
from datetime import datetime
import uuid
from app.database.connection import get_db_connection, release_db_connection
from app.services.email_service import email_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/newsletter", tags=["newsletter"])

class SubscribeRequest(BaseModel):
    email: EmailStr
    name: str = None
    source: str = "unknown"

class SubscribeResponse(BaseModel):
    success: bool
    message: str

@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe_newsletter(
    request: SubscribeRequest, 
    req: Request,
    background_tasks: BackgroundTasks
):
    """Subscribe to newsletter with database storage and welcome email"""
    connection = None
    try:
        connection = await get_db_connection()
        
        # Check if already subscribed
        existing = await connection.fetchrow(
            "SELECT id, status FROM newsletter_subscribers WHERE email = $1",
            request.email.lower()
        )
        
        if existing:
            if existing['status'] == 'active':
                logger.info(f"User already subscribed: {request.email}")
                return SubscribeResponse(
                    success=True,
                    message="You're already subscribed! Welcome back to our wellness community."
                )
            else:
                # Reactivate subscription
                await connection.execute(
                    """UPDATE newsletter_subscribers 
                       SET status = 'active', updated_at = CURRENT_TIMESTAMP 
                       WHERE email = $1""",
                    request.email.lower()
                )
                logger.info(f"Reactivated subscription: {request.email}")
                
                # Send welcome email for reactivated subscription
                background_tasks.add_task(
                    email_service.send_welcome_email,
                    email=request.email.lower(),
                    name=request.name,
                    subscription_id=existing['id']
                )
                
                return SubscribeResponse(
                    success=True,
                    message="Welcome back! Your subscription has been reactivated. Check your email for a welcome message."
                )
        
        # Create new subscription
        subscription_id = str(uuid.uuid4())
        
        await connection.execute("""
            INSERT INTO newsletter_subscribers (
                id, email, name, source, status, 
                client_ip, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, 
            subscription_id,
            request.email.lower(),
            request.name,
            request.source,
            'active',
            req.client.host if req.client else None
        )
        
        # Send welcome email in background (non-blocking)
        background_tasks.add_task(
            email_service.send_welcome_email,
            email=request.email.lower(),
            name=request.name,
            subscription_id=subscription_id
        )
        
        logger.info(f"Newsletter subscription created: {request.email} from {request.source}")
        
        return SubscribeResponse(
            success=True,
            message="Successfully subscribed! Check your email for a welcome message."
        )
        
    except Exception as e:
        logger.error(f"Newsletter subscription error for {request.email}: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Subscription failed. Please try again later."
        )
    finally:
        if connection:
            await release_db_connection(connection)

@router.get("/subscribers")
async def get_subscribers():
    """Admin endpoint to view newsletter subscribers"""
    connection = None
    try:
        connection = await get_db_connection()
        
        # Get subscriber statistics
        total_count = await connection.fetchval(
            "SELECT COUNT(*) FROM newsletter_subscribers"
        )
        
        active_count = await connection.fetchval(
            "SELECT COUNT(*) FROM newsletter_subscribers WHERE status = 'active'"
        )
        
        # Get recent subscribers (last 50)
        recent_subscribers = await connection.fetch("""
            SELECT id, email, name, source, status, 
                   created_at, updated_at, client_ip
            FROM newsletter_subscribers 
            ORDER BY created_at DESC 
            LIMIT 50
        """)
        
        # Convert to dict format
        subscribers_list = []
        for subscriber in recent_subscribers:
            subscribers_list.append({
                'id': subscriber['id'],
                'email': subscriber['email'],
                'name': subscriber['name'],
                'source': subscriber['source'],
                'status': subscriber['status'],
                'subscribed_at': subscriber['created_at'].isoformat() if subscriber['created_at'] else None,
                'updated_at': subscriber['updated_at'].isoformat() if subscriber['updated_at'] else None,
                'ip_address': subscriber['client_ip']
            })
        
        return {
            "total": total_count,
            "active": active_count,
            "recent_subscribers": subscribers_list,
            "database_storage": True  # Indicates we're using database now
        }
        
    except Exception as e:
        logger.error(f"Failed to load subscribers: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to load subscribers"
        )
    finally:
        if connection:
            await release_db_connection(connection)

@router.get("/stats")
async def get_newsletter_stats():
    """Get newsletter subscription statistics"""
    connection = None
    try:
        connection = await get_db_connection()
        
        # Get comprehensive stats
        stats_query = """
            SELECT 
                COUNT(*) as total_subscribers,
                COUNT(*) FILTER (WHERE status = 'active') as active_subscribers,
                COUNT(*) FILTER (WHERE status = 'pending') as pending_subscribers,
                COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') as this_week,
                COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '30 days') as this_month,
                COUNT(DISTINCT source) as unique_sources
            FROM newsletter_subscribers
        """
        
        stats = await connection.fetchrow(stats_query)
        
        # Get top sources
        sources_query = """
            SELECT source, COUNT(*) as count 
            FROM newsletter_subscribers 
            WHERE status = 'active'
            GROUP BY source 
            ORDER BY count DESC 
            LIMIT 10
        """
        
        top_sources = await connection.fetch(sources_query)
        
        return {
            "total_subscribers": stats['total_subscribers'],
            "active_subscribers": stats['active_subscribers'],
            "pending_subscribers": stats['pending_subscribers'],
            "subscriptions_this_week": stats['this_week'],
            "subscriptions_this_month": stats['this_month'],
            "unique_sources": stats['unique_sources'],
            "top_sources": [dict(source) for source in top_sources],
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get newsletter stats: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve statistics"
        )
    finally:
        if connection:
            await release_db_connection(connection)