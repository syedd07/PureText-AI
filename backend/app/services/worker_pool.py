# backend/app/services/worker_pool.py
import asyncio
from typing import List, Dict, Any, Callable, Awaitable
import random
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class ScraperWorkerPool:
    """Manages parallel scraping with intelligent work distribution"""
    
    def __init__(self, max_workers=12, max_per_domain=2):
        self.max_workers = max_workers
        self.max_per_domain = max_per_domain
        self.domain_semaphores = {}
        self.global_semaphore = asyncio.Semaphore(max_workers)
    
    async def scrape_urls(self, 
                        urls: List[str], 
                        scrape_func: Callable[[str], Awaitable[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Scrape multiple URLs in parallel with domain rate limiting"""
        results = []
        tasks = []
        
        # Group URLs by domain for better distribution
        domain_groups = {}
        for url in urls:
            domain = urlparse(url).netloc
            if domain not in domain_groups:
                domain_groups[domain] = []
            domain_groups[domain].append(url)
        
        # Create domain semaphores if needed
        for domain in domain_groups:
            if domain not in self.domain_semaphores:
                self.domain_semaphores[domain] = asyncio.Semaphore(self.max_per_domain)
        
        # Process high-value domains first (academic, news, etc.)
        priority_domains = ['sciencedirect.com', 'springer.com', 'wiley.com', 'ncbi.nlm.nih.gov']
        
        # Sort domain groups by priority
        sorted_domains = sorted(
            domain_groups.keys(),
            key=lambda d: sum(1 for pd in priority_domains if pd in d),
            reverse=True
        )
        
        # Create tasks with domain-based rate limiting
        for domain in sorted_domains:
            for url in domain_groups[domain]:
                task = asyncio.create_task(self._scrape_with_semaphores(
                    url, 
                    scrape_func, 
                    self.domain_semaphores[domain]
                ))
                tasks.append(task)
        
        # Wait for all tasks with progressive results
        for completed in asyncio.as_completed(tasks):
            try:
                result = await completed
                if result and result.get("content"):
                    results.append(result)
                    logger.info(f"Completed scraping: {result.get('url')}")
            except Exception as e:
                logger.error(f"Task error: {str(e)}")
        
        return results
    
    async def _scrape_with_semaphores(self, 
                                    url: str, 
                                    scrape_func: Callable[[str], Awaitable[Dict[str, Any]]], 
                                    domain_semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        """Execute a scrape operation with both global and domain-specific rate limiting"""
        # Use both global worker limit and domain-specific limit
        async with self.global_semaphore:
            async with domain_semaphore:
                # Add jitter to avoid thundering herd
                await asyncio.sleep(random.uniform(0.1, 0.5))
                return await scrape_func(url)