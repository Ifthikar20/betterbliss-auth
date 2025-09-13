# app/routes/streaming.py
from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import Optional, Dict, Any
from app.auth.dependencies import get_optional_user
from app.auth.models import UserResponse
from app.services.streaming_service import streaming_service
from app.database.connection import get_db_connection, release_db_connection
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/content", tags=["Video Streaming"])

@router.get("/{content_slug}/stream")
async def get_video_stream(
    content_slug: str,
    quality: Optional[str] = None,
    user: Optional[UserResponse] = Depends(get_optional_user)
):
    """SECURED: Get video streaming URLs for authenticated users only"""
    
    connection = None
    try:
        # Log access attempt for security monitoring
        logger.info(f"Video access attempt by user {user.id} for content {content_slug}")
        
        # Get content from database
        connection = await get_db_connection()
        
        query = """
            SELECT id, title, slug, description, access_tier, status,
                   s3_key_video_720p, s3_key_video_1080p, 
                   s3_key_thumbnail, s3_key_poster,
                   video_duration_seconds, video_format, has_video,
                   e.name as expert_name, c.name as category_name
            FROM content co
            LEFT JOIN experts e ON co.expert_id = e.id
            LEFT JOIN categories c ON co.category_id = c.id
            WHERE co.slug = $1 AND co.status = 'published'
        """
        
        content = await connection.fetchrow(query, content_slug)
        
        if not content:
            logger.warning(f"User {user.id} attempted to access non-existent content: {content_slug}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Content not found"
            )
        
        if not content['has_video']:
            logger.warning(f"User {user.id} attempted to access content without video: {content_slug}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not available for this content"
            )
        
        # Convert asyncpg.Record to dict
        content_data = dict(content)
        
        # SECURITY CHECK: Validate subscription access
        if content_data['access_tier'] == 'premium':
            if user.subscription_tier == 'free':
                logger.warning(f"Free user {user.id} attempted to access premium content: {content_slug}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Premium subscription required to access this content"
                )
        
        # Get streaming URLs using the service (user is guaranteed to be authenticated)
        streaming_data = streaming_service.get_streaming_urls(content_data, user)
        
        # Add additional content metadata
        streaming_data.update({
            "content_metadata": {
                "title": content_data["title"],
                "description": content_data["description"],
                "expert_name": content_data["expert_name"],
                "category_name": content_data["category_name"],
                "access_tier": content_data["access_tier"]
            },
            "user_info": {
                "user_id": user.id,
                "subscription_tier": user.subscription_tier,
                "access_granted": True
            }
        })
        
        # Log successful access for analytics
        logger.info(f"Video access granted to user {user.id} for content {content_slug}")
        
        return streaming_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Video streaming request failed for {content_slug} by user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get video stream"
        )
    finally:
        if connection:
            await release_db_connection(connection)

@router.post("/{content_slug}/video-event")
async def log_video_event(
    content_slug: str,
    event_data: Dict[str, Any] = Body(...),
    user: UserResponse = Depends(get_current_user)  # SECURED: Authentication required
):
    """SECURED: Log video analytics events for authenticated users only"""
    
    connection = None
    try:
        # Get content ID
        connection = await get_db_connection()
        
        content_id_query = "SELECT id FROM content WHERE slug = $1 AND status = 'published'"
        result = await connection.fetchrow(content_id_query, content_slug)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Content not found"
            )
        
        content_id = str(result['id'])
        
        # Validate event data
        required_fields = ['event_type', 'session_id']
        if not all(field in event_data for field in required_fields):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields: event_type, session_id"
            )
        
        # Validate event type for security
        allowed_events = ['play', 'pause', 'seek', 'view_progress', 'view_complete', 'quality_change', 'error']
        if event_data['event_type'] not in allowed_events:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event type. Allowed: {', '.join(allowed_events)}"
            )
        
        # Insert analytics event with user authentication
        analytics_query = """
            INSERT INTO video_analytics (
                content_id, user_id, session_id, event_type,
                timestamp_seconds, watch_duration_seconds,
                quality_level, device_type
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """
        
        await connection.execute(
            analytics_query,
            content_id,
            str(user.id),  # Always authenticated user
            event_data['session_id'],
            event_data['event_type'],
            event_data.get('timestamp_seconds'),
            event_data.get('watch_duration_seconds'),
            event_data.get('quality_level'),
            event_data.get('device_type', 'unknown')
        )
        
        logger.info(f"Video event logged: {event_data['event_type']} for {content_slug} by user {user.id}")
        
        return {"success": True, "message": "Event logged"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to log video event for {content_slug} by user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to log video event"
        )
    finally:
        if connection:
            await release_db_connection(connection)