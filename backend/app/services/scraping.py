from typing import List, Dict, Any
import base64
import requests
import json
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from app.core.config import settings
# Import the correct client
# from zyte_api import client

# # Initialize Zyte client with your API key
# zyte_client = client.ScraperClient(api_key=settings.ZYTE_API_KEY)

async def search_relevant_content(themes: List[str], max_results: int = 10) -> List[str]:
    """
    Search for relevant content based on themes
    
    Args:
        themes: List of themes to search for
        max_results: Maximum number of results to return
        
    Returns:
        List of URLs to relevant content
    """
    # In a production app, you'd use a search API here
    # For now, we'll generate plausible sample URLs based on themes
    urls = []
    
    for theme in themes:
        clean_theme = theme.lower().replace(' ', '-')
        urls.extend([
            f"https://en.wikipedia.org/wiki/{clean_theme}",
            f"https://www.sciencedaily.com/terms/{clean_theme}.htm",
            f"https://www.researchgate.net/topic/{clean_theme}"
        ])
    
    # Return only the requested number of results
    return urls[:max_results]

async def scrape_multiple_content(urls: List[str]) -> List[Dict[str, Any]]:
    """
    Scrape content from multiple URLs
    """
    results = []
    for url in urls:
        try:
            content = await scrape_content(url)
            if content:
                results.append({
                    "url": url,
                    "content": content
                })
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
    
    return results

async def scrape_content(url: str) -> str:
    """
    Scrape content using Zyte API with the correct request format
    """
    zyte_api_url = "https://api.zyte.com/v1/extract"
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"  # Add this header
    }
    
    payload = {
        "url": url,
        "browserHtml": True  # Keep it simple, remove article parameter
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Use BasicAuth directly instead of constructing the header manually
            auth = aiohttp.BasicAuth(login=settings.ZYTE_API_KEY, password="")
            
            async with session.post(
                zyte_api_url, 
                json=payload,  # Use json parameter, not data
                headers=headers,
                auth=auth
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Process HTML response
                    if data and data.get('browserHtml'):
                        soup = BeautifulSoup(data['browserHtml'], 'html.parser')
                        for script in soup(["script", "style"]):
                            script.decompose()
                        text = soup.get_text()
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        return '\n'.join(chunk for chunk in chunks if chunk)
                
                print(f"Error using Zyte API: {response.status}")
                return ""
    except Exception as e:
        print(f"Exception when using Zyte API: {str(e)}")
        return ""
        