from app.services.spider_queue import spider_queue
from typing import List, Dict, Any, Optional, Tuple, Set
import asyncio
import hashlib
import time
import re
import logging
import aiohttp
import httpx
from bs4 import BeautifulSoup
import random
from urllib.parse import urlparse, urljoin, quote_plus
import json
from collections import defaultdict
import nltk
from app.core.config import settings

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize availability check during startup
PLAYWRIGHT_AVAILABLE = False  # Default to False until checked

# Cache dictionary for backward compatibility
# New code should use ScrapeCache from cache_manager.py
SCRAPE_CACHE = {}
CONTENT_FINGERPRINTS = {}
CACHE_EXPIRY = 60 * 60 * 24  # 24 hours

async def is_playwright_available():
    """Check if Playwright is properly installed and available"""
    try:
        import importlib.util
        has_module = importlib.util.find_spec("playwright") is not None
        if not has_module:
            logging.info("Playwright module not found")
            return False
            
        # Check if we're in a restricted environment by testing subprocess capabilities
        try:
            # Simple test of subprocess capabilities
            import asyncio
            proc = await asyncio.create_subprocess_shell(
                "echo test", 
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
        except NotImplementedError:
            logging.warning("Subprocess creation not supported in this environment (Windows Store Python)")
            return False
            
        # If we made it here, try the actual Playwright check
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=True)
                await browser.close()
                return True
            except Exception as e:
                logging.error(f"Playwright browser launch failed: {str(e)}")
                return False
    except Exception as e:
        logging.error(f"Playwright availability check failed: {str(e)}")
        return False

async def initialize_playwright_check():
    """Initialize the playwright availability check at startup"""
    global PLAYWRIGHT_AVAILABLE
    PLAYWRIGHT_AVAILABLE = await is_playwright_available()
    logging.info(f"Playwright availability: {PLAYWRIGHT_AVAILABLE}")

# ----- Helper Functions -----

def extract_search_phrases(text: str, num_phrases: int = 3) -> List[str]:
    """Extract key distinctive phrases from text that would be good for plagiarism search"""
    try:
        # Use NLTK for better sentence tokenization
        from nltk.tokenize import sent_tokenize
        sentences = sent_tokenize(text)
    except:
        # Fallback to regex if NLTK fails
        sentences = re.split(r'[.!?]', text)
    
    # Clean sentences
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    if not sentences:
        return [text[:100]]
    
    # Score sentences by uniqueness/distinctiveness for plagiarism detection
    scored_sentences = []
    for sentence in sentences:
        # Count non-common words (potential plagiarism indicators)
        words = re.findall(r'\b\w{4,}\b', sentence.lower())
        
        # Skip sentences that are too short after processing
        if not words or len(words) < 3:
            continue
            
        # Score based on uniqueness and length
        # Prefer sentences with specialized terms (longer words more likely to be field-specific)
        unique_words = set(words)
        avg_word_len = sum(len(w) for w in words) / len(words) if words else 0
        
        # Higher score = better for plagiarism search
        score = len(unique_words) * (avg_word_len / 5)
        
        scored_sentences.append((sentence, score))
    
    # Sort by score (most distinctive first)
    scored_sentences.sort(key=lambda x: x[1], reverse=True)
    
    # Select top sentences
    selected = [s[0] for s in scored_sentences[:num_phrases]]
    
    # If we don't have enough sentences, add from the original order
    if len(selected) < num_phrases:
        for sentence in sentences:
            if sentence not in selected:
                selected.append(sentence)
                if len(selected) >= num_phrases:
                    break
    
    return selected[:num_phrases]

def calculate_content_relevance(original_text: str, source_content: str) -> float:
    """Calculate how relevant a source is to the original text for plagiarism detection"""
    # Extract keywords from original text
    original_words = set(re.findall(r'\b\w{4,}\b', original_text.lower()))
    
    if not original_words:
        return 0
    
    # Find matching keywords in source
    source_words = set(re.findall(r'\b\w{4,}\b', source_content.lower()))
    
    # Calculate keyword overlap
    common_words = original_words.intersection(source_words)
    if not common_words:
        return 0
        
    # Calculate relevance score based on word overlap and density
    overlap_ratio = len(common_words) / len(original_words)
    content_length_factor = min(1.0, 5000 / max(500, len(source_content)))  # Prefer concise sources
    
    return overlap_ratio * content_length_factor * 100  # Scale to 0-100

def classify_website(url: str) -> str:
    """
    Classifies websites to determine the best scraping approach without hardcoding domains.
    Returns: 'scientific', 'news', 'standard', or 'complex'
    """
    from app.services.zyte_manager import ZyteServiceRouter
    router = ZyteServiceRouter(
        api_key=settings.ZYTE_API_KEY,
        project_id=settings.ZYTE_PROJECT_ID
    )
    return router.classify_website(url)

# ----- Scraping Functions - Now Use ZyteServiceRouter -----

async def smart_scrape_content(url: str) -> Dict[str, Any]:
    """Smart scraping using ZyteServiceRouter"""
    from app.services.zyte_manager import ZyteServiceRouter
    
    # Create router instance
    router = ZyteServiceRouter(
        api_key=settings.ZYTE_API_KEY,
        project_id=settings.ZYTE_PROJECT_ID
    )
    
    try:
        # Use the optimal service selection
        return await router.scrape_with_optimal_service(url)
    finally:
        # Ensure resources are cleaned up
        await router.close()

async def scrape_content(url: str) -> str:
    """Scrape content with optimized settings - returns just the content text"""
    result = await smart_scrape_content(url)
    return result.get("content", "")

async def scrape_multiple_content(urls: List[str], max_concurrent: int = 3) -> List[Dict[str, Any]]:
    """Scrape multiple URLs concurrently using ZyteServiceRouter"""
    from app.services.zyte_manager import ZyteServiceRouter
    
    # Create router instance
    router = ZyteServiceRouter(
        api_key=settings.ZYTE_API_KEY,
        project_id=settings.ZYTE_PROJECT_ID
    )
    
    try:
        # Use the router's parallel scraping capability
        return await router.scrape_urls_in_parallel(
            urls=urls,
            max_concurrent=max_concurrent
        )
    finally:
        # Ensure resources are cleaned up
        await router.close()

# Add this function after the other scraping functions section
async def direct_scrape_url(url: str) -> Dict[str, Any]:
    """
    Legacy function for backward compatibility - delegates to ZyteServiceRouter.
    
    Note: Consider updating code that calls this function to use ZyteServiceRouter directly.
    """
    logger.warning("direct_scrape_url is deprecated - use ZyteServiceRouter instead")
    from app.services.zyte_manager import ZyteServiceRouter
    
    router = ZyteServiceRouter(
        api_key=settings.ZYTE_API_KEY,
        project_id=settings.ZYTE_PROJECT_ID
    )
    
    try:
        return await router.scrape_with_http(url)
    finally:
        await router.close()

# ----- Search Functions -----

async def search_relevant_content(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """Search for content relevant to the query"""
    from app.services.zyte_manager import ZyteServiceRouter
    
    router = ZyteServiceRouter(
        api_key=settings.ZYTE_API_KEY,
        project_id=settings.ZYTE_PROJECT_ID
    )
    
    try:
        # First check if we've implemented a search method in ZyteServiceRouter
        # If not, fall back to legacy implementation
        
        # For now, use the legacy search implementation from ZyteClient
        client = get_zyte_client()
        
        # Optimize query for plagiarism detection
        optimized_query = f"{query}"
        
        # Search using client's advanced search method
        results = await client.search_web(optimized_query, max_results * 2)
        
        # Advanced filtering for plagiarism-relevant sources
        filtered_results = []
        for result in results:
            url = result["url"]
            domain = urlparse(url).netloc
            
            # Skip obvious non-content pages
            if re.search(r'/(login|signup|register|cart|checkout|account|profile|contact|about)/?$', url, re.I):
                continue
                
            # Skip PDFs, office docs, etc.
            if re.search(r'\.(pdf|doc|docx|ppt|pptx)$', url, re.I):
                continue
                
            # Skip social media
            if any(site in domain for site in ['facebook.com', 'twitter.com', 'instagram.com', 'tiktok.com', 'youtube.com']):
                continue
                
            filtered_results.append(result)
            
            # Stop once we have enough results
            if len(filtered_results) >= max_results:
                break
        
        # Sort results by relevance to plagiarism (academic & educational sources first)
        filtered_results.sort(key=lambda x: (
            # Educational/academic sources get highest priority
            2 if x.get('content_type') == 'academic' or '.edu' in urlparse(x['url']).netloc else
            # Wikipedia and other reference sources next
            1 if x.get('content_type') == 'encyclopedia' else
            # Everything else
            0
        ), reverse=True)
        
        return filtered_results[:max_results]
    finally:
        await router.close()

async def find_and_scrape_sources(text: str, max_sources: int = 5) -> List[Dict[str, Any]]:
    """Find and scrape potential plagiarism sources"""
    # Use the new optimized version
    return await find_and_scrape_sources_optimized(text, max_sources)

async def find_and_scrape_sources_optimized(text: str, max_sources: int = 5) -> List[Dict[str, Any]]:
    """Find and scrape potential plagiarism sources using the service router"""
    from app.services.zyte_manager import ZyteServiceRouter
    
    # 1. Extract search phrases - use multiple phrases to increase chances of finding matches
    search_phrases = extract_search_phrases(text, num_phrases=2)
    if not search_phrases:
        return []
    
    # Track all found URLs across queries
    all_urls_to_scrape = []
    
    # 2. Try multiple search phrases to maximize chances of finding matches
    for phrase in search_phrases:
        # Add academic-specific terms to search query for better results
        search_query = phrase
        if 'paper' in text.lower() or 'study' in text.lower() or 'research' in text.lower():
            search_query = f"{phrase} academic research paper"
            
        logger.info(f"Searching with query: {search_query[:100]}...")
        search_results = await search_relevant_content(search_query, max_results=8)
        
        # Extract URLs from results
        urls_from_query = [result.get("url") for result in search_results if result.get("url")]
        all_urls_to_scrape.extend(urls_from_query)
        
        # Break early if we have enough URLs
        if len(all_urls_to_scrape) >= max_sources * 3:
            break
    
    # Remove duplicates while preserving order
    urls_to_scrape = []
    seen_urls = set()
    for url in all_urls_to_scrape:
        if url not in seen_urls:
            seen_urls.add(url)
            urls_to_scrape.append(url)
    
    if not urls_to_scrape:
        return []
    
    # Log the URLs we'll be scraping
    logger.info(f"Found {len(urls_to_scrape)} URLs to scrape for potential matches")
    
    # 3. Initialize the service router
    router = ZyteServiceRouter(
        api_key=settings.ZYTE_API_KEY,
        project_id=settings.ZYTE_PROJECT_ID
    )
    
    try:
        # 4. Scrape URLs in parallel - limit to avoid rate limits and timeouts
        max_urls_to_scrape = min(max_sources * 3, len(urls_to_scrape))
        results = await router.scrape_urls_in_parallel(
            urls=urls_to_scrape[:max_urls_to_scrape],
            max_concurrent=2  # Lower concurrency for more reliability
        )
        
        # 5. Filter and format results
        sources = []
        for result in results:
            if result and result.get("content") and len(result.get("content", "")) > 200:
                # Calculate relevance to the original text
                relevance = calculate_content_relevance(text, result.get("content", ""))
                
                sources.append({
                    "url": result["url"],
                    "content": result["content"],
                    "title": result.get("title", ""),
                    "relevance": relevance
                })
        
        # 6. Sort by relevance and return top results
        sources.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        return sources[:max_sources]
    finally:
        # Ensure router is closed
        await router.close()

# ----- Legacy ZyteClient for Backward Compatibility -----

class ZyteClient:
    """Legacy ZyteClient - Still needed for search_web functionality"""
    
    def __init__(self, api_key: str, project_id: str):
        self.api_key = api_key
        self.project_id = project_id
        self.session = None
        self.rate_limit_delay = 1.0
        self.adaptive_timeout = 60
        self.requests_counter = 0
        self.failed_requests = 0
        self.backoff_factor = 1.5
        self.max_retries = 3
    
    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def search_web(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """Search the web using Google CSE"""
        # Log search attempt
        logger.info(f"Searching for: {query[:100]}")
        
        if settings.GOOGLE_API_KEY and settings.GOOGLE_CSE_ID:
            try:
                search_url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    "q": query,
                    "key": settings.GOOGLE_API_KEY,
                    "cx": settings.GOOGLE_CSE_ID,
                    "num": min(10, max_results)
                }
                
                # Debug logging
                if settings.DEBUG_SEARCH:
                    logger.debug(f"Google CSE request: {search_url} with params: {params}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(search_url, params=params, timeout=15) as response:
                        # Get full response for inspection
                        response_text = await response.text()
                        
                        if response.status == 200:
                            try:
                                data = json.loads(response_text)
                                results = []
                                
                                # Check if we got search results
                                if "items" in data:
                                    for item in data["items"]:
                                        results.append({
                                            "url": item.get("link"),
                                            "title": item.get("title", ""),
                                            "snippet": item.get("snippet", "")
                                        })
                                    
                                    logger.info(f"Google CSE found {len(results)} results for query: {query[:50]}...")
                                    return results[:max_results]
                                else:
                                    # No results found but API worked
                                    logger.info(f"Google CSE returned no results for: {query[:50]}...")
                            except json.JSONDecodeError as e:
                                logger.error(f"Google CSE returned invalid JSON: {str(e)}")
                        else:
                            # Log detailed error info
                            logger.error(f"Google CSE error (HTTP {response.status}): {response_text[:500]}")
                            
                            # Check for common error types
                            if response.status == 403:
                                logger.error("Google CSE API key unauthorized. Check your API key permissions.")
                            elif response.status == 429:
                                logger.error("Google CSE quota exceeded. Consider upgrading your plan.")
                
            except Exception as e:
                logger.error(f"Google CSE search failed: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        else:
            logger.warning("Google API key or CSE ID not configured, using fallback search methods")
        
        # Fall back to direct scraping methods if API fails or isn't configured
        return await self._fallback_search(query, max_results)
    
    async def _fallback_search(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Enhanced fallback search with crawler integration"""
        # 1. Try Playwright crawler if installed
        try:
            # Check if playwright is installed first
            import importlib.util
            if importlib.util.find_spec("playwright"):
                from app.services.crawler import crawl_search_results
                crawler_results = await crawl_search_results(query, max_pages=max_results)
                
                if crawler_results:
                    logger.info(f"Found {len(crawler_results)} results using Playwright crawler")
                    return [
                        {
                            "url": result["url"],
                            "title": result["title"],
                            "snippet": BeautifulSoup(result["html"], 'html.parser').get_text()[:150] + "...",
                        }
                        for result in crawler_results
                    ]
        except ImportError:
            logger.warning("Playwright not installed, skipping crawler-based search")
        except Exception as e:
            logger.warning(f"Playwright crawler failed: {str(e)}")
        
        # 2. Fall back to direct HTML scraping of search engines
        for search_method in [self._direct_google_search, self._direct_bing_search, self._direct_ddg_search]:
            try:
                results = await search_method(query, max_results)
                if results:
                    return results
            except Exception as e:
                logger.warning(f"Search method failed: {str(e)}")
        
        # 3. Last resort fallback
        return [{
            "url": f"https://en.wikipedia.org/wiki/{quote_plus(query)}",
            "title": f"Wikipedia - {query}",
            "snippet": ""
        }]
    
    async def _direct_google_search(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Direct HTML scraping for Google search results"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15"
        ]
        
        headers = {"User-Agent": random.choice(user_agents)}
        search_url = f"https://www.google.com/search?q={quote_plus(query)}&num={max_results}"
        
        try:
            session = await self._get_session()
            async with session.get(search_url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    results = []
                    for g in soup.select('div.g'):
                        # Extract link
                        link_elem = g.select_one('a')
                        if not link_elem:
                            continue
                            
                        link = link_elem.get('href', '')
                        if not link.startswith('http'):
                            continue
                            
                        # Extract title
                        title_elem = g.select_one('h3')
                        title = title_elem.text if title_elem else ""
                        
                        # Extract snippet
                        snippet_elem = g.select_one('.VwiC3b')
                        snippet = snippet_elem.text if snippet_elem else ""
                        
                        results.append({
                            "url": link,
                            "title": title,
                            "snippet": snippet
                        })
                        
                        if len(results) >= max_results:
                            break
                    
                    return results
            
            return []
        except Exception as e:
            logger.warning(f"Direct Google search failed: {str(e)}")
            return []

    async def _direct_bing_search(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Direct HTML scraping for Bing search results"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        search_url = f"https://www.bing.com/search?q={quote_plus(query)}&count={max_results}"
        
        try:
            session = await self._get_session()
            async with session.get(search_url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_bing_html(html, max_results)
            return []
        except Exception as e:
            logger.warning(f"Direct Bing search failed: {str(e)}")
            return []
    
    def _parse_bing_html(self, html: str, max_results: int) -> List[Dict[str, str]]:
        """Parse Bing search results from HTML"""
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all search results
        for result in soup.select('li.b_algo')[:max_results]:
            link = result.select_one('h2 a')
            snippet = result.select_one('.b_caption p')
            
            if link:
                url = link.get('href', '')
                title = link.get_text(strip=True)
                snippet_text = snippet.get_text(strip=True) if snippet else ""
                
                results.append({
                    "url": url,
                    "title": title,
                    "snippet": snippet_text
                })
        
        return results

    async def _direct_ddg_search(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Direct HTML scraping for DuckDuckGo search results"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        
        try:
            session = await self._get_session()
            async with session.get(search_url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    results = []
                    for result in soup.select('.result'):
                        link_elem = result.select_one('.result__a')
                        if not link_elem:
                            continue
                            
                        link = link_elem.get('href', '')
                        # DuckDuckGo uses redirects
                        if '/redirect/' in link:
                            link_parts = link.split('uddg=')
                            if len(link_parts) > 1:
                                link = link_parts[1]
                                
                        title = link_elem.text.strip()
                        
                        # Extract snippet
                        snippet_elem = result.select_one('.result__snippet')
                        snippet = snippet_elem.text.strip() if snippet_elem else ""
                        
                        results.append({
                            "url": link,
                            "title": title,
                            "snippet": snippet
                        })
                        
                        if len(results) >= max_results:
                            break
                    
                    return results
            
            return []
        except Exception as e:
            logger.warning(f"Direct DuckDuckGo search failed: {str(e)}")
            return []
            
    async def close(self):
        """Close the client session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

# ----- Singleton Client Management -----

_zyte_client = None

def get_zyte_client() -> ZyteClient:
    """Get or create singleton ZyteClient instance"""
    global _zyte_client
    if (_zyte_client is None):
        _zyte_client = ZyteClient(
            api_key=settings.ZYTE_API_KEY,
            project_id=settings.ZYTE_PROJECT_ID
        )
    return _zyte_client

async def close_client():
    """Close the Zyte client when application shuts down"""
    global _zyte_client
    if _zyte_client:
        await _zyte_client.close()
        _zyte_client = None