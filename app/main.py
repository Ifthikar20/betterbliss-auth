from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.config import settings
from app.auth.routes import router as auth_router
from app.middleware.cors import setup_cors
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Better & Bliss API",
    description="Mental Health and Wellness Platform API",
    version="1.0.0"
)

# Setup CORS
setup_cors(app)

# Include routers
app.include_router(auth_router)

@app.get("/")
async def root():
    return {"message": "Better & Bliss API", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.environment,
        "cognito_configured": bool(settings.cognito_user_pool_id)
    }

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