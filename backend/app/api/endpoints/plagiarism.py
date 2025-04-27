from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict

from app.models.schema import StatusResponse, ResultResponse
from app.services.similarity import detect_plagiarism
from app.services.scraping import scrape_content, scrape_multiple_content  # Add this
from app.api.endpoints.analyze import jobs  # Shared jobs storage

router = APIRouter()

@router.get("/status/{job_id}", response_model=StatusResponse)
async def check_status(job_id: str):
    """
    Check the status of a plagiarism detection job
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
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
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job["status"] not in ["analyzed", "failed"]:
        if job["status"] == "processing":
            return {"status": "processing", "progress": job.get("progress", 0)}
        elif job["status"] == "completed":
            return {"status": "completed", "progress": 100}
        else:
            raise HTTPException(status_code=400, detail=f"Invalid job status: {job['status']}")
    
    # Reset job status for plagiarism checking
    job["status"] = "processing"
    job["progress"] = 0
    
    # Start plagiarism check in background
    background_tasks.add_task(_process_plagiarism_check, job_id)
    
    return {
        "status": "processing",
        "progress": 0
    }

@router.get("/results/{job_id}", response_model=ResultResponse)
async def get_results(job_id: str):
    """
    Get the results of a completed plagiarism check
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job["status"] != "completed":
        if job["status"] == "failed":
            raise HTTPException(status_code=400, detail=f"Job failed: {job.get('error', 'Unknown error')}")
        else:
            raise HTTPException(status_code=400, detail="Job not yet completed")
    
    return job["result"]

async def _process_plagiarism_check(job_id: str):
    """Background task to process plagiarism check"""
    try:
        job = jobs[job_id]
        
        # Update job status
        job["status"] = "processing"
        job["progress"] = 10
        
        # Get content from job
        content = job["content"]
        
        # Scrape content from previously identified URLs
        job["progress"] = 30
        sources = await scrape_multiple_content(job["urls"])
        job["sources"] = sources
        
        # Detect plagiarism
        job["progress"] = 60
        result = await detect_plagiarism(content, sources)
        
        # Add themes to result
        result["themes"] = job["themes"]
        
        # Store result and mark job as completed
        job["result"] = result
        job["progress"] = 100
        job["status"] = "completed"
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)