# app/main.py (Updated with content router)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.config import settings
from app.middleware.cors import setup_cors
from app.database.connection import DatabaseConnection
from app.routes.streaming import router as streaming_router
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Better & Bliss API...")
    try:
        # Initialize database connection pool
        await DatabaseConnection.get_pool()
        logger.info("Database connection pool initialized")
    except Exception as e:
        if settings.environment == "development":
            logger.warning(f"Database connection failed (development mode): {e}")
            logger.warning("Continuing without database connection for local testing")
        else:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Better & Bliss API...")
    try:
        await DatabaseConnection.close_pool()
        logger.info("Database connections closed")
    except Exception as e:
        logger.warning(f"Error closing database connections: {e}")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Better & Bliss API",
    description="Mental Health and Wellness Platform API",
    version="1.0.0",
    lifespan=lifespan
)

# Setup CORS
setup_cors(app)

# Import and include routers
from app.auth.routes import router as auth_router
app.include_router(auth_router)

# Include content router (now working!)
from app.content.routes import router as content_router
app.include_router(content_router)

app.include_router(streaming_router)

@app.get("/")
async def root():
    return {"message": "Better & Bliss API", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Enhanced health check including database"""
    try:
        # Test database connection
        pool = await DatabaseConnection.get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval('SELECT 1')
        db_healthy = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_healthy = False
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "environment": settings.environment,
        "cognito_configured": bool(settings.cognito_user_pool_id),
        "database_healthy": db_healthy,
        "services": {
            "cognito": "configured" if settings.cognito_user_pool_id else "not_configured",
            "database": "healthy" if db_healthy else "unhealthy"
        }
    }

@app.get("/content/check-data")
async def check_database_data():
    """Temporary endpoint to check database data"""
    try:
        from app.database.connection import get_db_connection, release_db_connection
        
        connection = await get_db_connection()
        
        # Check experts
        experts = await connection.fetch("SELECT name, title, verified FROM experts")
        
        # Check content  
        content = await connection.fetch("SELECT title, access_tier, content_type FROM content")
        
        # Check categories
        categories = await connection.fetch("SELECT name, slug FROM categories")
        
        await release_db_connection(connection)
        
        return {
            "experts": [{"name": e["name"], "title": e["title"], "verified": e["verified"]} for e in experts],
            "content": [{"title": c["title"], "tier": c["access_tier"], "type": c["content_type"]} for c in content],
            "categories": [{"name": cat["name"], "slug": cat["slug"]} for cat in categories],
            "totals": {
                "experts": len(experts),
                "content": len(content), 
                "categories": len(categories)
            }
        }
        
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        return {"error": str(e), "database_accessible": False}

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.environment == "development" else False
    )