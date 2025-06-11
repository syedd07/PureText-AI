from typing import List, Optional, Dict, Any
from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class PlagiarismSettings(BaseSettings):
    """Dedicated settings class for plagiarism detection parameters"""
    # Main similarity threshold (lowered from 0.78 to capture more potential matches)
    SIMILARITY_THRESHOLD: float = 0.65
    
    # Multi-level matching thresholds
    SENTENCE_SIMILARITY_THRESHOLD: float = 0.70  # For sentence-level comparisons
    PARAGRAPH_SIMILARITY_THRESHOLD: float = 0.60  # For paragraph-level matches
    EXACT_MATCH_THRESHOLD: float = 0.95  # For declaring 100% match
    
    # Verification parameters
    MIN_CHARS_MATCH: int = 20  # Minimum characters that must match exactly
    MIN_MATCH_PERCENT: float = 0.40  # Minimum % of content that must match exactly
    WORD_OVERLAP_THRESHOLD: float = 0.70  # Word overlap for verification
    
    # Detection strategies to use (enable/disable)
    USE_EXACT_MATCHING: bool = True  # Full-text exact matching
    USE_PARAGRAPH_MATCHING: bool = True  # Paragraph level matching
    USE_SENTENCE_MATCHING: bool = True  # Sentence level matching
    USE_WORD_OVERLAP: bool = True  # Word overlap verification
    
    # Normalization options
    NORMALIZE_WHITESPACE: bool = True  # Normalize all whitespace
    NORMALIZE_PUNCTUATION: bool = True  # Remove punctuation
    NORMALIZE_CASE: bool = True  # Convert to lowercase
    
    # Performance settings
    MAX_SENTENCES_PER_SOURCE: int = 800  # Max sentences to analyze per source
    SENTENCE_MIN_LENGTH: int = 15  # Min sentence length to consider

class Settings(BaseSettings):
    # Project settings
    PROJECT_NAME: str = "PureText AI"
    API_V1_STR: str = "/api"
    
    # Server settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", 
                           "http://localhost:8080", "https://puretextai.netlify.app"]
    
    # API keys with proper annotations
    ZYTE_API_KEY: Optional[str] = None
    ZYTE_PROJECT_ID: Optional[str] = None
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_CSE_ID: str = os.getenv("GOOGLE_CSE_ID", "e2d9b097c28dd4c41")
    
    # Advanced settings
    USE_FAISS: bool = True
    MAX_SOURCES: int = 10
    
    # Plagiarism detection settings
    plagiarism: PlagiarismSettings = PlagiarismSettings()
    
    # Model settings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    # Content types for adaptive thresholds
    CONTENT_TYPE_THRESHOLDS: Dict[str, float] = {
        "academic": 0.70,
        "general": 0.65,
        "technical": 0.60,
        "creative": 0.72
    }
    
    # Debug flags
    DEBUG_SEARCH: bool = os.getenv("DEBUG_SEARCH", "False").lower() == "true"
    DEBUG_PLAGIARISM: bool = os.getenv("DEBUG_PLAGIARISM", "False").lower() == "true"
    
    # Add a method to validate required settings on startup
    def validate(self) -> List[str]:
        """Validate that all required settings are provided"""
        errors = []
        
        # Validate Google CSE settings
        if not self.GOOGLE_API_KEY:
            errors.append("GOOGLE_API_KEY is not set")
        if not self.GOOGLE_CSE_ID:
            errors.append("GOOGLE_CSE_ID is not set")
            
        # Validate plagiarism thresholds make sense
        if self.plagiarism.SIMILARITY_THRESHOLD > 0.9:
            errors.append("SIMILARITY_THRESHOLD is too high (>0.9), will miss most matches")
            
        if self.plagiarism.MIN_MATCH_PERCENT > 0.7:
            errors.append("MIN_MATCH_PERCENT is too high (>0.7), verification will be too strict")
        
        return errors
        
    # Smart configuration helper method
    def get_threshold_for_content_length(self, length: int) -> float:
        """Returns adaptive threshold based on content length"""
        if length < 200:
            return self.plagiarism.SIMILARITY_THRESHOLD + 0.05  # Stricter for short texts
        elif length > 2000:
            return self.plagiarism.SIMILARITY_THRESHOLD - 0.05  # More lenient for long texts
        else:
            return self.plagiarism.SIMILARITY_THRESHOLD
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

# Create global settings object
settings = Settings()