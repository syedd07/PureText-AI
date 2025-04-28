from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from typing import Optional
import uuid

from app.models.schema import TextInput, PlagiarismResponse
from app.services.embedding import get_text_themes
from app.services.scraping import search_relevant_content
 
router = APIRouter()

# In-memory job storage (replace with database in production)
jobs = {}

@router.post("/analyze", response_model=PlagiarismResponse)
async def analyze_text(
    background_tasks: BackgroundTasks,
    text_input: Optional[str] = Form(None),  # Changed from text_input_json
    file: Optional[UploadFile] = File(None)
):
    """Analyze text content to extract themes and categories"""
    
    # Handle text input
    content = ""
    if text_input:
        try:
            # Try to parse as JSON
            import json
            data = json.loads(text_input)
            if isinstance(data, dict) and "content" in data:
                content = data["content"]
            else:
                content = text_input  # Use as raw text if not properly formatted
        except json.JSONDecodeError:
            # Not JSON, use as plain text
            content = text_input
    elif file:
        # Read file content
        content = await file.read()
        content = content.decode("utf-8")
    else:
        raise HTTPException(
            status_code=400, 
            detail="Either text_input or file must be provided"
        )
    
    job_id = str(uuid.uuid4())
    
    # Create job entry
    jobs[job_id] = {
        "status": "processing",
        "content": content,
        "themes": [],
        "urls": [],
        "sources": [],
        "result": None,
        "progress": 0
    }
    
    # Process text analysis in background
    background_tasks.add_task(_process_analysis, job_id, content)
    
    return {
        "success": True,
        "job_id": job_id,
        "message": "Text analysis started"
    }

async def _process_analysis(job_id: str, content: str):
    """Background task to process text analysis"""
    try:
        # Update job status
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 10
        
        # Extract themes
        themes = await get_text_themes(content)
        jobs[job_id]["themes"] = themes
        jobs[job_id]["progress"] = 50
        
        # Find relevant content for themes
        urls = await search_relevant_content(themes)
        jobs[job_id]["urls"] = urls
        jobs[job_id]["progress"] = 100
        
        # Mark job as ready for plagiarism check
        jobs[job_id]["status"] = "analyzed"
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)