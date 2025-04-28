import azure.functions as func
import logging
import json
from app_proxy import app  # Use proxy import instead

async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Functions entry point that wraps FastAPI app
    """
    logging.info('Python HTTP trigger function processed a request.')
    
    # Get the request body
    body = req.get_body()
    
    # Convert Azure Function request to FastAPI compatible format
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": req.method,
        "scheme": "https",
        "path": "/analyze",  # Match the route from function.json
        "query_string": req.params,
        "headers": [[k.encode(), v.encode()] for k, v in req.headers.items()],
        "server": ("azure-functions", "1.0"),
        "client": ("0.0.0.0", 0),
    }
    
    # Response objects
    response_body = []
    response_status = None
    response_headers = []
    
    # Create ASGI-compatible callbacks
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    
    async def send(message):
        nonlocal response_body, response_status, response_headers
        if message["type"] == "http.response.start":
            response_status = message["status"]
            response_headers = message.get("headers", [])
        elif message["type"] == "http.response.body":
            response_body.append(message.get("body", b""))
    
    # Process the request through FastAPI
    await app(scope, receive, send)
    
    # Convert headers to dict for Azure Functions
    headers = {k.decode(): v.decode() for k, v in response_headers}
    
    # Return Azure Functions HTTP response
    return func.HttpResponse(
        body=b"".join(response_body),
        status_code=response_status,
        headers=headers,
        mimetype=headers.get("content-type", "application/json")
    )