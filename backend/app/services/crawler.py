import asyncio
from typing import List, Dict, Any
from urllib.parse import quote_plus
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

async def crawl_search_results(query: str, max_pages: int = 5) -> List[Dict[str, Any]]:
    """Use Playwright to execute JS and crawl search results pages"""
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        page = await context.new_page()
        
        # Search Google
        await page.goto(f"https://www.google.com/search?q={quote_plus(query)}")
        await page.wait_for_load_state("networkidle")
        
        # Extract results
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        for result in soup.select(".g")[:max_pages]:
            link = result.select_one("a")
            if not link:
                continue
                
            href = link.get("href", "")
            if href.startswith("/url?q="):
                href = href[7:].split("&")[0]
            elif not href.startswith("http"):
                continue
                
            title = result.select_one("h3")
            if title:
                # Visit the page to extract content
                try:
                    result_page = await context.new_page()
                    await result_page.goto(href, timeout=30000)
                    await result_page.wait_for_load_state("networkidle")
                    
                    page_content = await result_page.content()
                    await result_page.close()
                    
                    results.append({
                        "url": href,
                        "title": title.text,
                        "html": page_content
                    })
                    
                    if len(results) >= max_pages:
                        break
                except Exception as e:
                    logger.error(f"Error visiting {href}: {str(e)}")
        
        await browser.close()
    
    return results