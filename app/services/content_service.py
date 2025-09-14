# app/services/content_service.py
from typing import Optional, List, Dict, Any
from app.database.connection import get_db_connection, release_db_connection
from app.auth.models import UserResponse
import logging

logger = logging.getLogger(__name__)

class ContentService:
    """Service for managing content operations"""
    
    async def get_browse_content(
        self, 
        user: Optional[UserResponse] = None, 
        category_slug: Optional[str] = None, 
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get content for browse page with access control"""
        connection = None
        try:
            connection = await get_db_connection()
            
            # Base query
            query = """
                SELECT c.id, c.title, c.slug, c.description, c.access_tier,
                       c.duration_seconds, c.featured, c.content_type,
                       e.name as expert_name, e.title as expert_title,
                       cat.name as category_name, cat.color as category_color
                FROM content c
                LEFT JOIN experts e ON c.expert_id = e.id
                LEFT JOIN categories cat ON c.category_id = cat.id
                WHERE c.status = 'published'
            """
            
            params = []
            param_count = 1
            
            # Filter by category if specified
            if category_slug:
                query += f" AND cat.slug = ${param_count}"
                params.append(category_slug)
                param_count += 1
            
            # Filter by access level based on user subscription
            if not user or user.subscription_tier == 'free':
                query += f" AND c.access_tier = 'free'"
            
            # Order and limit
            query += " ORDER BY c.featured DESC, c.created_at DESC"
            query += f" LIMIT ${param_count}"
            params.append(limit)
            
            content_list = await connection.fetch(query, *params)
            
            return {
                "content": [dict(row) for row in content_list],
                "total": len(content_list),
                "user_access_level": user.subscription_tier if user else "anonymous"
            }
            
        except Exception as e:
            logger.error(f"Failed to get browse content: {e}")
            return {"content": [], "total": 0}
        finally:
            if connection:
                await release_db_connection(connection)
    
    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get all active categories"""
        connection = None
        try:
            connection = await get_db_connection()
            
            categories = await connection.fetch("""
                SELECT name, slug, description, icon, color, sort_order
                FROM categories
                WHERE is_active = true
                ORDER BY sort_order, name
            """)
            
            return [dict(row) for row in categories]
            
        except Exception as e:
            logger.error(f"Failed to get categories: {e}")
            return []
        finally:
            if connection:
                await release_db_connection(connection)
    
    async def get_featured_experts(self, limit: int = 6) -> List[Dict[str, Any]]:
        """Get featured experts"""
        connection = None
        try:
            connection = await get_db_connection()
            
            experts = await connection.fetch("""
                SELECT name, slug, title, bio, specialties, verified, featured
                FROM experts
                WHERE featured = true AND status = 'active'
                ORDER BY created_at DESC
                LIMIT $1
            """, limit)
            
            return [dict(row) for row in experts]
            
        except Exception as e:
            logger.error(f"Failed to get featured experts: {e}")
            return []
        finally:
            if connection:
                await release_db_connection(connection)

    async def get_content_detail(
        self, 
        content_slug: str, 
        user: Optional[UserResponse] = None
    ) -> Optional[Dict[str, Any]]:
        """Get detailed content with access control"""
        connection = None
        try:
            connection = await get_db_connection()
            
            content = await connection.fetchrow("""
                SELECT c.*, 
                       e.name as expert_name, e.title as expert_title, e.bio as expert_bio,
                       cat.name as category_name, cat.color as category_color
                FROM content c
                LEFT JOIN experts e ON c.expert_id = e.id
                LEFT JOIN categories cat ON c.category_id = cat.id
                WHERE c.slug = $1 AND c.status = 'published'
            """, content_slug)
            
            if not content:
                return None
            
            content_dict = dict(content)
            
            # Check access permissions
            if content_dict['access_tier'] == 'premium':
                if not user or user.subscription_tier == 'free':
                    # Return limited info for premium content
                    return {
                        **content_dict,
                        'access_denied': True,
                        'message': 'Premium subscription required'
                    }
            
            return content_dict
            
        except Exception as e:
            logger.error(f"Failed to get content detail for {content_slug}: {e}")
            return None
        finally:
            if connection:
                await release_db_connection(connection)

# Global service instance
content_service = ContentService()