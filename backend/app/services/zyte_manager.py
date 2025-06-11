from typing import Dict, Any, Optional, List, Callable
import aiohttp
import asyncio
import logging
from urllib.parse import urlparse
from app.services.cache_manager import ScrapeCache
from bs4 import BeautifulSoup
import re
import time
import random
import json

logger = logging.getLogger(__name__)

class ZyteServiceRouter:
    """Routes scraping requests to appropriate Zyte service based on site complexity"""
    
    def __init__(self, api_key: str, project_id: str):
        self.api_key = api_key
        self.project_id = project_id
        self.http_semaphore = asyncio.Semaphore(10)  # Allow more HTTP requests (faster)
        self.zyte_semaphore = asyncio.Semaphore(2)   # Limit Zyte API requests (rate limits)
        self.cloud_semaphore = asyncio.Semaphore(1)  # Limit Scrapy Cloud requests (expensive)
        self.session = None
        self.cache = ScrapeCache()
    
    async def get_session(self):
        """Get or create an aiohttp ClientSession"""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    def classify_site_complexity(self, url: str) -> str:
        """Determine which Zyte service to use based on URL complexity"""
        domain = urlparse(url).netloc.lower()
        path = urlparse(url).path.lower()
        
        # Academic/complex sites - use Scrapy Cloud (full browser rendering)
        academic_patterns = ['sciencedirect', 'springer', 'wiley', 'pubmed', 
                           'ncbi', 'ieee', 'jstor', 'elsevier', 'nature', 
                           'academia.edu', 'researchgate', 'frontiers', 'oxford',
                           'tandfonline', 'sage', 'nih.gov', 'acm.org']
        if any(p in domain for p in academic_patterns):
            return "scrapy_cloud"
            
        # News/medium complexity - use Zyte API (faster than Scrapy Cloud)
        news_patterns = ['news', 'blog', 'times', 'post', '.gov', 'cnn', 
                         'bbc', 'guardian', 'nytimes', 'washingtonpost',
                         'medium.com', 'reuters', 'bloomberg']
        if any(p in domain for p in news_patterns):
            return "zyte_api"
            
        # JavaScript-heavy sites - use Zyte API
        js_patterns = ['angular', 'react', 'vue', 'spa', 'dashboard', 'app.']
        if any(p in domain or p in path for p in js_patterns):
            return "zyte_api"
            
        # Default to direct HTTP (for simple sites)
        return "direct_http"
    
    async def scrape_with_optimal_service(self, url: str) -> Dict[str, Any]:
        """Route the request to the optimal Zyte service based on site complexity"""
        # Check cache first
        cached_content = self.cache.get_content(url)
        if cached_content:
            logger.info(f"Cache hit for {url}")
            return cached_content
            
        # Determine the best service based on site complexity
        service_type = self.classify_site_complexity(url)
        logger.info(f"Classified {url} as {service_type}")
        
        # Route to appropriate service
        if service_type == "direct_http":
            result = await self.scrape_with_http(url)
        elif service_type == "zyte_api":
            result = await self.scrape_with_zyte_api(url)
        else:  # scrapy_cloud
            result = await self.scrape_with_scrapy_cloud(url)
        
        # Cache successful results with content
        if result and result.get("content") and len(result.get("content", "")) > 200:
            self.cache.set_content(url, result)
            
        return result
    
    async def scrape_with_http(self, url: str) -> Dict[str, Any]:
        """Simple HTTP scraping for basic sites"""
        async with self.http_semaphore:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml",
                "Accept-Language": "en-US,en;q=0.9"
            }
            
            session = await self.get_session()
            try:
                async with session.get(url, headers=headers, timeout=30) as response:
                    if response.status != 200:
                        return {"url": url, "error": f"HTTP error: {response.status}", "content": ""}
                        
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract title
                    title = soup.title.string if soup.title else ""
                    
                    # Try to find main content
                    content = ""
                    main_selectors = ['article', 'main', '.post-content', '.entry-content', 
                                      '#content', '.content', '.article', '.post',
                                      '#main-content', '.page-content', '.wiki-body-section',
                                      '#mw-content-text', '.mw-parser-output']
                    
                    for selector in main_selectors:
                        elements = soup.select(selector)
                        if elements:
                            for element in elements:
                                # Skip tiny elements
                                if len(element.get_text()) < 100:
                                    continue
                                    
                                # Remove unwanted elements
                                for tag in element.select('script, style, nav, .nav, footer, .footer, .comment, .sidebar, aside'):
                                    tag.decompose()
                                    
                                element_text = element.get_text(separator=' ', strip=True)
                                if len(element_text) > 200:  # Only use substantial content
                                    content = element_text
                                    break
                        
                        if content:
                            break
                    
                    # Fallback to paragraphs if no content found
                    if not content:
                        paragraphs = []
                        for p in soup.select('p'):
                            p_text = p.get_text(strip=True)
                            if len(p_text) > 40:  # Only include substantial paragraphs
                                paragraphs.append(p_text)
                        
                        if paragraphs:
                            content = ' '.join(paragraphs)
                    
                    # Last resort - get all text from body
                    if not content or len(content) < 200:
                        body = soup.find('body')
                        if body:
                            for tag in body.select('script, style, nav, header, footer'):
                                tag.decompose()
                            content = body.get_text(separator=' ', strip=True)
                    
                    # Clean up content
                    content = re.sub(r'\s+', ' ', content).strip()
                    
                    return {
                        "url": url,
                        "title": title,
                        "content": content,
                        "error": "" if content else "Failed to extract content"
                    }
            except Exception as e:
                logger.error(f"HTTP scraping error for {url}: {str(e)}")
                return {"url": url, "error": str(e), "content": ""}
    
    async def scrape_with_zyte_api(self, url: str) -> Dict[str, Any]:
        """Use Zyte API for medium-complexity sites (faster than Scrapy Cloud)"""
        async with self.zyte_semaphore:
            session = await self.get_session()
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Basic {self.api_key}"
            }
            
            # Zyte API payload with improved settings
            payload = {
                "url": url,
                "browserHtml": True,
                "javascript": True,
                "timeout": 20,
                "actions": [
                    {"action": "waitForSelector", "selector": "article, main, .content, #content, p", "optional": True},
                    {"action": "waitForTimeout", "timeout": 2000}
                ]
            }
            
            try:
                async with session.post(
                    "https://api.zyte.com/v1/extract", 
                    json=payload,
                    headers=headers,
                    timeout=45
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract and clean content from browserHtml
                        if data.get("browserHtml"):
                            html = data.get("browserHtml", "")
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Extract title
                            title = data.get("title", "")
                            if not title and soup.title:
                                title = soup.title.string
                            
                            # Extract main content using same selectors as HTTP scraper
                            content = ""
                            main_selectors = ['article', 'main', '.post-content', '.entry-content', 
                                            '#content', '.content', '.article', '.post']
                            
                            for selector in main_selectors:
                                elements = soup.select(selector)
                                if elements:
                                    for element in elements:
                                        # Remove unwanted elements
                                        for tag in element.select('script, style, nav, footer, aside'):
                                            tag.decompose()
                                            
                                        element_text = element.get_text(separator=' ', strip=True)
                                        if len(element_text) > 200:
                                            content = element_text
                                            break
                                
                                if content:
                                    break
                            
                            # Fallback to paragraphs
                            if not content:
                                paragraphs = []
                                for p in soup.select('p'):
                                    p_text = p.get_text(strip=True)
                                    if len(p_text) > 40:
                                        paragraphs.append(p_text)
                                
                                if paragraphs:
                                    content = ' '.join(paragraphs)
                            
                            # If no content found with selectors or paragraphs, use full text
                            if not content:
                                body = soup.find('body')
                                if body:
                                    # Clean the body
                                    for tag in body.select('script, style, nav, header, footer'):
                                        tag.decompose()
                                    content = body.get_text(separator=' ', strip=True)
                            
                            # Clean up content
                            content = re.sub(r'\s+', ' ', content).strip()
                        else:
                            # Use other fields if browserHtml not available
                            content = data.get("article", {}).get("body", "")
                            title = data.get("article", {}).get("headline", data.get("title", ""))
                        
                        return {
                            "url": url,
                            "title": title,
                            "content": content,
                            "error": ""
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Zyte API error: {response.status}, {error_text[:200]}")
                        return {"url": url, "error": f"API error: {response.status}", "content": ""}
            except Exception as e:
                logger.error(f"Error with Zyte API for {url}: {str(e)}")
                return {"url": url, "error": str(e), "content": ""}
    
    async def scrape_with_scrapy_cloud(self, url: str) -> Dict[str, Any]:
        """Use Scrapy Cloud for complex academic sites (reserve this for hardest sites)"""
        async with self.cloud_semaphore:
            session = await self.get_session()
            job_timestamp = int(time.time())
            job_random = random.randint(10000, 99999)
            unique_job_id = f"{job_timestamp}-{job_random}"
            
            # Prepare request data for Scrapy Cloud
            data = {
                "project": int(self.project_id),
                "spider": "content_spider",
                "jobid": unique_job_id,
                "start_url": url
            }
            
            # API key in URL params
            params = {
                "apikey": self.api_key,
                "spider_args": f"start_url={url}"
            }
            
            try:
                # Submit the job to Scrapy Cloud
                async with session.post(
                    "https://app.zyte.com/api/run.json",
                    data=data,
                    params=params,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        job_id = data.get("jobid")
                        if job_id:
                            logger.info(f"Scheduled Scrapy Cloud job: {job_id} for {url}")
                            
                            # Wait for job to complete
                            job_finished = await self._wait_for_job(job_id)
                            if job_finished:
                                items = await self._get_job_items(job_id)
                                
                                if items:
                                    # Process the first item
                                    if isinstance(items, list):
                                        if items and isinstance(items[0], list):  # Nested list
                                            item = items[0][0] if items[0] else {}
                                        else:  # Flat list
                                            item = items[0] if items else {}
                                    else:
                                        item = {}
                                    
                                    content = item.get("content", "")
                                    title = item.get("title", "")
                                    
                                    if content:
                                        # Clean content
                                        content = self._clean_content(content)
                                    
                                    return {
                                        "url": url,
                                        "title": title,
                                        "content": content,
                                        "error": "" if content else "Empty content from Scrapy Cloud"
                                    }
                                else:
                                    return {"url": url, "error": "No items returned from Scrapy Cloud", "content": ""}
                            else:
                                return {"url": url, "error": "Scrapy Cloud job timed out or failed", "content": ""}
                        else:
                            return {"url": url, "error": "Failed to start Scrapy Cloud job", "content": ""}
                    else:
                        text = await response.text()
                        logger.error(f"Error scheduling spider: {response.status}, {text}")
                        return {"url": url, "error": f"API error: {response.status}", "content": ""}
            except Exception as e:
                logger.error(f"Exception in Scrapy Cloud scraping: {str(e)}")
                return {"url": url, "error": str(e), "content": ""}

    def _clean_content(self, content: str) -> str:
        """Clean content by removing boilerplate and normalizing spacing"""
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Remove common boilerplate text
        patterns_to_remove = [
            r'Copyright ©.*?(\.|$)',
            r'All rights reserved\.?',
            r'Terms (of|and) (use|service|conditions).*?(\.|$)',
            r'Privacy Policy\.?',
            r'Cookie Policy\.?',
            r'\d+ views',
            r'\d+ comments',
            r'Share this:',
            r'Follow us on:',
            r'Last updated:.*?(\.|$)'
        ]
        
        for pattern in patterns_to_remove:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        return content.strip()

    async def _wait_for_job(self, job_id: str, timeout: int = 90) -> bool:
        """Wait for a Scrapy Cloud job to complete"""
        start_time = time.time()
        polling_interval = 2  # Start with 2 seconds
        
        while (time.time() - start_time) < timeout:
            status = await self._check_job_status(job_id)
            
            if status == "finished":
                return True
            elif status in ["error", "deleted", "failed"]:
                return False
                
            # Wait before polling again
            await asyncio.sleep(polling_interval)
            # Increase polling interval up to 10 seconds
            polling_interval = min(10, polling_interval * 1.5)
        
        return False  # Timeout

    async def _check_job_status(self, job_id: str) -> str:
        """Check status of a Scrapy Cloud job"""
        session = await self.get_session()
        
        params = {
            "apikey": self.api_key,
            "project": self.project_id,
            "job": job_id
        }
        
        try:
            async with session.get(
                "https://app.zyte.com/api/jobs/list.json",
                params=params,
                timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    jobs = data.get("jobs", [])
                    if jobs:
                        return jobs[0].get("state", "unknown")
                    return "not_found"
                else:
                    logger.error(f"Error checking job status: {response.status}")
                    return "error"
        except Exception as e:
            logger.error(f"Exception checking job status: {str(e)}")
            return "error"

    async def _get_job_items(self, job_id: str) -> List[Dict]:
        """Get items from a completed Scrapy Cloud job"""
        session = await self.get_session()
        
        # Format the storage job ID correctly
        storage_job_id = f"{self.project_id}/{job_id}" if "/" not in job_id else job_id
        
        params = {
            "apikey": self.api_key,
            "format": "json"
        }
        
        try:
            async with session.get(
                f"https://storage.scrapinghub.com/items/{storage_job_id}",
                params=params,
                timeout=15
            ) as response:
                if response.status == 200:
                    text = await response.text()
                    
                    # Parse JSONL format
                    items = []
                    for line in text.strip().split('\n'):
                        if not line.strip():
                            continue
                        try:
                            items.append(json.loads(line))
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse item: {line[:100]}...")
                    
                    return items
                else:
                    logger.error(f"Error getting job items: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Exception getting job items: {str(e)}")
            return []

    async def _scrape_with_fallback_chain(self, url: str, methods: List[Callable]) -> Dict[str, Any]:
        """Try multiple scraping methods in sequence until one succeeds"""
        last_error = None
        
        for method in methods:
            try:
                result = await method(url)
                if result and result.get("content") and len(result.get("content", "")) > 200:
                    # Found valid content
                    return result
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Method {method.__name__} failed for {url}: {str(e)}")
                continue
        
        # All methods failed
        return {"url": url, "error": f"All methods failed: {last_error}", "content": ""}

    async def _http_scrape(self, url: str) -> Dict[str, Any]:
        """Basic HTTP scraping for standard sites"""
        return await self.scrape_with_http(url)

    async def _scientific_http_scrape(self, url: str) -> Dict[str, Any]:
        """Specialized HTTP scraping for scientific content"""
        async with self.http_semaphore:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://scholar.google.com/",  # Important for academic sites
                "DNT": "1",  # Do Not Track
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "cross-site",
                "Sec-Fetch-User": "?1"
            }
            
            session = await self.get_session()
            try:
                # Add timeout and allow redirects
                async with session.get(url, headers=headers, timeout=45, allow_redirects=True) as response:
                    if response.status != 200:
                        return {"url": url, "error": f"HTTP error: {response.status}", "content": ""}
                        
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    title = soup.title.string if soup.title else ""
                    content = ""
                    
                    # Academic-specific content selectors (expanded)
                    academic_selectors = [
                        'article', '.article', '.article-body', '.paper', '.content-block',
                        '#content', '.content', '.main-content', '.article-content',
                        '.publication-content', '.research-article', '.fulltext-view',
                        '.article-fulltext', '.article__body', '.article__sections',
                        '#main-content', '.section-container', '.page-content',
                        '#abstract', '.abstract', '.abstractSection', '.abstract-content',
                        '#body', '.body', '.fulltext', '.full-text', '#full-text-content',
                        '.article-text', '.article-section__content', '.article-section'
                    ]
                    
                    # Try to find the content with multiple approaches
                    # 1. First try specific selectors
                    for selector in academic_selectors:
                        elements = soup.select(selector)
                        if elements:
                            for element in elements:
                                # Remove unwanted elements
                                for unwanted in element.select('nav, .nav, header, footer, .header, .footer, .figure, .fig, .author-info, .references, aside, .aside, .metrics, .extra, .supplementary, .article-tools'):
                                    if unwanted:
                                        unwanted.decompose()
                                
                                # Extract paragraphs for better text quality
                                paragraphs = [p.get_text(strip=True) for p in element.select('p')]
                                if paragraphs and sum(len(p) for p in paragraphs) > 200:
                                    content = ' '.join(paragraphs)
                                    break
                                else:
                                    content = element.get_text(strip=True)
                                    
                            if content and len(content) > 200:
                                break
                    
                    # 2. If no content found, try getting all paragraphs
                    if not content or len(content) < 200:
                        paragraphs = []
                        for p in soup.select('p'):
                            p_text = p.get_text(strip=True)
                            if len(p_text) > 30:  # More lenient for academic content
                                paragraphs.append(p_text)
                        
                        if paragraphs:
                            content = ' '.join(paragraphs)
                    
                    # 3. If still no content, try div elements with substantial text
                    if not content or len(content) < 200:
                        for div in soup.select('div'):
                            div_text = div.get_text(strip=True)
                            if len(div_text) > 500:  # Look for divs with substantial content
                                content = div_text
                                break
                    
                    # Clean up content
                    content = re.sub(r'\s+', ' ', content).strip()
                    
                    # Debug log length of extracted content
                    logger.info(f"Extracted {len(content)} chars from academic URL: {url}")
                    
                    return {
                        "url": url,
                        "title": title,
                        "content": content,
                        "error": "" if content else "Failed to extract scientific content"
                    }
            except Exception as e:
                logger.error(f"Scientific HTTP scraping error for {url}: {str(e)}")
                return {"url": url, "error": str(e), "content": ""}

    async def _zyte_scrape(self, url: str) -> Dict[str, Any]:
        """Use Zyte API with concurrency control"""
        async with self.zyte_semaphore:
            return await self.scrape_with_zyte_api(url)

    async def _playwright_scrape(self, url: str) -> Dict[str, Any]:
        """Attempt to use Playwright if available"""
        try:
            # Check if playwright is available
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                try:
                    await page.goto(url, timeout=30000)
                    await page.wait_for_load_state("networkidle")
                    
                    # Extract content after JavaScript has rendered
                    html = await page.content()
                    title = await page.title()
                    
                    # Extract main content using DOM
                    content_selectors = ['article', 'main', '#content', '.content']
                    content = ""
                    
                    for selector in content_selectors:
                        try:
                            element = await page.query_selector(selector)
                            if element:
                                content = await element.text_content()
                                if len(content) > 500:  # Found substantial content
                                    break
                        except:
                            pass
                    
                    # If no content found from selectors, extract body text
                    if not content:
                        body = await page.query_selector('body')
                        if body:
                            content = await body.text_content()
                    
                    await browser.close()
                    return {
                        "url": url,
                        "title": title,
                        "content": content,
                        "error": ""
                    }
                    
                except Exception as e:
                    await browser.close()
                    raise e
        except ImportError:
            logger.warning("Playwright not available for scraping")
            return {"url": url, "error": "Playwright not available", "content": ""}
        except Exception as e:
            logger.error(f"Error with Playwright scraping: {str(e)}")
            return {"url": url, "error": str(e), "content": ""}

    def classify_website(self, url: str) -> str:
        """Classify websites to determine the best scraping approach"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        path = parsed_url.path.lower()
        
        # 1. TLD-based classification
        scientific_tlds = ['.edu', '.ac.uk', '.ac.jp', '.ac.', '.research.']
        if any(tld in domain for tld in scientific_tlds):
            return 'scientific'
            
        # 2. Domain name pattern matching (scientific publishers)
        scientific_patterns = [
            'science', 'research', 'journal', 'academic', 'scholar', 
            'university', 'institute', 'lab', 'proceedings', 'publications',
            'springer', 'wiley', 'elsevier', 'nature', 'cell', 'pubmed', 
            'sciencedirect', 'frontiers', 'arxiv', 'ieee', 'acm', 'jstor'
        ]
        
        if any(pattern in domain for pattern in scientific_patterns):
            return 'scientific'
            
        # 3. URL path analysis
        scientific_paths = [
            '/article/', '/journal/', '/abstract/', '/doi/', '/publication/', 
            '/paper/', '/research/', '/science/', '/content/', '/fulltext/'
        ]
        
        if any(sci_path in path for sci_path in scientific_paths):
            return 'scientific'
        
        # 4. News site detection
        news_patterns = [
            'news', 'times', 'post', 'tribune', 'herald', 
            'guardian', 'bbc', 'cnn', 'nyt', 'reuters', 'bloomberg'
        ]
        
        if any(pattern in domain for pattern in news_patterns):
            return 'news'
        
        # 5. Complex site detection (JavaScript-heavy sites)
        complex_patterns = [
            'angular', 'react', 'vue', 'spa', 'dashboard', 'app.',
            'facebook', 'twitter', 'linkedin', 'instagram', 'youtube'
        ]
        
        if any(pattern in domain or pattern in path for pattern in complex_patterns):
            return 'complex'
            
        # Default to standard
        return 'standard'

async def scrape_urls_in_parallel(self, urls: List[str], max_concurrent: int = 3) -> List[Dict[str, Any]]:
    """Scrape multiple URLs in parallel with optimal service selection"""
    from app.services.worker_pool import ScraperWorkerPool
    
    # Use worker pool for better performance and stability
    worker_pool = ScraperWorkerPool(max_workers=max_concurrent, max_per_domain=2)
    results = []
    
    async def scrape_url_with_strategy(url: str) -> Dict[str, Any]:
        """Select and apply the best strategy for each URL"""
        # First check cache
        cached_content = self.cache.get_content(url)
        if cached_content:
            logger.info(f"Cache hit for {url}")
            return cached_content
            
        # Use specialized scientific scraping for academic sites
        site_type = self.classify_website(url)
        logger.info(f"Classified {url} as {site_type}")
        
        if site_type == 'scientific':
            try:
                # Try direct scientific scraping first as it's faster
                result = await self._scientific_http_scrape(url)
                if result and result.get("content") and len(result.get("content", "")) > 300:
                    logger.info(f"Scientific scraping succeeded for {url}")
                    return result
                    
                # If direct scraping failed or returned limited content, try Zyte API
                if self.api_key and not self.api_key.startswith('ENTER_YOUR'):
                    result = await self.scrape_with_zyte_api(url)
                    if result and result.get("content") and len(result.get("content", "")) > 300:
                        return result
                
                # As last resort for academic content, try basic HTTP
                return await self._http_scrape(url)
                
            except Exception as e:
                logger.error(f"Error scraping academic content from {url}: {str(e)}")
                # Fallback to basic HTTP scraping
                return await self._http_scrape(url)
        else:
            # For non-academic content use standard approach
            return await self.scrape_with_optimal_service(url)
    
    # Process URLs with worker pool
    # This approach is more stable than using as_completed directly
    results = await worker_pool.scrape_urls(urls, scrape_url_with_strategy)
    
    # Filter out results without content
    valid_results = [r for r in results if r and r.get("content") and len(r.get("content", "")) > 200]
    logger.info(f"Successfully scraped {len(valid_results)} out of {len(urls)} URLs")
    
    return valid_results