from fastapi import APIRouter, Form, UploadFile, File, HTTPException, BackgroundTasks
import logging
logger = logging.getLogger(__name__)

from typing import Optional, Dict, Any
import asyncio
import uuid
import json
import os

from app.services.scraping import find_and_scrape_sources, find_and_scrape_sources_optimized, scrape_content, scrape_multiple_content
from app.services.similarity import detect_plagiarism
from app.core.config import settings
from app.models.schema import StatusResponse, ResultResponse
from app.services.job_store import job_store  # Import the centralized job store
from app.services.similarity import perform_plagiarism_check

router = APIRouter()

# Remove these lines - REMOVE THESE
# In-memory job storage (replace with database in production)
# JOBS = {}
# from app.api.endpoints.analyze import jobs  # Shared jobs storage

@router.post("/check")  # Changed from GET to POST
async def check_plagiarism(
    background_tasks: BackgroundTasks,
    content: str = Form(None),
    file: UploadFile = File(None)
):
    """Start a plagiarism check job with validation"""
    from app.models.schema import ContentValidator
    
    # Validate that we have content
    if not content and not file:
        raise HTTPException(status_code=400, detail="No content provided")
    
    # Generate a unique job ID
    job_id = str(uuid.uuid4())
    
    # Process text content
    text_content = content
    if not content and file:
        try:
            # Read file content with size limit
            file_content = await file.read()
            
            # Validate file
            valid, error_msg = ContentValidator.validate_file(file_content, file.filename)
            if not valid:
                raise HTTPException(status_code=400, detail=error_msg)
            
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252']
            for encoding in encodings:
                try:
                    text_content = file_content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
                    
            # If we couldn't decode with any encoding
            if not text_content:
                raise HTTPException(status_code=400, detail="Could not decode file content")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")
    
    # Validate the text content
    valid, error_msg = ContentValidator.validate_text(text_content)
    if not valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Create the job
    job_store.create_job(
        job_id=job_id, 
        status="processing",
        original_content=text_content,
        content_length=len(text_content),
    )
    
    # Run plagiarism detection in background
    background_tasks.add_task(process_plagiarism_check, job_id, text_content)
    
    return {"success": True, "jobId": job_id}

@router.get("/status/{job_id}", response_model=StatusResponse)
async def check_status(job_id: str):
    """
    Check the status of a plagiarism detection job
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "status": job["status"],
        "progress": job.get("progress", 0),
        "message": job.get("error", None) if job["status"] == "failed" else None
    }

@router.post("/plagiarism-check/{job_id}", response_model=StatusResponse)
async def start_plagiarism_check(job_id: str, background_tasks: BackgroundTasks):
    """
    Start plagiarism check process for a previously analyzed text
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] not in ["analyzed", "failed"]:
        if job["status"] == "processing":
            return {"status": "processing", "progress": job.get("progress", 0)}
        elif job["status"] == "completed":
            return {"status": "completed", "progress": 100}
        else:
            raise HTTPException(status_code=400, detail=f"Invalid job status: {job['status']}")
    
    # Reset job status for plagiarism checking
    job_store.update_job(job_id, status="processing", progress=0)
    
    # Start plagiarism check in background
    background_tasks.add_task(_process_plagiarism_check, job_id)
    
    return {
        "status": "processing",
        "progress": 0
    }

# This endpoint is already using job_store, keep it as-is
@router.get("/results/{job_id}", response_model=ResultResponse)
async def get_results(job_id: str):
    """
    Get the results of a completed plagiarism check
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] != "completed":
        if job["status"] == "failed":
            raise HTTPException(status_code=400, detail=f"Job failed: {job.get('error', 'Unknown error')}")
        else:
            raise HTTPException(status_code=400, detail="Job not yet completed")
    
    return job["result"]

async def _process_plagiarism_check(job_id: str):
    """Background task to process plagiarism check"""
    try:
        job = job_store.get_job(job_id)
        if not job:
            return
        
        # Update job status
        job_store.update_job(job_id, status="processing", progress=10)
        
        # Get content from job
        content = job["content"]
        
        # Use the same pipeline as /api/check with proper logging:
        job_store.update_job(job_id, progress=30, status_message="Searching web for sources")
        
        # Find and scrape sources
        sources = await find_and_scrape_sources_optimized(content, max_sources=settings.MAX_SOURCES)
        
        # Log source details to help debugging
        source_info = [f"{src['url']} ({len(src.get('content', ''))} chars)" for src in sources]
        logger.info(f"Plagiarism check for job {job_id}: Found {len(sources)} sources")
        for i, source in enumerate(source_info):
            logger.info(f"Source {i+1}: {source}")
            
        job_store.update_job(job_id, progress=60, sources=sources)
        
        # Run check with the fully collected sources
        logger.info(f"Running plagiarism check for job {job_id} with {len(sources)} sources")
        result = await perform_plagiarism_check(content, sources)
        
        # Add debug info about the result
        logger.info(f"Plagiarism check result: {result.get('plagiarism_percentage')}% match with {len(result.get('matches', []))} matching sources")
        
        # Add themes to result if they exist
        if "themes" in job:
            result["themes"] = job["themes"]
        
        # Store result and mark job as completed
        job_store.set_job_completed(job_id, result)
        
    except Exception as e:
        import traceback
        logger.error(f"Plagiarism check error: {str(e)}")
        logger.error(traceback.format_exc())
        job_store.set_job_failed(job_id, str(e))

async def process_plagiarism_check(job_id: str, text_content: str):
    """Process plagiarism check in the background with unified job store"""
    try:
        # Update job status
        job_store.update_job(job_id, status="processing", progress=10)
        
        # Find potential sources
        job_store.update_job(job_id, status="processing", progress=30, 
                             status_message="Searching web for sources")
        sources = await find_and_scrape_sources(text_content, max_sources=settings.MAX_SOURCES)
        
        # Debug log
        source_info = [f"{src['url']} ({len(src.get('content', ''))} chars)" for src in sources]
        logger.info(f"Check for job {job_id}: Found {len(sources)} sources")
        for i, source in enumerate(source_info):
            logger.info(f"Source {i+1}: {source}")
        
        # Update job status
        job_store.update_job(job_id, progress=60, 
                             status_message="Analyzing similarity")
        
        # Use perform_plagiarism_check for consistent results
        result = await perform_plagiarism_check(text_content, sources)
        logger.info(f"Check result: {result.get('plagiarism_percentage')}% match with {len(result.get('matches', []))} matching sources")
        
        # Store the result
        job_store.set_job_completed(job_id, result)
        
    except Exception as e:
        import traceback
        logger.error(f"Error in plagiarism check: {str(e)}")
        logger.error(traceback.format_exc())
        job_store.set_job_failed(job_id, str(e))