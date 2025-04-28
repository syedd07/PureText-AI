import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.endpoints import analyze, plagiarism

# Add this at the top
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        description="Plagiarism detection API for PureText AI",
        version="0.1.0"
    )

    # Configure CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    application.include_router(analyze.router, prefix="/api", tags=["analysis"])
    application.include_router(plagiarism.router, prefix="/api", tags=["plagiarism"])

    @application.get("/", tags=["health"])
    async def health_check():
        """
        Health check endpoint for the API
        """
        return {"status": "ok", "service": "PureText AI API"}

    return application

app = create_application()