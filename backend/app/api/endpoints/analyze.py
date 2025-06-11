from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from typing import Optional, List
import uuid

from app.models.schema import TextInput, PlagiarismResponse
from app.services.embedding import get_text_themes
from app.services.scraping import search_relevant_content
from app.services.job_store import job_store  # Import the centralized job store

router = APIRouter()

# Remove local jobs dictionary - REMOVE THIS LINE

@router.post("/analyze", response_model=PlagiarismResponse)
async def analyze_text(
    background_tasks: BackgroundTasks,
    text_input: Optional[str] = Form(None),
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
    
    # Create job entry using job_store
    job_store.create_job(
        job_id=job_id,
        status="processing",
        content=content,
        themes=[],
        urls=[],
        sources=[],
        result=None,
        progress=0
    )
    
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
        job_store.update_job(job_id, status="processing", progress=10)
        
        # Extract themes
        themes = await get_text_themes(content)
        job_store.update_job(job_id, themes=themes, progress=50)
        
        # Find relevant content for themes
        urls = await search_relevant_content(themes)
        job_store.update_job(job_id, urls=urls, progress=100, status="analyzed")
        
    except Exception as e:
        job_store.set_job_failed(job_id, str(e))