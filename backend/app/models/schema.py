from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class TextInput(BaseModel):
    content: str

class PlagiarismResponse(BaseModel):
    success: bool = Field(True, description="Success status")
    job_id: str = Field(..., description="Unique job identifier")
    message: Optional[str] = Field(None, description="Additional information")

class StatusResponse(BaseModel):
    status: str = Field(..., description="Job status: processing, completed, or failed")
    progress: Optional[float] = Field(None, description="Progress percentage (0-100)")
    message: Optional[str] = Field(None, description="Additional status information")

class Match(BaseModel):
    text_snippet: str = Field(..., description="Matched text snippet")
    source_url: str = Field(..., description="Source URL of the match")
    similarity_score: float = Field(..., description="Similarity score (0-1)")

class ResultResponse(BaseModel):
    success: bool = Field(True, description="Success status")
    plagiarism_percentage: float = Field(..., description="Overall plagiarism percentage")
    matches: List[Match] = Field(default_factory=list, description="List of matched text snippets")
    full_text_with_highlights: str = Field(..., description="Original text with highlighted plagiarized sections")
    themes: List[str] = Field(default_factory=list, description="Detected themes in the text")