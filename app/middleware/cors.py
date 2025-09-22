from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

def setup_cors(app: FastAPI):
    """Configure CORS for the application"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.frontend_url,
            "http://localhost:3000",  # React dev server
            "http://localhost:5173",  # Vite dev server
            "http://localhost:5174",  # Alternative Vite port
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"]
    )