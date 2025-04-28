import logging
import sys
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.endpoints import analyze, plagiarism

# Enhanced logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting application initialization...")

try:
    # Log environment details
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Files in current directory: {os.listdir('.')}")
    
    def create_application() -> FastAPI:
        logger.info("Creating FastAPI application...")
        application = FastAPI(
            title=settings.PROJECT_NAME,
            description="Plagiarism detection API for PureText AI",
            version="0.1.0"
        )

        # Configure CORS
        logger.info(f"Setting up CORS with origins: {settings.CORS_ORIGINS}")
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Include API routes
        logger.info("Including API routes...")
        application.include_router(analyze.router, prefix="/api", tags=["analysis"])
        application.include_router(plagiarism.router, prefix="/api", tags=["plagiarism"])

        @application.get("/", tags=["health"])
        async def health_check():
            """
            Health check endpoint for the API
            """
            return {"status": "ok", "service": "PureText AI API"}
        
        logger.info("Application created successfully")
        return application

    # Create app inside try block to catch startup errors
    app = create_application()
    logger.info("Application initialization complete")
    
except Exception as e:
    # Log detailed error information
    logger.error(f"ERROR DURING STARTUP: {str(e)}")
    import traceback
    logger.error(f"Traceback: {traceback.format_exc()}")
    print(f"CRITICAL ERROR: {str(e)}", file=sys.stderr)
    
    # Create a minimal app that will at least start
    app = FastAPI()
    
    @app.get("/")
    def error_app():
        return {"status": "error", "message": f"App failed to initialize: {str(e)}"}