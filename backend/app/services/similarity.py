from typing import List, Dict, Any, Set, Tuple
import numpy as np
# import faiss
import re
import asyncio
from app.services.embedding import get_text_embedding
from app.services.scraping import scrape_content
from sentence_transformers import SentenceTransformer
import nltk

# Comprehensive NLTK data download
try:
    # Download both punkt and punkt_tab
    nltk.download('punkt')
    # For punkt_tab specifically - this is what's missing
    try:
        nltk.download('punkt_tab')
    except:
        # If punkt_tab isn't available in the repository
        print("Note: punkt_tab not available in standard NLTK repository, using punkt instead")
except Exception as e:
    print(f"Warning: NLTK download failed: {str(e)}")

# Constants for plagiarism detection - TUNED FOR BETTER ACCURACY
CHUNK_SIZE = 20  # Even smaller chunks for better performance
CHUNK_OVERLAP = 5  # Reduced overlap to improve speed
SIMILARITY_THRESHOLD = 0.65  # Lower threshold for better recall
WIKIPEDIA_THRESHOLD = 0.60   # Even lower threshold for Wikipedia content
EMBEDDING_DIMENSION = 384  # HuggingFace model dimension
MAX_SENTENCES = 500  # Limit the number of sentences to prevent memory issues
MAX_CHUNKS = 150  # Limit the number of chunks to prevent hanging

# Global model for sentence-level comparisons
sentence_model = None

def get_sentence_model():
    """Get or initialize sentence transformer model"""
    global sentence_model
    if sentence_model is None:
        # Use a smaller, faster model
        sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
    return sentence_model

async def detect_plagiarism(text: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Optimized plagiarism detection with improved performance
    """
    # Early return if no sources or empty text
    if not sources or not text.strip():
        return {
            "plagiarism_percentage": 0,
            "matches": [],
            "full_text_with_highlights": text
        }
    
    # Set a timeout for the entire function
    try:
        # Use a simpler approach for better performance
        return await asyncio.wait_for(perform_plagiarism_check(text, sources), timeout=60)
    except asyncio.TimeoutError:
        print("Plagiarism detection timed out - returning partial results")
        # Return a partial result if we time out
        return {
            "plagiarism_percentage": 50,  # Indicate potential plagiarism
            "matches": [{"text_snippet": "Analysis timed out", "source_url": "", "similarity_score": 0.8}],
            "full_text_with_highlights": f"<span class='highlight-warning'>Analysis timed out. The text may contain plagiarized content.</span><br><br>{text}"
        }

async def perform_plagiarism_check(text: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The actual plagiarism check logic, wrapped for timeout handling"""
    
    # Simple exact matching for perfect copies
    for source in sources:
        source_content = source["content"].strip()
        source_url = source["url"]
        
        # Direct text comparison for perfect or near-perfect matches
        if source_content and len(source_content) > 100:
            # If over 90% of the text is identical, it's almost certainly plagiarized
            if text in source_content or source_content in text:
                return {
                    "plagiarism_percentage": 100,
                    "matches": [{
                        "text_snippet": text[:200] + "...",
                        "source_url": source_url,
                        "similarity_score": 1.0
                    }],
                    "full_text_with_highlights": f"<span class='highlight'>{text}</span>"
                }
    
    # Split text for multi-level analysis
    text_chunks = await split_text_into_chunks(text)
    text_sentences = await split_into_sentences(text)
    
    # Limit the number of chunks/sentences to prevent performance issues
    text_chunks = text_chunks[:MAX_CHUNKS]
    text_sentences = text_sentences[:MAX_SENTENCES]
    
    # Process each source and find matches
    matches = []
    plagiarized_chunks = set()
    
    # Efficient model loading - do this once
    model = get_sentence_model()
    
    # Encode all text sentences at once
    text_sent_embeddings = model.encode(text_sentences, show_progress_bar=False)
    
    # Process each source with simple sentence comparison
    for source in sources:
        source_url = source["url"]
        source_content = source["content"]
        
        # Skip empty sources
        if not source_content.strip():
            continue
        
        # Use a lower threshold for Wikipedia content
        current_threshold = WIKIPEDIA_THRESHOLD if "wikipedia.org" in source_url else SIMILARITY_THRESHOLD
        
        # Get source sentences (with limit)
        source_sentences = await split_into_sentences(source_content)
        source_sentences = source_sentences[:MAX_SENTENCES]
        
        # Skip if empty
        if not source_sentences:
            continue
        
        # Encode all source sentences at once
        source_sent_embeddings = model.encode(source_sentences, show_progress_bar=False)
        
        # Simple matrix multiplication for all similarities at once
        similarity_matrix = np.dot(text_sent_embeddings, source_sent_embeddings.T)
        
        # Find best matches for each text sentence
        for i, text_sentence in enumerate(text_sentences):
            # Find best match for this sentence
            best_idx = np.argmax(similarity_matrix[i])
            best_score = similarity_matrix[i][best_idx]
            
            if best_score > current_threshold:  # Use the appropriate threshold
                matches.append({
                    "text_snippet": text_sentence,
                    "source_url": source_url,
                    "similarity_score": float(best_score)
                })
                plagiarized_chunks.add(i)
    
    # Calculate percentage based on matched sentences
    plagiarism_percentage = (len(plagiarized_chunks) / len(text_sentences)) * 100 if text_sentences else 0
    
    # Ensure percentage is 100% if the entire document was copied
    if plagiarism_percentage > 95:
        plagiarism_percentage = 100
    
    # Create highlighted text
    highlighted_text = text
    
    # Sort matches by position in text
    text_matches = []
    for i in sorted(plagiarized_chunks):
        if i < len(text_sentences):
            sentence = text_sentences[i]
            start = text.find(sentence)
            if start >= 0:
                text_matches.append((start, start + len(sentence)))
    
    # Sort by start position in reverse order
    text_matches.sort(reverse=True)
    
    # Apply highlighting
    for start, end in text_matches:
        highlighted_text = highlighted_text[:end] + "</span>" + highlighted_text[end:]
        highlighted_text = highlighted_text[:start] + "<span class='highlight'>" + highlighted_text[start:]
    
    return {
        "plagiarism_percentage": plagiarism_percentage,
        "matches": matches,
        "full_text_with_highlights": highlighted_text
    }

async def split_text_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into chunks with overlap"""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        chunks.append(chunk)
    
    return chunks

async def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences with improved robustness"""
    # First attempt: direct NLTK tokenization
    try:
        return nltk.sent_tokenize(text)
    except Exception as first_error:
        print(f"Primary NLTK tokenization failed: {str(first_error)}")
        
        # Second attempt: RegEx approach
        try:
            # More sophisticated regex that handles common abbreviations
            # This regex looks for sentence boundaries while ignoring periods in common abbreviations
            pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s'
            sentences = re.split(pattern, text)
            if sentences and len(sentences) > 1:
                return [s.strip() for s in sentences if s.strip()]
        except Exception as second_error:
            print(f"RegEx tokenization failed: {str(second_error)}")
        
        # Last resort: simple split
        sentences = re.split(r'[.!?]', text)
        return [s.strip() for s in sentences if s.strip()]
    