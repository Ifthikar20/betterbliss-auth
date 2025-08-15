from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

def setup_cors(app):
    """Configure CORS for the application"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"]
    )