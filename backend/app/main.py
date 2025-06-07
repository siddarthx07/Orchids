import os
import uuid
import json
import requests
import asyncio
from typing import Dict, Optional, List, Set
from datetime import datetime
from urllib.parse import urlparse

from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
import io

from .models import CloneRequestModel, CloneResponseModel, CloneResultModel
from .scraper import WebsiteScraper
from .llm import WebsiteCloner

# In-memory storage for cloning requests
# In a production app, this would be a database
clone_requests: Dict[str, Dict] = {}

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        # requestId -> Set of connected websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, request_id: str):
        await websocket.accept()
        if request_id not in self.active_connections:
            self.active_connections[request_id] = set()
        self.active_connections[request_id].add(websocket)
        
    def disconnect(self, websocket: WebSocket, request_id: str):
        if request_id in self.active_connections:
            self.active_connections[request_id].discard(websocket)
            if not self.active_connections[request_id]:
                del self.active_connections[request_id]
        
    async def broadcast_status(self, request_id: str, data: dict):
        if request_id in self.active_connections:
            disconnected_websockets = set()
            for websocket in self.active_connections[request_id]:
                try:
                    await websocket.send_json(data)
                except Exception:
                    disconnected_websockets.add(websocket)
            
            # Clean up any disconnected websockets
            for ws in disconnected_websockets:
                self.disconnect(ws, request_id)

manager = ConnectionManager()

app = FastAPI(
    title="Website Cloning API",
    description="API for cloning websites using Browserbase SDK with Playwright and Gemini 1.5 Pro",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    # Allow requests from any localhost port
    allow_origins=["http://localhost:3000", "http://localhost:3002", "http://localhost", "http://127.0.0.1", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root():
    """Root endpoint"""
    return {"message": "Website Cloning API is running"}


@app.post("/api/clone", response_model=CloneResponseModel)
async def clone_website(request: CloneRequestModel, background_tasks: BackgroundTasks):
    """Initiate a website cloning process"""
    request_id = str(uuid.uuid4())
    
    # Store initial request data
    clone_requests[request_id] = {
        "request_id": request_id,
        "status": "pending",
        "url": request.url,
        "submitted_at": datetime.now().isoformat(),
        "options": request.options,
        "result": None
    }
    
    # Start background task for cloning
    background_tasks.add_task(
        process_clone_request,
        request_id=request_id,
        url=request.url,
        options=request.options
    )
    
    return {
        "request_id": request_id,
        "status": "pending",
        "url": request.url
    }


@app.get("/api/clone/{request_id}", response_model=CloneResultModel)
async def get_clone_result(request_id: str):
    """Get the result of a cloning request"""
    if request_id not in clone_requests:
        raise HTTPException(status_code=404, detail="Clone request not found")
    
    request_data = clone_requests[request_id]
    result = request_data.get("result", {}) or {}
    
    return {
        "request_id": request_id,
        "status": request_data["status"],
        "url": request_data["url"],
        "cloned_html": result.get("cloned_html"),
        "error": result.get("error"),
        "metadata": result.get("metadata")
    }


@app.get("/api/clone/{request_id}/html", response_class=HTMLResponse)
async def get_clone_html(request_id: str):
    """Get the cloned HTML directly"""
    if request_id not in clone_requests:
        raise HTTPException(status_code=404, detail="Clone request not found")
    
    request_data = clone_requests[request_id]
    
    if request_data["status"] != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Clone request is not completed (status: {request_data['status']})"
        )
    
    result = request_data.get("result", {}) or {}
    cloned_html = result.get("cloned_html")
    if not cloned_html:
        raise HTTPException(status_code=400, detail="No HTML content available")
    
    return cloned_html


@app.get("/api/clone/{request_id}/{asset_path:path}")
async def get_asset(request_id: str, asset_path: str):
    """Proxy assets from the original website"""
    try:
        # Get the original URL from the clone request
        if request_id not in clone_requests:
            raise HTTPException(status_code=404, detail="Clone request not found")
            
        request_data = clone_requests[request_id]
        original_url = request_data.get("url", "")
        if not original_url:
            raise HTTPException(status_code=404, detail="Original URL not found")
            
        # Extract the base URL (domain) from the original URL
        parsed_url = urlparse(original_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Request the asset from the original website
        asset_url = f"{base_url}/{asset_path}"
        print(f"Fetching asset from original site: {asset_url}")
        
        response = requests.get(asset_url, stream=True)
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Asset not found on original site")
            
        # Return the asset with the correct content type
        return StreamingResponse(
            io.BytesIO(response.content), 
            media_type=response.headers.get("content-type", "application/octet-stream")
        )
        
    except Exception as e:
        print(f"Error fetching asset: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching asset: {str(e)}")



async def process_clone_request(request_id: str, url: str, options: Dict):
    """Background task to process a website cloning request"""
    if request_id not in clone_requests:
        return
    
    request_data = clone_requests[request_id]
    
    try:
        # Update status
        request_data["status"] = "scraping"
        # Send status update via WebSocket
        await manager.broadcast_status(request_id, {
            "request_id": request_id,
            "status": "scraping",
            "url": url,
            "message": "Scraping website content..."
        })
        
        # Initialize scraper
        scraper = WebsiteScraper()
        
        # Scrape the website
        scrape_data = await scraper.scrape_website(url)
        
        if "error" in scrape_data:
            request_data["status"] = "failed"
            request_data["result"] = {"error": scrape_data["error"]}
            # Send error status via WebSocket
            await manager.broadcast_status(request_id, {
                "request_id": request_id,
                "status": "failed",
                "error": scrape_data["error"]
            })
            return
        
        # Update status
        request_data["status"] = "cloning"
        # Send status update via WebSocket
        await manager.broadcast_status(request_id, {
            "request_id": request_id,
            "status": "cloning",
            "url": url,
            "message": "Generating clone with AI..."
        })
        
        # Initialize cloner
        cloner = WebsiteCloner()
        
        # Generate clone
        clone_result = await cloner.clone_website(scrape_data)
        
        # Update request data
        if "error" in clone_result:
            request_data["status"] = "failed"
            request_data["result"] = {"error": clone_result["error"]}
            # Send error status via WebSocket
            await manager.broadcast_status(request_id, {
                "request_id": request_id,
                "status": "failed",
                "error": clone_result["error"]
            })
        else:
            request_data["status"] = "completed"
            request_data["result"] = clone_result
            request_data["completed_at"] = datetime.now().isoformat()
            # Send completion status via WebSocket
            await manager.broadcast_status(request_id, {
                "request_id": request_id,
                "status": "completed",
                "url": url
            })
            
    except Exception as e:
        request_data["status"] = "failed"
        request_data["result"] = {"error": str(e)}
        # Send error status via WebSocket
        await manager.broadcast_status(request_id, {
            "request_id": request_id,
            "status": "failed",
            "error": str(e)
        })


@app.websocket("/ws/{request_id}")
async def websocket_endpoint(websocket: WebSocket, request_id: str):
    await manager.connect(websocket, request_id)
    try:
        # Send initial status if request exists
        if request_id in clone_requests:
            status_data = {
                "request_id": request_id,
                "status": clone_requests[request_id]["status"],
                "url": clone_requests[request_id]["url"]
            }
            
            # Add result data if available
            if "result" in clone_requests[request_id]:
                if clone_requests[request_id]["status"] == "failed":
                    status_data["error"] = clone_requests[request_id]["result"].get("error", "Unknown error")
            
            await websocket.send_json(status_data)
        
        # Keep the connection open until client disconnects
        while True:
            # Wait for any message from client (heartbeat)
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, request_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
