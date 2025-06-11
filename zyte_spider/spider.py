# spider.py
import scrapy
from bs4 import BeautifulSoup
import logging

class ContentSpider(scrapy.Spider):
    name = "content_spider"
    
    def __init__(self, start_url=None, *args, **kwargs):
        super(ContentSpider, self).__init__(*args, **kwargs)
        # Log the received URL for debugging
        self.logger.info(f"Spider initialized with URL: {start_url}")
        
        if start_url and start_url.startswith("http"):
            self.start_urls = [start_url]
        else:
            self.logger.error(f"Invalid or missing start_url: {start_url}")
            # Don't use example.com, this causes confusion
            self.start_urls = []
    
    def start_requests(self):
        """Override to better handle empty URLs"""
        if not self.start_urls:
            self.logger.error("No valid start URLs provided, spider will finish without requests")
            return
            
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse)
    
    def parse(self, response):
        # Log successful request
        self.logger.info(f"Processing URL: {response.url}")
        
        # Get page content using various selectors
        main_content = response.css('article, main, .content, #content, .post, .entry').get()
        
        if main_content:
            # Clean HTML
            soup = BeautifulSoup(main_content, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            content = soup.get_text(' ', strip=True)
        else:
            # Fallback to paragraphs
            paragraphs = response.css('p::text').getall()
            content = ' '.join(paragraphs)
        
        yield {
            "url": response.url,
            "title": response.css('title::text').get(),
            "content": content
        }