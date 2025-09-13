# app/services/streaming_service.py
import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any, List
from app.config import settings
from app.auth.models import UserResponse, SubscriptionTier
from app.database.connection import get_db_connection, release_db_connection
from datetime import datetime, timedelta
import logging
import uuid

logger = logging.getLogger(__name__)

class StreamingService:
    """Service class for handling secure video streaming operations"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3', region_name=settings.aws_region)
        self.bucket_name = getattr(settings, 'video_bucket_name', 'betterbliss-videos-production')
        self.cloudfront_domain = getattr(settings, 'cloudfront_domain', None)
        self.url_expiry_minutes = getattr(settings, 'video_url_expiry_minutes', 120)
        self.thumbnail_expiry_hours = getattr(settings, 'thumbnail_url_expiry_hours', 24)
        self.default_quality = getattr(settings, 'default_video_quality', '720p')
        self.available_qualities = getattr(settings, 'available_qualities', ['720p', '1080p'])
    
    async def get_content_streaming_data(
        self, 
        content_slug: str, 
        user: UserResponse
    ) -> Dict[str, Any]:
        """
        Get complete streaming data for content including security validation
        
        Args:
            content_slug: Content slug identifier
            user: Authenticated user object
            
        Returns:
            Dictionary with streaming URLs and content metadata
        """
        connection = None
        try:
            # Get content from database
            connection = await get_db_connection()
            
            content_data = await self._get_content_by_slug(connection, content_slug)
            if not content_data:
                raise ValueError("Content not found")
            
            if not content_data.get('has_video'):
                raise ValueError("Video not available for this content")
            
            # Validate user access
            if not self._validate_user_access(content_data, user):
                raise PermissionError(
                    f"Insufficient permissions to access this content"
                )
            
            # Generate streaming URLs
            streaming_data = await self._generate_streaming_urls(content_data, user)
            
            # Add content metadata
            streaming_data["content_metadata"] = {
                "title": content_data["title"],
                "description": content_data["description"],
                "expert_name": content_data.get("expert_name"),
                "category_name": content_data.get("category_name"),
                "access_tier": content_data["access_tier"]
            }
            
            logger.info(f"Streaming data generated for content {content_slug} for user {user.id}")
            return streaming_data
            
        except Exception as e:
            logger.error(f"Failed to get streaming data for {content_slug}: {e}")
            raise
        finally:
            if connection:
                await release_db_connection(connection)
    
    async def log_video_analytics(
        self,
        content_slug: str,
        event_data: Dict[str, Any],
        user: UserResponse
    ) -> bool:
        """
        Log video analytics event to database
        
        Args:
            content_slug: Content slug identifier
            event_data: Event information (type, timestamp, etc.)
            user: Authenticated user object
            
        Returns:
            bool: True if logged successfully
        """
        connection = None
        try:
            connection = await get_db_connection()
            
            # Get content ID
            content_id_query = "SELECT id FROM content WHERE slug = $1 AND status = 'published'"
            result = await connection.fetchrow(content_id_query, content_slug)
            
            if not result:
                raise ValueError("Content not found")
            
            content_id = str(result['id'])
            
            # Validate event data
            self._validate_event_data(event_data)
            
            # Insert analytics event
            await self._insert_video_event(connection, content_id, event_data, user)
            
            logger.info(f"Video event logged: {event_data['event_type']} for {content_slug} by user {user.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log video event for {content_slug}: {e}")
            raise
        finally:
            if connection:
                await release_db_connection(connection)
    
    async def get_user_video_progress(
        self,
        user_id: str,
        content_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get user's video watching progress
        
        Args:
            user_id: User identifier
            content_id: Optional specific content ID
            
        Returns:
            List of progress records
        """
        connection = None
        try:
            connection = await get_db_connection()
            
            if content_id:
                query = """
                    SELECT content_id, MAX(timestamp_seconds) as last_position,
                           SUM(watch_duration_seconds) as total_watch_time,
                           COUNT(*) as session_count
                    FROM video_analytics 
                    WHERE user_id = $1 AND content_id = $2
                    GROUP BY content_id
                """
                progress = await connection.fetch(query, user_id, content_id)
            else:
                query = """
                    SELECT va.content_id, c.title, c.slug,
                           MAX(va.timestamp_seconds) as last_position,
                           SUM(va.watch_duration_seconds) as total_watch_time,
                           COUNT(*) as session_count,
                           c.video_duration_seconds
                    FROM video_analytics va
                    JOIN content c ON va.content_id = c.id
                    WHERE va.user_id = $1
                    GROUP BY va.content_id, c.title, c.slug, c.video_duration_seconds
                    ORDER BY MAX(va.created_at) DESC
                """
                progress = await connection.fetch(query, user_id)
            
            return [dict(record) for record in progress]
            
        except Exception as e:
            logger.error(f"Failed to get video progress for user {user_id}: {e}")
            raise
        finally:
            if connection:
                await release_db_connection(connection)
    
    # Private helper methods
    
    async def _get_content_by_slug(self, connection, content_slug: str) -> Optional[Dict[str, Any]]:
        """Get content data from database by slug"""
        query = """
            SELECT co.id, co.title, co.slug, co.description, co.access_tier, co.status,
                   co.s3_key_video_720p, co.s3_key_video_1080p, 
                   co.s3_key_thumbnail, co.s3_key_poster,
                   co.video_duration_seconds, co.video_format, co.has_video,
                   e.name as expert_name, c.name as category_name
            FROM content co
            LEFT JOIN experts e ON co.expert_id = e.id
            LEFT JOIN categories c ON co.category_id = c.id
            WHERE co.slug = $1 AND co.status = 'published'
        """
        
        result = await connection.fetchrow(query, content_slug)
        return dict(result) if result else None
    
    def _validate_user_access(self, content_data: Dict[str, Any], user: UserResponse) -> bool:
        """Validate if user has permission to access content"""
        content_tier = content_data.get("access_tier", "free")
        
        if content_tier == "free":
            return True
        
        if content_tier == "premium":
            return user.subscription_tier in [SubscriptionTier.PREMIUM, SubscriptionTier.BASIC]
        
        if content_tier == "admin":
            return user.role == "admin"
        
        logger.warning(f"Unknown content access tier: {content_tier}")
        return False
    
    async def _generate_streaming_urls(self, content_data: Dict[str, Any], user: UserResponse) -> Dict[str, Any]:
        """Generate secure streaming URLs for content"""
        streaming_data = {
            "content_id": content_data["id"],
            "title": content_data["title"],
            "duration_seconds": content_data.get("video_duration_seconds", 0),
            "available_qualities": [],
            "streaming_urls": {},
            "thumbnail_url": None,
            "poster_url": None,
            "expires_at": datetime.now() + timedelta(minutes=self.url_expiry_minutes),
            "session_id": str(uuid.uuid4()),
            "user_access_level": user.subscription_tier
        }
        
        # Generate video URLs for available qualities
        video_urls_generated = 0
        for quality in self.available_qualities:
            s3_key_field = f"s3_key_video_{quality}"
            
            if content_data.get(s3_key_field):
                s3_key = content_data[s3_key_field]
                
                if self._verify_s3_object_exists(s3_key):
                    try:
                        video_url = self._generate_secure_video_url(s3_key)
                        streaming_data["streaming_urls"][quality] = video_url
                        streaming_data["available_qualities"].append(quality)
                        video_urls_generated += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to generate {quality} URL: {e}")
                        continue
        
        if video_urls_generated == 0:
            raise ValueError("No video formats available")
        
        # Generate thumbnail URLs
        if content_data.get("s3_key_thumbnail"):
            try:
                streaming_data["thumbnail_url"] = self._generate_thumbnail_url(
                    content_data["s3_key_thumbnail"]
                )
            except Exception as e:
                logger.warning(f"Failed to generate thumbnail URL: {e}")
        
        # Set default quality
        streaming_data["default_quality"] = self._determine_default_quality(
            streaming_data["available_qualities"]
        )
        
        return streaming_data
    
    def _generate_secure_video_url(self, s3_key: str) -> str:
        """Generate secure presigned URL for video"""
        try:
            if self.cloudfront_domain:
                # Use CloudFront domain with S3 presigned URL for security
                return self._generate_s3_presigned_url(s3_key, self.url_expiry_minutes * 60)
            
            return self._generate_s3_presigned_url(s3_key, self.url_expiry_minutes * 60)
            
        except Exception as e:
            logger.error(f"Failed to generate secure video URL for {s3_key}: {e}")
            raise
    
    def _generate_thumbnail_url(self, s3_key: str) -> str:
        """Generate URL for thumbnail images"""
        try:
            if self.cloudfront_domain:
                return f"https://{self.cloudfront_domain}/{s3_key}"
            
            expiry_seconds = self.thumbnail_expiry_hours * 3600
            return self._generate_s3_presigned_url(s3_key, expiry_seconds)
            
        except Exception as e:
            logger.error(f"Failed to generate thumbnail URL for {s3_key}: {e}")
            raise
    
    def _generate_s3_presigned_url(self, s3_key: str, expiry_seconds: int) -> str:
        """Generate S3 presigned URL with security headers"""
        try:
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key,
                    'ResponseContentType': self._get_content_type(s3_key),
                    'ResponseContentDisposition': 'inline'
                },
                ExpiresIn=expiry_seconds
            )
            
            return presigned_url
            
        except ClientError as e:
            logger.error(f"S3 presigned URL generation failed for {s3_key}: {e}")
            raise
    
    def _verify_s3_object_exists(self, s3_key: str) -> bool:
        """Check if S3 object exists"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.warning(f"Error checking S3 object {s3_key}: {e}")
            return False
    
    def _determine_default_quality(self, available_qualities: List[str]) -> str:
        """Determine best default quality"""
        if self.default_quality in available_qualities:
            return self.default_quality
        
        quality_preference = ['720p', '1080p', '480p']
        for preferred in quality_preference:
            if preferred in available_qualities:
                return preferred
        
        return available_qualities[0] if available_qualities else None
    
    def _get_content_type(self, s3_key: str) -> str:
        """Get content type based on file extension"""
        extension = s3_key.lower().split('.')[-1]
        content_types = {
            'mp4': 'video/mp4',
            'webm': 'video/webm',
            'mov': 'video/quicktime',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'webp': 'image/webp'
        }
        return content_types.get(extension, 'application/octet-stream')
    
    def _validate_event_data(self, event_data: Dict[str, Any]) -> None:
        """Validate video analytics event data"""
        required_fields = ['event_type', 'session_id']
        if not all(field in event_data for field in required_fields):
            raise ValueError("Missing required fields: event_type, session_id")
        
        allowed_events = ['play', 'pause', 'seek', 'view_progress', 'view_complete', 'quality_change', 'error']
        if event_data['event_type'] not in allowed_events:
            raise ValueError(f"Invalid event type. Allowed: {', '.join(allowed_events)}")
    
    async def _insert_video_event(
        self, 
        connection, 
        content_id: str, 
        event_data: Dict[str, Any], 
        user: UserResponse
    ) -> None:
        """Insert video analytics event into database"""
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
            str(user.id),
            event_data['session_id'],
            event_data['event_type'],
            event_data.get('timestamp_seconds'),
            event_data.get('watch_duration_seconds'),
            event_data.get('quality_level'),
            event_data.get('device_type', 'unknown')
        )

# Global service instance
streaming_service = StreamingService()