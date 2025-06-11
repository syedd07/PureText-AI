from typing import List, Dict, Any, Set, Tuple
import re
import asyncio

import numpy as np

from app.services.embedding import get_text_embedding, get_text_embeddings, create_faiss_index, search_similar_vectors
from sentence_transformers import SentenceTransformer, util
import nltk
from app.core.config import settings


# cache a single model load
_model = SentenceTransformer("all-MiniLM-L6-v2")

# Comprehensive NLTK data download
try:
    nltk.download('punkt')
    try:
        nltk.download('punkt_tab')
    except:
        print("Note: punkt_tab not available in standard NLTK repository, using punkt instead")
except Exception as e:
    print(f"Warning: NLTK download failed: {str(e)}")

# Constants for plagiarism detection
CHUNK_SIZE = 20
CHUNK_OVERLAP = 5
SIMILARITY_THRESHOLD = settings.plagiarism.SIMILARITY_THRESHOLD  # FIXED: Use nested attribute
WIKIPEDIA_THRESHOLD = 0.82
EMBEDDING_DIMENSION = 384
MIN_SENTENCE_LENGTH = settings.plagiarism.SENTENCE_MIN_LENGTH
MAX_SENTENCES = settings.plagiarism.MAX_SENTENCES_PER_SOURCE
MAX_CHUNKS = 150

# Global model for sentence-level comparisons
sentence_model = None

def get_sentence_model():
    """Get or initialize sentence transformer model""" 
    global sentence_model
    if sentence_model is None:
        sentence_model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return sentence_model

def normalize_text(text: str) -> str:
    """Normalize text for more accurate comparison"""
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    return text.strip()

def verify_match(text_sentence: str, source_content: str, threshold: float = 0.75) -> bool:
    """Verify match with multiple techniques"""
    # Lower threshold to catch more matches (0.8 → 0.75)
    
    # Exact substring match (normalized)
    norm_text = normalize_text(text_sentence)
    norm_source = normalize_text(source_content)
    
    # Direct match
    if norm_text in norm_source:
        return True
    
    # Also check for match with minor differences (75% of words matching)    
    text_words = set(norm_text.split())
    if len(text_words) > 5:  # Only for substantial sentences
        for source_sentence in split_into_sentences(source_content):
            source_words = set(normalize_text(source_sentence).split())
            if len(text_words) > 0:
                overlap = len(text_words.intersection(source_words)) / len(text_words)
                if overlap > threshold:
                    return True
    
    return False

async def detect_plagiarism(original_text: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Embed text and each source, compute cosine sim, return % and matches."""
    # 0) Quick exact‐match override: if the full text appears verbatim in any source, return 100%
    for src in sources:
        content = src.get("content", "")
        if original_text.strip() and original_text.strip() in content:
            return {
                "success": True,
                "plagiarism_percentage": 100.0,
                "matches": [{
                    "text_snippet": original_text.strip(),
                    "source_url": src.get("url", ""),
                    "similarity_score": 100.0
                }],
                "full_text_with_highlights": f"<span class='highlight'>{original_text}</span>"
            }

    # 1) embed once
    orig_emb = _model.encode(original_text, convert_to_tensor=True)
    matches = []
    highest = 0.0

    for src in sources:
        content = src.get("content", "")
        if not content:
            continue

        emb = _model.encode(content, convert_to_tensor=True)
        score = util.cos_sim(orig_emb, emb).item()  # [-1..1]
        pct = max(0.0, min(1.0, score)) * 100

        if pct >= 20.0:  # threshold, adjust as needed
            matches.append({
                "text_snippet": content[:200].strip().replace("\n", " "),
                "source_url": src.get("url", ""),
                "similarity_score": round(pct, 2)
            })

        highest = max(highest, pct)

    return {
        "success": True,
        "plagiarism_percentage": round(highest, 2),
        "matches": matches,
        "full_text_with_highlights": original_text
    }

async def perform_plagiarism_check(text: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The actual plagiarism check logic with FAISS optimization - FIXED VERSION"""
    
    # Add debug logging to track what's happening
    import logging
    logger = logging.getLogger(__name__)
    
    # CRITICAL FIX 1: Better normalization for full text comparison
    def deep_normalize(content: str) -> str:
        """Deeply normalize text for robust matching using configurable settings"""
        if not content:
            return ""
        
        # Apply normalization based on config
        if settings.plagiarism.NORMALIZE_CASE:
            content = content.lower()
    
        if settings.plagiarism.NORMALIZE_WHITESPACE:
            content = re.sub(r'\s+', ' ', content)  # Normalize all whitespace
    
        if settings.plagiarism.NORMALIZE_PUNCTUATION:
            content = re.sub(r'[^\w\s]', '', content)  # Remove punctuation

        return content.strip()
    
    # Extra robust normalization (handles more edge cases)
    def extra_normalize(content: str) -> str:
        """Even more aggressive normalization for truly difficult cases"""
        if not content:
            return ""
        content = content.lower()
        # Remove ALL non-alphanumeric characters (including spaces)
        content = re.sub(r'[^a-z0-9]', '', content)
        return content
    
    # Log input data size
    logger.info(f"Checking text ({len(text)} chars) against {len(sources)} sources")
    
    # First try bi-directional exact match with normalized text
    normalized_text = deep_normalize(text)
    xnormalized_text = extra_normalize(text)
    
    # CRITICAL FIX: Try exact matching with more flexible normalization
    for source in sources:
        source_content = source.get("content", "").strip()
        source_url = source.get("url", "")
        
        if not source_content or len(source_content) < 100:
            continue
            
        logger.info(f"Checking against source: {source_url[:60]}...")
        
        # Try multiple normalization strategies
        normalized_source = deep_normalize(source_content)
        xnormalized_source = extra_normalize(source_content)
        
        # EXACT MATCH: Use regular expressions to be more flexible with matching
        # This handles the case where the text is reformatted or has different line breaks
        
        # Check for substantial inclusion
        if len(normalized_text) > 100 and settings.plagiarism.USE_EXACT_MATCHING:
            # 1. Direct normalized text match - fastest check
            if normalized_text in normalized_source or normalized_source in normalized_text:
                logger.info(f"EXACT MATCH FOUND: {source_url}")
                return create_100_percent_result(text, source_url)
                
            # 2. Super-normalized match - catches more reformatting issues
            if (len(xnormalized_text) > 100 and 
                (xnormalized_text in xnormalized_source or xnormalized_source in xnormalized_text)):
                logger.info(f"EXTRA-NORMALIZED MATCH FOUND: {source_url}")
                return create_100_percent_result(text, source_url)
                
            # 3. Paragraph-level matching
            if settings.plagiarism.USE_PARAGRAPH_MATCHING:
                paragraphs = text.split("\n\n")
                matches = 0
                total = 0
            
                for para in paragraphs:
                    if len(para.strip()) > 80:  # Only check substantial paragraphs
                        total += 1
                        para_norm = deep_normalize(para)
                        if para_norm in normalized_source:
                            matches += 1
            
            # If more than 50% of paragraphs match exactly, it's a 100% match
            if total > 0 and matches / total > settings.plagiarism.PARAGRAPH_SIMILARITY_THRESHOLD:
                logger.info(f"PARAGRAPH MATCH FOUND: {matches}/{total} paragraphs match in {source_url}")
                return create_100_percent_result(text, source_url)
    
    # 2. Split text for multi-level analysis
    text_sentences = await split_into_sentences(text)
    text_sentences = [s for s in text_sentences if len(s) >= MIN_SENTENCE_LENGTH]
    
    # Limit the number of sentences to prevent performance issues
    text_sentences = text_sentences[:MAX_SENTENCES]
    
    # 3. Process each source and find VERIFIED matches
    verified_matches = []
    matched_sentences = set()
    
    # Get embeddings for text sentences once
    model = get_sentence_model()
    text_sent_embeddings = model.encode(text_sentences, show_progress_bar=False)
    
    # Track exactly which pieces of text matched which sources
    match_details = []
    
    # 4. Process each source
    for source_idx, source in enumerate(sources):
        source_url = source.get("url", "")
        source_content = source.get("content", "")
        
        # Skip empty sources
        if not source_content or len(source_content.strip()) < 100:
            continue
        
        # Get source sentences
        source_sentences = await split_into_sentences(source_content)
        source_sentences = [s for s in source_sentences if len(s) >= MIN_SENTENCE_LENGTH]
        source_sentences = source_sentences[:MAX_SENTENCES]
        
        # Skip if empty
        if not source_sentences:
            continue
        
        # Source embeddings
        source_sent_embeddings = model.encode(source_sentences, show_progress_bar=False)
        
        # CRITICAL FIX: Store the actual matching text from the source for display
        source_matches = []
        
        # 5. Compare each text sentence with source sentences
        for i, (text_sentence, text_embedding) in enumerate(zip(text_sentences, text_sent_embeddings)):
            if i in matched_sentences:
                continue  # Skip sentences we've already matched
                
            # Calculate similarities with source sentences
            similarities = util.cos_sim(text_embedding, source_sent_embeddings)[0]
            
            # Find best match
            best_idx = np.argmax(similarities.numpy())
            best_score = similarities[best_idx].item()
            
            # CRITICAL FIX: Less stringent verification - reduced from 60% to 40%
            if best_score > SIMILARITY_THRESHOLD and settings.plagiarism.USE_SENTENCE_MATCHING:
                source_sentence = source_sentences[best_idx]
                
                # CRITICAL FIX: Multiple normalization strategies for comparison
                normalized_text_sent = deep_normalize(text_sentence)
                normalized_source_sent = deep_normalize(source_sentence)
                
                # Only consider verified if there's SUBSTANTIAL exact text overlap
                # CRITICAL FIX: Reduce verification threshold from 60% to 40%
                min_match_length = max(
                    settings.plagiarism.MIN_CHARS_MATCH,
                    int(len(normalized_text_sent) * settings.plagiarism.MIN_MATCH_PERCENT)
                )
                
                # Check for exact substring match first (fastest)
                is_verified = False
                
                # 1. Direct normalized match
                if settings.plagiarism.USE_EXACT_MATCHING:
                    if (normalized_text_sent in normalized_source_sent or 
                        normalized_source_sent in normalized_text_sent):
                        is_verified = True
                    
                # 2. Word-overlap match (more flexible)
                elif settings.plagiarism.USE_WORD_OVERLAP and len(normalized_text_sent) > 30:
                    text_words = set(normalized_text_sent.split())
                    source_words = set(normalized_source_sent.split())
                    
                    if len(text_words) > 0:
                        word_overlap = len(text_words.intersection(source_words)) / len(text_words)
                        is_verified = word_overlap > settings.plagiarism.WORD_OVERLAP_THRESHOLD
                
                # 3. Longest common substring as last resort
                if not is_verified:
                    # Calculate longest common substring as fallback
                    common_length = common_substring(normalized_text_sent, normalized_source_sent)
                    is_verified = common_length >= min_match_length
                
                if is_verified:
                    matched_sentences.add(i)
                    
                    # Store match details with ACTUAL matching source text
                    source_matches.append({
                        "text_snippet": text_sentence,
                        "source_snippet": source_sentence,
                        "similarity_score": float(best_score * 100),
                        "verified": True
                    })
                    logger.info(f"Verified match: '{text_sentence[:30]}...' -> '{source_sentence[:30]}...'")
        
        # If we found verified matches for this source, add the source to our results
        if source_matches:
            match_details.append({
                "source_url": source_url,
                "matches": source_matches
            })
    
    # 6. Build final result
    total_chars = sum(len(s) for s in text_sentences)
    matched_chars = sum(len(text_sentences[i]) for i in matched_sentences)
    
    # Calculate plagiarism percentage
    plagiarism_percentage = (matched_chars / total_chars * 100) if total_chars > 0 else 0
    plagiarism_percentage = round(plagiarism_percentage, 1)
    
    # Format matches for the response
    api_matches = []
    for source in match_details:
        source_url = source["source_url"]
        for match in source["matches"]:
            api_matches.append({
                "text_snippet": match["text_snippet"],
                "source_url": source_url,
                "similarity_score": match["similarity_score"],
                "source_snippet": match["source_snippet"]  # Include the actual source text
            })
    
    logger.info(f"Final plagiarism result: {plagiarism_percentage}% from {len(api_matches)} matches")
    
    # Create highlighted text
    highlighted_text = text
    
    # Sort matches by position in text (reverse order to preserve positions)
    text_matches = []
    for i in sorted(matched_sentences):
        if i < len(text_sentences):
            sentence = text_sentences[i]
            start = text.find(sentence)
            if start >= 0:
                text_matches.append((start, start + len(sentence)))
    
    # Sort by start position in reverse order to avoid messing up indices
    text_matches.sort(reverse=True)
    
    # Apply highlighting
    for start, end in text_matches:
        highlighted_text = highlighted_text[:end] + "</span>" + highlighted_text[end:]
        highlighted_text = highlighted_text[:start] + "<span class='highlight'>" + highlighted_text[start:]
    
    return {
        "plagiarism_percentage": plagiarism_percentage,
        "matches": api_matches,
        "full_text_with_highlights": highlighted_text
    }

def create_100_percent_result(text: str, source_url: str) -> Dict[str, Any]:
    """Helper to create a 100% plagiarism result"""
    return {
        "plagiarism_percentage": 100,
        "matches": [{
            "text_snippet": text[:200] + "...",
            "source_url": source_url,
            "similarity_score": 100.0
        }],
        "full_text_with_highlights": f"<span class='highlight'>{text}</span>"
    }

def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Split text into chunks with overlap"""
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        if i + chunk_size <= len(text):
            chunk = text[i:i + chunk_size]
            chunks.append(chunk)
        else:
            chunk = text[i:]
            if len(chunk) > 0.5 * chunk_size:  # Only include final chunk if substantial
                chunks.append(chunk)
    return chunks

def extract_domain(url: str) -> str:
    """Extract domain from URL"""
    try:
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        return domain
    except:
        return url  # Fallback to full URL if parsing fails
        
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
            pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s'
            sentences = re.split(pattern, text)
            if sentences and len(sentences) > 1:
                return [s.strip() for s in sentences if s.strip()]
        except Exception as second_error:
            print(f"RegEx tokenization failed: {str(second_error)}")
        
        # Last resort: simple split
        sentences = re.split(r'[.!?]', text)
        return [s.strip() for s in sentences if s.strip()]

def common_substring(str1: str, str2: str) -> int:
    """Find the longest common substring between two strings"""
    str1, str2 = str1.lower(), str2.lower()
    m, n = len(str1), len(str2)
    dp = [[0 for _ in range(n+1)] for _ in range(m+1)]
    longest = 0
    
    for i in range(1, m+1):
        for j in range(1, n+1):
            if str1[i-1] == str2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
                longest = max(longest, dp[i][j])
    
    return longest