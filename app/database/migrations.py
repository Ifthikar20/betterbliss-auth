# app/database/migrations.py (Optional: Add database user preferences sync)
import asyncpg
from app.database.connection import get_db_connection, release_db_connection
import logging

logger = logging.getLogger(__name__)

async def sync_user_preferences(cognito_sub: str, preferences: Dict[str, Any]):
    """Sync user preferences to database"""
    connection = None
    try:
        connection = await get_db_connection()
        
        query = """
            INSERT INTO user_preferences (
                user_id, preferred_categories, preferred_content_types, 
                wellness_goals, dark_mode, autoplay_videos, email_notifications
            )
            SELECT id, $2, $3, $4, $5, $6, $7
            FROM users WHERE cognito_sub = $1
            ON CONFLICT (user_id) 
            DO UPDATE SET
                preferred_categories = EXCLUDED.preferred_categories,
                preferred_content_types = EXCLUDED.preferred_content_types,
                wellness_goals = EXCLUDED.wellness_goals,
                dark_mode = EXCLUDED.dark_mode,
                autoplay_videos = EXCLUDED.autoplay_videos,
                email_notifications = EXCLUDED.email_notifications,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
        """
        
        result = await connection.fetchrow(
            query,
            cognito_sub,
            preferences.get('preferred_categories', []),
            preferences.get('preferred_content_types', []),
            preferences.get('wellness_goals', []),
            preferences.get('dark_mode', False),
            preferences.get('autoplay_videos', True),
            preferences.get('email_notifications', True)
        )
        
        return dict(result) if result else None
        
    except Exception as e:
        logger.error(f"Failed to sync user preferences: {e}")
        raise
    finally:
        if connection:
            await release_db_connection(connection)