from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os

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

# Add enhanced validation models

class ContentValidator:
    """Validation utilities for content"""
    
    @staticmethod
    def validate_text(text: str) -> tuple[bool, str]:
        """Validate text content"""
        if not text:
            return False, "Content cannot be empty"
            
        if len(text) < 10:
            return False, "Content too short (minimum 10 characters)"
            
        if len(text) > 100000:
            return False, "Content too large (maximum 100,000 characters)"
            
        # Check for excessive special characters (potential spam)
        special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
        if special_chars / len(text) > 0.3:
            return False, "Content contains too many special characters"
            
        return True, ""
        
    @staticmethod
    def validate_file(file_content: bytes, file_name: str) -> tuple[bool, str]:
        """Validate file content"""
        if not file_content:
            return False, "File is empty"
            
        if len(file_content) > 10 * 1024 * 1024:  # 10 MB
            return False, "File too large (maximum 10MB)"
            
        # Check file extension
        allowed_extensions = ['.txt', '.doc', '.docx', '.pdf', '.rtf', '.odt']
        file_ext = os.path.splitext(file_name.lower())[1]
        if file_ext not in allowed_extensions:
            return False, f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
            
        return True, ""