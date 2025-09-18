# app/utils/rate_limiting.py
import logging
from app.database.connection import get_db_connection, release_db_connection

logger = logging.getLogger(__name__)

class RateLimiter:
    async def check_rate_limit(
        self, 
        identifier: str, 
        max_requests: int = 5, 
        window: int = 3600,
        endpoint: str = "newsletter"
    ) -> bool:
        """Check if request is within rate limits"""
        
        connection = None
        try:
            connection = await get_db_connection()
            
            # Clean old entries first
            await connection.execute(
                f"DELETE FROM rate_limits WHERE window_start < NOW() - INTERVAL '{window} seconds'"
            )
            
            # Check current count for this identifier
            current_count = await connection.fetchval("""
                SELECT COALESCE(SUM(requests_count), 0)
                FROM rate_limits 
                WHERE identifier = $1 AND endpoint = $2 
                AND window_start > NOW() - INTERVAL '%s seconds'
            """, identifier, endpoint, window)
            
            if current_count and current_count >= max_requests:
                logger.warning(f"Rate limit exceeded for {identifier} on {endpoint}")
                return False
            
            # Record this request
            await connection.execute("""
                INSERT INTO rate_limits (identifier, endpoint, requests_count, window_start)
                VALUES ($1, $2, 1, CURRENT_TIMESTAMP)
            """, identifier, endpoint)
            
            return True
            
        except Exception as e:
            logger.error(f"Rate limiting check failed: {e}")
            # Allow request if rate limiting fails
            return True
        finally:
            if connection:
                await release_db_connection(connection)