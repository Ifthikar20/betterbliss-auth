# app/main.py - Updated to use ONLY enhanced routes
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.config import settings
from app.middleware.cors import setup_cors
from app.database.connection import DatabaseConnection


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
        await DatabaseConnection.get_pool()
        logger.info("Database connection pool initialized")
    except Exception as e:
        if settings.environment == "development":
            logger.warning(f"Database connection failed (development mode): {e}")
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

app = FastAPI(
    title="Better & Bliss API",
    description="Mental Health and Wellness Platform API",
    version="1.0.0",
    lifespan=lifespan
)

# Setup CORS
setup_cors(app)

# CRITICAL: Use ONLY the enhanced auth router
from app.auth.enhanced_routes import router as auth_router
app.include_router(auth_router)

# Include other routers
from app.content.routes import router as content_router
app.include_router(content_router)

from app.routes.streaming import router as streaming_router
app.include_router(streaming_router)

# ADD THIS LINE - Newsletter router
from app.routes.newsletter import router as newsletter_router
app.include_router(newsletter_router)

@app.get("/")
async def root():
    return {"message": "Better & Bliss API", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Enhanced health check including database"""
    try:
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
        "auth_system": "enhanced_with_db"  # Clearly indicate which system is active
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )