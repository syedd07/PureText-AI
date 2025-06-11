from typing import List, Dict, Any, Union
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import logging
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model for embeddings
_embedding_model = None

def get_embedding_model() -> SentenceTransformer:
    """Get or initialize embedding model"""
    global _embedding_model
    if _embedding_model is None:
        model_name = settings.EMBEDDING_MODEL
        logger.info(f"Loading embedding model: {model_name}")
        _embedding_model = SentenceTransformer(model_name)
    return _embedding_model

def get_text_embeddings(texts: List[str]) -> np.ndarray:
    """Convert text to embeddings"""
    model = get_embedding_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings

def get_text_embedding(text: str) -> np.ndarray:
    """Convert single text to embedding"""
    return get_text_embeddings([text])[0]

def create_faiss_index(embeddings: np.ndarray, index_type: str = "flat") -> faiss.Index:
    """
    Create a FAISS index for fast similarity search
    
    Args:
        embeddings: Matrix of embeddings
        index_type: Type of index ('flat' for exact, 'ivf' for approximate)
    
    Returns:
        FAISS index
    """
    dimension = embeddings.shape[1]
    
    # Create the appropriate index type
    if index_type == "flat":
        # Flat index - exact but slower
        index = faiss.IndexFlatIP(dimension)  # Inner product = cosine on normalized vecs
    elif index_type == "ivf":
        # IVF index - approximate but faster
        quantizer = faiss.IndexFlatIP(dimension)
        nlist = min(512, max(64, embeddings.shape[0] // 10))  # Dynamic based on dataset size
        index = faiss.IndexIVFFlat(quantizer, dimension, nlist, faiss.METRIC_INNER_PRODUCT)
        index.train(embeddings)
        index.nprobe = 3  # Number of cells to probe (more = slower but more accurate)
    else:
        raise ValueError(f"Unknown index type: {index_type}")
    
    # Normalize embeddings for cosine similarity
    faiss.normalize_L2(embeddings)
    
    # Add vectors to the index
    index.add(embeddings.astype(np.float32))
    return index

def search_similar_vectors(query_embedding: np.ndarray, index: faiss.Index, k: int = 5) -> tuple:
    """
    Search for similar vectors in the index
    
    Args:
        query_embedding: Query embedding vector
        index: FAISS index
        k: Number of results to return
    
    Returns:
        Tuple of (distances, indices)
    """
    # Normalize query for cosine similarity
    query_embedding_normalized = query_embedding.copy().astype(np.float32)
    faiss.normalize_L2(query_embedding_normalized.reshape(1, -1))
    
    # Search the index
    distances, indices = index.search(query_embedding_normalized.reshape(1, -1), k)
    return distances[0], indices[0]

async def get_text_themes(text: str, max_themes: int = 5) -> List[str]:
    """Extract main themes from text content using embeddings"""
    try:
        # Extract key noun phrases
        import re
        from collections import Counter
        
        # Extract potential themes using simple NLP techniques
        # 1. Split into sentences
        sentences = re.split(r'[.!?]', text)
        
        # 2. Extract noun phrases (simplified approach)
        noun_phrases = []
        for sentence in sentences:
            # Look for potential noun phrases with adjectives
            matches = re.findall(r'\b[A-Z][a-z]*(?:\s+[a-z]+){1,3}\b', sentence)
            noun_phrases.extend(matches)
            
            # Also add any capitalized terms (potential named entities)
            matches = re.findall(r'\b[A-Z][a-z]{2,}\b', sentence)
            noun_phrases.extend(matches)
        
        # Count occurrences
        theme_counts = Counter(noun_phrases)
        
        # Get the most common themes
        common_themes = [theme for theme, count in theme_counts.most_common(max_themes) 
                        if len(theme) > 3]  # Filter out very short themes
        
        # If we don't have enough themes, extract keywords
        if len(common_themes) < max_themes:
            # Extract keywords from text (simplified)
            words = re.findall(r'\b[a-zA-Z]{4,}\b', text)
            word_counts = Counter(words)
            
            # Add top keywords that aren't already in themes
            for word, _ in word_counts.most_common(max_themes * 2):
                if len(common_themes) >= max_themes:
                    break
                if word.lower() not in [theme.lower() for theme in common_themes]:
                    common_themes.append(word)
        
        return common_themes[:max_themes]
    
    except Exception as e:
        print(f"Error extracting themes: {str(e)}")
        return ["general"]  # Fallback theme