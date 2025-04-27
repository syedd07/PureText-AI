from typing import List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
import os
import asyncio
from functools import lru_cache
from app.core.config import settings

# Global model instance (lazy-loaded)
_model = None

@lru_cache(maxsize=1)
def get_model():
    """
    Lazy-load the Sentence Transformer model
    Returns a singleton instance of the model
    """
    global _model
    if _model is None:
        print("Loading SBERT model - this may take a moment on first run...")
        _model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    return _model

async def get_text_embedding(text: str) -> List[float]:
    """
    Get embeddings for text using Sentence Transformers
    
    Args:
        text: The text to generate embeddings for
        
    Returns:
        A list of floating point numbers representing the text embedding
    """
    try:
        # Run model inference in a thread pool to avoid blocking
        model = get_model()
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, lambda: model.encode(text, convert_to_numpy=True))
        
        # Convert numpy array to list for JSON serialization
        return embedding.tolist()
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        # Return empty embedding in case of error - use model dimension
        model = get_model()
        return [0.0] * model.get_sentence_embedding_dimension()

async def get_text_themes(text: str, max_themes: int = 3) -> List[str]:
    """
    Extract themes from text using a rule-based approach
    
    Args:
        text: The text to analyze
        max_themes: Maximum number of themes to return
        
    Returns:
        List of identified themes
    """
    try:
        # Since we're not using OpenAI anymore, we'll implement a simple
        # keyword-based theme extraction approach
        
        # Common topics/domains to check against
        domains = {
            "technology": ["computer", "software", "hardware", "digital", "tech", "algorithm", "data", "internet"],
            "science": ["research", "experiment", "scientific", "biology", "physics", "chemistry", "study"],
            "medicine": ["health", "medical", "disease", "treatment", "patient", "doctor", "clinical"],
            "business": ["company", "market", "finance", "economic", "investment", "corporate", "startup"],
            "education": ["school", "student", "learning", "teaching", "academic", "education", "university"],
            "arts": ["creative", "art", "music", "film", "literature", "design", "culture"],
            "politics": ["government", "policy", "political", "election", "law", "regulation"],
            "environment": ["climate", "sustainable", "green", "environmental", "conservation", "ecology"]
        }
        
        # Convert text to lowercase for matching
        lower_text = text.lower()
        
        # Count occurrences of domain keywords
        domain_counts = {}
        for domain, keywords in domains.items():
            count = sum(lower_text.count(keyword) for keyword in keywords)
            if count > 0:
                domain_counts[domain] = count
        
        # Sort domains by count
        sorted_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Get top themes
        themes = [domain for domain, count in sorted_domains[:max_themes]]
        
        # If no themes found, return general
        if not themes:
            return ["general"]
            
        return themes
    except Exception as e:
        print(f"Error identifying themes: {str(e)}")
        return ["general"]  # Fallback to a generic theme if error occurs
    