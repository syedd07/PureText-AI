from typing import List
from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Settings(BaseSettings):
    # Project settings
    PROJECT_NAME: str = "PureText AI"
    API_V1_STR: str = "/api"
    
    # Server settings
    API_HOST: str = "0.0.0.0"  # Added this field
    API_PORT: int = 8000       # Added this field
    DEBUG: bool = True         # Added this field
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8080"]
    
    # API keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ZYTE_API_KEY: str = os.getenv("ZYTE_API_KEY", "")
    
    # Model settings
    EMBEDDING_MODEL: str = "text-embedding-ada-002"
    TEXT_MODEL: str = "gpt-3.5-turbo"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Add this to ignore extra fields

# Create global settings object
settings = Settings()
