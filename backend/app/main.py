from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.endpoints import plagiarism, analyze
from app.api.endpoints import test

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize services on startup
    from app.services.spider_queue import init_spider_queue
    from app.services.scraping import initialize_playwright_check
    
    await init_spider_queue()
    await initialize_playwright_check()  # Add this line

    yield

    # Shutdown: Clean up resources on shutdown
    from app.services.spider_queue import spider_queue
    from app.services.scraping import close_client
    await spider_queue.stop()
    await close_client()

# Create FastAPI app with the lifespan manager
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Plagiarism detection API for PureText AI",
    version="0.1.0",
    lifespan=lifespan  # Connect the lifespan manager here
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
app.include_router(analyze.router, prefix=settings.API_V1_STR)  # First: analysis endpoints
app.include_router(plagiarism.router, prefix=settings.API_V1_STR)  # Second: plagiarism endpoints
# app.include_router(test.router, prefix=settings.API_V1_STR)  # Last: test/debug endpoints

@app.get("/", tags=["health"])
async def health_check():
    """
    Health check endpoint for the API
    """
    return {"status": "ok", "service": "PureText AI API"}

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", 
        host=settings.API_HOST, 
        port=settings.API_PORT,
        reload=settings.DEBUG
    )

