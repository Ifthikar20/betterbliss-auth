# app/content/routes.py - Secure content API routes
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional, List, Dict, Any
from app.auth.dependencies import get_optional_user
from app.auth.models import UserResponse
from app.services.content_service import content_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/content", tags=["Content"])

@router.get("/browse")
async def get_browse_content(
    category: Optional[str] = Query(None, description="Filter by category slug"),
    limit: int = Query(20, ge=1, le=50, description="Number of items to return"),
    user: Optional[UserResponse] = Depends(get_optional_user)
):
    """Get content for browse page with proper access control"""
    try:
        # Validate and sanitize inputs
        if category and not category.replace('-', '').replace('_', '').isalnum():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category format"
            )
        
        result = await content_service.get_browse_content(
            user=user,
            category_slug=category,
            limit=limit
        )
        
        # Add security metadata to response
        response_data = {
            **result,
            'user_authenticated': user is not None,
            'premium_available': len([c for c in result['content'] if c['access_tier'] == 'premium']) > 0
        }
        
        # Remove user access level from response for security
        response_data.pop('user_access_level', None)
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Browse content request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve content"
        )

@router.get("/categories")
async def get_categories():
    """Get all active categories (public endpoint)"""
    try:
        categories = await content_service.get_categories()
        
        return {
            'categories': categories,
            'total': len(categories)
        }
        
    except Exception as e:
        logger.error(f"Categories request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve categories"
        )

@router.get("/experts")
async def get_featured_experts(
    limit: int = Query(6, ge=1, le=20, description="Number of experts to return")
):
    """Get featured experts (public endpoint)"""
    try:
        experts = await content_service.get_featured_experts(limit=limit)
        
        return {
            'experts': experts,
            'total': len(experts)
        }
        
    except Exception as e:
        logger.error(f"Featured experts request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve experts"
        )

@router.get("/detail/{content_slug}")
async def get_content_detail(
    content_slug: str,
    user: Optional[UserResponse] = Depends(get_optional_user)
):
    """Get detailed content with access control"""
    try:
        # Validate slug format for security
        if not content_slug.replace('-', '').replace('_', '').isalnum():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid content slug format"
            )
        
        content_detail = await content_service.get_content_detail(
            content_slug=content_slug,
            user=user
        )
        
        if not content_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Content not found"
            )
        
        return content_detail
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Content detail request failed for {content_slug}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve content detail"
        )

@router.get("/search")
async def search_content(
    q: str = Query(..., min_length=2, max_length=100, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    user: Optional[UserResponse] = Depends(get_optional_user)
):
    """Search content securely"""
    try:
        # Sanitize search query to prevent injection
        search_query = q.strip()
        if not search_query:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search query cannot be empty"
            )
        
        # Basic search implementation (can be enhanced later)
        result = await content_service.get_browse_content(
            user=user,
            category_slug=category,
            limit=20
        )
        
        # Filter results by search query (simple text matching for now)
        filtered_content = []
        for item in result['content']:
            if (search_query.lower() in item['title'].lower() or 
                search_query.lower() in item['description'].lower()):
                filtered_content.append(item)
        
        return {
            'content': filtered_content,
            'query': search_query,
            'total_results': len(filtered_content),
            'user_authenticated': user is not None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search request failed for query '{q}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )