import azure.functions as func
import logging
from app import app  # Import your existing FastAPI app
import json
import asyncio

# Azure Functions entry point
async def main(req: func.HttpRequest) -> func.HttpResponse:
    # Get the path from the request
    route = req.route_params.get('route', '')
    path = f"/{route}" if route else "/"
    
    # Create a FastAPI-compatible request scope
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": req.method,
        "scheme": "https",
        "path": path,
        "raw_path": path.encode(),
        "query_string": req.url.split('?')[1].encode() if '?' in req.url else b'',
        "headers": [[k.lower().encode(), v.encode()] for k, v in req.headers.items()],
        "server": ("azure-functions", "123"),
        "client": ("0.0.0.0", 0)
    }
    
    # Handle body
    body = req.get_body() or b''
    
    # Create response objects
    response = {}
    response_status = 200
    response_headers = {}
    
    # Process the request with FastAPI
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    async def send(message):
        nonlocal response, response_status, response_headers
        if message["type"] == "http.response.start":
            response_status = message["status"]
            response_headers = {k.decode(): v.decode() for k, v in message["headers"]}
        elif message["type"] == "http.response.body":
            response = message.get("body", b"")
    
    # Call the FastAPI application
    await app(scope, receive, send)
    
    # Return Azure Functions response
    return func.HttpResponse(
        response,
        status_code=response_status,
        headers=response_headers,
        mimetype=response_headers.get("content-type", "text/plain")
    )