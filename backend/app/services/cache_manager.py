# backend/app/services/cache_manager.py
import diskcache
import hashlib
import time
from typing import Dict, Any, List, Optional, Union
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class ScrapeCache:
    """Multi-level caching for scraper optimization"""
    
    def __init__(self, cache_dir=None):
        # Use settings if available, default to ./cache otherwise
        if cache_dir is None:
            try:
                from app.core.config import settings
                cache_dir = getattr(settings, "CACHE_DIR", "./cache")
            except ImportError:
                cache_dir = "./cache"
        
        # Create separate caches for different content types
        self.search_cache = diskcache.Cache(f"{cache_dir}/search")
        self.content_cache = diskcache.Cache(f"{cache_dir}/content")
        self.metadata_cache = diskcache.Cache(f"{cache_dir}/metadata")
        
        # TTL values in seconds
        self.ttls = {
            "search": 60 * 60 * 24,     # 24 hours for search results
            "academic": 60 * 60 * 24 * 7,  # 7 days for academic content
            "news": 60 * 60 * 24 * 3,     # 3 days for news
            "standard": 60 * 60 * 24 * 5,  # 5 days for standard sites
            "metadata": 60 * 60 * 24 * 30  # 30 days for metadata
        }
    
    def _make_key(self, value: str) -> str:
        """Create standardized cache keys"""
        return hashlib.md5(value.encode()).hexdigest()
    
    def get_content(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached content for a URL"""
        key = self._make_key(url)
        result = self.content_cache.get(key)
        if result:
            logger.info(f"Cache hit for content: {url}")
        return result
    
    def set_content(self, url: str, content: Dict[str, Any]) -> None:
        """Store content with appropriate TTL based on content type"""
        key = self._make_key(url)
        domain = urlparse(url).netloc.lower()
        
        # Determine content type for TTL
        content_type = "standard"
        if any(a in domain for a in ['sciencedirect', 'springer', 'wiley', 'ncbi']):
            content_type = "academic"
        elif any(n in domain for n in ['news', 'times', 'post', 'article']):
            content_type = "news"
        
        # Store with appropriate TTL
        self.content_cache.set(key, content, expire=self.ttls[content_type])
        logger.info(f"Cached content for {url} as {content_type}")
    
    def get_search_results(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached search results"""
        key = self._make_key(query)
        return self.search_cache.get(key)
    
    def set_search_results(self, query: str, results: List[Dict[str, Any]]) -> None:
        """Store search results"""
        key = self._make_key(query)
        self.search_cache.set(key, results, expire=self.ttls["search"])
    
    def get_domain_info(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get cached domain metadata (complexity, best scraper, etc.)"""
        return self.metadata_cache.get(domain)
    
    def set_domain_info(self, domain: str, info: Dict[str, Any]) -> None:
        """Store domain metadata for future optimization"""
        self.metadata_cache.set(domain, info, expire=self.ttls["metadata"])
    
    def clear_expired(self) -> None:
        """Clear expired cache entries (maintenance)"""
        self.search_cache.expire()
        self.content_cache.expire()
        self.metadata_cache.expire()