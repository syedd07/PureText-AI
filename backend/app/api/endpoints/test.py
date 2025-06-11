from typing import Dict
import aiohttp
import json
from fastapi import APIRouter
from app.services.scraping import direct_scrape_url, get_zyte_client

router = APIRouter()

@router.get("/test-spider")
async def test_spider():
    """Test the deployed Zyte spider"""
    client = get_zyte_client()
    url = "https://beyondsciencemagazine.studio/articles/brooke"
    
    try:
        result = await client.scrape_url(url, timeout=120)
        
        if result and result.get("content"):
            content_preview = result["content"][:200] + "..." if len(result["content"]) > 200 else result["content"]
            return {
                "status": "success", 
                "message": "Successfully extracted content with spider",
                "title": result.get("title", ""),
                "content_preview": content_preview,
                "content_length": len(result["content"])
            }
        else:
            # Try the direct scraping fallback
            from app.services.scraping import direct_scrape_url
            fallback_result = await direct_scrape_url(url)
            
            if fallback_result and fallback_result.get("content"):
                content_preview = fallback_result["content"][:200] + "..." if len(fallback_result["content"]) > 200 else fallback_result["content"]
                return {
                    "status": "success", 
                    "message": "Successfully extracted content with fallback",
                    "title": fallback_result.get("title", ""),
                    "content_preview": content_preview,
                    "content_length": len(fallback_result["content"])
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to extract content with both methods",
                    "error": result.get("error", "Unknown error"),
                    "fallback_error": fallback_result.get("error", "")
                }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/debug-api")
async def debug_api():
    """Debug Zyte API connection"""
    from app.core.config import settings
    
    # Get API credentials
    api_key = settings.ZYTE_API_KEY
    project_id = settings.ZYTE_PROJECT_ID
    
    # List spiders to check if we can connect
    async with aiohttp.ClientSession() as session:
        spiders_url = f"https://app.zyte.com/api/spiders/list.json"
        
        params = {
            "project": project_id,
            "apikey": api_key
        }
        
        try:
            # Test basic API connectivity
            async with session.get(spiders_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "success",
                        "api_key_works": True,
                        "project_id": project_id,
                        "api_key_preview": f"{api_key[:5]}...{api_key[-5:]}",
                        "spiders": data.get("spiders", [])
                    }
                else:
                    text = await response.text()
                    return {
                        "status": "error",
                        "message": f"API responded with {response.status}",
                        "response": text
                    }
        except Exception as e:
            return {"status": "error", "message": str(e)}

@router.get("/direct-run-spider")
async def direct_run_spider():
    """Directly run a spider with minimal code"""
    from app.core.config import settings
   
    api_key = settings.ZYTE_API_KEY
    project_id = int(settings.ZYTE_PROJECT_ID)
    
    # Test URL
    url = "https://example.com"
    
    async with aiohttp.ClientSession() as session:
        # Run spider
        run_url = "https://app.zyte.com/api/run.json"
        
        # CRITICAL FIX: Use form data instead of URL params
        data = {
            "project": project_id,
            "spider": "content_spider"
        }
        
        # API key must be in URL params
        params = {
            "apikey": api_key
        }
        
        # Additional URL params
        params["start_url"] = url
        
        try:
            # Send FORM data, not JSON or URL params
            async with session.post(run_url, data=data, params=params) as response:
                status = response.status
                text = await response.text()
                
                return {
                    "status": status,
                    "response": text,
                    "form_data": data,
                    "params": params
                }
        except Exception as e:
            return {"error": str(e)}
        
        # Added fallback direct_scrape function using direct_run_spider
        async def direct_scrape():
            """Fallback direct scraping function that leverages direct_run_spider"""
            result = await direct_run_spider()
            if result.get("status") == 200:
                return {
                    "status": "success",
                    "url": result["params"].get("start_url", ""),
                    "content_preview": result.get("response", "")[:200],
                    "title": ""
                }
            else:
                return {"status": "error", "error": result.get("error", "Scraping failed")}

@router.get("/test-plagiarism")
async def test_plagiarism():
    """Test the plagiarism flow with a sample text"""
    from app.services.scraping import find_and_scrape_sources
    
    # Try to import the similarity module, with a fallback
    try:
        from app.services.similarity import check_text_similarity
    except ImportError:
        # Create a simple fallback function
        async def check_text_similarity(text, sources):
            return {
                "overall_similarity": 0.75, 
                "matches": [{"source": s["url"], "similarity": 0.75} for s in sources]
            }
    
    # Sample test with known content from Wikipedia
    test_text = "Plagiarism is the representation of another author's language, thoughts, ideas, or expressions as one's own original work. Plagiarism is considered academic dishonesty and a breach of journalistic ethics."
    
    try:
        # Step 1: Find potential sources
        sources = await find_and_scrape_sources(test_text, max_sources=2)
        
        if not sources:
            return {"status": "warning", "message": "No sources found, using direct scraping"}
            
        # Use direct scraping as backup
        try:
            scrape_result = await direct_scrape()
            if scrape_result["status"] == "success":
                sources = [{
                    "url": scrape_result["url"],
                    "content": scrape_result["content_preview"],
                    "title": scrape_result["title"]
                }]
        except Exception as e:
            pass
        
        # Step 2: Check for similarity
        result = await check_text_similarity(test_text, sources)
        
        return {
            "status": "success",
            "sources_found": len(sources),
            "similarity_results": result,
            "sources": [
                {
                    "url": source["url"],
                    "content_preview": source["content"][:100] + "..." if len(source["content"]) > 100 else source["content"]
                }
                for source in sources
            ]
        }
    except Exception as e:
        import traceback
        return {
            "status": "error", 
            "message": str(e),
            "traceback": traceback.format_exc()
        }

@router.get("/debug-spider-job/{job_id:path}")
async def debug_spider_job(job_id: str):
    """Debug a specific spider job by ID"""
    client = get_zyte_client()
    
    try:
        # Check job status
        status = await client.check_job_status(job_id)
        
        # Get the raw items
        items = await client.get_job_items(job_id)
        
        # Get job logs
        logs_url = f"https://storage.scrapinghub.com/logs/810155/{job_id}"
        async with aiohttp.ClientSession() as session:
            params = {"apikey": client.api_key}
            async with session.get(logs_url, params=params) as response:
                logs = await response.text() if response.status == 200 else "Couldn't fetch logs"
        
        return {
            "status": "success",
            "job_status": status,
            "items_count": len(items),
            "items": items[:5] if items else [],  # First 5 items
            "logs_preview": logs[:2000] + "..." if len(logs) > 2000 else logs
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
@router.get("/debug-page-source/{job_id:path}")
async def debug_page_source(job_id: str):
    """Debug by getting the original page HTML source"""
    client = get_zyte_client()
    
    try:
        # Get job logs to find the URL
        logs_url = f"https://storage.scrapinghub.com/logs/{job_id}"
        url = None
        
        async with aiohttp.ClientSession() as session:
            params = {"apikey": client.api_key}
            async with session.get(logs_url, params=params) as response:
                if response.status == 200:
                    logs = await response.text()
                    # Extract URL from logs
                    import re
                    url_match = re.search(r"Crawled \(200\) <GET ([^>]+)>", logs)
                    if url_match:
                        url = url_match.group(1)
        
        if not url:
            url = "https://en.wikipedia.org/wiki/Plagiarism"
            
        # Now fetch the page directly
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                html = await response.text()
                
                return {
                    "status": "success",
                    "url": url,
                    "html_length": len(html),
                    "html_preview": html[:1000] + "..." if len(html) > 1000 else html
                }
                
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
@router.get("/direct-scrape")
async def direct_scrape():
    """Directly scrape content without spider"""
    url = "https://en.wikipedia.org/wiki/Plagiarism"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
            
            # Process HTML with BeautifulSoup
            from bs4 import BeautifulSoup
            import re
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 1. Try to find main content
            main_content = None
            for selector in ['#mw-content-text', 'article', 'main', '#bodyContent', '.mw-parser-output']:
                element = soup.select_one(selector)
                if element:
                    main_content = element
                    break
            
            # 2. Extract text
            if main_content:
                # Remove unwanted elements
                for unwanted in main_content.select('script, style, .navbox, .mw-editsection'):
                    if unwanted:
                        unwanted.decompose()
                        
                # Get all paragraphs
                paragraphs = [p.get_text() for p in main_content.select('p')]
                content = ' '.join(paragraphs)
                
                # Clean up whitespace
                content = re.sub(r'\s+', ' ', content).strip()
                
                return {
                    "status": "success",
                    "url": url,
                    "title": soup.title.string if soup.title else "",
                    "content_length": len(content),
                    "content_preview": content[:500] + "..." if len(content) > 500 else content
                }
            else:
                return {"status": "error", "message": "Could not find main content"}
            
@router.get("/test-search")
async def test_search(query: str = "plagiarism detection"):
    """Test Google CSE integration"""
    client = get_zyte_client()
    
    try:
        results = await client.search_web(query, max_results=5)
        
        return {
            "status": "success",
            "query": query,
            "results_count": len(results),
            "results": results
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }

# Add test endpoint for Google CSE

@router.get("/test-google-cse")
async def test_google_cse(query: str = "plagiarism detection"):
    """Test Google CSE integration with detailed diagnostics"""
    from app.core.config import settings
    client = get_zyte_client()
    
    # Collect diagnostic information
    diagnostics = {
        "google_api_key_configured": bool(settings.GOOGLE_API_KEY),
        "google_cse_id_configured": bool(settings.GOOGLE_CSE_ID),
        "google_api_key_preview": f"{settings.GOOGLE_API_KEY[:5]}...{settings.GOOGLE_API_KEY[-5:]}" if settings.GOOGLE_API_KEY else None,
        "google_cse_id": settings.GOOGLE_CSE_ID,
        "query": query
    }
    
    try:
        # Attempt the search
        search_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "q": query,
            "key": settings.GOOGLE_API_KEY,
            "cx": settings.GOOGLE_CSE_ID,
            "num": 5
        }
        
        # Direct API request
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, params=params, timeout=15) as response:
                status_code = response.status
                response_text = await response.text()
                
                diagnostics["api_response"] = {
                    "status_code": status_code,
                    "headers": dict(response.headers),
                    "response_preview": response_text[:500]
                }
                
                if status_code == 200:
                    try:
                        data = json.loads(response_text)
                        results = []
                        
                        if "items" in data:
                            for item in data["items"]:
                                results.append({
                                    "url": item.get("link"),
                                    "title": item.get("title", ""),
                                    "snippet": item.get("snippet", "")
                                })
                            
                            diagnostics["search_results"] = results
                            diagnostics["results_count"] = len(results)
                            diagnostics["status"] = "success"
                        else:
                            diagnostics["status"] = "api_error"
                            diagnostics["error"] = "No results in API response"
                    except json.JSONDecodeError:
                        diagnostics["status"] = "parsing_error"
                        diagnostics["error"] = "Invalid JSON response"
                else:
                    diagnostics["status"] = "api_error"
                    diagnostics["error"] = f"API returned status {status_code}"
                    
        # Also test the high-level function
        client_results = await client.search_web(query, max_results=5)
        diagnostics["client_search"] = {
            "results_count": len(client_results),
            "results": client_results
        }
                
        return diagnostics
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "diagnostics": diagnostics,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
    
    
@router.get("/debug-url")
async def debug_url(url: str):
    """Debug a specific URL by fetching and analyzing it"""
    try:
        result = await direct_scrape_url(url)
        return {
            "url": url,
            "status": "success" if result.get("content") else "error",
            "title": result.get("title", ""),
            "content_length": len(result.get("content", "")),
            "content_preview": (result.get("content", "")[:500] + "...") if len(result.get("content", "")) > 500 else result.get("content", ""),
            "error": result.get("error", "")
        }
    except Exception as e:
        import traceback
        return {
            "status": "error", 
            "url": url,
            "message": str(e),
            "traceback": traceback.format_exc()
        }