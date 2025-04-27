"""
PureText AI - Plagiarism detection backend application
"""

__version__ = "0.1.0"

# FastAPI backend package for PureText AI
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.endpoints import analyze, plagiarism

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Plagiarism detection API for PureText AI",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(analyze.router, prefix="/api", tags=["analysis"])
app.include_router(plagiarism.router, prefix="/api", tags=["plagiarism"])

@app.get("/", tags=["health"])
async def health_check():
    """
    Health check endpoint for the API
    """
    return {"status": "ok", "service": "PureText AI API"}